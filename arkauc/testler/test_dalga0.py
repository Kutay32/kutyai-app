"""Dalga 0 sozlesme testleri: sema, tohum, hata zarfi, guvenlik, kesif."""

from __future__ import annotations

import sqlalchemy as sa
from fastapi import Depends, FastAPI

from arkauc.app.cekirdek import guvenlik
from arkauc.app.cekirdek.bagimliliklar import gecerli_personel
from arkauc.app.cekirdek.hatalar import isleyicileri_kur
from bdm_veritabani.modeller import MaskelemeKurali, Rol, Taban
from bdm_veritabani.oturum import oturum_fabrikasi

BEKLENEN_TABLOLAR = {
    "kullanici",
    "oturum",
    "dogrulama_jetonu",
    "api_anahtari",
    "bdm",
    "konusma",
    "mesaj",
    "kullanim_kaydi",
    "kota",
    "islem_kaydi",
    "ayar",
    "maskeleme_kurali",
}


async def test_sema_on_iki_tabloyu_icerir():
    assert set(Taban.metadata.tables) == BEKLENEN_TABLOLAR


async def test_tohum_maskeleme_kurallarini_ekler():
    async with oturum_fabrikasi()() as oturum:
        adlar = set((await oturum.execute(sa.select(MaskelemeKurali.ad))).scalars().all())
    assert {"tckn", "eposta", "telefon", "iban", "kredi_karti"} <= adlar


async def test_saglik_ucu_ayakta(istemci):
    yanit = await istemci.get("/api/v1/saglik")
    assert yanit.status_code == 200
    assert yanit.json()["durum"] == "ayakta"


async def test_hazirlik_ucu_veritabanini_dogrular(istemci):
    yanit = await istemci.get("/api/v1/saglik/hazir")
    assert yanit.status_code == 200
    assert yanit.json()["veritabani"] == "tamam"


async def test_kurulum_ucu_baslangicta_tamamlanmamis(istemci):
    yanit = await istemci.get("/api/v1/saglik/kurulum")
    assert yanit.status_code == 200
    assert yanit.json()["kurulum_tamam"] is False


async def test_bilinmeyen_yol_hata_zarfi_dondurur(istemci):
    yanit = await istemci.get("/api/v1/boyle-bir-yol-yok")
    assert yanit.status_code == 404
    govde = yanit.json()
    assert govde["hata"]["kod"] == "bulunamadi"
    assert govde["hata"]["mesaj"]


async def test_yonlendirici_kesfi_sistem_modulunu_yukler(uygulama):
    assert "arkauc.app.api.sistem" in uygulama.state.yuklenen_yonlendiriciler


def test_sifre_ozeti_ve_dogrulama():
    ozet = guvenlik.sifre_hashle("Parola123!")
    assert guvenlik.sifre_dogrula(ozet, "Parola123!")[0] is True
    assert guvenlik.sifre_dogrula(ozet, "yanlis-parola")[0] is False


def test_erisim_jetonu_uret_ve_coz():
    jeton, jti = guvenlik.erisim_jetonu_uret(7, "yonetici")
    govde = guvenlik.jeton_coz(jeton)
    assert govde["sub"] == "7"
    assert govde["rol"] == "yonetici"
    assert govde["jti"] == jti


def test_api_anahtari_bicimi_ve_ozeti():
    anahtar = guvenlik.api_anahtari_uret()
    assert anahtar["tam"].startswith("kuty_")
    assert len(anahtar["tam"]) == len("kuty_") + 32
    assert anahtar["onek"] == anahtar["tam"][:12]
    assert anahtar["son_dort"] == anahtar["tam"][-4:]
    assert anahtar["hash"] == guvenlik.ozet(anahtar["tam"])


def test_fernet_gidis_donus():
    sifreli = guvenlik.sifrele("gizli-deger")
    assert sifreli != "gizli-deger"
    assert guvenlik.coz(sifreli) == "gizli-deger"


def test_upstream_anahtari_maskelenir():
    assert guvenlik.maskele("sk-1234567890abcdef") == "sk-1***cdef"
    assert guvenlik.maskele("") == ""
    assert guvenlik.maskele("kisa") == "***"


async def test_korumali_uc_kimlik_ister():
    import httpx

    deneme = FastAPI()
    isleyicileri_kur(deneme)

    @deneme.get("/koru")
    async def _koru(kullanici=Depends(gecerli_personel())):
        return {"eposta": kullanici.eposta}

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=deneme), base_url="http://test"
    ) as istemci:
        yanit = await istemci.get("/koru")
    assert yanit.status_code == 401
    assert yanit.json()["hata"]["kod"] == "kimlik_gerekli"


async def test_son_kullanici_personel_ucuna_giremez(istemci, yardimci, uygulama):
    import httpx

    kullanici = await yardimci.kullanici_ekle(rol=Rol.son_kullanici)
    deneme = FastAPI()
    isleyicileri_kur(deneme)

    @deneme.get("/koru")
    async def _koru(kimlik=Depends(gecerli_personel())):
        return {"eposta": kimlik.eposta}

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=deneme), base_url="http://test"
    ) as istemci:
        yanit = await istemci.get("/koru", headers=yardimci.basliklar(kullanici))
    assert yanit.status_code == 403
    assert yanit.json()["hata"]["kod"] == "yetki_yok"


async def test_yonetici_personel_ucuna_girebilir(yardimci):
    import httpx

    yonetici = await yardimci.yonetici()
    deneme = FastAPI()
    isleyicileri_kur(deneme)

    @deneme.get("/koru")
    async def _koru(kimlik=Depends(gecerli_personel())):
        return {"eposta": kimlik.eposta}

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=deneme), base_url="http://test"
    ) as istemci:
        yanit = await istemci.get("/koru", headers=yardimci.basliklar(yonetici))
    assert yanit.status_code == 200
    assert yanit.json()["eposta"] == yonetici.eposta
