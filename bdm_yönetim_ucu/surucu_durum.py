"""Konteyner çalışma zamanı özeti — `GET /surucu/durum` (spec §7.6)."""

from __future__ import annotations

from typing import Any

from arkauc.app.cekirdek.hatalar import SurucuYok
from arkauc.app.servisler.konteyner import surucu_al


def _bos() -> dict[str, Any]:
    return {
        "surucu": "yok",
        "docker": False,
        "gpu": False,
        "gpu_listesi": [],
        "image_onbellek": [],
        "mesaj": "",
    }


async def durum_ozeti() -> dict[str, Any]:
    """Docker, GPU listesi ve imaj önbelleği özetini döndürür.

    `surucu_al("ozel", True)` dondurulmuş seçim kuralına göre Docker sürücüsünü verir.
    """
    try:
        durum = await surucu_al("ozel", True).durum()
    except SurucuYok as hata:
        return {**_bos(), "mesaj": hata.mesaj}
    except Exception as hata:  # pragma: no cover - altyapi arizasi
        return {**_bos(), "mesaj": f"Çalışma zamanı durumu okunamadı: {hata}"}
    return {
        "surucu": durum.surucu_adi,
        "docker": durum.docker_var,
        "gpu": durum.gpu_var,
        "gpu_listesi": list(durum.gpu_listesi),
        "image_onbellek": list(durum.image_onbellek),
        "mesaj": durum.mesaj,
    }
