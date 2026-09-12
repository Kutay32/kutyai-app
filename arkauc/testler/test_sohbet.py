"""Sohbet uclari, SSE akisi ve konusma sahipligi testleri (spec §7.4)."""

from __future__ import annotations

import json

import httpx
import sqlalchemy as sa

from arkauc.app.api import sohbet as sohbet_ucu
from arkauc.app.servisler.akış import sohbet_akisi
from arkauc.testler.sahte_ust import SahteUst, YavasAkis
from bdm_konusma_gecmisi import konusma_olustur, mesaj_ekle, ust_saglayici_mesajlari
from bdm_listesi import BdmOlustur, bdm_olustur
from bdm_veritabani.modeller import (
    Bdm,
    BdmDurumu,
    KullanimKaydi,
    KullanimDurumu,
    Konusma,
    Mesaj,
    MesajRolu,
    Saglayici,
)
from bdm_veritabani.oturum import oturum_fabrikasi

SOHBET = "/api/v1/sohbet"
AKIS = "/api/v1/sohbet/akis"
KONUSMALAR = "/api/v1/sohbet/konusmalar"
EPOSTA = "ayse.yilmaz@acme.com"


async def bdm_ekle(*, durum: BdmDurumu = BdmDurumu.hazir, ad: str = "Test Model") -> Bdm:
    """Kullanilabilir bir BDM kaydi uretir."""
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_olustur(
            oturum,
            BdmOlustur(
                gorunen_ad=ad,
                saglayici=Saglayici.ollama,
                temel_url="http://sahte.local/v1",
                upstream_model="sahte-model",
            ),
        )
        bdm.durum = durum
        await oturum.commit()
        await oturum.refresh(bdm)
        return bdm


async def kayitlari_oku() -> tuple[list[Mesaj], list[KullanimKaydi], list[Konusma]]:
    async with oturum_fabrikasi()() as oturum:
        mesajlar = list((await oturum.execute(sa.select(Mesaj).order_by(Mesaj.id))).scalars())
        kayitlar = list((await oturum.execute(sa.select(KullanimKaydi))).scalars())
        konusmalar = list((await oturum.execute(sa.select(Konusma).order_by(Konusma.id))).scalars())
    return mesajlar, kayitlar, konusmalar


def olaylari_coz(metin: str) -> list[tuple[str, dict]]:
    """SSE govdesini `(event, data)` ciftlerine ayirir."""
    olaylar: list[tuple[str, dict]] = []
    for blok in metin.split("\n\n"):
        ad: str | None = None
        veri: str | None = None
        for satir in blok.strip().splitlines():
            if satir.startswith("event: "):
                ad = satir[len("event: ") :]
            elif satir.startswith("data: "):
                veri = satir[len("data: ") :]
        if ad:
            olaylar.append((ad, json.loads(veri) if veri else {}))
    return olaylar


def sahte_bagla(uygulama, sahte: SahteUst) -> None:
    uygulama.dependency_overrides[sohbet_ucu.ust_saglayici] = sahte.saglayici


async def test_akis_olay_sirasi(istemci, yardimci, uygulama):
    bdm = await bdm_ekle()
    kullanici = await yardimci.kullanici_ekle()
    sahte = SahteUst()
    sahte_bagla(uygulama, sahte)

    yanit = await istemci.post(
        AKIS,
        json={"bdm_id": bdm.id, "mesaj": "Merhaba"},
        headers=yardimci.basliklar(kullanici),
    )

    assert yanit.status_code == 200
    assert yanit.headers["content-type"].startswith("text/event-stream")
    assert yanit.headers["cache-control"] == "no-cache"
    assert yanit.headers["x-accel-buffering"] == "no"

    olaylar = olaylari_coz(yanit.text)
    adlar = [ad for ad, _ in olaylar]
    assert adlar == ["baslangic", *["parca"] * len(sahte.parcalar), "kullanim", "bitti"]
    assert "".join(veri["icerik"] for ad, veri in olaylar if ad == "parca") == sahte.icerik
    assert olaylar[0][1]["konusma_id"] > 0
    assert olaylar[0][1]["mesaj_id"] > 0
    kullanim = next(veri for ad, veri in olaylar if ad == "kullanim")
    assert kullanim["token_girdi"] == 12
    assert kullanim["token_cikti"] == 7
    assert kullanim["gecikme_ms"] >= 0
    assert olaylar[-1][1] == {}
    assert sahte.son_govde["stream"] is True
    assert sahte.son_govde["messages"] == [{"role": "kullanici", "content": "Merhaba"}]


