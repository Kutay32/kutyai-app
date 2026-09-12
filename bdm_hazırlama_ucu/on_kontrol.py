"""On kontrol: Docker, GPU, disk ve imaj hazirligi (spec §7.5, §10).

GPU gerektiren saglayicida (vllm, tgi) GPU yoksa `uygun=False` ve spec §10'daki
Turkce yonlendirme mesaji `uyarilar` listesine eklenir.
"""

from __future__ import annotations

import logging
import pathlib
import shutil
from typing import Any

from arkauc.app.cekirdek.hatalar import KutyaiHatasi
from arkauc.app.servisler.konteyner import SurucuDurumu, surucu_al
from bdm_hazırlama_ucu.manifest import bellek_tahmini
from bdm_listesi.saglayicilar import saglayici_bilgisi
from bdm_veritabani.modeller import Bdm

logger = logging.getLogger("kutyai.hazirlama")

# spec §10 — GPU eksikliginde panelde gosterilen yonlendirme.
GPU_UYARI_MESAJI = (
    "Bu model GPU gerektirir; Ollama gibi CPU uyumlu bir sağlayıcı seçin "
    "veya GPU çalışma zamanını kurun."
)
DOCKER_UYARI_MESAJI = "Docker bulunamadı; konteyner tabanlı hazırlama yapılamaz."
# Docker gerektiren yerel saglayicilar: GPU olmadan da imaj calistirilamaz.
DOCKER_ZORUNLU_SAGLAYICILAR = frozenset({"vllm", "tgi"})


def _kok_dizini() -> pathlib.Path:
    """Disk sorgusu icin kok dizin (surucunun bulundugu birim)."""
    return pathlib.Path(__file__).resolve().anchor


def _disk_gb() -> float:
    try:
        kullanim = shutil.disk_usage(_kok_dizini())
    except OSError:  # pragma: no cover - altyapi arizasi
        return 0.0
    return round(kullanim.free / (1024**3), 1)


async def _surucu_durumu(bdm: Bdm) -> SurucuDurumu:
    try:
        return await surucu_al(bdm.saglayici.value, bdm.yerel_mi).durum()
    except KutyaiHatasi as hata:
        logger.warning("BDM %s icin surucu durumu alinamadi: %s", bdm.id, hata.mesaj)
        return SurucuDurumu(surucu_adi="yok", mesaj=hata.mesaj)
    except Exception as hata:  # pragma: no cover - beklenmeyen surucu hatasi
        logger.exception("BDM %s icin surucu durumu alinamadi.", bdm.id)
        return SurucuDurumu(surucu_adi="yok", mesaj=str(hata))


async def on_kontrol(bdm: Bdm) -> dict[str, Any]:
    """Hazirlama oncesi ortam kontrolu; `{docker, gpu, disk_gb, image_var, uygun, uyarilar}`."""
    bilgi = saglayici_bilgisi(bdm.saglayici.value)
    durum = await _surucu_durumu(bdm)
    disk_gb = _disk_gb()

    uyarilar: list[str] = []
    uygun = True

    if bilgi.gpu_gerekir and not durum.gpu_var:
        uygun = False
        uyarilar.append(GPU_UYARI_MESAJI)

    if bilgi.konteyner_image is not None and not durum.docker_var:
        if bilgi.ad in DOCKER_ZORUNLU_SAGLAYICILAR:
            uygun = False
        uyarilar.append(DOCKER_UYARI_MESAJI)

    image = bilgi.konteyner_image
    image_var = bool(image and image in (durum.image_onbellek or []))
    if image is not None and not image_var:
        uyarilar.append(
            f"'{image}' imajı yerel önbellekte yok; ilk çalıştırmada indirilecek."
        )

    gereken_gb = bellek_tahmini(bdm)
    if disk_gb and disk_gb < gereken_gb:
        uyarilar.append(
            f"Boş disk alanı {disk_gb} GB; bu model için yaklaşık {gereken_gb} GB önerilir."
        )

    return {
        "docker": durum.docker_var,
        "gpu": durum.gpu_var,
        "disk_gb": disk_gb,
        "image_var": image_var,
        "uygun": uygun,
        "uyarilar": uyarilar,
    }
