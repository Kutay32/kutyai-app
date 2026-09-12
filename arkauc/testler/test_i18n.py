"""Dil (i18n) altyapısı testleri (spec §10)."""

from __future__ import annotations

from arkauc.app.cekirdek.i18n import DESTEKLENEN_DILLER, katalog, mesaj


def test_kataloglar_ayni_anahtar_kumesine_sahip():
    tr = set(katalog("tr"))
    en = set(katalog("en"))
    assert tr, "TR kataloğu boş olmamalı"
    assert tr == en, f"Eksik/fazla anahtarlar: {sorted(tr ^ en)}"


def test_mesaj_bilinmeyen_anahtarda_anahtari_dondurur():
    assert mesaj("boyle_bir_anahtar_yok", "tr") == "boyle_bir_anahtar_yok"


def test_mesaj_yer_tutuculari_doldurur():
    from arkauc.app.cekirdek.i18n import _bicimle

    assert _bicimle("Merhaba {ad}", {"ad": "Ayşe"}) == "Merhaba Ayşe"
    # Eksik değişkende çökmemeli
    assert _bicimle("Merhaba {ad}", {}) == "Merhaba {ad}"


def test_dil_cozme():
    from arkauc.app.cekirdek.i18n import dil_coz

    assert dil_coz(None) == "tr"
    assert dil_coz("en-US,en;q=0.9") == "en"
    assert dil_coz("tr-TR") == "tr"
    assert dil_coz("de-DE") == "tr"
    assert dil_coz("") == "tr"


async def test_diller_ucu(istemci):
    yanit = await istemci.get("/api/v1/i18n/diller")
    assert yanit.status_code == 200
    kodlar = [d["kod"] for d in yanit.json()]
    assert kodlar == list(DESTEKLENEN_DILLER)
    assert any(d["varsayilan"] is True for d in yanit.json())


async def test_sozluk_uclari(istemci):
    tr = await istemci.get("/api/v1/i18n/sozluk/tr")
    en = await istemci.get("/api/v1/i18n/sozluk/en")
    assert tr.status_code == 200 and en.status_code == 200
    assert tr.json()["yetki_yok"] == "Bu işlem için yetkiniz yok."
    assert en.json()["yetki_yok"] == "You are not allowed to perform this action."
    assert set(tr.json()) == set(en.json())

    yok = await istemci.get("/api/v1/i18n/sozluk/de")
    assert yok.status_code == 404


async def test_hata_mesaji_accept_language_ile_cevrilir(istemci):
    tr = await istemci.get("/api/v1/bdm")
    assert tr.status_code == 401
    assert tr.json()["hata"]["kod"] == "kimlik_gerekli"
    assert tr.json()["hata"]["mesaj"] == "Bu işlem için giriş yapmalısınız."

    en = await istemci.get("/api/v1/bdm", headers={"Accept-Language": "en-US,en;q=0.9"})
    assert en.status_code == 401
    assert en.json()["hata"]["kod"] == "kimlik_gerekli"
    assert en.json()["hata"]["mesaj"] == "You must sign in to perform this action."


async def test_ozel_hata_kodu_katalog_anahtarindan_turetilir(istemci, yardimci):
    """`raise Bulunamadi("plan_bulunamadi")` → kod da `plan_bulunamadi` olur."""
    yanit = await istemci.get("/api/v1/i18n/sozluk/tr")
    assert yanit.status_code == 200

    yonetici = await yardimci.yonetici()
    organizasyon = await yardimci.organizasyon(sahibi=yonetici)
    basliklar = yardimci.org_basliklari(yonetici, organizasyon)
    yanit = await istemci.post(
        "/api/v1/faturalama/abonelik", json={"plan_id": 999999}, headers=basliklar
    )
    assert yanit.status_code == 404
    assert yanit.json()["hata"]["kod"] == "plan_bulunamadi"
    assert yanit.json()["hata"]["mesaj"] == "Plan bulunamadı."

    ingilizce = await istemci.post(
        "/api/v1/faturalama/abonelik",
        json={"plan_id": 999999},
        headers={**basliklar, "Accept-Language": "en"},
    )
    assert ingilizce.status_code == 404
    assert ingilizce.json()["hata"]["mesaj"] == "Plan not found."