async def test_mesaj_ve_kullanim_maskelenerek_yazilir(istemci, yardimci, uygulama):
    bdm = await bdm_ekle()
    kullanici = await yardimci.kullanici_ekle()
    sahte = SahteUst()
    sahte_bagla(uygulama, sahte)

    yanit = await istemci.post(
        SOHBET,
        json={"bdm_id": bdm.id, "mesaj": f"Bana {EPOSTA} adresinden yazın"},
        headers=yardimci.basliklar(kullanici),
    )

    assert yanit.status_code == 200
    gonderilen = sahte.son_govde["messages"][-1]["content"]
    assert EPOSTA not in gonderilen
    assert "[MASKELENDI:eposta]" in gonderilen

    mesajlar, kayitlar, _ = await kayitlari_oku()
    assert [mesaj.rol for mesaj in mesajlar] == [MesajRolu.kullanici, MesajRolu.asistan]
    assert EPOSTA not in mesajlar[0].icerik
    assert "[MASKELENDI:eposta]" in mesajlar[0].icerik
    assert mesajlar[1].icerik == sahte.icerik
    assert len(kayitlar) == 1
    assert (kayitlar[0].girdi_token, kayitlar[0].cikti_token) == (12, 7)
    assert kayitlar[0].durum == KullanimDurumu.basarili
    assert kayitlar[0].kullanici_id == kullanici.id


async def test_konusma_basligi_ilk_mesajdan_turetilir(istemci, yardimci, uygulama):
    bdm = await bdm_ekle()
    kullanici = await yardimci.kullanici_ekle()
    sahte_bagla(uygulama, SahteUst())
    basliklar = yardimci.basliklar(kullanici)

    await istemci.post(SOHBET, json={"bdm_id": bdm.id, "mesaj": "Kısa başlık"}, headers=basliklar)
    uzun = "a" * 90
    await istemci.post(SOHBET, json={"bdm_id": bdm.id, "mesaj": uzun}, headers=basliklar)

    _, _, konusmalar = await kayitlari_oku()
    assert [konusma.baslik for konusma in konusmalar] == ["Kısa başlık", "a" * 60 + "…"]


async def test_tek_yanit_ve_konusma_detayi(istemci, yardimci, uygulama):
    bdm = await bdm_ekle()
    kullanici = await yardimci.kullanici_ekle()
    sahte = SahteUst()
    sahte_bagla(uygulama, sahte)
    basliklar = yardimci.basliklar(kullanici)

    yanit = await istemci.post(SOHBET, json={"bdm_id": bdm.id, "mesaj": "Selam"}, headers=basliklar)

    assert yanit.status_code == 200
    govde = yanit.json()
    assert govde["icerik"] == sahte.icerik
    assert (govde["token_girdi"], govde["token_cikti"]) == (12, 7)
    assert govde["gecikme_ms"] >= 0
    assert govde["konusma_id"] > 0 and govde["mesaj_id"] > 0
    assert sahte.son_govde["stream"] is False

    liste = await istemci.get(KONUSMALAR, headers=basliklar)
    assert liste.status_code == 200
    kayit = liste.json()["kayitlar"][0]
    assert set(kayit) == {
        "id",
        "baslik",
        "bdm_id",
        "bdm_ad",
        "guncellenme",
        "mesaj_sayisi",
        "token_girdi",
        "token_cikti",
    }
    assert kayit["mesaj_sayisi"] == 2
    assert kayit["bdm_ad"] == bdm.gorunen_ad
    assert liste.json()["toplam"] == 1

    detay = await istemci.get(f"{KONUSMALAR}/{govde['konusma_id']}", headers=basliklar)
    assert detay.status_code == 200
    assert detay.json()["baslik"] == "Selam"
    assert [mesaj["rol"] for mesaj in detay.json()["mesajlar"]] == ["kullanici", "asistan"]
    assert detay.json()["mesajlar"][1]["icerik"] == sahte.icerik


