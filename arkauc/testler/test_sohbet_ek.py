"""Sohbet ucunun Dalga 1 yetenekleri: dosya bagi, RAG ve arac cagirma (spec §3-§5).

Dalga 1'in diger modulleri (dosya, gomme, vektor, arac) paralel yazildigi icin
testler gercek modullere degil, `sohbet.py`/`akis.py` icindeki modul
referanslarina enjekte edilen sahte uygulamalara dayanir. Sahteler ilgili
modullerin dondurulmus sozlesmesini (donus sekli, 404 davranisi) uygular.
"""

from __future__ import annotations

import json

import pytest
import sqlalchemy as sa

from arkauc.app.api import sohbet as sohbet_ucu
from arkauc.app.cekirdek.ayarlar import ayarlar
from arkauc.app.cekirdek.hatalar import Bulunamadi
from arkauc.app.servisler import akış as akis_modulu
from bdm_listesi import BdmOlustur, bdm_olustur
from bdm_veritabani.modeller import (
    Arac,
    AracCagrisi,
    AracCagrisiDurumu,
    AracTuru,
    Bdm,
    BdmDurumu,
    Dosya,
    Kota,
    KotaKapsami,
    Mesaj,
    MesajRolu,
    Organizasyon,
    Saglayici,
    VektorBelgesi,
)
from bdm_veritabani.oturum import oturum_fabrikasi

SOHBET = "/api/v1/sohbet"
AKIS = "/api/v1/sohbet/akis"
VARSAYILAN_YETENEKLER = {"akis": True, "gorsel": False, "arac": False, "ses": False}


async def bdm_ekle(org: Organizasyon, *, yetenekler: dict | None = None) -> Bdm:
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_olustur(
            oturum,
            BdmOlustur(
                gorunen_ad="Ek Model",
                saglayici=Saglayici.ollama,
                temel_url="http://sahte.local/v1",
                upstream_model="sahte-model",
            ),
            org_id=org.id,
        )
        bdm.durum = BdmDurumu.hazir
        bdm.yetenekler = dict(yetenekler or VARSAYILAN_YETENEKLER)
        await oturum.commit()
        await oturum.refresh(bdm)
        return bdm


async def dosya_ekle(org: Organizasyon, ad: str, metin: str) -> Dosya:
    async with oturum_fabrikasi()() as oturum:
        dosya = Dosya(
            org_id=org.id, ad=ad, mime="text/plain", boyut=len(metin.encode()), metin=metin
        )
        oturum.add(dosya)
        await oturum.commit()
        await oturum.refresh(dosya)
        return dosya


async def belge_ekle(org: Organizasyon, ad: str = "El Kitabı") -> VektorBelgesi:
    async with oturum_fabrikasi()() as oturum:
        belge = VektorBelgesi(org_id=org.id, ad=ad, parca_sayisi=1)
        oturum.add(belge)
        await oturum.commit()
        await oturum.refresh(belge)
        return belge


async def arac_ekle(org: Organizasyon, slug: str = "hesap_makinesi") -> Arac:
    async with oturum_fabrikasi()() as oturum:
        arac = Arac(
            org_id=org.id,
            ad="Hesap Makinesi",
            slug=slug,
            aciklama="Basit ifade değerlendirir",
            json_sema={"type": "object", "properties": {"ifade": {"type": "string"}}},
            tur=AracTuru.yerlesik,
            etkin=True,
        )
        oturum.add(arac)
        await oturum.commit()
        await oturum.refresh(arac)
        return arac


async def kota_ekle(org: Organizasyon, **alanlar: int) -> Kota:
    async with oturum_fabrikasi()() as oturum:
        kayit = Kota(kapsam=KotaKapsami.organizasyon, kapsam_id=org.id, **alanlar)
        oturum.add(kayit)
        await oturum.commit()
        await oturum.refresh(kayit)
        return kayit


async def mesajlari_oku() -> list[Mesaj]:
    async with oturum_fabrikasi()() as oturum:
        return list(
            (await oturum.execute(sa.select(Mesaj).order_by(Mesaj.id))).scalars()
        )


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


