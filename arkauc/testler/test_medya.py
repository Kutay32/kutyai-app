"""T1.4 — Medya uclari: gorsel uretimi, ses uretimi ve ses cozumu (spec §8).

Ag erisimi yoktur: saglayici cagrilari `httpx.MockTransport` ile enjekte edilir
(`uygulama.dependency_overrides[medya_ucu.varsayilan_tasima]`). Uretilen
dosyalar gercek `dosya` tablosuna yazilir ve `GET /dosyalar/{id}/icerik` ile
geri okunur.
"""

from __future__ import annotations

import base64
import itertools
import json

import httpx
import pytest
import sqlalchemy as sa

from arkauc.app.api import medya as medya_ucu
from arkauc.app.cekirdek.hatalar import MedyaDesteklenmiyor, UstSaglayiciHatasi
from arkauc.app.servisler import medya
from bdm_listesi import BdmOlustur, bdm_olustur
from bdm_veritabani.modeller import (
    Bdm,
    Dosya,
    KullanimDurumu,
    KullanimKaydi,
    Rol,
    Saglayici,
    UyelikRolu,
)
from bdm_veritabani.oturum import oturum_fabrikasi

GORSEL = "/api/v1/medya/gorsel"
SES = "/api/v1/medya/ses"
COZ = "/api/v1/medya/coz"
DOSYALAR = "/api/v1/dosyalar"

PNG = b"\x89PNG\r\n\x1a\n" + b"sahte-gorsel-icerigi"
JPEG = b"\xff\xd8\xff\xe0" + b"sahte-jpeg-icerigi"
WEBP = b"RIFF\x00\x00\x00\x00WEBP" + b"sahte-webp"
SES_BAYT = b"ID3\x04\x00\x00sahte-ses-icerigi"
TEMEL_URL = "https://api.sahte.test/v1"

_sayac = itertools.count(1)


class SahteMedya:
    """MockTransport tabanli sahte medya saglayicisi; istekleri kaydeder."""

    def __init__(
        self,
        *,
        gorsel_bicimi: str = "b64",
        gorsel_icerik: bytes = PNG,
        gorsel_adet: int | None = None,
        gorsel_durum: int = 200,
        ses_durum: int = 200,
        cozum_durum: int = 200,
        cozum_metni: str = "merhaba dünya",
        hata: Exception | None = None,
    ) -> None:
        self.gorsel_bicimi = gorsel_bicimi
        self.gorsel_icerik = gorsel_icerik
        self.gorsel_adet = gorsel_adet
        self.gorsel_durum = gorsel_durum
        self.ses_durum = ses_durum
        self.cozum_durum = cozum_durum
        self.cozum_metni = cozum_metni
        self.hata = hata
        self.yollar: list[tuple[str, str]] = []
        self.govdeler: dict[str, dict] = {}
        self.ham: dict[str, bytes] = {}
        self.basliklar: dict[str, dict[str, str]] = {}

    def tasima(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.isleyici)

    def _kaydet(self, istek: httpx.Request) -> str:
        yol = istek.url.path
        self.yollar.append((istek.method, yol))
        self.ham[yol] = istek.content
        self.basliklar[yol] = dict(istek.headers)
        return yol

    def isleyici(self, istek: httpx.Request) -> httpx.Response:
        if self.hata is not None:
            raise self.hata
        yol = self._kaydet(istek)
        if yol.endswith("/images/generations"):
            self.govdeler[yol] = json.loads(istek.content.decode("utf-8"))
            if self.gorsel_durum >= 400:
                return httpx.Response(self.gorsel_durum, json={"error": {"message": "yok"}})
            adet = self.gorsel_adet or int(self.govdeler[yol]["n"])
            veriler = []
            for sira in range(adet):
                if self.gorsel_bicimi == "url":
                    veriler.append({"url": f"https://cdn.sahte.test/g{sira}.png"})
                else:
                    veriler.append(
                        {"b64_json": base64.b64encode(self.gorsel_icerik).decode("ascii")}
                    )
            return httpx.Response(200, json={"data": veriler})
        if istek.method == "GET":
            return httpx.Response(200, content=self.gorsel_icerik)
        if yol.endswith("/audio/speech"):
            self.govdeler[yol] = json.loads(istek.content.decode("utf-8"))
            if self.ses_durum >= 400:
                return httpx.Response(self.ses_durum, json={"error": {"message": "yok"}})
            return httpx.Response(
                200, content=SES_BAYT, headers={"content-type": "audio/mpeg"}
            )
        if yol.endswith("/audio/transcriptions"):
            if self.cozum_durum >= 400:
                return httpx.Response(self.cozum_durum, json={"error": {"message": "yok"}})
            return httpx.Response(200, json={"text": self.cozum_metni})
        return httpx.Response(404, json={"error": {"message": "bilinmeyen yol"}})


