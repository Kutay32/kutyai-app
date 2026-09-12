"""Tek konteynerin sağlık görünümü (spec §7.6)."""

from __future__ import annotations

from typing import Any

from arkauc.app.servisler.konteyner import SaglikDurumu
from bdm_veritabani.modeller import Bdm

from . import yasam_dongusu


def sozluk(saglik: SaglikDurumu) -> dict[str, Any]:
    """`GET /{bdm_id}/saglik` yanıtı."""
    return {
        "calisiyor": saglik.calisiyor,
        "hazir": saglik.hazir,
        "mesaj": saglik.mesaj,
        "ayrinti": saglik.ayrinti,
    }


async def saglik_ozeti(bdm: Bdm) -> dict[str, Any]:
    """Çalışan konteynerin sağlığını API sözlüğü olarak döndürür."""
    return sozluk(await yasam_dongusu.saglik_al(bdm))


async def durum_ozeti(bdm: Bdm) -> dict[str, Any]:
    """`GET /{bdm_id}/durum` yanıtı: durum + konteyner kimliği + sağlık özeti."""
    saglik = await yasam_dongusu.saglik_al(bdm)
    return {
        "durum": bdm.durum.value,
        "konteyner_id": yasam_dongusu.konteyner_kimligi(bdm, zorunlu=False),
        "saglik": {
            "calisiyor": saglik.calisiyor,
            "hazir": saglik.hazir,
            "mesaj": saglik.mesaj,
        },
    }
