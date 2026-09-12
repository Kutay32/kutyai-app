"""Saklama politikasi: eski kayitlarin temizligi (spec §11)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek.ayarlar_db import ayar_oku
from bdm_veritabani.modeller import Konusma


async def eski_konusmalari_sil(
    oturum: AsyncSession, gun: int | None = None
) -> int:
    """`gun` gunden eski konusmalari siler; silinen kayit sayisini dondurur."""
    if gun is None:
        gun = int(await ayar_oku(oturum, "saklama_gun", 90) or 90)
    gun = max(1, int(gun))
    esik = datetime.now(timezone.utc) - timedelta(days=gun)
    kayitlar = (
        await oturum.execute(sa.select(Konusma).where(Konusma.olusturulma < esik))
    ).scalars().all()
    for konusma in kayitlar:
        await oturum.delete(konusma)
    await oturum.flush()
    return len(kayitlar)