@pytest.fixture
def sahte() -> SahteMedya:
    return SahteMedya()


@pytest.fixture(autouse=True)
def tasima_bagla(uygulama, sahte: SahteMedya):
    """Sahte medya tasimasini uclara baglar."""
    uygulama.dependency_overrides[medya_ucu.varsayilan_tasima] = lambda: sahte.tasima()
    yield
    uygulama.dependency_overrides.pop(medya_ucu.varsayilan_tasima, None)


async def bdm_ekle(
    *,
    gorsel: bool = False,
    ses: bool = False,
    org_id: int | None = None,
    upstream_model: str = "gpt-image-1",
) -> Bdm:
    """Medya yetenekleri verilen bir BDM kaydi olusturur."""
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_olustur(
            oturum,
            BdmOlustur(
                gorunen_ad=f"Medya Modeli {next(_sayac)}",
                saglayici=Saglayici("openai"),
                upstream_model=upstream_model,
                temel_url=TEMEL_URL,
                api_anahtari="sk-test",
                yetenekler={"akis": False, "gorsel": gorsel, "arac": False, "ses": ses},
            ),
            org_id=org_id,
        )
        await oturum.commit()
        return bdm


async def kayitlari_getir(model: type) -> list:
    async with oturum_fabrikasi()() as oturum:
        return list((await oturum.execute(sa.select(model))).scalars().all())


async def dosyalari_getir() -> list[Dosya]:
    return await kayitlari_getir(Dosya)


async def kullanimlari_getir() -> list[KullanimKaydi]:
    return await kayitlari_getir(KullanimKaydi)


# -- servis katmani ---------------------------------------------------------


async def test_servis_gorsel_b64_ve_url_yollari():
    bdm = await bdm_ekle(gorsel=True)
    sahte_b64 = SahteMedya(gorsel_bicimi="b64")
    sahte_url = SahteMedya(gorsel_bicimi="url")
    async with oturum_fabrikasi()() as oturum:
        kayit = await oturum.get(Bdm, bdm.id)
        assert await medya.gorsel_uret(kayit, "kedi", tasima=sahte_b64.tasima()) == [PNG]
        assert await medya.gorsel_uret(kayit, "kedi", tasima=sahte_url.tasima()) == [PNG]
    # URL yolu: once uretim, sonra gorselin indirilmesi.
    assert sahte_url.yollar == [
        ("POST", "/v1/images/generations"),
        ("GET", "/g0.png"),
    ]


async def test_servis_gorsel_govdesi_ve_basliklari():
    sahte = SahteMedya()
    bdm = await bdm_ekle(gorsel=True)
    async with oturum_fabrikasi()() as oturum:
        kayit = await oturum.get(Bdm, bdm.id)
        await medya.gorsel_uret(
            kayit, "mavi balina", boyut="512x512", adet=2, tasima=sahte.tasima()
        )
    assert sahte.govdeler["/v1/images/generations"] == {
        "model": "gpt-image-1",
        "prompt": "mavi balina",
        "size": "512x512",
        "n": 2,
    }
    assert sahte.basliklar["/v1/images/generations"]["authorization"] == "Bearer sk-test"