async def test_baslik_guncellenir_ve_konusma_silinir(istemci, yardimci, uygulama):
    bdm = await bdm_ekle()
    kullanici = await yardimci.kullanici_ekle()
    sahte_bagla(uygulama, SahteUst())
    basliklar = yardimci.basliklar(kullanici)
    konusma_id = (
        await istemci.post(SOHBET, json={"bdm_id": bdm.id, "mesaj": "Sil beni"}, headers=basliklar)
    ).json()["konusma_id"]

    guncel = await istemci.patch(
        f"{KONUSMALAR}/{konusma_id}", json={"baslik": "Yeni başlık"}, headers=basliklar
    )
    assert guncel.status_code == 200
    assert guncel.json() == {"id": konusma_id, "baslik": "Yeni başlık"}

    silindi = await istemci.delete(f"{KONUSMALAR}/{konusma_id}", headers=basliklar)
    assert silindi.status_code == 204
    assert (await istemci.get(f"{KONUSMALAR}/{konusma_id}", headers=basliklar)).status_code == 404


async def test_kimliksiz_401(istemci):
    sohbet_yaniti = await istemci.post(SOHBET, json={"bdm_id": 1, "mesaj": "selam"})
    assert sohbet_yaniti.status_code == 401
    assert sohbet_yaniti.json()["hata"]["kod"] == "kimlik_gerekli"

    akis_yaniti = await istemci.post(AKIS, json={"bdm_id": 1, "mesaj": "selam"})
    assert akis_yaniti.status_code == 401

    liste_yaniti = await istemci.get(KONUSMALAR)
    assert liste_yaniti.status_code == 401
    assert liste_yaniti.json()["hata"]["kod"] == "kimlik_gerekli"


async def test_hazir_olmayan_bdm_503(istemci, yardimci):
    bdm = await bdm_ekle(durum=BdmDurumu.taslak)
    kullanici = await yardimci.kullanici_ekle()

    yanit = await istemci.post(
        SOHBET,
        json={"bdm_id": bdm.id, "mesaj": "selam"},
        headers=yardimci.basliklar(kullanici),
    )

    assert yanit.status_code == 503
    assert yanit.json()["hata"]["kod"] == "bdm_hazir_degil"
    assert yanit.json()["hata"]["ayrinti"]["durum"] == "taslak"


async def test_bilinmeyen_bdm_404(istemci, yardimci):
    kullanici = await yardimci.kullanici_ekle()
    yanit = await istemci.post(
        SOHBET, json={"bdm_id": 9999, "mesaj": "selam"}, headers=yardimci.basliklar(kullanici)
    )
    assert yanit.status_code == 404
    assert yanit.json()["hata"]["kod"] == "bulunamadi"


async def test_upstream_500_502_dondurur(istemci, yardimci, uygulama):
    bdm = await bdm_ekle()
    kullanici = await yardimci.kullanici_ekle()
    sahte_bagla(uygulama, SahteUst(durum=500))
    basliklar = yardimci.basliklar(kullanici)

    tek = await istemci.post(SOHBET, json={"bdm_id": bdm.id, "mesaj": "selam"}, headers=basliklar)
    assert tek.status_code == 502
    assert tek.json()["hata"]["kod"] == "ust_saglayici_hatasi"
    assert tek.json()["hata"]["ayrinti"]["durum"] == 500

    akis = await istemci.post(AKIS, json={"bdm_id": bdm.id, "mesaj": "selam"}, headers=basliklar)
    assert akis.status_code == 200
    olaylar = olaylari_coz(akis.text)
    assert [ad for ad, _ in olaylar] == ["baslangic", "hata"]
    assert olaylar[1][1]["hata"]["kod"] == "ust_saglayici_hatasi"

    _, kayitlar, _ = await kayitlari_oku()
    assert {kayit.durum for kayit in kayitlar} == {KullanimDurumu.hata}
    assert len(kayitlar) == 2


async def test_baskasinin_konusmasi_404(istemci, yardimci, uygulama):
    bdm = await bdm_ekle()
    sahibi = await yardimci.kullanici_ekle()
    yabanci = await yardimci.kullanici_ekle()
    sahte_bagla(uygulama, SahteUst())

    konusma_id = (
        await istemci.post(
            SOHBET,
            json={"bdm_id": bdm.id, "mesaj": "özel"},
            headers=yardimci.basliklar(sahibi),
        )
    ).json()["konusma_id"]

    yabanci_basliklar = yardimci.basliklar(yabanci)
    detay = await istemci.get(f"{KONUSMALAR}/{konusma_id}", headers=yabanci_basliklar)
    assert detay.status_code == 404
    assert detay.json()["hata"]["kod"] == "bulunamadi"
    duzenle = await istemci.patch(
        f"{KONUSMALAR}/{konusma_id}", json={"baslik": "ele geçir"}, headers=yabanci_basliklar
    )
    assert duzenle.status_code == 404
    sil = await istemci.delete(f"{KONUSMALAR}/{konusma_id}", headers=yabanci_basliklar)
    assert sil.status_code == 404
    assert (
        await istemci.get(KONUSMALAR, headers=yabanci_basliklar)
    ).json()["toplam"] == 0
    assert (
        await istemci.get(f"{KONUSMALAR}/{konusma_id}", headers=yardimci.basliklar(sahibi))
    ).status_code == 200