class SahteSaglayici:
    """Tur tur yanit ureten sahte upstream; gonderilen istekleri kaydeder."""

    def __init__(
        self,
        *,
        cevaplar: list[dict] | None = None,
        parcalar: tuple[str, ...] = ("yanit",),
        tekrar_arac: dict | None = None,
        kullanim: tuple[int, int] = (10, 5),
    ) -> None:
        self.cevaplar = list(cevaplar or [])
        self.parcalar = tuple(parcalar)
        self.tekrar_arac = tekrar_arac
        self.kullanim = {"girdi": kullanim[0], "cikti": kullanim[1]}
        self.istekler: list[dict] = []

    def _siradaki(self) -> dict:
        if self.cevaplar:
            return self.cevaplar.pop(0)
        if self.tekrar_arac is not None:
            return {"icerik": "", "arac_cagrilari": [self.tekrar_arac]}
        return {"icerik": "".join(self.parcalar), "arac_cagrilari": []}

    async def tek_yanit(self, bdm, mesajlar, *, sicaklik=None, maks_token=None, araclar=None):
        self.istekler.append({"mesajlar": mesajlar, "araclar": araclar})
        cevap = self._siradaki()
        return {
            "icerik": cevap.get("icerik", ""),
            "kullanim": dict(self.kullanim),
            "arac_cagrilari": cevap.get("arac_cagrilari", []),
        }

    async def akis_uret(self, bdm, mesajlar, *, sicaklik=None, maks_token=None, araclar=None):
        self.istekler.append({"mesajlar": mesajlar, "araclar": araclar})
        cevap = self._siradaki()
        cagrilar = cevap.get("arac_cagrilari", [])
        parcalar = cevap.get("parcalar")
        if parcalar is None:
            parcalar = () if cagrilar else self.parcalar
        for parca in parcalar:
            yield {"parca": parca}
        yield {"kullanim": dict(self.kullanim)}
        if cagrilar:
            yield {"arac_cagrilari": cagrilar}


def saglayici_bagla(uygulama, sahte: SahteSaglayici) -> None:
    uygulama.dependency_overrides[sohbet_ucu.ust_saglayici] = lambda: sahte


@pytest.fixture
def sahte_dosya(monkeypatch):
    """`dosya.baglam_metni` sozlesmesini uygulayan sahte (org disi -> 404)."""
    kayit: list[dict] = []

    async def baglam(oturum, org_id, dosya_idleri, *, sinir):
        kayit.append({"org_id": org_id, "dosya_idleri": list(dosya_idleri), "sinir": sinir})
        satirlar = list(
            (
                await oturum.execute(
                    sa.select(Dosya)
                    .where(Dosya.org_id == org_id, Dosya.id.in_(dosya_idleri))
                    .order_by(Dosya.id)
                )
            ).scalars()
        )
        bulunan = {dosya.id for dosya in satirlar}
        eksik = [dosya_id for dosya_id in dosya_idleri if dosya_id not in bulunan]
        if eksik:
            raise Bulunamadi("Dosya bulunamadı.", {"dosya_idleri": eksik})
        metin = "\n".join(
            f"--- {dosya.ad} ---\n{dosya.metin}" for dosya in satirlar if dosya.metin
        )
        return metin[:sinir]

    monkeypatch.setattr(sohbet_ucu, "baglam_metni", baglam)
    return kayit


@pytest.fixture
def sahte_rag(monkeypatch):
    """`gomme_uret` / `vektor_ara` sozlesmesini uygulayan sahte."""
    kayit: dict[str, list] = {"gomme": [], "arama": []}

    async def gomme(bdm, metinler, *, tasima=None):
        kayit["gomme"].append(list(metinler))
        return [[0.1, 0.2, 0.3]]

    async def ara(oturum, *, org_id, sorgu_vektoru, ust_k=4, belge_idleri=None):
        kayit["arama"].append(
            {
                "org_id": org_id,
                "ust_k": ust_k,
                "belge_idleri": belge_idleri,
                "vektor": list(sorgu_vektoru),
            }
        )
        return [
            {
                "belge_id": 7,
                "belge_ad": "El Kitabı",
                "sira": 2,
                "icerik": "İade süresi 14 gündür.",
                "skor": 0.87654,
            }
        ]

    monkeypatch.setattr(sohbet_ucu, "gomme_uret", gomme)
    monkeypatch.setattr(sohbet_ucu, "vektor_ara", ara)
    return kayit