async def test_servis_gorsel_yetenegi_yoksa_400():
    bdm = await bdm_ekle(gorsel=False)
    async with oturum_fabrikasi()() as oturum:
        kayit = await oturum.get(Bdm, bdm.id)
        with pytest.raises(MedyaDesteklenmiyor) as yakalanan:
            await medya.gorsel_uret(kayit, "kedi", tasima=SahteMedya().tasima())
    assert yakalanan.value.kod == "medya_desteklenmiyor"
    assert yakalanan.value.ayrinti["yetenek"] == "gorsel"


async def test_servis_ses_uretir_ve_cozer():
    sahte = SahteMedya()
    bdm = await bdm_ekle(ses=True, upstream_model="whisper-1")
    async with oturum_fabrikasi()() as oturum:
        kayit = await oturum.get(Bdm, bdm.id)
        assert await medya.ses_uret(
            kayit, "merhaba", ses="nova", bicim="wav", tasima=sahte.tasima()
        ) == SES_BAYT
        metin = await medya.ses_coz(kayit, "ses.mp3", SES_BAYT, tasima=sahte.tasima())
    assert metin == "merhaba dünya"
    assert sahte.govdeler["/v1/audio/speech"] == {
        "model": "whisper-1",
        "input": "merhaba",
        "voice": "nova",
        "response_format": "wav",
    }
    # Cozumleme multipart gonderir; sinir degerini httpx uretir.
    multipart = sahte.basliklar["/v1/audio/transcriptions"]["content-type"]
    assert multipart.startswith("multipart/form-data; boundary=")
    ham = sahte.ham["/v1/audio/transcriptions"]
    assert b'name="file"' in ham and b'filename="ses.mp3"' in ham
    assert b'name="model"' in ham and b"whisper-1" in ham
    assert SES_BAYT in ham


async def test_servis_saglayici_hatasi_502_olur():
    sahte = SahteMedya(gorsel_durum=404)
    bdm = await bdm_ekle(gorsel=True)
    async with oturum_fabrikasi()() as oturum:
        kayit = await oturum.get(Bdm, bdm.id)
        with pytest.raises(UstSaglayiciHatasi) as yakalanan:
            await medya.gorsel_uret(kayit, "kedi", tasima=sahte.tasima())
    assert yakalanan.value.durum_kodu == 502
    assert yakalanan.value.ayrinti["durum"] == 404
    assert "sağlayıcı" in yakalanan.value.mesaj.lower()


async def test_servis_tasima_hatasi_502_olur():
    sahte = SahteMedya(hata=httpx.ConnectError("kopuk baglanti"))
    bdm = await bdm_ekle(ses=True)
    async with oturum_fabrikasi()() as oturum:
        kayit = await oturum.get(Bdm, bdm.id)
        with pytest.raises(UstSaglayiciHatasi) as yakalanan:
            await medya.ses_uret(kayit, "merhaba", tasima=sahte.tasima())
    assert yakalanan.value.ayrinti["durum"] == 0


def test_gorsel_mime_imzadan_secilir():
    assert medya.gorsel_mime(PNG) == ("png", "image/png")
    assert medya.gorsel_mime(JPEG) == ("jpg", "image/jpeg")
    assert medya.gorsel_mime(WEBP) == ("webp", "image/webp")
    assert medya.gorsel_mime(b"bilinmeyen") == ("png", "image/png")


# -- uclar: mutlu yol -------------------------------------------------------


