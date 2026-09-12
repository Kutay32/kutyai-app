"""Ödeme, abonelik ve faturalama testleri (spec §6)."""

from __future__ import annotations

import hashlib
import hmac
import json
import time

import httpx
import pytest
import sqlalchemy as sa

from arkauc.app.cekirdek.ayarlar import ayarlar
from bdm_veritabani.modeller import (
    Abonelik,
    AbonelikDurumu,
    Fatura,
    FaturaDurumu,
    Kota,
    KotaKapsami,
    Plan,
    UyelikRolu,
)
from bdm_veritabani.oturum import oturum_fabrikasi

FATURALAMA = "/api/v1/faturalama"


async def _plan_ekle(slug: str = "test-plan", *, fiyat: int = 99_000, istek: int = 100) -> Plan:
    async with oturum_fabrikasi()() as oturum:
        plan = Plan(
            ad=f"Plan {slug}",
            slug=slug,
            aylik_fiyat_kurus=fiyat,
            dahil_istek=istek,
            dahil_token=10_000,
            ozellikler={"rag": True},
        )
        oturum.add(plan)
        await oturum.commit()
        await oturum.refresh(plan)
        return plan


def _imza(govde: bytes, sir: str, *, zaman: int | None = None) -> str:
    t = int(time.time()) if zaman is None else zaman
    hesap = hmac.new(sir.encode(), f"{t}.".encode() + govde, hashlib.sha256).hexdigest()
    return f"t={t},v1={hesap}"


# -- planlar ve abonelik -------------------------------------------------------


