"""Faturalama uçları (spec §6)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek.bagimliliklar import (
    aktif_organizasyon,
    gecerli_personel,
    veritabani_oturumu,
)
from arkauc.app.cekirdek.denetim import islem_kaydet
from arkauc.app.cekirdek.hatalar import Bulunamadi, GecersizIstek
from arkauc.app.cekirdek.organizasyon import ORG_BASLIGI  # noqa: F401  (sözleşme dışa aktarımı)
from arkauc.app.servisler.odeme import (
    abonelik_durumu,
    aktif_abonelik,
    donem_sonu,
    erisim_var_mi,
    kurus_bicimle,
    plan_kotasini_uygula,
    saglayici_sec,
)
from bdm_veritabani.modeller import (
    ORG_YONETIM_ROLLERI,
    Abonelik,
    AbonelikDurumu,
    Fatura,
    FaturaDurumu,
    Kullanici,
    Organizasyon,
    Plan,
)
from bdm_veritabani.oturum import oturum_fabrikasi

router = APIRouter(tags=["faturalama"])

logger = logging.getLogger("kutyai.faturalama")

VARSAYILAN_SAYFA = 25
EN_BUYUK_SAYFA = 200

#: Durum guncelleyen Stripe olaylari; digerleri `uygulandi: false` doner.
_WEBHOOK_TURLERI = (
    "checkout.session.completed",
    "invoice.paid",
    "invoice.payment_failed",
    "customer.subscription.deleted",
)


class AbonelikIstegi(BaseModel):
    plan_id: int
    donem_gun: int = Field(default=30, ge=1, le=3650)


class OdemeOturumuIstegi(BaseModel):
    fatura_id: int


def _plan_sozlugu(plan: Plan) -> dict:
    return {
        "id": plan.id,
        "ad": plan.ad,
        "slug": plan.slug,
        "aylik_fiyat_kurus": plan.aylik_fiyat_kurus,
        "aylik_fiyat": kurus_bicimle(plan.aylik_fiyat_kurus, plan.para),
        "para": plan.para,
        "dahil_istek": plan.dahil_istek,
        "dahil_token": plan.dahil_token,
        "ozellikler": plan.ozellikler or {},
        "etkin": plan.etkin,
    }


def _abonelik_sozlugu(abonelik: Abonelik | None, plan: Plan | None) -> dict | None:
    if abonelik is None:
        return None
    return {
        "id": abonelik.id,
        "durum": abonelik.durum.value,
        "plan": _plan_sozlugu(plan) if plan else None,
        "donem_basi": abonelik.donem_basi.isoformat(),
        "donem_sonu": abonelik.donem_sonu.isoformat(),
        "saglayici": abonelik.saglayici,
        "dis_id": abonelik.dis_id,
        "erisim": erisim_var_mi(abonelik.durum),
    }


def _fatura_sozlugu(fatura: Fatura) -> dict:
    return {
        "id": fatura.id,
        "tutar_kurus": fatura.tutar_kurus,
        "tutar": kurus_bicimle(fatura.tutar_kurus, fatura.para),
        "para": fatura.para,
        "durum": fatura.durum.value,
        "kalemler": fatura.kalemler or [],
        "dis_id": fatura.dis_id,
        "olusturulma": fatura.olusturulma.isoformat(),
        "odeme_tarihi": fatura.odeme_tarihi.isoformat() if fatura.odeme_tarihi else None,
    }


async def _plan_getir(oturum: AsyncSession, plan_id: int) -> Plan:
    plan = await oturum.get(Plan, plan_id)
    if plan is None or not plan.etkin:
        raise Bulunamadi("plan_bulunamadi", {"plan_id": plan_id}, kod="plan_bulunamadi")
    return plan


async def _fatura_getir(oturum: AsyncSession, org_id: int, fatura_id: int) -> Fatura:
    fatura = await oturum.get(Fatura, fatura_id)
    if fatura is None or fatura.org_id != org_id:
        raise Bulunamadi("fatura_bulunamadi", {"fatura_id": fatura_id}, kod="fatura_bulunamadi")
    return fatura


@router.get("/faturalama/planlar")
async def planlari_listele(
    oturum: AsyncSession = Depends(veritabani_oturumu),
    _personel: Kullanici = Depends(gecerli_personel()),
) -> list[dict]:
    planlar = (
        await oturum.execute(sa.select(Plan).where(Plan.etkin.is_(True)).order_by(Plan.aylik_fiyat_kurus))
    ).scalars().all()
    return [_plan_sozlugu(plan) for plan in planlar]


@router.get("/faturalama/abonelik")
async def aboneligi_getir(
    oturum: AsyncSession = Depends(veritabani_oturumu),
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
    _personel: Kullanici = Depends(gecerli_personel()),
) -> dict | None:
    abonelik = await aktif_abonelik(oturum, organizasyon.id)
    if abonelik is None:
        return None
    plan = await oturum.get(Plan, abonelik.plan_id)
    return _abonelik_sozlugu(abonelik, plan)


@router.post("/faturalama/abonelik", status_code=201)
async def abonelik_baslat(
    veri: AbonelikIstegi,
    istek: Request,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
    personel: Kullanici = Depends(gecerli_personel(ORG_YONETIM_ROLLERI)),
) -> dict:
    """Plan secer, ilk faturayi uretir, saglayicida odeme oturumu acar.

    Odeme onayi saglayicidan (webhook) gelene kadar abonelik `deneme`,
    fatura `taslak` kalir; `yerel` surucude tahsilat manuel oldugu icin
    abonelik hemen `aktif` olur ve kota yazilir.
    """
    plan = await _plan_getir(oturum, veri.plan_id)
    saglayici = saglayici_sec()

    abonelik = await aktif_abonelik(oturum, organizasyon.id)
    yeni = abonelik is None
    if abonelik is None:
        abonelik = Abonelik(org_id=organizasyon.id, plan_id=plan.id)
        oturum.add(abonelik)
    abonelik.plan_id = plan.id
    abonelik.durum = AbonelikDurumu.deneme
    if yeni:
        abonelik.donem_basi = datetime.now(timezone.utc)
    abonelik.donem_sonu = donem_sonu(veri.donem_gun)
    abonelik.saglayici = saglayici.ad
    # Saglayici metadata'si ve kota icin kimlikler simdiden gerekli.
    await oturum.flush()

    fatura = Fatura(
        org_id=organizasyon.id,
        abonelik_id=abonelik.id,
        tutar_kurus=plan.aylik_fiyat_kurus,
        para=plan.para,
        durum=FaturaDurumu.taslak,
        kalemler=[
            {
                "aciklama": f"{plan.ad} — {veri.donem_gun} günlük abonelik",
                "tutar_kurus": plan.aylik_fiyat_kurus,
            }
        ],
    )
    oturum.add(fatura)
    await oturum.flush()

    baslat = await saglayici.abonelik_baslat(
        oturum,
        organizasyon=organizasyon,
        plan=plan,
        abonelik=abonelik,
        fatura=fatura,
    )
    abonelik.dis_id = str(baslat.get("dis_id") or "")
    fatura.dis_id = str(baslat.get("oturum_id") or baslat.get("dis_id") or "")

    if not baslat.get("odeme_bekliyor"):
        abonelik.durum = AbonelikDurumu.aktif
        await plan_kotasini_uygula(oturum, org_id=organizasyon.id, plan=plan)

    await islem_kaydet(
        oturum,
        "faturalama.abonelik_baslatildi",
        org_id=organizasyon.id,
        kullanici_id=personel.id,
        hedef_tur="abonelik",
        hedef_id=abonelik.id,
        ayrinti={
            "plan": plan.slug,
            "saglayici": saglayici.ad,
            "odeme_bekliyor": bool(baslat.get("odeme_bekliyor")),
        },
        ip=istek.client.host if istek.client else "",
    )
    await oturum.flush()
    return {
        "abonelik": _abonelik_sozlugu(abonelik, plan),
        "fatura": _fatura_sozlugu(fatura),
        "odeme_url": baslat.get("url"),
    }


@router.post("/faturalama/abonelik/iptal")
async def abonelik_iptal(
    istek: Request,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
    personel: Kullanici = Depends(gecerli_personel(ORG_YONETIM_ROLLERI)),
) -> dict:
    abonelik = await aktif_abonelik(oturum, organizasyon.id)
    if abonelik is None:
        raise Bulunamadi("abonelik_yok", kod="abonelik_yok")
    abonelik.durum = AbonelikDurumu.iptal
    await islem_kaydet(
        oturum,
        "faturalama.abonelik_iptal",
        org_id=organizasyon.id,
        kullanici_id=personel.id,
        hedef_tur="abonelik",
        hedef_id=abonelik.id,
        ip=istek.client.host if istek.client else "",
    )
    await oturum.flush()
    plan = await oturum.get(Plan, abonelik.plan_id)
    return _abonelik_sozlugu(abonelik, plan)


@router.get("/faturalama/faturalar")
async def faturalari_listele(
    sayfa: int = 1,
    boyut: int = VARSAYILAN_SAYFA,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
    _personel: Kullanici = Depends(gecerli_personel()),
) -> dict:
    if sayfa < 1 or boyut < 1 or boyut > EN_BUYUK_SAYFA:
        raise GecersizIstek("Sayfalama değerleri geçersiz.", {"sayfa": sayfa, "boyut": boyut})
    kosul = Fatura.org_id == organizasyon.id
    toplam = (
        await oturum.execute(sa.select(sa.func.count()).select_from(Fatura).where(kosul))
    ).scalar_one()
    satirlar = (
        await oturum.execute(
            sa.select(Fatura)
            .where(kosul)
            .order_by(Fatura.id.desc())
            .offset((sayfa - 1) * boyut)
            .limit(boyut)
        )
    ).scalars().all()
    return {
        "toplam": int(toplam),
        "sayfa": sayfa,
        "boyut": boyut,
        "kayitlar": [_fatura_sozlugu(fatura) for fatura in satirlar],
    }


@router.post("/faturalama/faturalar/{fatura_id}/odendi")
async def fatura_odendi(
    fatura_id: int,
    istek: Request,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
    personel: Kullanici = Depends(gecerli_personel(ORG_YONETIM_ROLLERI)),
) -> dict:
    """Manuel tahsilat: yalniz `yerel` surucude."""
    saglayici = saglayici_sec()
    if saglayici.ad != "yerel":
        raise GecersizIstek(
            "Bu ödeme sağlayıcısında fatura elle işaretlenemez.",
            {"saglayici": saglayici.ad},
        )
    fatura = await _fatura_getir(oturum, organizasyon.id, fatura_id)
    if fatura.durum == FaturaDurumu.odendi:
        raise GecersizIstek("Fatura zaten ödenmiş.", {"fatura_id": fatura_id})
    fatura.durum = FaturaDurumu.odendi
    fatura.odeme_tarihi = datetime.now(timezone.utc)
    abonelik = await aktif_abonelik(oturum, organizasyon.id)
    if abonelik is not None and abonelik.durum == AbonelikDurumu.gecikmis:
        abonelik.durum = AbonelikDurumu.aktif
    await islem_kaydet(
        oturum,
        "faturalama.fatura_odendi",
        org_id=organizasyon.id,
        kullanici_id=personel.id,
        hedef_tur="fatura",
        hedef_id=fatura.id,
        ip=istek.client.host if istek.client else "",
    )
    await oturum.flush()
    return _fatura_sozlugu(fatura)


@router.post("/faturalama/odeme-oturumu")
async def odeme_oturumu_olustur(
    veri: OdemeOturumuIstegi,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
    _personel: Kullanici = Depends(gecerli_personel(ORG_YONETIM_ROLLERI)),
) -> dict:
    fatura = await _fatura_getir(oturum, organizasyon.id, veri.fatura_id)
    saglayici = saglayici_sec()
    sonuc = await saglayici.odeme_oturumu(
        oturum, organizasyon=organizasyon, fatura=fatura
    )
    if sonuc.get("dis_id"):
        fatura.dis_id = str(sonuc["dis_id"])
        await oturum.flush()
    return sonuc


@router.post("/faturalama/webhook/stripe")
async def stripe_webhook(istek: Request) -> dict:
    """Stripe webhook'u — kimlik yok, imza dogrulamasi zorunlu."""
    from arkauc.app.cekirdek.ayarlar import ayarlar

    if (ayarlar.odeme_saglayici or "").strip().lower() != "stripe":
        raise GecersizIstek(
            "odeme_saglayici_yok",
            {"saglayici": ayarlar.odeme_saglayici},
            kod="odeme_saglayici_yok",
        )

    govde = await istek.body()
    basliklar = dict(istek.headers)
    saglayici = saglayici_sec()
    olay = await saglayici.webhook_isle(oturum=None, govde=govde, basliklar=basliklar)  # type: ignore[arg-type]

    async with oturum_fabrikasi()() as oturum:
        uygulandi = await _webhook_uygula(oturum, olay)
        await oturum.commit()
    return {"alindi": True, "tur": olay.get("tur"), "uygulandi": uygulandi}