async def test_api_anahtari_yalniz_kendi_konusmalarini_gorur(istemci, yardimci, uygulama):
    bdm = await bdm_ekle()
    anahtar, tam = await yardimci.anahtar_ekle()
    kullanici = await yardimci.kullanici_ekle()
    sahte_bagla(uygulama, SahteUst())
    anahtar_basliklari = yardimci.anahtar_basliklari(tam)

    yanit = await istemci.post(
        SOHBET, json={"bdm_id": bdm.id, "mesaj": "anahtarla"}, headers=anahtar_basliklari
    )
    assert yanit.status_code == 200
    konusma_id = yanit.json()["konusma_id"]

    anahtar_listesi = await istemci.get(KONUSMALAR, headers=anahtar_basliklari)
    assert anahtar_listesi.json()["toplam"] == 1
    assert anahtar_listesi.json()["kayitlar"][0]["id"] == konusma_id

    kullanici_basliklari = yardimci.basliklar(kullanici)
    assert (await istemci.get(KONUSMALAR, headers=kullanici_basliklari)).json()["toplam"] == 0
    assert (
        await istemci.get(f"{KONUSMALAR}/{konusma_id}", headers=kullanici_basliklari)
    ).status_code == 404

    _, kayitlar, _ = await kayitlari_oku()
    assert kayitlar[0].api_anahtari_id == anahtar.id
    assert kayitlar[0].kullanici_id is None


async def test_izinli_olmayan_model_403(istemci, yardimci, uygulama):
    bdm = await bdm_ekle()
    _, tam = await yardimci.anahtar_ekle(izinli_modeller=["baska-model"])
    sahte_bagla(uygulama, SahteUst())

    yanit = await istemci.post(
        SOHBET,
        json={"bdm_id": bdm.id, "mesaj": "selam"},
        headers=yardimci.anahtar_basliklari(tam),
    )

    assert yanit.status_code == 403
    assert yanit.json()["hata"]["kod"] == "yetki_yok"


async def test_konusma_devami_ve_slug_ile_istek(istemci, yardimci, uygulama):
    bdm = await bdm_ekle()
    kullanici = await yardimci.kullanici_ekle()
    sahte = SahteUst(parcalar=("yanıt",))
    sahte_bagla(uygulama, sahte)
    basliklar = yardimci.basliklar(kullanici)

    ilk = await istemci.post(
        SOHBET, json={"bdm_slug": bdm.slug, "mesaj": "ilk"}, headers=basliklar
    )
    assert ilk.status_code == 200

    devam = await istemci.post(
        SOHBET,
        json={"bdm_slug": bdm.slug, "konusma_id": ilk.json()["konusma_id"], "mesaj": "ikinci"},
        headers=basliklar,
    )
    assert devam.status_code == 200
    assert devam.json()["konusma_id"] == ilk.json()["konusma_id"]
    assert sahte.son_govde["messages"] == [
        {"role": "kullanici", "content": "ilk"},
        {"role": "asistan", "content": "yanıt"},
        {"role": "kullanici", "content": "ikinci"},
    ]
    assert sahte.son_govde["model"] == bdm.upstream_model

    farkli = await istemci.post(
        SOHBET,
        json={"bdm_id": bdm.id, "konusma_id": ilk.json()["konusma_id"] + 99, "mesaj": "üçüncü"},
        headers=basliklar,
    )
    assert farkli.status_code == 404


async def test_done_sonrasi_gelen_parca_yok_sayilir(istemci, yardimci, uygulama):
    bdm = await bdm_ekle()
    kullanici = await yardimci.kullanici_ekle()
    kuyruk = 'data: {"choices":[{"index":0,"delta":{"content":"SONRA"}}]}\n\n'
    sahte_bagla(uygulama, SahteUst(parcalar=("tek",), kuyruk=kuyruk))

    yanit = await istemci.post(
        AKIS, json={"bdm_id": bdm.id, "mesaj": "selam"}, headers=yardimci.basliklar(kullanici)
    )

    olaylar = olaylari_coz(yanit.text)
    assert [veri["icerik"] for ad, veri in olaylar if ad == "parca"] == ["tek"]