async def test_gorsel_ucu_dosya_yazar_ve_indirilebilir(istemci, yardimci):
    bdm = await bdm_ekle(gorsel=True)
    yonetici = await yardimci.yonetici()

    yanit = await istemci.post(
        GORSEL,
        json={"bdm_id": bdm.id, "istem": "mavi kedi", "boyut": "1024x1024", "adet": 1},
        headers=yardimci.basliklar(yonetici),
    )
    assert yanit.status_code == 200, yanit.text
    kayitlar = yanit.json()
    assert len(kayitlar) == 1
    kayit = kayitlar[0]
    assert set(kayit) == {"dosya_id", "ad", "mime", "boyut"}
    assert kayit["mime"] == "image/png"
    assert kayit["boyut"] == len(PNG)
    assert kayit["ad"].endswith(".png")

    satirlar = await dosyalari_getir()
    assert len(satirlar) == 1
    assert satirlar[0].id == kayit["dosya_id"]
    assert satirlar[0].org_id == bdm.org_id
    assert satirlar[0].kullanici_id == yonetici.id
    assert satirlar[0].boyut == len(PNG)

    indirme = await istemci.get(
        f"{DOSYALAR}/{kayit['dosya_id']}/icerik", headers=yardimci.basliklar(yonetici)
    )
    assert indirme.status_code == 200
    assert indirme.content == PNG

    kullanim = await kullanimlari_getir()
    assert len(kullanim) == 1
    assert kullanim[0].bdm_id == bdm.id
    assert kullanim[0].org_id == bdm.org_id
    assert kullanim[0].kullanici_id == yonetici.id
    assert kullanim[0].durum == KullanimDurumu.basarili


async def test_gorsel_ucu_url_yolundan_indirir(istemci, yardimci, sahte):
    sahte.gorsel_bicimi = "url"
    bdm = await bdm_ekle(gorsel=True)
    yonetici = await yardimci.yonetici()

    yanit = await istemci.post(
        GORSEL,
        json={"bdm_id": bdm.id, "istem": "deniz"},
        headers=yardimci.basliklar(yonetici),
    )
    assert yanit.status_code == 200, yanit.text
    dosya_id = yanit.json()[0]["dosya_id"]
    indirme = await istemci.get(
        f"{DOSYALAR}/{dosya_id}/icerik", headers=yardimci.basliklar(yonetici)
    )
    assert indirme.content == PNG
    assert ("GET", "/g0.png") in sahte.yollar


async def test_gorsel_ucu_adet_kadar_dosya_yazar(istemci, yardimci):
    bdm = await bdm_ekle(gorsel=True)
    yonetici = await yardimci.yonetici()
    yanit = await istemci.post(
        GORSEL,
        json={"bdm_id": bdm.id, "istem": "uc kedi", "adet": 3},
        headers=yardimci.basliklar(yonetici),
    )
    assert yanit.status_code == 200, yanit.text
    assert len(yanit.json()) == 3
    assert len({k["ad"] for k in yanit.json()}) == 3
    assert len(await dosyalari_getir()) == 3


async def test_ses_ucu_dosya_yazar(istemci, yardimci):
    bdm = await bdm_ekle(ses=True)
    yonetici = await yardimci.yonetici()
    yanit = await istemci.post(
        SES,
        json={"bdm_id": bdm.id, "metin": "merhaba", "ses": "alloy", "bicim": "mp3"},
        headers=yardimci.basliklar(yonetici),
    )
    assert yanit.status_code == 200, yanit.text
    dosya_id = yanit.json()["dosya_id"]
    satirlar = await dosyalari_getir()
    assert len(satirlar) == 1
    assert satirlar[0].id == dosya_id
    assert satirlar[0].mime == "audio/mpeg"
    assert satirlar[0].ad.endswith(".mp3")

    indirme = await istemci.get(
        f"{DOSYALAR}/{dosya_id}/icerik", headers=yardimci.basliklar(yonetici)
    )
    assert indirme.content == SES_BAYT


async def test_coz_ucu_metin_dondurur(istemci, yardimci, sahte):
    bdm = await bdm_ekle(ses=True, upstream_model="whisper-1")
    yonetici = await yardimci.yonetici()
    ses_yaniti = await istemci.post(
        SES,
        json={"bdm_id": bdm.id, "metin": "merhaba"},
        headers=yardimci.basliklar(yonetici),
    )
    assert ses_yaniti.status_code == 200, ses_yaniti.text
    dosya_id = ses_yaniti.json()["dosya_id"]

    yanit = await istemci.post(
        COZ,
        json={"bdm_id": bdm.id, "dosya_id": dosya_id},
        headers=yardimci.basliklar(yonetici),
    )
    assert yanit.status_code == 200, yanit.text
    assert yanit.json() == {"metin": "merhaba dünya"}
    ham = sahte.ham["/v1/audio/transcriptions"]
    assert b'name="file"' in ham and b'name="model"' in ham
    assert len(await kullanimlari_getir()) == 2


