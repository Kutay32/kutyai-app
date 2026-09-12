"""Dil ve sozluk uclari (spec §10.1).

Bu uclar kimlik dogrulamasi GEREKTIRMEZ: arayuzler giris ekranindan once
katalogu yuklemek zorundadir ve icerik hassas veri tasimaz.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from arkauc.app.cekirdek.i18n import (
    DESTEKLENEN_DILLER,
    dil_listesi,
    katalog,
)

router = APIRouter(tags=["i18n"])


@router.get("/i18n/diller")
async def diller() -> list[dict[str, object]]:
    """Desteklenen diller ve varsayilan."""
    return dil_listesi()


@router.get("/i18n/sozluk/{dil}")
async def sozluk(dil: str) -> dict[str, str]:
    """Arayuzun kullanacagi mesaj katalogu."""
    kod = dil.strip().lower()
    if kod not in DESTEKLENEN_DILLER:
        raise HTTPException(status_code=404, detail="Dil desteklenmiyor.")
    return dict(katalog(kod))
