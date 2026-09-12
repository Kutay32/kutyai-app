"""Kurulum sihirbazı uç testleri (API §4)."""

from __future__ import annotations

import sys
import types

import sqlalchemy as sa

from arkauc.app.cekirdek import guvenlik
from arkauc.app.cekirdek.ayarlar_db import ayar_oku
from bdm_veritabani.modeller import Bdm, IslemKaydi, Kullanici, KullaniciDurumu, Rol
from bdm_veritabani.oturum import oturum_fabrikasi

YONETICI_PAROLA = "Kurulum123!"


def _govde(*, dogrula: bool = False, eposta: str = "admin@acme.com") -> dict:
    return {
        "marka_adi": "Acme AI",
        "yonetici": {
            "eposta": eposta,
            "ad_soyad": "Ayşe Yılmaz",
            "parola": YONETICI_PAROLA,
        },
        "bdm": {
            "gorunen_ad": "Yerel Llama 3",
            "saglayici": "ollama",
            "temel_url": "http://localhost:11434/v1",
            "upstream_model": "llama3",
            "api_anahtari": "",
            "yerel_mi": True,
            "sistem_istemi": "",
        },
        "dogrula": dogrula,
    }


async def test_kurulum_yoneticiyi_ilk_bdmi_ve_marka_ayarlarini_olusturur(istemci):
    yanit = await istemci.post("/api/v1/kurulum", json=_govde())
    assert yanit.status_code == 201
    govde = yanit.json()

    assert govde["kurulum_tamam"] is True
    assert govde["dogrulama"] is None
    yonetici = govde["yonetici"]
    assert yonetici["eposta"] == "admin@acme.com"
    assert yonetici["ad_soyad"] == "Ayşe Yılmaz"
    assert yonetici["rol"] == "yonetici"
    assert yonetici["durum"] == "aktif"
    assert yonetici["eposta_dogrulandi"] is True
    assert yonetici["son_giris"] is None
    assert "sifre_hash" not in govde

    bdm = govde["bdm"]
    assert bdm["slug"] == "yerel-llama-3"
    assert bdm["saglayici"] == "ollama"
    assert bdm["upstream_model"] == "llama3"
    assert bdm["yerel_mi"] is True
    assert bdm["durum"] == "taslak"

    async with oturum_fabrikasi()() as oturum:
        kayitli = (
            await oturum.execute(sa.select(Kullanici).where(Kullanici.eposta == "admin@acme.com"))
        ).scalar_one()
        assert kayitli.rol is Rol.yonetici
        assert kayitli.durum is KullaniciDurumu.aktif
        assert guvenlik.sifre_dogrula(kayitli.sifre_hash, YONETICI_PAROLA)[0] is True
        assert guvenlik.sifre_dogrula(kayitli.sifre_hash, "yanlis-parola")[0] is False

        kayitli_bdm = (
            await oturum.execute(sa.select(Bdm).where(Bdm.id == bdm["id"]))
        ).scalar_one()
        assert kayitli_bdm.slug == bdm["slug"]
        assert await ayar_oku(oturum, "marka_adi") == "Acme AI"
        assert await ayar_oku(oturum, "varsayilan_bdm_slug") == bdm["slug"]
        assert await ayar_oku(oturum, "kurulum_tamam") is True
        eylemler = (
            await oturum.execute(sa.select(IslemKaydi.eylem))
        ).scalars().all()
        assert "kurulum.tamamlandi" in eylemler

    yanit = await istemci.get("/api/v1/saglik/kurulum")
    assert yanit.status_code == 200
    assert yanit.json()["kurulum_tamam"] is True
    assert yanit.json()["marka_adi"] == "Acme AI"


async def test_kurulum_ikinci_cagrida_409_dondurur(istemci):
    ilk = await istemci.post("/api/v1/kurulum", json=_govde())
    assert ilk.status_code == 201

    ikinci = await istemci.post(
        "/api/v1/kurulum", json=_govde(eposta="baska@acme.com")
    )
    assert ikinci.status_code == 409
    assert ikinci.json()["hata"]["kod"] == "kurulum_zaten_tamam"

    async with oturum_fabrikasi()() as oturum:
        sayi = (
            await oturum.execute(sa.select(sa.func.count()).select_from(Kullanici))
        ).scalar_one()
    assert sayi == 1


async def test_kurulum_ayni_epostayi_409_ile_reddeder(istemci, yardimci):
    await yardimci.kullanici_ekle(eposta="admin@acme.com")
    yanit = await istemci.post("/api/v1/kurulum", json=_govde())
    assert yanit.status_code == 409
    assert yanit.json()["hata"]["kod"] == "cakisma"


async def test_kurulum_dogrulama_sonucunu_yanita_tasir(istemci, monkeypatch):
    """Hazırlama ucu hazır olduğunda `dogrula` sonucu sadeleştirilerek döner."""
    cagrilar: list[tuple[object, object]] = []

    async def sahte_dogrula(oturum, bdm):  # noqa: ANN001 - sahte imza
        cagrilar.append((oturum, bdm))
        return {"basarili": True, "mesaj": "Model yanıt verdi.", "gecikme_ms": 12}

    paket = types.ModuleType("bdm_hazırlama_ucu")
    paket.__path__ = []  # type: ignore[attr-defined]
    modul = types.ModuleType("bdm_hazırlama_ucu.dogrulama")
    modul.dogrula = sahte_dogrula  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "bdm_hazırlama_ucu", paket)
    monkeypatch.setitem(sys.modules, "bdm_hazırlama_ucu.dogrulama", modul)

    yanit = await istemci.post("/api/v1/kurulum", json=_govde(dogrula=True))
    assert yanit.status_code == 201
    assert yanit.json()["dogrulama"] == {"basarili": True, "mesaj": "Model yanıt verdi."}
    assert len(cagrilar) == 1
    assert cagrilar[0][1] is not None