# -- yetenek ve yetki -------------------------------------------------------


async def test_yetenek_kapali_gorsel_400(istemci, yardimci):
    bdm = await bdm_ekle(gorsel=False)
    yonetici = await yardimci.yonetici()
    yanit = await istemci.post(
        GORSEL,
        json={"bdm_id": bdm.id, "istem": "kedi"},
        headers=yardimci.basliklar(yonetici),
    )
    assert yanit.status_code == 400
    hata = yanit.json()["hata"]
    assert hata["kod"] == "medya_desteklenmiyor"
    assert hata["ayrinti"]["yetenek"] == "gorsel"
    assert hata["mesaj"] == "Model yeteneklerinde bu üretim türü kapalı."
    assert await dosyalari_getir() == []
    kullanim = await kullanimlari_getir()
    assert len(kullanim) == 1
    assert kullanim[0].durum == KullanimDurumu.hata


async def test_yetenek_kapali_ses_400_ingilizce_mesaj(istemci, yardimci):
    bdm = await bdm_ekle(ses=False)
    yonetici = await yardimci.yonetici()
    yanit = await istemci.post(
        SES,
        json={"bdm_id": bdm.id, "metin": "merhaba"},
        headers={**yardimci.basliklar(yonetici), "Accept-Language": "en"},
    )
    assert yanit.status_code == 400
    hata = yanit.json()["hata"]
    assert hata["kod"] == "medya_desteklenmiyor"
    assert hata["mesaj"] == "This generation type is disabled in the model capabilities."


@pytest.mark.parametrize(
    ("yol", "govde"),
    [
        (GORSEL, {"istem": "kedi"}),
        (SES, {"metin": "merhaba"}),
        (COZ, {"dosya_id": 1}),
    ],
)
async def test_yetkisiz_roller_403(istemci, yardimci, yol, govde):
    """`son_kullanici` ve `izleyici` medya uretemez."""
    bdm = await bdm_ekle(gorsel=True, ses=True)
    son = await yardimci.kullanici_ekle(rol=Rol.son_kullanici)
    izleyici = await yardimci.kullanici_ekle(rol=Rol.izleyici)
    for kullanici in (son, izleyici):
        yanit = await istemci.post(
            yol,
            json={"bdm_id": bdm.id, **govde},
            headers=yardimci.basliklar(kullanici),
        )
        assert yanit.status_code == 403, (yol, kullanici.rol, yanit.text)
        assert yanit.json()["hata"]["kod"] == "yetki_yok"


@pytest.mark.parametrize(
    ("yol", "govde"),
    [(GORSEL, {"istem": "kedi"}), (SES, {"metin": "merhaba"})],
)
async def test_operator_uretebilir(istemci, yardimci, yol, govde):
    bdm = await bdm_ekle(gorsel=True, ses=True)
    operator = await yardimci.kullanici_ekle(rol=Rol.operator)
    yanit = await istemci.post(
        yol, json={"bdm_id": bdm.id, **govde}, headers=yardimci.basliklar(operator)
    )
    assert yanit.status_code == 200, yanit.text


async def test_rol_izleyici_uyelikte_403(istemci, yardimci):
    """Uyelik rolu izleyici olan personel medya uretemez."""
    izleyici = await yardimci.kullanici_ekle(rol=Rol.izleyici)
    organizasyon = await yardimci.organizasyon("Izleyici Org")
    await yardimci.uye_yap(organizasyon, izleyici, UyelikRolu.izleyici)
    bdm = await bdm_ekle(gorsel=True, org_id=organizasyon.id)
    yanit = await istemci.post(
        GORSEL,
        json={"bdm_id": bdm.id, "istem": "kedi"},
        headers=yardimci.org_basliklari(izleyici, organizasyon),
    )
    assert yanit.status_code == 403
    assert yanit.json()["hata"]["kod"] == "yetki_yok"


