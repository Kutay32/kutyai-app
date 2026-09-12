"""`ayar` tablosu icin okuma/yazma yardimcilari (dondurulmus cekirdek)."""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from bdm_veritabani.modeller import Ayar


async def ayar_oku(oturum: AsyncSession, anahtar: str, varsayilan: Any = None) -> Any:
    satir = await oturum.get(Ayar, anahtar)
    if satir is None:
        return varsayilan
    return satir.deger


async def ayar_yaz(oturum: AsyncSession, anahtar: str, deger: Any) -> None:
    satir = await oturum.get(Ayar, anahtar)
    if satir is None:
        oturum.add(Ayar(anahtar=anahtar, deger=deger))
    else:
        satir.deger = deger
    await oturum.flush()


async def tum_ayarlar(oturum: AsyncSession) -> dict[str, Any]:
    satirlar = (await oturum.execute(sa.select(Ayar))).scalars().all()
    return {satir.anahtar: satir.deger for satir in satirlar}