@pytest.fixture
def sahte_arac(monkeypatch):
    """`arac.araclari_getir`/`arac_bul`/`arac_calistir` sozlesmesini uygular."""
    kayit: dict[str, list] = {"arama": [], "calistirmalar": []}

    async def araclari_getir(oturum, org_id, idler=None):
        sorgu = (
            sa.select(Arac)
            .where(Arac.org_id == org_id, Arac.etkin.is_(True))
            .order_by(Arac.id)
        )
        if idler is not None:
            sorgu = sorgu.where(Arac.id.in_(idler))
        return list((await oturum.execute(sorgu)).scalars())

    async def arac_bul(oturum, org_id, anahtar):
        kayit["arama"].append(anahtar)
        sorgu = sa.select(Arac).where(Arac.org_id == org_id)
        sorgu = (
            sorgu.where(Arac.id == int(anahtar))
            if str(anahtar).isdigit()
            else sorgu.where(Arac.slug == anahtar)
        )
        arac = (await oturum.execute(sorgu)).scalar_one_or_none()
        if arac is None:
            raise Bulunamadi("Araç bulunamadı.", {"arac": anahtar})
        return arac

    async def calistir(oturum, *, org_id, arac, argumanlar, konusma_id=None, mesaj_id=None):
        kayit["calistirmalar"].append(
            {
                "slug": arac.slug,
                "argumanlar": argumanlar,
                "org_id": org_id,
                "konusma_id": konusma_id,
                "mesaj_id": mesaj_id,
            }
        )
        return {
            "durum": "basarili",
            "sonuc": {"sonuc": 4},
            "hata": None,
            "gecikme_ms": 3,
        }

    def tanim(arac):
        return {
            "type": "function",
            "function": {
                "name": arac.slug,
                "description": arac.aciklama,
                "parameters": arac.json_sema,
            },
        }

    monkeypatch.setattr(sohbet_ucu, "araclari_getir", araclari_getir)
    monkeypatch.setattr(sohbet_ucu, "arac_bul", arac_bul)
    monkeypatch.setattr(akis_modulu, "arac_calistir", calistir)
    monkeypatch.setattr(akis_modulu, "arac_tanimi", tanim)
    return kayit


def arac_cagrisi(ifade: str = "2+2", cagri_id: str = "cagri_1") -> dict:
    return {"id": cagri_id, "ad": "hesap_makinesi", "argumanlar": {"ifade": ifade}}


# --------------------------------------------------------------------------
# Dosya bağlamı
# --------------------------------------------------------------------------


async def test_dosya_metni_sistem_isteminin_sonuna_eklenir(
    istemci, yardimci, uygulama, sahte_dosya
):
    kullanici = await yardimci.kullanici_ekle()
    org = await yardimci.organizasyon(sahibi=kullanici)
    bdm = await bdm_ekle(org)
    dosya = await dosya_ekle(org, "rapor.txt", "İade süresi 14 gündür.")
    sahte = SahteSaglayici()
    saglayici_bagla(uygulama, sahte)

    yanit = await istemci.post(
        SOHBET,
        json={
            "bdm_id": bdm.id,
            "mesaj": "Raporu özetle",
            "sistem_istemi": "Temel istem",
            "dosya_idleri": [dosya.id],
        },
        headers=yardimci.org_basliklari(kullanici, org),
    )

    assert yanit.status_code == 200
    sistem = sahte.istekler[0]["mesajlar"][0]
    assert sistem["role"] == "system"
    assert sistem["content"].startswith("Temel istem")
    assert "\n\n--- Ekli dosyalar ---\n" in sistem["content"]
    assert "--- rapor.txt ---\nİade süresi 14 gündür." in sistem["content"]
    assert sahte_dosya[0]["org_id"] == org.id
    assert sahte_dosya[0]["sinir"] == ayarlar.dosya_baglam_kr


async def test_org_disi_dosya_404_ve_mesaj_yazilmaz(istemci, yardimci, uygulama, sahte_dosya):
    kullanici = await yardimci.kullanici_ekle()
    org = await yardimci.organizasyon(sahibi=kullanici)
    yabanci = await yardimci.organizasyon(ad="Yabancı Org")
    bdm = await bdm_ekle(org)
    gizli = await dosya_ekle(yabanci, "gizli.txt", "başka organizasyonun dosyası")
    saglayici_bagla(uygulama, SahteSaglayici())

    yanit = await istemci.post(
        SOHBET,
        json={"bdm_id": bdm.id, "mesaj": "oku", "dosya_idleri": [gizli.id]},
        headers=yardimci.org_basliklari(kullanici, org),
    )

    assert yanit.status_code == 404
    assert yanit.json()["hata"]["kod"] == "bulunamadi"
    assert await mesajlari_oku() == []