async def _webhook_uygula(oturum: AsyncSession, olay: dict) -> bool:
    """Webhook olayini abonelik/fatura durumuna isler (spec §6).

    Esleme once `metadata` kimlikleri (`abonelik_id`, `fatura_id`), sonra
    saglayici `dis_id` kimlikleri (checkout oturumu, abonelik) uzerinden
    yapilir; hicbir kayda oturmayan olay uygulanmaz (`uygulandi: false`) ve
    gunluge yazilir. Odeme onaylandiginda abonelik `aktif` olur ve plan
    kotasi uygulanir.
    """
    tur = str(olay.get("tur", ""))
    if tur not in _WEBHOOK_TURLERI:
        return False

    abonelik = await _olay_aboneligi(oturum, olay)
    fatura = await _olay_faturasi(oturum, olay)
    # Kiraci tutarliligi: olay ancak kendi organizasyonunun kayitlarini
    # etkiler (checkout oturumundaki `client_reference_id`).
    beklenen_org = str(olay.get("org_id") or "")
    if beklenen_org.isdigit():
        org_id = int(beklenen_org)
        if abonelik is not None and abonelik.org_id != org_id:
            logger.warning("Stripe olayı başka organizasyonun aboneliğini hedefliyor: %s", org_id)
            abonelik = None
        if fatura is not None and fatura.org_id != org_id:
            logger.warning("Stripe olayı başka organizasyonun faturasını hedefliyor: %s", org_id)
            fatura = None
    if abonelik is None and fatura is not None and fatura.abonelik_id:
        abonelik = await oturum.get(Abonelik, fatura.abonelik_id)
    if abonelik is None and fatura is None:
        logger.warning(
            "Eşleşmeyen Stripe olayı: tur=%s dis_id=%s abonelik=%s fatura=%s",
            tur,
            olay.get("dis_id"),
            olay.get("abonelik_id") or olay.get("abonelik_dis_id") or "",
            olay.get("fatura_id"),
        )
        return False

    uygulandi = False
    if tur in ("checkout.session.completed", "invoice.paid"):
        if abonelik is not None:
            abonelik.durum = AbonelikDurumu.aktif
            abonelik_dis_id = str(olay.get("abonelik_dis_id") or "")
            if abonelik_dis_id:
                # Checkout oturumundan gelen gercek abonelik kimligi sonraki
                # fatura olaylarinin eslesmesini saglar.
                abonelik.dis_id = abonelik_dis_id
            plan = await oturum.get(Plan, abonelik.plan_id)
            if plan is not None:
                await plan_kotasini_uygula(oturum, org_id=abonelik.org_id, plan=plan)
            uygulandi = True
        if fatura is not None:
            fatura.durum = FaturaDurumu.odendi
            fatura.odeme_tarihi = datetime.now(timezone.utc)
            uygulandi = True
    elif tur == "invoice.payment_failed":
        if abonelik is not None:
            abonelik.durum = AbonelikDurumu.gecikmis
            uygulandi = True
        if fatura is not None:
            fatura.durum = FaturaDurumu.basarisiz
            uygulandi = True
    elif abonelik is not None:  # customer.subscription.deleted
        abonelik.durum = AbonelikDurumu.iptal
        uygulandi = True

    if not uygulandi:
        logger.warning(
            "Stripe olayı uygulanacak kayıt bulamadı: tur=%s abonelik=%s fatura=%s",
            tur,
            olay.get("abonelik_id") or olay.get("abonelik_dis_id") or olay.get("dis_id"),
            olay.get("fatura_id"),
        )
        return False

    await oturum.flush()
    return True