async def test_azure_api_key_openai_bearer_basliklari():
    from arkauc.app.servisler.upstream import UstSaglayici

    async with oturum_fabrikasi()() as oturum:
        azure = await bdm_olustur(
            oturum,
            BdmOlustur(
                gorunen_ad="Azure Model",
                saglayici=Saglayici.azure,
                temel_url="https://ornek.openai.azure.com",
                upstream_model="gpt-4o-mini",
                api_anahtari="azure-gizli-123",
            ),
        )
        openai = await bdm_olustur(
            oturum,
            BdmOlustur(
                gorunen_ad="OpenAI Model",
                saglayici=Saglayici.openai,
                temel_url="https://api.openai.com/v1",
                upstream_model="gpt-4o-mini",
                api_anahtari="sk-test-123",
            ),
        )
        yerel = await bdm_olustur(
            oturum,
            BdmOlustur(
                gorunen_ad="Yerel Model",
                saglayici=Saglayici.ollama,
                temel_url="http://sahte.local/v1",
                upstream_model="llama3",
            ),
        )
        await oturum.commit()

    sahte = SahteUst(parcalar=("tamam",))
    istemci_ust = sahte.saglayici()
    await istemci_ust.tek_yanit(azure, [{"role": "kullanici", "content": "selam"}])
    assert sahte.son_istek["basliklar"]["api-key"] == "azure-gizli-123"
    assert "authorization" not in sahte.son_istek["basliklar"]
    assert sahte.son_istek["url"] == "https://ornek.openai.azure.com/chat/completions"

    await istemci_ust.tek_yanit(openai, [{"role": "kullanici", "content": "selam"}])
    assert sahte.son_istek["basliklar"]["authorization"] == "Bearer sk-test-123"
    assert "api-key" not in sahte.son_istek["basliklar"]

    await istemci_ust.tek_yanit(yerel, [{"role": "kullanici", "content": "selam"}])
    assert "authorization" not in sahte.son_istek["basliklar"]
    assert "api-key" not in sahte.son_istek["basliklar"]
    assert sahte.son_istek["govde"]["model"] == "llama3"


async def test_tasima_hatasi_502_ve_durum_sifir(istemci, yardimci, uygulama):
    bdm = await bdm_ekle()
    kullanici = await yardimci.kullanici_ekle()
    sahte_bagla(uygulama, SahteUst(hata=httpx.ConnectError("bağlantı kurulamadı")))

    yanit = await istemci.post(
        SOHBET, json={"bdm_id": bdm.id, "mesaj": "selam"}, headers=yardimci.basliklar(kullanici)
    )

    assert yanit.status_code == 502
    assert yanit.json()["hata"]["kod"] == "ust_saglayici_hatasi"
    assert yanit.json()["hata"]["ayrinti"]["durum"] == 0


async def test_istemci_koptugunda_kismi_yanit_kaydedilmez():
    bdm = await bdm_ekle()
    yavas = YavasAkis(("bir", "iki", "üç"), gecikme=0.02)
    sahte = SahteUst(yavas=yavas)

    async with oturum_fabrikasi()() as oturum:
        konusma = await konusma_olustur(oturum, bdm_id=bdm.id)
        kullanici_mesaji = await mesaj_ekle(
            oturum, konusma=konusma, rol=MesajRolu.kullanici, icerik="koptu"
        )
        await oturum.commit()
        mesajlar = await ust_saglayici_mesajlari(oturum, konusma)
        akis = sohbet_akisi(
            oturum,
            ust=sahte.saglayici(),
            bdm=bdm,
            konusma=konusma,
            kullanici_mesaji=kullanici_mesaji,
            mesajlar=mesajlar,
            kullanici_id=None,
            api_anahtari_id=None,
            sicaklik=0.7,
            maks_token=128,
        )
        assert "event: baslangic" in await akis.__anext__()
        assert "event: parca" in await akis.__anext__()
        await akis.aclose()

    mesajlar_db, kayitlar, _ = await kayitlari_oku()
    assert [mesaj.rol for mesaj in mesajlar_db] == [MesajRolu.kullanici]
    assert kayitlar == []
    assert yavas.kapandi is True