async def test_bilinmeyen_bdm_404(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    yanit = await istemci.post(
        GORSEL,
        json={"bdm_id": 9999, "istem": "kedi"},
        headers=yardimci.basliklar(yonetici),
    )
    assert yanit.status_code == 404
    assert yanit.json()["hata"]["kod"] == "bulunamadi"


# -- org izolasyonu ---------------------------------------------------------


async def test_org_izolasyonu_bdm_ve_dosya(istemci, yardimci):
    yonetici_a = await yardimci.yonetici()
    bdm_a = await bdm_ekle(gorsel=True, ses=True)

    sahip_b = await yardimci.yonetici()
    org_b = await yardimci.organizasyon("B Organizasyonu", sahibi=sahip_b)
    bdm_b = await bdm_ekle(gorsel=True, org_id=org_b.id)

    # A kendi organizasyonunda uretir.
    uretim = await istemci.post(
        GORSEL,
        json={"bdm_id": bdm_a.id, "istem": "kedi"},
        headers=yardimci.basliklar(yonetici_a),
    )
    assert uretim.status_code == 200, uretim.text
    dosya_a = uretim.json()[0]["dosya_id"]

    # B, A'nin modelini goremez.
    yanit_bdm = await istemci.post(
        GORSEL,
        json={"bdm_id": bdm_a.id, "istem": "kedi"},
        headers=yardimci.org_basliklari(sahip_b, org_b),
    )
    assert yanit_bdm.status_code == 404, yanit_bdm.text
    assert yanit_bdm.json()["hata"]["kod"] == "bulunamadi"

    # B, A'nin dosyasini cozemez.
    yanit_dosya = await istemci.post(
        COZ,
        json={"bdm_id": bdm_b.id, "dosya_id": dosya_a},
        headers=yardimci.org_basliklari(sahip_b, org_b),
    )
    assert yanit_dosya.status_code == 404, yanit_dosya.text
    assert yanit_dosya.json()["hata"]["kod"] == "bulunamadi"

    # A kendi dosyasini hala okuyabilir; kimliksiz istek 401.
    indirme = await istemci.get(
        f"{DOSYALAR}/{dosya_a}/icerik", headers=yardimci.basliklar(yonetici_a)
    )
    assert indirme.status_code == 200
    assert indirme.content == PNG

    anonim = await istemci.post(GORSEL, json={"bdm_id": bdm_a.id, "istem": "kedi"})
    assert anonim.status_code == 401


# -- saglayici hatalari -----------------------------------------------------


async def test_ust_saglayici_404_502_ve_hata_kaydi(istemci, yardimci, sahte):
    sahte.gorsel_durum = 404
    bdm = await bdm_ekle(gorsel=True)
    yonetici = await yardimci.yonetici()
    yanit = await istemci.post(
        GORSEL,
        json={"bdm_id": bdm.id, "istem": "kedi"},
        headers=yardimci.basliklar(yonetici),
    )
    assert yanit.status_code == 502
    assert yanit.json()["hata"]["kod"] == "ust_saglayici_hatasi"
    assert await dosyalari_getir() == []
    kullanim = await kullanimlari_getir()
    assert len(kullanim) == 1
    assert kullanim[0].durum == KullanimDurumu.hata


async def test_tasima_hatasi_502(istemci, yardimci, sahte):
    sahte.hata = httpx.ConnectError("kopuk baglanti")
    bdm = await bdm_ekle(ses=True)
    yonetici = await yardimci.yonetici()
    yanit = await istemci.post(
        SES,
        json={"bdm_id": bdm.id, "metin": "merhaba"},
        headers=yardimci.basliklar(yonetici),
    )
    assert yanit.status_code == 502
    assert yanit.json()["hata"]["kod"] == "ust_saglayici_hatasi"