async def _olay_aboneligi(oturum: AsyncSession, olay: dict) -> Abonelik | None:
    """Olayi abonelige esler: metadata `abonelik_id`, saglayici kimlikleri."""
    abonelik_id = str(olay.get("abonelik_id") or "")
    if abonelik_id.isdigit():
        abonelik = await oturum.get(Abonelik, int(abonelik_id))
        if abonelik is not None:
            return abonelik
    for kimlik in (str(olay.get("abonelik_dis_id") or ""), str(olay.get("dis_id") or "")):
        if not kimlik:
            continue
        abonelik = (
            await oturum.execute(
                sa.select(Abonelik).where(Abonelik.dis_id == kimlik)
            )
        ).scalar_one_or_none()
        if abonelik is not None:
            return abonelik
    return None


async def _olay_faturasi(oturum: AsyncSession, olay: dict) -> Fatura | None:
    """Olayi faturaya esler: metadata `fatura_id`, saglayici `dis_id`."""
    fatura_id = str(olay.get("fatura_id") or "")
    if fatura_id.isdigit():
        fatura = await oturum.get(Fatura, int(fatura_id))
        if fatura is not None:
            return fatura
    dis_id = str(olay.get("dis_id") or "")
    if not dis_id:
        return None
    return (
        await oturum.execute(sa.select(Fatura).where(Fatura.dis_id == dis_id))
    ).scalar_one_or_none()


__all__ = ["router", "abonelik_durumu"]
