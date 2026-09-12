"""Konteyner günlüklerinin SSE akışı (spec §7.6)."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from arkauc.app.servisler.konteyner import KonteynerSurucusu

SSE_BASLIKLARI = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
}


def cerceve(olay: str, veri: dict[str, object]) -> str:
    """Tek bir SSE olayı üretir."""
    return f"event: {olay}\ndata: {json.dumps(veri, ensure_ascii=False)}\n\n"


async def akis(
    surucu: KonteynerSurucusu, konteyner_id: str, satir: int
) -> AsyncIterator[str]:
    """Sürücü günlüklerini `event: satir` + `data: {"metin": ...}` olarak akıtır."""
    async for metin in surucu.gunlukler(konteyner_id, satir):
        yield cerceve("satir", {"metin": metin})
