"""Kullanim uclari: ozet ve zaman serisi (spec §7.7, §13)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek.bagimliliklar import gecerli_personel, veritabani_oturumu
from arkauc.app.cekirdek.hatalar import GecersizIstek
from bdm_konusma_gecmisi import kullanim_ozeti, kullanim_zaman_serisi
from bdm_veritabani.modeller import Kullanici

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