async def test_planlar_listelenir(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    await _plan_ekle()
    yanit = await istemci.get(f"{FATURALAMA}/planlar", headers=yardimci.basliklar(yonetici))
    assert yanit.status_code == 200
    planlar = yanit.json()
    secili = next(p for p in planlar if p["slug"] == "test-plan")
    assert secili["aylik_fiyat"] == "TRY 990,00"
    assert secili["ozellikler"] == {"rag": True}
    # Sıralama: en düşük fiyat önce (ücretsiz deneme planı başta)
    fiyatlar = [p["aylik_fiyat_kurus"] for p in planlar]
    assert fiyatlar == sorted(fiyatlar)


async def test_abonelik_plan_kotasini_yazar_ve_fatura_uretir(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    organizasyon = await yardimci.organizasyon(sahibi=yonetici)
    plan = await _plan_ekle(fiyat=149_900, istek=500)

    yanit = await istemci.post(
        f"{FATURALAMA}/abonelik",
        json={"plan_id": plan.id},
        headers=yardimci.org_basliklari(yonetici, organizasyon),
    )
    assert yanit.status_code == 201, yanit.text
    govde = yanit.json()
    assert govde["abonelik"]["durum"] == "aktif"
    assert govde["abonelik"]["plan"]["slug"] == "test-plan"
    assert govde["fatura"]["durum"] == "taslak"
    assert govde["fatura"]["tutar_kurus"] == 149_900

    async with oturum_fabrikasi()() as oturum:
        kota = (
            await oturum.execute(
                sa.select(Kota).where(
                    Kota.kapsam == KotaKapsami.organizasyon,
                    Kota.kapsam_id == organizasyon.id,
                )
            )
        ).scalar_one()
        assert kota.gunluk_istek == 500
        assert kota.aylik_token == 10_000
        assert kota.kullanilan_gunluk == 0

        kayitlar = (
            await oturum.execute(
                sa.select(sa.func.count()).select_from(Fatura).where(Fatura.org_id == organizasyon.id)
            )
        ).scalar_one()
        assert int(kayitlar) == 1


async def test_abonelik_iptal_edilir(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    organizasyon = await yardimci.organizasyon(sahibi=yonetici)
    plan = await _plan_ekle()
    basliklar = yardimci.org_basliklari(yonetici, organizasyon)

    await istemci.post(f"{FATURALAMA}/abonelik", json={"plan_id": plan.id}, headers=basliklar)
    yanit = await istemci.post(f"{FATURALAMA}/abonelik/iptal", headers=basliklar)
    assert yanit.status_code == 200
    assert yanit.json()["durum"] == "iptal"
    assert yanit.json()["erisim"] is False


async def test_abonelik_yoksa_bos_doner(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    organizasyon = await yardimci.organizasyon(sahibi=yonetici)
    yanit = await istemci.get(
        f"{FATURALAMA}/abonelik", headers=yardimci.org_basliklari(yonetici, organizasyon)
    )
    assert yanit.status_code == 200
    assert yanit.json() is None

    iptal = await istemci.post(
        f"{FATURALAMA}/abonelik/iptal", headers=yardimci.org_basliklari(yonetici, organizasyon)
    )
    assert iptal.status_code == 404


async def test_bilinmeyen_plan_404(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    organizasyon = await yardimci.organizasyon(sahibi=yonetici)
    yanit = await istemci.post(
        f"{FATURALAMA}/abonelik",
        json={"plan_id": 9999},
        headers=yardimci.org_basliklari(yonetici, organizasyon),
    )
    assert yanit.status_code == 404
    assert yanit.json()["hata"]["kod"] == "plan_bulunamadi"


# -- faturalar -----------------------------------------------------------------


async def test_fatura_elle_odendi_isaretlenir(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    organizasyon = await yardimci.organizasyon(sahibi=yonetici)
    plan = await _plan_ekle()
    basliklar = yardimci.org_basliklari(yonetici, organizasyon)

    olustur = await istemci.post(
        f"{FATURALAMA}/abonelik", json={"plan_id": plan.id}, headers=basliklar
    )
    fatura_id = olustur.json()["fatura"]["id"]

    odendi = await istemci.post(f"{FATURALAMA}/faturalar/{fatura_id}/odendi", headers=basliklar)
    assert odendi.status_code == 200
    assert odendi.json()["durum"] == "odendi"
    assert odendi.json()["odeme_tarihi"] is not None

    tekrar = await istemci.post(f"{FATURALAMA}/faturalar/{fatura_id}/odendi", headers=basliklar)
    assert tekrar.status_code == 400

    liste = await istemci.get(f"{FATURALAMA}/faturalar", headers=basliklar)
    assert liste.json()["toplam"] == 1
    assert liste.json()["kayitlar"][0]["durum"] == "odendi"


async def test_fatura_sayfalama_siniri(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    organizasyon = await yardimci.organizasyon(sahibi=yonetici)
    basliklar = yardimci.org_basliklari(yonetici, organizasyon)
    yanit = await istemci.get(f"{FATURALAMA}/faturalar?boyut=999", headers=basliklar)
    assert yanit.status_code == 400


async def test_baska_organizasyonun_faturasi_gorunmez(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    birinci = await yardimci.organizasyon(ad="Birinci Org", sahibi=yonetici)
    ikinci = await yardimci.organizasyon(ad="İkinci Org", sahibi=yonetici)
    plan = await _plan_ekle()

    await istemci.post(
        f"{FATURALAMA}/abonelik",
        json={"plan_id": plan.id},
        headers=yardimci.org_basliklari(yonetici, birinci),
    )
    liste = await istemci.get(
        f"{FATURALAMA}/faturalar", headers=yardimci.org_basliklari(yonetici, ikinci)
    )
    assert liste.json()["toplam"] == 0


async def test_yetki_matrisi(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    organizasyon = await yardimci.organizasyon(sahibi=yonetici)
    plan = await _plan_ekle()

    anonim = await istemci.get(f"{FATURALAMA}/planlar")
    assert anonim.status_code == 401

    izleyici = await yardimci.kullanici_ekle()
    await yardimci.uye_yap(organizasyon, izleyici, UyelikRolu.izleyici)
    izleyici_basliklar = yardimci.org_basliklari(izleyici, organizasyon)

    okuma = await istemci.get(f"{FATURALAMA}/planlar", headers=izleyici_basliklar)
    assert okuma.status_code == 200

    yazma = await istemci.post(
        f"{FATURALAMA}/abonelik", json={"plan_id": plan.id}, headers=izleyici_basliklar
    )
    assert yazma.status_code == 403

    son_kullanici = await yardimci.kullanici_ekle()
    await yardimci.uye_yap(organizasyon, son_kullanici, UyelikRolu.son_kullanici)
    sk = await istemci.get(
        f"{FATURALAMA}/planlar",
        headers=yardimci.org_basliklari(son_kullanici, organizasyon),
    )
    assert sk.status_code == 403


# -- Stripe --------------------------------------------------------------------


async def test_stripe_secili_ama_anahtar_yoksa_400(istemci, yardimci, monkeypatch):
    monkeypatch.setattr(ayarlar, "odeme_saglayici", "stripe")
    monkeypatch.setattr(ayarlar, "stripe_gizli_anahtar", "")
    yonetici = await yardimci.yonetici()
    organizasyon = await yardimci.organizasyon(sahibi=yonetici)
    plan = await _plan_ekle()
    yanit = await istemci.post(
        f"{FATURALAMA}/abonelik",
        json={"plan_id": plan.id},
        headers=yardimci.org_basliklari(yonetici, organizasyon),
    )
    assert yanit.status_code == 400
    assert yanit.json()["hata"]["kod"] == "odeme_saglayici_yok"


async def test_stripe_checkout_oturumu_uretir(monkeypatch):
    from arkauc.app.servisler.odeme_stripe import StripeSaglayici

    monkeypatch.setattr(ayarlar, "stripe_gizli_anahtar", "sk_test_123")
    yakalanan: dict = {}

    async def isleyici(istek: httpx.Request) -> httpx.Response:
        yakalanan["url"] = str(istek.url)
        yakalanan["govde"] = istek.content.decode()
        yakalanan["yetki"] = istek.headers.get("authorization")
        return httpx.Response(
            200, json={"id": "cs_test_1", "url": "https://checkout.stripe.com/c/pay/1"}
        )

    surucu = StripeSaglayici(tasima=httpx.MockTransport(isleyici))
    async with oturum_fabrikasi()() as oturum:
        plan = Plan(ad="Stripe Plan", slug="stripe-plan", aylik_fiyat_kurus=199_900)
        oturum.add(plan)
        await oturum.flush()
        organizasyon = await _organizasyon_olustur(oturum, "Stripe Org")
        sonuc = await surucu.abonelik_baslat(
            oturum, organizasyon=organizasyon, plan=plan
        )

    assert sonuc["dis_id"] == "cs_test_1"
    assert sonuc["url"].startswith("https://checkout.stripe.com/")
    assert yakalanan["yetki"] == "Bearer sk_test_123"
    assert "mode=subscription" in yakalanan["govde"]
    assert "unit_amount%5D=199900" in yakalanan["govde"]


async def test_stripe_webhook_imzasi_dogrulanir(istemci, yardimci, monkeypatch):
    monkeypatch.setattr(ayarlar, "odeme_saglayici", "stripe")
    monkeypatch.setattr(ayarlar, "stripe_gizli_anahtar", "sk_test_123")
    monkeypatch.setattr(ayarlar, "stripe_webhook_sirri", "whsec_test")
    yonetici = await yardimci.yonetici()
    organizasyon = await yardimci.organizasyon(sahibi=yonetici)
    plan = await _plan_ekle()

    async with oturum_fabrikasi()() as oturum:
        abonelik = Abonelik(
            org_id=organizasyon.id,
            plan_id=plan.id,
            durum=AbonelikDurumu.deneme,
            saglayici="stripe",
            dis_id="sub_test_1",
        )
        fatura = Fatura(
            org_id=organizasyon.id,
            tutar_kurus=99_000,
            durum=FaturaDurumu.taslak,
            dis_id="in_test_1",
        )
        oturum.add_all([abonelik, fatura])
        await oturum.commit()
        await oturum.refresh(abonelik)
        await oturum.refresh(fatura)
        fatura_id = fatura.id

    olay = {
        "type": "invoice.paid",
        "data": {
            "object": {
                "id": "in_test_1",
                "subscription": "sub_test_1",
                "metadata": {"fatura_id": str(fatura_id)},
            }
        },
    }
    govde = json.dumps(olay).encode()

    gecersiz = await istemci.post(
        f"{FATURALAMA}/webhook/stripe",
        content=govde,
        headers={"Stripe-Signature": "t=1,v1=deadbeef"},
    )
    assert gecersiz.status_code == 502
    assert gecersiz.json()["hata"]["ayrinti"]["kod"] == "webhook_imzasi_gecersiz"

    eksik = await istemci.post(f"{FATURALAMA}/webhook/stripe", content=govde)
    assert eksik.status_code == 502

    eski = await istemci.post(
        f"{FATURALAMA}/webhook/stripe",
        content=govde,
        headers={"Stripe-Signature": _imza(govde, "whsec_test", zaman=int(time.time()) - 4000)},
    )
    assert eski.status_code == 502

    gecerli = await istemci.post(
        f"{FATURALAMA}/webhook/stripe",
        content=govde,
        headers={"Stripe-Signature": _imza(govde, "whsec_test")},
    )
    assert gecerli.status_code == 200, gecerli.text
    assert gecerli.json()["uygulandi"] is True

    async with oturum_fabrikasi()() as oturum:
        assert (await oturum.get(Abonelik, abonelik.id)).durum == AbonelikDurumu.aktif
        assert (await oturum.get(Fatura, fatura_id)).durum == FaturaDurumu.odendi


async def test_stripe_odeme_basarisiz_abonelik_gecikmis(istemci, yardimci, monkeypatch):
    monkeypatch.setattr(ayarlar, "odeme_saglayici", "stripe")
    monkeypatch.setattr(ayarlar, "stripe_gizli_anahtar", "sk_test_123")
    monkeypatch.setattr(ayarlar, "stripe_webhook_sirri", "whsec_test")
    yonetici = await yardimci.yonetici()
    organizasyon = await yardimci.organizasyon(sahibi=yonetici)
    plan = await _plan_ekle()

    async with oturum_fabrikasi()() as oturum:
        abonelik = Abonelik(
            org_id=organizasyon.id,
            plan_id=plan.id,
            durum=AbonelikDurumu.aktif,
            saglayici="stripe",
            dis_id="sub_test_2",
        )
        oturum.add(abonelik)
        await oturum.commit()
        await oturum.refresh(abonelik)
        abonelik_id = abonelik.id

    govde = json.dumps(
        {"type": "invoice.payment_failed", "data": {"object": {"subscription": "sub_test_2"}}}
    ).encode()
    yanit = await istemci.post(
        f"{FATURALAMA}/webhook/stripe",
        content=govde,
        headers={"Stripe-Signature": _imza(govde, "whsec_test")},
    )
    assert yanit.status_code == 200

    async with oturum_fabrikasi()() as oturum:
        assert (
            await oturum.get(Abonelik, abonelik_id)
        ).durum == AbonelikDurumu.gecikmis


async def test_yerel_surucude_webhook_calismaz(istemci, monkeypatch):
    monkeypatch.setattr(ayarlar, "odeme_saglayici", "yerel")
    yanit = await istemci.post(
        f"{FATURALAMA}/webhook/stripe",
        content=b"{}",
        headers={"Stripe-Signature": "t=1,v1=x"},
    )
    assert yanit.status_code == 400
    assert yanit.json()["hata"]["kod"] == "odeme_saglayici_yok"


async def _organizasyon_olustur(oturum, ad: str):
    from bdm_listesi.katalog import slug_uret
    from bdm_veritabani.modeller import Organizasyon

    organizasyon = Organizasyon(ad=ad, slug=slug_uret(ad))
    oturum.add(organizasyon)
    await oturum.flush()
    return organizasyon


@pytest.mark.parametrize("durum,erisim", [(AbonelikDurumu.aktif, True), (AbonelikDurumu.gecikmis, False)])
def test_erisim_kurali(durum, erisim):
    from arkauc.app.servisler.odeme import erisim_var_mi

    assert erisim_var_mi(durum) is erisim
