"""Denetim izi yardimcisi (spec §11)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from bdm_veritabani.modeller import IslemKaydi


async def islem_kaydet(
    oturum: AsyncSession,
    eylem: str,
    *,
    org_id: int | None = None,
    kullanici_id: int | None = None,
    hedef_tur: str = "",
    hedef_id: str | int = "",
    ayrinti: dict[str, Any] | None = None,
    ip: str = "",
) -> None:
    """Denetim izine bir satir ekler. Cagiran taraf commit eder."""
    oturum.add(
        IslemKaydi(
            org_id=org_id,
            kullanici_id=kullanici_id,
            eylem=eylem,
            hedef_tur=hedef_tur,
            hedef_id=str(hedef_id),
            ayrinti=ayrinti or {},
            ip=ip,
        )
    )
    await oturum.flush()
