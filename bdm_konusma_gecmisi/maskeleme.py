"""KVKK maskeleme: kayit aninda uygulanir, geri donusturulemez (spec §11)."""

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


async def maskele_metin(oturum: AsyncSession, metin: str) -> str:
    if not metin:
        return metin
    from arkauc.app.cekirdek.ayarlar import ayarlar

    if not ayarlar.maskeleme_aktif:
        return metin
    return maskele(metin, await kurallari_yukle(oturum))
