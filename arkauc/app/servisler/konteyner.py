"""Konteyner orkestrasyonu sozlesmesi (spec §10) — DONDURULMUS.

Bu modul yalnizca arayuzu, durum nesnelerini ve test surucusunu tanimlar.
Gercek suruculer `konteyner_docker.py` (Docker + GPU) ve `konteyner_yerel.py`
(Ollama) icinde yasar ve `surucu_al()` uzerinden secilir.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from arkauc.app.cekirdek.hatalar import SurucuYok


@dataclass(slots=True)
class SurucuDurumu:
    """Calisma zamaninin yetenekleri."""

    surucu_adi: str = "yok"
    docker_var: bool = False
    gpu_var: bool = False
    gpu_listesi: list[str] = field(default_factory=list)
    image_onbellek: list[str] = field(default_factory=list)
    surum: str = ""
    mesaj: str = ""


@dataclass(slots=True)
class SaglikDurumu:
    """Tek bir konteynerin sagligi."""

    calisiyor: bool = False
    hazir: bool = False
    mesaj: str = ""
    ayrinti: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class KonteynerSurucusu(Protocol):
    """Tum suruculerin uymasi gereken sozlesme."""

    ad: str

    async def durum(self) -> SurucuDurumu: ...

    async def baslat(self, bdm: dict[str, Any], manifest: dict[str, Any]) -> str:
        """Konteyneri baslatir ve konteyner kimligini dondurur."""
        ...

    async def durdur(self, konteyner_id: str) -> None: ...

    async def sil(self, konteyner_id: str) -> None: ...

    async def saglik(self, konteyner_id: str) -> SaglikDurumu: ...

    def gunlukler(self, konteyner_id: str, satir: int = 200) -> AsyncIterator[str]: ...


class SahteSurucu:
    """Bellek ici surucu: test, onizleme ve GPU'suz gelistirme icin."""

    ad = "sahte"

    def __init__(
        self,
        *,
        docker_var: bool = True,
        gpu_var: bool = False,
        gpu_listesi: list[str] | None = None,
        image_onbellek: list[str] | None = None,
    ) -> None:
        self.docker_var = docker_var
        self.gpu_var = gpu_var
        self.gpu_listesi = gpu_listesi if gpu_listesi is not None else (["NVIDIA GeForce RTX 4090"] if gpu_var else [])
        self.image_onbellek = image_onbellek if image_onbellek is not None else ["ollama/ollama:latest"]
        self.konteynerler: dict[str, dict[str, Any]] = {}
        self.gunluk_satirlari: list[str] = [
            "sahte konteyner baslatildi",
            "model yuklendi",
            "hazir",
        ]
        self.baslatma_hatasi: Exception | None = None
        self.cagrilar: list[tuple[str, dict[str, Any]]] = []

    async def durum(self) -> SurucuDurumu:
        return SurucuDurumu(
            surucu_adi=self.ad,
            docker_var=self.docker_var,
            gpu_var=self.gpu_var,
            gpu_listesi=list(self.gpu_listesi),
            image_onbellek=list(self.image_onbellek),
            surum="sahte-1.0",
            mesaj="" if self.docker_var else "Docker bulunamadi (sahte surucu).",
        )

    async def baslat(self, bdm: dict[str, Any], manifest: dict[str, Any]) -> str:
        if self.baslatma_hatasi is not None:
            raise self.baslatma_hatasi
        kimlik = f"sahte-{bdm.get('slug', 'bdm')}-{len(self.konteynerler) + 1}"
        self.konteynerler[kimlik] = {
            "bdm_id": bdm.get("id"),
            "manifest": manifest,
            "durum": "calisiyor",
            "baslama": time.time(),
        }
        self.cagrilar.append(("baslat", {"konteyner_id": kimlik, "manifest": manifest}))
        return kimlik

    async def durdur(self, konteyner_id: str) -> None:
        self._gerekli(konteyner_id)
        self.konteynerler[konteyner_id]["durum"] = "durdu"
        self.cagrilar.append(("durdur", {"konteyner_id": konteyner_id}))

    async def sil(self, konteyner_id: str) -> None:
        self.konteynerler.pop(konteyner_id, None)
        self.cagrilar.append(("sil", {"konteyner_id": konteyner_id}))

    async def saglik(self, konteyner_id: str) -> SaglikDurumu:
        kayit = self.konteynerler.get(konteyner_id)
        if kayit is None:
            return SaglikDurumu(calisiyor=False, hazir=False, mesaj="Konteyner bulunamadı.")
        calisiyor = kayit["durum"] == "calisiyor"
        return SaglikDurumu(
            calisiyor=calisiyor,
            hazir=calisiyor,
            mesaj="Çalışıyor." if calisiyor else "Durduruldu.",
            ayrinti={"konteyner_id": konteyner_id},
        )

    async def gunlukler(self, konteyner_id: str, satir: int = 200) -> AsyncIterator[str]:  # type: ignore[override]
        self._gerekli(konteyner_id)
        for satir_metni in self.gunluk_satirlari[-satir:]:
            yield satir_metni

    def _gerekli(self, konteyner_id: str) -> None:
        if konteyner_id not in self.konteynerler:
            raise SurucuYok("Konteyner bulunamadı.")


AKTIF_SURUCU: KonteynerSurucusu | None = None


def surucu_ata(surucu: KonteynerSurucusu | None) -> None:
    """Testlerin ve onizlemenin surucuyu gecici olarak gecersiz kilmasini saglar."""
    global AKTIF_SURUCU
    AKTIF_SURUCU = surucu


def surucu_temizle() -> None:
    surucu_ata(None)


def surucu_al(saglayici: str, yerel_mi: bool) -> KonteynerSurucusu:
    """Saglayiciya uygun surucuyu secer."""
    if AKTIF_SURUCU is not None:
        return AKTIF_SURUCU
    try:
        if saglayici == "ollama" or not yerel_mi:
            from arkauc.app.servisler.konteyner_yerel import YerelSurucusu

            return YerelSurucusu()
        from arkauc.app.servisler.konteyner_docker import DockerSurucusu

        return DockerSurucusu()
    except ImportError as hata:
        raise SurucuYok(
            "Konteyner çalışma zamanı bulunamadı. Docker kurulu ve çalışır durumda olmalıdır."
        ) from hata
