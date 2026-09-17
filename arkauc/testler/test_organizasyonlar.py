"""Organizasyon (kiracı) üye uçları: rol yükseltme koruması (API §15)."""

from __future__ import annotations

from bdm_veritabani.modeller import UyelikRolu

ORGANIZASYONLAR = "/api/v1/organizasyonlar"


async def test_yonetici_sahip_yukseltmesi_yapamaz(istemci, yardimci):
    """`sahip` rolü yalnız mevcut sahip tarafından verilebilir (yetki yükseltme koruması)."""
    sahip = await yardimci.yonetici()
    organizasyon = await yardimci.organizasyon(sahibi=sahip)
    yonetici = await yardimci.yonetici()
    await yardimci.uye_yap(organizasyon, yonetici, UyelikRolu.yonetici)
    uye = await yardimci.yonetici()
    await yardimci.uye_yap(organizasyon, uye, UyelikRolu.operator)
    basliklar = yardimci.basliklar(yonetici)

    kendisi = await istemci.patch(
        f"{ORGANIZASYONLAR}/{organizasyon.id}/uyeler/{yonetici.id}",
        json={"rol": "sahip"},
        headers=basliklar,
    )
    assert kendisi.status_code == 403, kendisi.text
    assert kendisi.json()["hata"]["kod"] == "yetki_yok"

    baskasina = await istemci.patch(
        f"{ORGANIZASYONLAR}/{organizasyon.id}/uyeler/{uye.id}",
        json={"rol": "sahip"},
        headers=basliklar,
    )
    assert baskasina.status_code == 403

    yeni = await yardimci.kullanici_ekle()
    ekleme = await istemci.post(
        f"{ORGANIZASYONLAR}/{organizasyon.id}/uyeler",
        json={"kullanici_id": yeni.id, "rol": "sahip"},
        headers=basliklar,
    )
    assert ekleme.status_code == 403

    # Yükseltme dışındaki rol değişiklikleri yöneticide kalır.
    yukseltme = await istemci.patch(
        f"{ORGANIZASYONLAR}/{organizasyon.id}/uyeler/{uye.id}",
        json={"rol": "izleyici"},
        headers=basliklar,
    )
    assert yukseltme.status_code == 200, yukseltme.text
    assert yukseltme.json()["rol"] == "izleyici"


async def test_sahip_baskasini_sahip_yapar_ve_son_sahip_korunur(istemci, yardimci):
    sahip = await yardimci.yonetici()
    organizasyon = await yardimci.organizasyon(sahibi=sahip)
    yonetici = await yardimci.yonetici()
    await yardimci.uye_yap(organizasyon, yonetici, UyelikRolu.yonetici)

    yanit = await istemci.patch(
        f"{ORGANIZASYONLAR}/{organizasyon.id}/uyeler/{yonetici.id}",
        json={"rol": "sahip"},
        headers=yardimci.basliklar(sahip),
    )
    assert yanit.status_code == 200, yanit.text
    assert yanit.json()["rol"] == "sahip"

    yeni = await yardimci.kullanici_ekle()
    ekleme = await istemci.post(
        f"{ORGANIZASYONLAR}/{organizasyon.id}/uyeler",
        json={"kullanici_id": yeni.id, "rol": "sahip"},
        headers=yardimci.basliklar(sahip),
    )
    assert ekleme.status_code == 201, ekleme.text
    assert ekleme.json()["rol"] == "sahip"

    # Son sahip / kendi sahipliğini düşürme kuralı aynen sürer.
    dusurme = await istemci.patch(
        f"{ORGANIZASYONLAR}/{organizasyon.id}/uyeler/{sahip.id}",
        json={"rol": "yonetici"},
        headers=yardimci.basliklar(sahip),
    )
    assert dusurme.status_code == 409
    assert dusurme.json()["hata"]["kod"] == "gecersiz_gecis"

    silme = await istemci.delete(
        f"{ORGANIZASYONLAR}/{organizasyon.id}/uyeler/{yonetici.id}",
        headers=yardimci.basliklar(sahip),
    )
    assert silme.status_code == 204