# --------------------------------------------------------------------------
# RAG
# --------------------------------------------------------------------------


async def test_rag_parcalari_sistem_istemine_eklenir_ve_kaynaklar_doner(
    istemci, yardimci, uygulama, sahte_rag
):
    kullanici = await yardimci.kullanici_ekle()
    org = await yardimci.organizasyon(sahibi=kullanici)
    bdm = await bdm_ekle(org)
    sahte = SahteSaglayici()
    saglayici_bagla(uygulama, sahte)

    yanit = await istemci.post(
        SOHBET,
        json={"bdm_id": bdm.id, "mesaj": "İade süresi nedir?", "rag": True},
        headers=yardimci.org_basliklari(kullanici, org),
    )

    assert yanit.status_code == 200
    assert yanit.json()["kaynaklar"] == [
        {"belge_id": 7, "belge_ad": "El Kitabı", "sira": 2, "skor": 0.8765}
    ]
    sistem = sahte.istekler[0]["mesajlar"][0]
    assert "--- Bilgi tabanı ---" in sistem["content"]
    assert "[El Kitabı#2] İade süresi 14 gündür." in sistem["content"]
    assert sahte_rag["gomme"] == [["İade süresi nedir?"]]
    assert sahte_rag["arama"][0]["ust_k"] == ayarlar.rag_ust_k
    assert sahte_rag["arama"][0]["org_id"] == org.id

    await istemci.post(
        SOHBET,
        json={"bdm_id": bdm.id, "mesaj": "yine", "rag": True, "rag_ust_k": 2},
        headers=yardimci.org_basliklari(kullanici, org),
    )
    assert sahte_rag["arama"][1]["ust_k"] == 2


async def test_rag_akisinda_kaynaklar_bitti_olayinda_doner(
    istemci, yardimci, uygulama, sahte_rag
):
    kullanici = await yardimci.kullanici_ekle()
    org = await yardimci.organizasyon(sahibi=kullanici)
    bdm = await bdm_ekle(org)
    saglayici_bagla(uygulama, SahteSaglayici())

    yanit = await istemci.post(
        AKIS,
        json={"bdm_id": bdm.id, "mesaj": "süre?", "rag": True},
        headers=yardimci.org_basliklari(kullanici, org),
    )

    olaylar = olaylari_coz(yanit.text)
    assert [ad for ad, _ in olaylar] == ["baslangic", "parca", "kullanim", "bitti"]
    assert olaylar[-1][1]["kaynaklar"] == [
        {"belge_id": 7, "belge_ad": "El Kitabı", "sira": 2, "skor": 0.8765}
    ]


async def test_org_disi_belge_404(istemci, yardimci, uygulama, sahte_rag):
    kullanici = await yardimci.kullanici_ekle()
    org = await yardimci.organizasyon(sahibi=kullanici)
    yabanci = await yardimci.organizasyon(ad="Yabancı Org")
    bdm = await bdm_ekle(org)
    belge = await belge_ekle(yabanci)
    saglayici_bagla(uygulama, SahteSaglayici())

    yanit = await istemci.post(
        SOHBET,
        json={
            "bdm_id": bdm.id,
            "mesaj": "yabancı belge",
            "rag": True,
            "rag_belge_idleri": [belge.id],
        },
        headers=yardimci.org_basliklari(kullanici, org),
    )

    assert yanit.status_code == 404
    assert yanit.json()["hata"]["kod"] == "belge_bulunamadi"
    assert sahte_rag["gomme"] == []


# --------------------------------------------------------------------------
# Araç çağırma
# --------------------------------------------------------------------------


