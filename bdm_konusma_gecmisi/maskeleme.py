"""Maskeleme ayarini veritabanindan okur (spec §11).

Panelden `PUT /ayarlar` ile degistirilen `maskeleme_aktif` degeri etkili olmali;
ortam degiskeni yalnizca veritabani bos oldugunda yedek yol olarak kullanilir.
"""

from __future__ import annotations

import re

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from bdm_veritabani.modeller import MaskelemeKurali

Kural = tuple[str, re.Pattern[str]]


async def kurallari_yukle(oturum: AsyncSession) -> list[Kural]:
    """Etkin maskeleme kurallarini sirayla dondurur."""
    satirlar = (
        await oturum.execute(
            sa.select(MaskelemeKurali)
            .where(MaskelemeKurali.etkin.is_(True))
            .order_by(MaskelemeKurali.sira)
        )
    ).scalars().all()
    return [(satir.ad, re.compile(satir.desen)) for satir in satirlar]


def maskele(metin: str, kurallar: list[Kural]) -> str:
    """Metindeki hassas desenleri `[MASKELENDI:ad]` ile degistirir."""
    if not metin:
        return metin
    sonuc = metin
    for ad, desen in kurallar:
        sonuc = desen.sub(f"[MASKELENDI:{ad}]", sonuc)
    return sonuc


async def maskeleme_etkin(oturum: AsyncSession) -> bool:
    """Panel ayari oncelikli, ortam degiskeni yedek."""
    from arkauc.app.cekirdek.ayarlar import ayarlar
    from arkauc.app.cekirdek.ayarlar_db import ayar_oku

    deger = await ayar_oku(oturum, "maskeleme_aktif", None)
    if deger is None:
        return bool(ayarlar.maskeleme_aktif)
    return bool(deger)


async def maskele_metin(oturum: AsyncSession, metin: str) -> str:
    if not metin:
        return metin
    if not await maskeleme_etkin(oturum):
        return metin
    return maskele(metin, await kurallari_yukle(oturum))
