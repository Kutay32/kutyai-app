"""Kurulum sihirbazı uç testleri (API §4)."""

from __future__ import annotations

import asyncio

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


async def test_es_zamanli_kurulum_tek_yonetici_ve_tek_bdm_olusturur(istemci):
    """İki eşzamanlı kurulumdan yalnız biri geçer; marka ayarları ezilmez (API §4)."""
    yanitlar = await asyncio.gather(
        istemci.post("/api/v1/kurulum", json=_govde(eposta="yaris-1@acme.com")),
        istemci.post("/api/v1/kurulum", json=_govde(eposta="yaris-2@acme.com")),
    )

    assert sorted(yanit.status_code for yanit in yanitlar) == [201, 409]
    basarili = next(y for y in yanitlar if y.status_code == 201).json()
    reddedilen = next(y for y in yanitlar if y.status_code == 409).json()
    assert reddedilen["hata"]["kod"] == "kurulum_zaten_tamam"

    async with oturum_fabrikasi()() as oturum:
        kullanici_sayisi = (
            await oturum.execute(sa.select(sa.func.count()).select_from(Kullanici))
        ).scalar_one()
        bdm_sayisi = (
            await oturum.execute(sa.select(sa.func.count()).select_from(Bdm))
        ).scalar_one()
        assert (kullanici_sayisi, bdm_sayisi) == (1, 1)
        assert await ayar_oku(oturum, "kurulum_tamam") is True
        assert await ayar_oku(oturum, "marka_adi") == "Acme AI"
        assert await ayar_oku(oturum, "varsayilan_bdm_slug") == basarili["bdm"]["slug"]


async def test_es_zamanli_ayni_eposta_409_dondurur_500_degil(istemci):
    """Aynı e-postayla yarışan kurulum tekil kısıt yerine 409 üretir."""
    yanitlar = await asyncio.gather(
        istemci.post("/api/v1/kurulum", json=_govde()),
        istemci.post("/api/v1/kurulum", json=_govde()),
    )

    assert sorted(yanit.status_code for yanit in yanitlar) == [201, 409]
    reddedilen = next(y for y in yanitlar if y.status_code == 409).json()
    assert reddedilen["hata"]["kod"] in {"kurulum_zaten_tamam", "cakisma"}

    async with oturum_fabrikasi()() as oturum:
        kullanici_sayisi = (
            await oturum.execute(sa.select(sa.func.count()).select_from(Kullanici))
        ).scalar_one()
        assert kullanici_sayisi == 1


async def test_kilitsiz_ayni_eposta_500_yerine_cakisma_dondurur(istemci, monkeypatch):
    """Ortak kilit yokken (çok işçili kurulum) tekil kısıt 500 değil 409 üretir."""
    import arkauc.app.api.kurulum as kurulum_uclari

    # Her çağrıda yeni kilit: işçiler arası paylaşımsız kurulumu taklit eder.
    monkeypatch.setattr(kurulum_uclari, "_kilit", asyncio.Lock, raising=False)

    yanitlar = await asyncio.gather(
        istemci.post("/api/v1/kurulum", json=_govde()),
        istemci.post("/api/v1/kurulum", json=_govde()),
    )

    assert sorted(yanit.status_code for yanit in yanitlar) == [201, 409]
    reddedilen = next(y for y in yanitlar if y.status_code == 409).json()
    assert reddedilen["hata"]["kod"] == "cakisma"

    async with oturum_fabrikasi()() as oturum:
        kullanici_sayisi = (
            await oturum.execute(sa.select(sa.func.count()).select_from(Kullanici))
        ).scalar_one()
        assert kullanici_sayisi == 1


async def test_kurulum_dogrulama_sonucunu_yanita_tasir(istemci, monkeypatch):
    """`dogrula` sonucu sadeleştirilerek yanıta taşınır; BDM ve oturum aktarılır."""
    import arkauc.app.api.kurulum as kurulum_uclari

    cagrilar: list[dict[str, object]] = []

    async def sahte_dogrula(bdm, *, oturum=None):  # noqa: ANN001 - sahte imza
        cagrilar.append({"bdm": bdm, "oturum": oturum})
        return {"basarili": True, "mesaj": "Model yanıt verdi.", "gecikme_ms": 12}

    monkeypatch.setattr(kurulum_uclari, "dogrula", sahte_dogrula)

    yanit = await istemci.post("/api/v1/kurulum", json=_govde(dogrula=True))
    assert yanit.status_code == 201
    assert yanit.json()["dogrulama"] == {"basarili": True, "mesaj": "Model yanıt verdi."}
    assert len(cagrilar) == 1
    assert cagrilar[0]["bdm"] is not None
    assert cagrilar[0]["oturum"] is not None


async def test_kurulum_dogrulama_istenmezse_cagrilmaz(istemci, monkeypatch):
    """`dogrula=false` iken upstream doğrulaması hiç çalışmaz ve yanıt `null` taşır."""
    import arkauc.app.api.kurulum as kurulum_uclari

    async def sahte_dogrula(bdm, *, oturum=None):  # noqa: ANN001 - sahte imza
        raise AssertionError("dogrula çağrılmamalıydı")

    monkeypatch.setattr(kurulum_uclari, "dogrula", sahte_dogrula)

    yanit = await istemci.post("/api/v1/kurulum", json=_govde())
    assert yanit.status_code == 201
    assert yanit.json()["dogrulama"] is None
