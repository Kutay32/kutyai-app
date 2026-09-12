"""Kullanim uclari: ozet ve zaman serisi (spec §7.7, §13)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek.bagimliliklar import (
    IstemciKimligi,
    gecerli_istemci,
    gecerli_personel,
    veritabani_oturumu,
)
from arkauc.app.cekirdek.hatalar import GecersizIstek
from arkauc.app.servisler.kota import kapsam_kota_durumu, kapsam_sec
from bdm_konusma_gecmisi import kullanim_ozeti, kullanim_zaman_serisi
from bdm_veritabani.modeller import KullanimKaydi, KotaKapsami, Kullanici

router = APIRouter(tags=["kullanim"])

OZET_ALANLARI = (
    "toplam_istek",
    "toplam_token",
    "basarili",
    "hatali",
    "kota_asimi",
    "ortalama_gecikme_ms",
)
KIRILIMLAR = ("bdm", "kullanici")
KAPSAM_SUTUNLARI = {
    KotaKapsami.kullanici: KullanimKaydi.kullanici_id,
    KotaKapsami.api_anahtari: KullanimKaydi.api_anahtari_id,
}


def _kapsam_kosulu(kimlik: IstemciKimligi) -> sa.ColumnElement[bool]:
    """Cagiranin kapsamina (anahtar varsa anahtar, yoksa kullanici) suzgec uretir."""
    secim = kapsam_sec(kullanici_id=kimlik.kullanici_id, api_anahtari_id=kimlik.anahtar_id)
    if secim is None:
        return sa.false()
    kapsam, kapsam_id = secim
    return KAPSAM_SUTUNLARI[kapsam] == kapsam_id


@router.get("/kullanim/ozet")
async def ozet(
    gun: int = Query(30, ge=1, le=365),
    oturum: AsyncSession = Depends(veritabani_oturumu),
    _personel: Kullanici = Depends(gecerli_personel()),
) -> dict[str, object]:
    """Son `gun` gunun kullanim ozeti."""
    sonuc = await kullanim_ozeti(oturum, gun=gun)
    return {alan: sonuc[alan] for alan in OZET_ALANLARI}


@router.get("/kullanim/zaman-serisi")
async def zaman_serisi(
    gun: int = Query(30, ge=1, le=365),
    kirilim: str = Query("bdm"),
    oturum: AsyncSession = Depends(veritabani_oturumu),
    _personel: Kullanici = Depends(gecerli_personel()),
) -> dict[str, object]:
    """`bdm` veya `kullanici` kiriliminda istek/token serisi."""
    if kirilim not in KIRILIMLAR:
        raise GecersizIstek(
            "kirilim 'bdm' veya 'kullanici' olmalıdır.", {"alan": "kirilim"}
        )
    sonuc = await kullanim_zaman_serisi(oturum, gun=gun, kirilim=kirilim)
    return {"seri": sonuc["seri"]}


@router.get("/kullanim/benim")
async def benim(
    gun: int = Query(30, ge=1, le=365),
    oturum: AsyncSession = Depends(veritabani_oturumu),
    kimlik: IstemciKimligi = Depends(gecerli_istemci),
) -> dict[str, object]:
    """Cagiran kullanicinin/anahtarin kisisel kullanim ozeti (API §13)."""
    esik = datetime.now(timezone.utc) - timedelta(days=gun)
    kosullar = (KullanimKaydi.olusturulma >= esik, _kapsam_kosulu(kimlik))

    adet, girdi, cikti, gecikme_toplam, gecikme_adet = (
        await oturum.execute(
            sa.select(
                sa.func.count(),
                sa.func.coalesce(sa.func.sum(KullanimKaydi.girdi_token), 0),
                sa.func.coalesce(sa.func.sum(KullanimKaydi.cikti_token), 0),
                sa.func.coalesce(sa.func.sum(KullanimKaydi.gecikme_ms), 0),
                sa.func.coalesce(
                    sa.func.sum(sa.case((KullanimKaydi.gecikme_ms > 0, 1), else_=0)), 0
                ),
            ).where(*kosullar)
        )
    ).one()

    satirlar = (
        await oturum.execute(
            sa.select(
                KullanimKaydi.olusturulma,
                KullanimKaydi.girdi_token,
                KullanimKaydi.cikti_token,
            )
            .where(*kosullar)
            .order_by(KullanimKaydi.olusturulma)
        )
    ).all()
    gunluk: dict[str, int] = {}
    for olusturulma, gun_girdi, gun_cikti in satirlar:
        tarih = olusturulma.date().isoformat()
        gunluk[tarih] = gunluk.get(tarih, 0) + int(gun_girdi or 0) + int(gun_cikti or 0)

    return {
        "gun": gun,
        "toplam_istek": int(adet),
        "toplam_token": int(girdi) + int(cikti),
        "girdi_token": int(girdi),
        "cikti_token": int(cikti),
        "ortalama_gecikme_ms": (
            round(int(gecikme_toplam) / int(gecikme_adet)) if int(gecikme_adet) else 0
        ),
        "kota": await kapsam_kota_durumu(
            oturum, kullanici_id=kimlik.kullanici_id, api_anahtari_id=kimlik.anahtar_id
        ),
        "seri": [{"tarih": tarih, "token": token} for tarih, token in sorted(gunluk.items())],
    }