async def test_arac_sonucu_modele_geri_verilir_ve_ozet_doner(
    istemci, yardimci, uygulama, sahte_arac
):
    kullanici = await yardimci.kullanici_ekle()
    org = await yardimci.organizasyon(sahibi=kullanici)
    bdm = await bdm_ekle(org)
    arac = await arac_ekle(org)
    sahte = SahteSaglayici(
        cevaplar=[
            {"icerik": "", "arac_cagrilari": [arac_cagrisi()]},
            {"icerik": "Sonuç: 4"},
        ]
    )
    saglayici_bagla(uygulama, sahte)

    yanit = await istemci.post(
        SOHBET,
        json={"bdm_id": bdm.id, "mesaj": "2+2 kaç?", "arac_sluglari": [arac.slug]},
        headers=yardimci.org_basliklari(kullanici, org),
    )

    assert yanit.status_code == 200
    assert yanit.json()["icerik"] == "Sonuç: 4"
    assert yanit.json()["arac_cagrilari"] == [{"ad": "hesap_makinesi", "durum": "basarili"}]
    assert sahte.istekler[0]["araclar"][0]["function"]["name"] == "hesap_makinesi"

    ikinci = sahte.istekler[1]["mesajlar"]
    asistan = next(m for m in ikinci if m["role"] == "assistant" and m.get("tool_calls"))
    assert asistan["tool_calls"][0]["function"]["name"] == "hesap_makinesi"
    assert json.loads(asistan["tool_calls"][0]["function"]["arguments"]) == {"ifade": "2+2"}
    sonuc = next(m for m in ikinci if m["role"] == "tool")
    assert json.loads(sonuc["content"]) == {
        "durum": "basarili",
        "sonuc": {"sonuc": 4},
        "hata": None,
    }
    assert sahte_arac["calistirmalar"][0]["org_id"] == org.id
    assert sahte_arac["calistirmalar"][0]["konusma_id"] is not None
    assert sahte_arac["calistirmalar"][0]["mesaj_id"] is not None

    mesajlar = await mesajlari_oku()
    assert [mesaj.rol for mesaj in mesajlar] == [
        MesajRolu.kullanici,
        MesajRolu.arac,
        MesajRolu.asistan,
    ]
    assert '"durum": "basarili"' in mesajlar[1].icerik


async def test_arac_tur_siniri_tek_yanitta_400(istemci, yardimci, uygulama, sahte_arac):
    kullanici = await yardimci.kullanici_ekle()
    org = await yardimci.organizasyon(sahibi=kullanici)
    bdm = await bdm_ekle(org)
    arac = await arac_ekle(org)
    saglayici_bagla(uygulama, SahteSaglayici(tekrar_arac=arac_cagrisi()))

    yanit = await istemci.post(
        SOHBET,
        json={"bdm_id": bdm.id, "mesaj": "döngü", "arac_sluglari": [arac.slug]},
        headers=yardimci.org_basliklari(kullanici, org),
    )

    assert yanit.status_code == 400
    assert yanit.json()["hata"]["kod"] == "arac_tur_siniri"
    assert len(sahte_arac["calistirmalar"]) == ayarlar.arac_maks_tur


async def test_arac_akisinda_olay_sirasi(istemci, yardimci, uygulama, sahte_arac):
    kullanici = await yardimci.kullanici_ekle()
    org = await yardimci.organizasyon(sahibi=kullanici)
    bdm = await bdm_ekle(org)
    arac = await arac_ekle(org)
    saglayici_bagla(
        uygulama,
        SahteSaglayici(
            cevaplar=[
                {"icerik": "", "arac_cagrilari": [arac_cagrisi()]},
                {"parcalar": ("Sonuç ", "4")},
            ]
        ),
    )

    yanit = await istemci.post(
        AKIS,
        json={"bdm_id": bdm.id, "mesaj": "2+2 kaç?", "arac_sluglari": [arac.slug]},
        headers=yardimci.org_basliklari(kullanici, org),
    )

    assert yanit.status_code == 200
    olaylar = olaylari_coz(yanit.text)
    assert [ad for ad, _ in olaylar] == [
        "baslangic",
        "arac_cagrisi",
        "arac_sonucu",
        "parca",
        "parca",
        "kullanim",
        "bitti",
    ]
    veriler = dict(olaylar)
    assert veriler["arac_cagrisi"] == {"ad": "hesap_makinesi", "argumanlar": {"ifade": "2+2"}}
    assert veriler["arac_sonucu"]["ad"] == "hesap_makinesi"
    assert veriler["arac_sonucu"]["durum"] == "basarili"
    assert veriler["arac_sonucu"]["ozet"]
    assert veriler["bitti"]["arac_cagrilari"] == [
        {"ad": "hesap_makinesi", "durum": "basarili"}
    ]
    assert "".join(veri["icerik"] for ad, veri in olaylar if ad == "parca") == "Sonuç 4"


