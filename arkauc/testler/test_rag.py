"""RAG / bilgi tabani testleri (spec §5).

Kapsam: parcalama sinirlari, kosinus (sifir vektor dahil), sahte
`/v1/embeddings` ile belge ekleme, arama siralamasi/ust_k/belge filtresi,
yeniden gomme, silme, org izolasyonu ve yetki matrisi.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import httpx
import pytest
import sqlalchemy as sa

from arkauc.app.api import rag as rag_ucu
from arkauc.app.cekirdek.hatalar import RagGommeHatasi
from arkauc.app.servisler import vektor
from arkauc.app.servisler.gomme import gomme_uret
from bdm_listesi import BdmOlustur, bdm_olustur
from bdm_veritabani.modeller import (
    Bdm,
    BdmDurumu,
    BelgeKaynagi,
    Dosya,
    Organizasyon,
    Rol,
    Saglayici,
    UyelikRolu,
    VektorBelgesi,
    VektorParcasi,
)
from bdm_veritabani.oturum import oturum_fabrikasi

BELGELER = "/api/v1/rag/belgeler"
ARA = "/api/v1/rag/ara"

#: Oyuncak gomme sozlugu: skorlar ongorulebilsin diye anahtar sozcuk sayimi.
SOZCUKLER = ("kedi", "kopek", "araba", "elma", "gunes", "yagmur")


def _vektor(metin: str) -> list[float]:
    kucuk = (metin or "").lower()
    vektor_ = [float(kucuk.count(sozcuk)) for sozcuk in SOZCUKLER]
    if not any(vektor_):
        vektor_[0] = 0.001  # sifir vektor uretmemek icin
    return vektor_


class SahteGomme:
    """OpenAI `/embeddings` yanitini taklit eden `httpx.MockTransport`."""

    def __init__(self, *, durum: int = 200) -> None:
        self.durum = durum
        self.istekler: list[dict] = []

    def saglayici(self) -> httpx.MockTransport:
        def isleyici(istek: httpx.Request) -> httpx.Response:
            govde = json.loads(istek.content.decode("utf-8"))
            self.istekler.append(govde)
            if self.durum >= 400:
                return httpx.Response(self.durum, json={"error": {"message": "patladi"}})
            veri = [
                {"index": sira, "embedding": _vektor(metin)}
                for sira, metin in enumerate(govde["input"])
            ]
            return httpx.Response(200, json={"data": veri, "model": govde["model"]})

        return httpx.MockTransport(isleyici)


@dataclass
class Kurulum:
    sahip: object
    org: Organizasyon
    bdm: object
    basliklar: dict[str, str]
    sahte: SahteGomme


async def _bdm_ekle(
    *,
    org_id: int | None = None,
    durum: BdmDurumu = BdmDurumu.hazir,
    gomme_modeli: str = "text-embedding-3-small",
    ad: str = "Test Model",
):
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_olustur(
            oturum,
            BdmOlustur(
                gorunen_ad=ad,
                saglayici=Saglayici.ollama,
                temel_url="http://sahte.local/v1",
                upstream_model="sahte-model",
            ),
            org_id=org_id,
        )
        bdm.durum = durum
        bdm.gomme_modeli = gomme_modeli
        await oturum.commit()
        await oturum.refresh(bdm)
        return bdm


async def _kur(yardimci, uygulama, *, sahte: SahteGomme | None = None, **bdm_kwargs) -> Kurulum:
    sahte = sahte or SahteGomme()
    sahip = await yardimci.kullanici_ekle(rol=Rol.yonetici)
    org = await yardimci.organizasyon("Bilgi Org", sahibi=sahip)
    bdm = await _bdm_ekle(org_id=org.id, **bdm_kwargs)
    uygulama.dependency_overrides[rag_ucu.gomme_tasimasi] = sahte.saglayici
    return Kurulum(sahip, org, bdm, yardimci.org_basliklari(sahip, org), sahte)


async def _ikinci_kurulum(yardimci, uygulama, sahte: SahteGomme, ad: str = "Öteki Org") -> Kurulum:
    """Ayni sahte tasimayi kullanan ikinci organizasyon (izolasyon testleri)."""
    sahip = await yardimci.kullanici_ekle(rol=Rol.yonetici)
    org = await yardimci.organizasyon(ad, sahibi=sahip)
    bdm = await _bdm_ekle(org_id=org.id)
    uygulama.dependency_overrides[rag_ucu.gomme_tasimasi] = sahte.saglayici
    return Kurulum(sahip, org, bdm, yardimci.org_basliklari(sahip, org), sahte)


async def _belge_ekle(istemci, kurulum: Kurulum, ad: str, metin: str, **ek) -> dict:
    govde = {"ad": ad, "bdm_id": kurulum.bdm.id, "metin": metin, **ek}
    yanit = await istemci.post(BELGELER, json=govde, headers=kurulum.basliklar)
    assert yanit.status_code == 201, yanit.text
    return yanit.json()


async def _sayilar() -> tuple[int, int]:
    async with oturum_fabrikasi()() as oturum:
        belge = (
            await oturum.execute(sa.select(sa.func.count()).select_from(VektorBelgesi))
        ).scalar_one()
        parca = (
            await oturum.execute(sa.select(sa.func.count()).select_from(VektorParcasi))
        ).scalar_one()
    return int(belge), int(parca)


async def _parcalari_oku(belge_id: int) -> list[VektorParcasi]:
    async with oturum_fabrikasi()() as oturum:
        return list(
            (
                await oturum.execute(
                    sa.select(VektorParcasi)
                    .where(VektorParcasi.belge_id == belge_id)
                    .order_by(VektorParcasi.sira)
                )
            )
            .scalars()
            .all()
        )


# -- parcalama ---------------------------------------------------------------


def test_parcala_boyut_ortusme_ve_kapsama():
    metin = "ab" * 1000  # 2000 karakter; cumle ve bosluk siniri yok
    parcalar = vektor.parcala(metin)
    assert len(parcalar) == 3
    assert [len(parca) for parca in parcalar] == [800, 800, 640]
    assert parcalar[0] + "".join(parca[120:] for parca in parcalar[1:]) == metin
    for onceki, sonraki in zip(parcalar, parcalar[1:]):
        assert sonraki[:120] == onceki[-120:]


def test_parcala_cumle_sinirina_saygi():
    parcalar = vektor.parcala("Cümle bir. " * 200)
    assert len(parcalar) > 2
    assert all(parca.endswith(".") for parca in parcalar)
    assert all(len(parca) <= 800 for parca in parcalar)
    assert all(len(parca) >= 50 for parca in parcalar)


def test_parcala_kisa_ve_bos_metin():
    assert vektor.parcala("") == []
    assert vektor.parcala("   \n  ") == []
    kisa = "Tek cumle." * 4
    assert len(kisa) < 50
    assert vektor.parcala(kisa) == [kisa]


def test_parcala_kuyruk_parcasi_birlestirilir():
    # Ilk satir cok kisa, ardindan uzun bir bosluk blogu: min parcadan kisa
    # parca uretilmez.
    parcalar = vektor.parcala("kisa\n" + "\n" * 2000, boyut=800)
    assert parcalar == ["kisa"]


def test_kosinus_sifir_vektor_sifir_doner():
    assert vektor.kosinus([0.0, 0.0, 0.0], [1.0, 2.0, 3.0]) == 0.0
    assert vektor.kosinus([1.0, 2.0], [0.0, 0.0]) == 0.0
    assert vektor.kosinus([], []) == 0.0
    assert vektor.kosinus([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert vektor.kosinus([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_kosinus_farkli_uzunluk_hata():
    with pytest.raises(ValueError):
        vektor.kosinus([1.0, 2.0], [1.0])


# -- gomme -------------------------------------------------------------------


async def test_gomme_uret_batch_32_ve_sira():
    sahte = SahteGomme()
    bdm = await _bdm_ekle()
    metinler = [f"metin {sira}" for sira in range(70)]
    vektorler = await gomme_uret(bdm, metinler, tasima=sahte.saglayici())
    assert len(vektorler) == 70
    assert [len(istek["input"]) for istek in sahte.istekler] == [32, 32, 6]
    assert sahte.istekler[0]["model"] == "text-embedding-3-small"
    assert vektorler[-1] == _vektor("metin 69")


async def test_gomme_uret_hata_ve_bos_model():
    sahte = SahteGomme(durum=500)
    bdm = await _bdm_ekle()
    with pytest.raises(RagGommeHatasi):
        await gomme_uret(bdm, ["kedi"], tasima=sahte.saglayici())

    bos = await _bdm_ekle(gomme_modeli="")
    with pytest.raises(RagGommeHatasi) as hata:
        await gomme_uret(bos, ["kedi"], tasima=SahteGomme().saglayici())
    assert hata.value.kod == "gomme_modeli_yok"


async def test_gomme_uret_bos_liste_istek_atmaz():
    sahte = SahteGomme()
    bdm = await _bdm_ekle()
    assert await gomme_uret(bdm, [], tasima=sahte.saglayici()) == []
    assert sahte.istekler == []


# -- belge ekleme / arama ----------------------------------------------------


async def test_belge_ekle_parcalar_ve_arama_sirasi(istemci, yardimci, uygulama):
    kurulum = await _kur(yardimci, uygulama)
    kedi = await _belge_ekle(istemci, kurulum, "Kedi", "kedi kedi kedi", meta={"kaynak": "test"})
    ikisi = await _belge_ekle(istemci, kurulum, "Kedi Kopek", "kedi kopek")
    araba = await _belge_ekle(istemci, kurulum, "Araba", "araba")

    assert kedi["kaynak"] == "metin"
    assert kedi["meta"] == {"kaynak": "test"}
    assert kedi["parca_sayisi"] == 1
    assert len(kurulum.sahte.istekler) == 3

    yanit = await istemci.post(ARA, json={"sorgu": "kedi"}, headers=kurulum.basliklar)
    assert yanit.status_code == 200, yanit.text
    govde = yanit.json()
    assert govde["ayrinti"]["yol"] == "python"
    assert govde["ayrinti"]["ust_k"] == 4
    sonuclar = govde["sonuclar"]
    assert [sonuc["belge_id"] for sonuc in sonuclar] == [kedi["id"], ikisi["id"], araba["id"]]
    skorlar = [sonuc["skor"] for sonuc in sonuclar]
    assert skorlar == sorted(skorlar, reverse=True)
    assert skorlar[0] == pytest.approx(1.0)
    assert skorlar[-1] == pytest.approx(0.0)
    assert sonuclar[0]["belge_ad"] == "Kedi"
    assert sonuclar[0]["sira"] == 0
    assert sonuclar[0]["icerik"] == "kedi kedi kedi"


async def test_arama_ust_k_ve_belge_filtresi(istemci, yardimci, uygulama):
    kurulum = await _kur(yardimci, uygulama)
    belgeler = [
        await _belge_ekle(
            istemci,
            kurulum,
            f"Belge {sira}",
            "kedi " * (sira + 1) + "kopek " * (5 - sira),
        )
        for sira in range(6)
    ]

    yanit = await istemci.post(ARA, json={"sorgu": "kedi"}, headers=kurulum.basliklar)
    assert len(yanit.json()["sonuclar"]) == 4  # ayarlar.rag_ust_k

    tek = await istemci.post(
        ARA, json={"sorgu": "kedi", "ust_k": 1}, headers=kurulum.basliklar
    )
    govde = tek.json()
    assert [sonuc["belge_id"] for sonuc in govde["sonuclar"]] == [belgeler[-1]["id"]]
    assert govde["ayrinti"]["ust_k"] == 1

    hedef = belgeler[1]["id"]
    filtreli = await istemci.post(
        ARA,
        json={"sorgu": "kedi", "belge_idleri": [hedef], "ust_k": 10},
        headers=kurulum.basliklar,
    )
    assert [sonuc["belge_id"] for sonuc in filtreli.json()["sonuclar"]] == [hedef]

    bos = await istemci.post(
        ARA, json={"sorgu": "kedi", "belge_idleri": []}, headers=kurulum.basliklar
    )
    assert bos.json()["sonuclar"] == []


async def test_belge_detayi_parcalari_dondurur(istemci, yardimci, uygulama):
    kurulum = await _kur(yardimci, uygulama)
    uzun = " ".join(f"cumle {sira} kedi." for sira in range(300))
    belge = await _belge_ekle(istemci, kurulum, "Uzun Belge", uzun)
    assert belge["parca_sayisi"] > 1

    yanit = await istemci.get(f"{BELGELER}/{belge['id']}", headers=kurulum.basliklar)
    assert yanit.status_code == 200
    govde = yanit.json()
    assert [parca["sira"] for parca in govde["parcalar"]] == list(range(belge["parca_sayisi"]))
    assert all(parca["icerik"] for parca in govde["parcalar"])
    assert govde["parca_sayisi"] == len(govde["parcalar"])


async def test_dosya_id_ile_belge_ekleme(istemci, yardimci, uygulama, tmp_path):
    kurulum = await _kur(yardimci, uygulama)
    yol = Path(tmp_path) / "bilgi.txt"
    yol.write_text("kedi kopek elma", encoding="utf-8")
    async with oturum_fabrikasi()() as oturum:
        dosya = Dosya(
            org_id=kurulum.org.id,
            kullanici_id=kurulum.sahip.id,
            ad="bilgi.txt",
            mime="text/plain",
            boyut=yol.stat().st_size,
            sha256="",
            yol=str(yol),
            metin="",
        )
        oturum.add(dosya)
        await oturum.commit()
        await oturum.refresh(dosya)
        dosya_id = dosya.id

    yanit = await istemci.post(
        BELGELER,
        json={"ad": "Dosyadan", "bdm_id": kurulum.bdm.id, "dosya_id": dosya_id},
        headers=kurulum.basliklar,
    )
    assert yanit.status_code == 201, yanit.text
    govde = yanit.json()
    assert govde["kaynak"] == "dosya"
    assert govde["dosya_id"] == dosya_id


async def test_yeniden_gom_vektorleri_tazeler(istemci, yardimci, uygulama):
    kurulum = await _kur(yardimci, uygulama)
    belge = await _belge_ekle(istemci, kurulum, "Belge", "kedi kedi")
    kurulum.sahte.istekler.clear()
    async with oturum_fabrikasi()() as oturum:
        bdm = await oturum.get(Bdm, kurulum.bdm.id)
        bdm.gomme_modeli = "yeni-gomme-modeli"
        await oturum.commit()

    yanit = await istemci.post(
        f"{BELGELER}/{belge['id']}/yeniden-gom",
        json={"bdm_id": kurulum.bdm.id},
        headers=kurulum.basliklar,
    )
    assert yanit.status_code == 200, yanit.text
    assert kurulum.sahte.istekler[0]["model"] == "yeni-gomme-modeli"
    assert yanit.json()["parca_sayisi"] == belge["parca_sayisi"]

    parcalar = await _parcalari_oku(belge["id"])
    assert [parca.sira for parca in parcalar] == list(range(belge["parca_sayisi"]))
    assert parcalar[0].vektor == _vektor("kedi kedi")


async def test_belge_silme(istemci, yardimci, uygulama):
    kurulum = await _kur(yardimci, uygulama)
    belge = await _belge_ekle(istemci, kurulum, "Silinecek", "kedi kopek")
    assert await _sayilar() == (1, 1)

    yanit = await istemci.delete(f"{BELGELER}/{belge['id']}", headers=kurulum.basliklar)
    assert yanit.status_code == 204
    assert await _sayilar() == (0, 0)

    detay = await istemci.get(f"{BELGELER}/{belge['id']}", headers=kurulum.basliklar)
    assert detay.status_code == 404
    assert detay.json()["hata"]["kod"] == "belge_bulunamadi"

    arama = await istemci.post(ARA, json={"sorgu": "kedi"}, headers=kurulum.basliklar)
    assert arama.json()["sonuclar"] == []


async def test_belge_listesi_yalniz_kendi_org(istemci, yardimci, uygulama):
    kurulum = await _kur(yardimci, uygulama)
    await _belge_ekle(istemci, kurulum, "Benim", "kedi")
    digeri = await _ikinci_kurulum(yardimci, uygulama, kurulum.sahte)
    await _belge_ekle(istemci, digeri, "Ötekinin", "kopek")

    benim = await istemci.get(BELGELER, headers=kurulum.basliklar)
    adlar = [kayit["ad"] for kayit in benim.json()]
    assert adlar == ["Benim"]

    oteki = await istemci.get(BELGELER, headers=digeri.basliklar)
    assert [kayit["ad"] for kayit in oteki.json()] == ["Ötekinin"]


# -- org izolasyonu ----------------------------------------------------------


async def test_org_izolasyonu_404_ve_bos_arama(istemci, yardimci, uygulama):
    a = await _kur(yardimci, uygulama)
    belge = await _belge_ekle(istemci, a, "A Belgesi", "kedi kedi")
    b = await _ikinci_kurulum(yardimci, uygulama, a.sahte)

    assert (
        await istemci.get(f"{BELGELER}/{belge['id']}", headers=b.basliklar)
    ).status_code == 404
    assert (
        await istemci.delete(f"{BELGELER}/{belge['id']}", headers=b.basliklar)
    ).status_code == 404
    assert (
        await istemci.post(
            f"{BELGELER}/{belge['id']}/yeniden-gom", json={}, headers=b.basliklar
        )
    ).status_code == 404

    arama = await istemci.post(ARA, json={"sorgu": "kedi"}, headers=b.basliklar)
    assert arama.json()["sonuclar"] == []
    filtreli = await istemci.post(
        ARA, json={"sorgu": "kedi", "belge_idleri": [belge["id"]]}, headers=b.basliklar
    )
    assert filtreli.json()["sonuclar"] == []

    # A organizasyonunun belgesi hala yerinde.
    assert (await istemci.get(f"{BELGELER}/{belge['id']}", headers=a.basliklar)).status_code == 200
    assert await _sayilar() == (1, 1)


async def test_baska_org_bdm_ile_belge_eklenemez(istemci, yardimci, uygulama):
    a = await _kur(yardimci, uygulama)
    b = await _ikinci_kurulum(yardimci, uygulama, a.sahte)
    yanit = await istemci.post(
        BELGELER,
        json={"ad": "Sizinti", "bdm_id": a.bdm.id, "metin": "kedi"},
        headers=b.basliklar,
    )
    assert yanit.status_code == 404
    assert await _sayilar() == (0, 0)


# -- yetki matrisi -----------------------------------------------------------


async def test_yetki_matrisi(istemci, yardimci, uygulama):
    kurulum = await _kur(yardimci, uygulama)
    belge = await _belge_ekle(istemci, kurulum, "Belge", "kedi")

    izleyici = await yardimci.kullanici_ekle()
    await yardimci.uye_yap(kurulum.org, izleyici, UyelikRolu.izleyici)
    izleyici_basliklari = yardimci.org_basliklari(izleyici, kurulum.org)

    son_kullanici = await yardimci.kullanici_ekle()
    await yardimci.uye_yap(kurulum.org, son_kullanici, UyelikRolu.son_kullanici)
    son_kullanici_basliklari = yardimci.org_basliklari(son_kullanici, kurulum.org)

    assert (await istemci.get(BELGELER, headers=izleyici_basliklari)).status_code == 200
    assert (
        await istemci.post(ARA, json={"sorgu": "kedi"}, headers=izleyici_basliklari)
    ).status_code == 200
    yazma = await istemci.post(
        BELGELER,
        json={"ad": "Izleyici", "bdm_id": kurulum.bdm.id, "metin": "kedi"},
        headers=izleyici_basliklari,
    )
    assert yazma.status_code == 403
    assert (
        await istemci.delete(f"{BELGELER}/{belge['id']}", headers=izleyici_basliklari)
    ).status_code == 403
    assert (
        await istemci.post(
            f"{BELGELER}/{belge['id']}/yeniden-gom",
            json={"bdm_id": kurulum.bdm.id},
            headers=izleyici_basliklari,
        )
    ).status_code == 403

    for yol, yontem, govde in (
        (BELGELER, "get", None),
        (BELGELER, "post", {"ad": "x", "bdm_id": kurulum.bdm.id, "metin": "kedi"}),
        (ARA, "post", {"sorgu": "kedi"}),
    ):
        cagri = getattr(istemci, yontem)
        yanit = await (
            cagri(yol, headers=son_kullanici_basliklari)
            if govde is None
            else cagri(yol, json=govde, headers=son_kullanici_basliklari)
        )
        assert yanit.status_code == 403, yanit.text


# -- dogrulama ve hata yollari -----------------------------------------------


async def test_kaynak_ve_metin_dogrulamasi(istemci, yardimci, uygulama):
    kurulum = await _kur(yardimci, uygulama)
    bos = await istemci.post(
        BELGELER, json={"ad": "Kaynaksiz", "bdm_id": kurulum.bdm.id}, headers=kurulum.basliklar
    )
    assert bos.status_code == 400
    assert bos.json()["hata"]["ayrinti"]["alanlar"] == ["metin", "dosya_id"]

    sadece_bosluk = await istemci.post(
        BELGELER,
        json={"ad": "Bos", "bdm_id": kurulum.bdm.id, "metin": "   "},
        headers=kurulum.basliklar,
    )
    assert sadece_bosluk.status_code == 400
    assert sadece_bosluk.json()["hata"]["kod"] == "belge_kaynak_gerekli"
    assert "metin veya dosya_id" in sadece_bosluk.json()["hata"]["mesaj"]

    ingilizce = await istemci.post(
        BELGELER,
        json={"ad": "Bos", "bdm_id": kurulum.bdm.id, "metin": "   "},
        headers={**kurulum.basliklar, "Accept-Language": "en"},
    )
    assert ingilizce.json()["hata"]["mesaj"] == "Provide either text or a file_id for the document."
    assert await _sayilar() == (0, 0)


async def test_bdm_hazir_degil_503(istemci, yardimci, uygulama):
    kurulum = await _kur(yardimci, uygulama, durum=BdmDurumu.taslak)
    yanit = await istemci.post(
        BELGELER,
        json={"ad": "Belge", "bdm_id": kurulum.bdm.id, "metin": "kedi"},
        headers=kurulum.basliklar,
    )
    assert yanit.status_code == 503
    assert yanit.json()["hata"]["kod"] == "bdm_hazir_degil"
    assert await _sayilar() == (0, 0)


async def test_gomme_modeli_yok_400(istemci, yardimci, uygulama):
    kurulum = await _kur(yardimci, uygulama, gomme_modeli="")
    yanit = await istemci.post(
        BELGELER,
        json={"ad": "Belge", "bdm_id": kurulum.bdm.id, "metin": "kedi"},
        headers=kurulum.basliklar,
    )
    assert yanit.status_code == 400
    assert yanit.json()["hata"]["kod"] == "gomme_modeli_yok"


async def test_gomme_saglayici_hatasi_502(istemci, yardimci, uygulama):
    kurulum = await _kur(yardimci, uygulama, sahte=SahteGomme(durum=502))
    yanit = await istemci.post(
        BELGELER,
        json={"ad": "Belge", "bdm_id": kurulum.bdm.id, "metin": "kedi"},
        headers=kurulum.basliklar,
    )
    assert yanit.status_code == 502
    assert yanit.json()["hata"]["kod"] == "rag_gomme_hatasi"
    assert await _sayilar() == (0, 0)


async def test_pgvector_yoksa_python_yolu(istemci, yardimci, uygulama):
    kurulum = await _kur(yardimci, uygulama)
    await _belge_ekle(istemci, kurulum, "Belge", "kedi")
    async with oturum_fabrikasi()() as oturum:
        assert await vektor.arama_yolu(oturum) == "python"


async def test_parcalari_yaz_ikinci_cagride_cogaltmaz(yardimci, uygulama):
    kurulum = await _kur(yardimci, uygulama)
    async with oturum_fabrikasi()() as oturum:
        belge = await vektor.belge_olustur(
            oturum,
            org_id=kurulum.org.id,
            ad="Elle",
            kaynak=BelgeKaynagi.metin,
            dosya_id=None,
            meta=None,
        )
        yazilan = await vektor.parcalari_yaz(
            oturum,
            org_id=kurulum.org.id,
            belge_id=belge.id,
            parcalar=["kedi", "kopek"],
            vektorler=[_vektor("kedi"), _vektor("kopek")],
        )
        assert yazilan == 2
        await vektor.parcalari_yaz(
            oturum,
            org_id=kurulum.org.id,
            belge_id=belge.id,
            parcalar=["elma"],
            vektorler=[_vektor("elma")],
        )
        await oturum.commit()
        belge_id = belge.id

    parcalar = await _parcalari_oku(belge_id)
    assert [(parca.sira, parca.icerik) for parca in parcalar] == [(0, "elma")]


async def test_bdm_id_zorunlu(istemci, yardimci, uygulama):
    kurulum = await _kur(yardimci, uygulama)
    yanit = await istemci.post(
        BELGELER, json={"ad": "Bdmsiz", "metin": "kedi"}, headers=kurulum.basliklar
    )
    assert yanit.status_code == 400
    assert yanit.json()["hata"]["kod"] == "dogrulama_hatasi"


async def test_baska_org_dosyasi_referans_edilemez(istemci, yardimci, uygulama, tmp_path):
    a = await _kur(yardimci, uygulama)
    b = await _ikinci_kurulum(yardimci, uygulama, a.sahte)
    yol = Path(tmp_path) / "gizli.txt"
    yol.write_text("kedi", encoding="utf-8")
    async with oturum_fabrikasi()() as oturum:
        dosya = Dosya(
            org_id=a.org.id,
            kullanici_id=a.sahip.id,
            ad="gizli.txt",
            mime="text/plain",
            boyut=4,
            sha256="",
            yol=str(yol),
            metin="",
        )
        oturum.add(dosya)
        await oturum.commit()
        await oturum.refresh(dosya)
        dosya_id = dosya.id

    yanit = await istemci.post(
        BELGELER,
        json={"ad": "Sizinti", "bdm_id": b.bdm.id, "dosya_id": dosya_id},
        headers=b.basliklar,
    )
    assert yanit.status_code == 404
    assert await _sayilar() == (0, 0)


async def test_eksik_gomme_yaniti_hata():
    bdm = await _bdm_ekle()

    def isleyici(istek: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [{"index": 0, "embedding": [1.0, 0.0]}]})

    with pytest.raises(RagGommeHatasi) as eksik:
        await gomme_uret(bdm, ["kedi", "kopek"], tasima=httpx.MockTransport(isleyici))
    assert eksik.value.kod == "rag_gomme_hatasi"
    assert eksik.value.ayrinti["neden"] == "gecersiz_vektor"

    def bozuk(istek: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"<html>degil json</html>")

    with pytest.raises(RagGommeHatasi) as bozuk_hata:
        await gomme_uret(bdm, ["kedi"], tasima=httpx.MockTransport(bozuk))
    assert bozuk_hata.value.ayrinti["neden"] == "gecersiz_json"