async def test_arac_tur_siniri_akista_hata_olayi(istemci, yardimci, uygulama, sahte_arac):
    kullanici = await yardimci.kullanici_ekle()
    org = await yardimci.organizasyon(sahibi=kullanici)
    bdm = await bdm_ekle(org)
    arac = await arac_ekle(org)
    saglayici_bagla(uygulama, SahteSaglayici(tekrar_arac=arac_cagrisi()))

    yanit = await istemci.post(
        AKIS,
        json={"bdm_id": bdm.id, "mesaj": "döngü", "arac_sluglari": [arac.slug]},
        headers=yardimci.org_basliklari(kullanici, org),
    )

    assert yanit.status_code == 200
    olaylar = olaylari_coz(yanit.text)
    assert [ad for ad, _ in olaylar] == [
        "baslangic",
        *["arac_cagrisi", "arac_sonucu"] * ayarlar.arac_maks_tur,
        "hata",
        "bitti",
    ]
    hata = next(veri for ad, veri in olaylar if ad == "hata")
    assert hata["hata"]["kod"] == "arac_tur_siniri"
    assert len(sahte_arac["calistirmalar"]) == ayarlar.arac_maks_tur


async def test_bdm_yetenegi_araci_otomatik_etkinlestirir(
    istemci, yardimci, uygulama, sahte_arac
):
    kullanici = await yardimci.kullanici_ekle()
    org = await yardimci.organizasyon(sahibi=kullanici)
    yetenekli = await bdm_ekle(org, yetenekler={**VARSAYILAN_YETENEKLER, "arac": True})
    yeteneksiz = await bdm_ekle(org)
    await arac_ekle(org)
    sahte = SahteSaglayici()
    saglayici_bagla(uygulama, sahte)
    basliklar = yardimci.org_basliklari(kullanici, org)

    await istemci.post(SOHBET, json={"bdm_id": yetenekli.id, "mesaj": "selam"}, headers=basliklar)
    await istemci.post(SOHBET, json={"bdm_id": yeteneksiz.id, "mesaj": "selam"}, headers=basliklar)

    assert [arac["function"]["name"] for arac in sahte.istekler[0]["araclar"]] == [
        "hesap_makinesi"
    ]
    assert sahte.istekler[1]["araclar"] is None


async def test_bilinmeyen_arac_slugu_404(istemci, yardimci, uygulama, sahte_arac):
    kullanici = await yardimci.kullanici_ekle()
    org = await yardimci.organizasyon(sahibi=kullanici)
    bdm = await bdm_ekle(org)
    saglayici_bagla(uygulama, SahteSaglayici())

    yanit = await istemci.post(
        SOHBET,
        json={"bdm_id": bdm.id, "mesaj": "selam", "arac_sluglari": ["yok-boyle-arac"]},
        headers=yardimci.org_basliklari(kullanici, org),
    )

    assert yanit.status_code == 404
    assert yanit.json()["hata"]["kod"] == "bulunamadi"


# --------------------------------------------------------------------------
# Org izolasyonu ve geriye uyumluluk
# --------------------------------------------------------------------------


async def test_org_disi_bdm_404(istemci, yardimci, uygulama):
    kullanici = await yardimci.kullanici_ekle()
    org = await yardimci.organizasyon(sahibi=kullanici)
    yabanci = await yardimci.organizasyon(ad="Yabancı Org")
    yabanci_bdm = await bdm_ekle(yabanci)
    saglayici_bagla(uygulama, SahteSaglayici())

    yanit = await istemci.post(
        SOHBET,
        json={"bdm_id": yabanci_bdm.id, "mesaj": "selam"},
        headers=yardimci.org_basliklari(kullanici, org),
    )

    assert yanit.status_code == 404
    assert yanit.json()["hata"]["kod"] == "bulunamadi"


async def test_gercek_yerlesik_arac_cagrisi_kaydedilir(istemci, yardimci, uygulama):
    """Gerçek `arac` servisiyle uçtan uca: çağrı loglanır, sonuç modele döner."""
    kullanici = await yardimci.kullanici_ekle()
    org = await yardimci.organizasyon(sahibi=kullanici)
    bdm = await bdm_ekle(org, yetenekler={**VARSAYILAN_YETENEKLER, "arac": True})
    await arac_ekle(org)
    sahte = SahteSaglayici(
        cevaplar=[
            {"icerik": "", "arac_cagrilari": [arac_cagrisi()]},
            {"icerik": "Dört."},
        ]
    )
    saglayici_bagla(uygulama, sahte)

    yanit = await istemci.post(
        SOHBET,
        json={"bdm_id": bdm.id, "mesaj": "2+2 kaç?"},
        headers=yardimci.org_basliklari(kullanici, org),
    )

    assert yanit.status_code == 200
    assert yanit.json()["icerik"] == "Dört."
    assert yanit.json()["arac_cagrilari"] == [{"ad": "hesap_makinesi", "durum": "basarili"}]
    sonuc = next(m for m in sahte.istekler[1]["mesajlar"] if m["role"] == "tool")
    assert json.loads(sonuc["content"]) == {
        "durum": "basarili",
        "sonuc": {"sonuc": 4},
        "hata": None,
    }

    async with oturum_fabrikasi()() as oturum:
        cagri = (
            await oturum.execute(sa.select(AracCagrisi))
        ).scalar_one()
        assert cagri.ad == "hesap_makinesi"
        assert cagri.durum == AracCagrisiDurumu.basarili
        assert cagri.argumanlar == {"ifade": "2+2"}
        assert cagri.sonuc == {"sonuc": 4}
        assert cagri.org_id == org.id
        assert cagri.konusma_id == yanit.json()["konusma_id"]
        assert cagri.mesaj_id is not None


async def test_organizasyon_kotasi_sohbette_tuketilir(istemci, yardimci, uygulama):
    kullanici = await yardimci.kullanici_ekle()
    org = await yardimci.organizasyon(sahibi=kullanici)
    bdm = await bdm_ekle(org)
    await kota_ekle(org, gunluk_istek=1)
    saglayici_bagla(uygulama, SahteSaglayici())
    basliklar = yardimci.org_basliklari(kullanici, org)

    ilk = await istemci.post(
        SOHBET, json={"bdm_id": bdm.id, "mesaj": "bir"}, headers=basliklar
    )
    assert ilk.status_code == 200

    async with oturum_fabrikasi()() as oturum:
        kayit = (
            await oturum.execute(
                sa.select(Kota).where(
                    Kota.kapsam == KotaKapsami.organizasyon, Kota.kapsam_id == org.id
                )
            )
        ).scalar_one()
        assert (kayit.kullanilan_gunluk, kayit.kullanilan_aylik) == (1, 15)

    ikinci = await istemci.post(
        SOHBET, json={"bdm_id": bdm.id, "mesaj": "iki"}, headers=basliklar
    )
    assert ikinci.status_code == 429
    assert ikinci.json()["hata"]["ayrinti"]["kapsam"] == "organizasyon"


async def test_yeni_alanlar_opsiyonel_ve_yanit_semasini_bozmaz(istemci, yardimci, uygulama):
    kullanici = await yardimci.kullanici_ekle()
    org = await yardimci.organizasyon(sahibi=kullanici)
    bdm = await bdm_ekle(org)
    saglayici_bagla(uygulama, SahteSaglayici(parcalar=("tek",)))

    tek = await istemci.post(
        SOHBET,
        json={"bdm_id": bdm.id, "mesaj": "selam"},
        headers=yardimci.org_basliklari(kullanici, org),
    )
    assert tek.status_code == 200
    assert set(tek.json()) == {
        "konusma_id",
        "mesaj_id",
        "icerik",
        "token_girdi",
        "token_cikti",
        "gecikme_ms",
    }

    akis = await istemci.post(
        AKIS,
        json={"bdm_id": bdm.id, "mesaj": "selam"},
        headers=yardimci.org_basliklari(kullanici, org),
    )
    olaylar = olaylari_coz(akis.text)
    assert [ad for ad, _ in olaylar] == ["baslangic", "parca", "kullanim", "bitti"]
    assert olaylar[-1][1] == {}
