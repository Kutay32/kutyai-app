"""Ollama (yerel) sürücüsü — spec §10.

Ollama zaten çalışan bir sunucudur; konteyner oluşturulmaz. `durum` ve
`saglik` doğrudan REST uçlarından yoklanır.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx

from arkauc.app.cekirdek.hatalar import SurucuYok, UstSaglayiciHatasi
from arkauc.app.servisler.konteyner import SaglikDurumu, SurucuDurumu

logger = logging.getLogger("kutyai.konteyner.yerel")

VARSAYILAN_TEMEL = "http://localhost:11434"
ZAMAN_ASIMI = 4.0


class YerelSurucusu:
    """Ollama REST tabanlı sürücü: `/api/tags` erişilebilirliği ve model boşaltma.

    `baslat` sırasında BDM'nin Ollama kök adresi ve model adı, konteyner kimliği
    altında hatırlanır; `saglik`, `gunlukler` ve `durdur` bu kaydı kullanır.
    """

    ad = "yerel"

    def __init__(self, temel_url: str | None = None) -> None:
        self._temel_url = self._temel(temel_url)
        # kimlik → {"temel": ..., "model": ...}
        self._bdmler: dict[str, dict[str, str]] = {}

    @staticmethod
    def _temel(url: str | None) -> str:
        """OpenAI uyumlu `/v1` ekinden arındırılmış Ollama kök adresi."""
        ham = (url or VARSAYILAN_TEMEL).strip().rstrip("/")
        if ham.endswith("/v1"):
            ham = ham[:-3]
        return ham.rstrip("/") or VARSAYILAN_TEMEL

    def _adres(self, konteyner_id: str) -> tuple[str, str]:
        """Konteyner kimliği için BDM'nin kayıtlı Ollama kök adresini döndürür.

        Adres `baslat` sırasında BDM'nin `temel_url` alanından hatırlanır; kayıt
        yoksa (süreç yeniden başladıysa) varsayılana düşülür ve bu, `ayrinti`
        içinde `adres_kaynagi="varsayilan"` olarak bildirilir.
        """
        kayit = self._bdmler.get(konteyner_id) or {}
        temel = str(kayit.get("temel") or "")
        if temel:
            return temel, "bellek"
        return self._temel_url, "varsayilan"

    def _yokla(self, temel: str) -> tuple[bool, list[str], str]:
        """`GET /api/tags` ile erişilebilirliği ve yerel modelleri döndürür."""
        try:
            yanit = httpx.get(f"{temel}/api/tags", timeout=ZAMAN_ASIMI)
        except Exception as hata:
            logger.error(
                "Ollama sunucusuna ulaşılamadı (%s): %s", temel, type(hata).__name__
            )
            return False, [], f"Ollama sunucusuna ulaşılamadı ({temel})."
        if yanit.status_code >= 400:
            return False, [], f"Ollama sunucusu {yanit.status_code} döndü ({temel})."
        try:
            ham = yanit.json().get("models") or []
            modeller = [str(m.get("name") or m.get("model") or "") for m in ham]
        except Exception:  # pragma: no cover - bozuk yanit
            modeller = []
        return True, [m for m in modeller if m], "Ollama sunucusu erişilebilir."

    async def durum(self) -> SurucuDurumu:
        return await asyncio.to_thread(self._durum)

    def _durum(self) -> SurucuDurumu:
        erisilebilir, modeller, mesaj = self._yokla(self._temel_url)
        return SurucuDurumu(
            surucu_adi=self.ad,
            docker_var=False,
            gpu_var=False,
            gpu_listesi=[],
            image_onbellek=modeller if erisilebilir else [],
            surum="",
            mesaj=mesaj,
        )

    async def baslat(self, bdm: dict[str, Any], manifest: dict[str, Any]) -> str:
        temel = self._temel(bdm.get("temel_url"))
        erisilebilir, _, mesaj = await asyncio.to_thread(self._yokla, temel)
        if not erisilebilir:
            raise SurucuYok(mesaj)
        kimlik = f"yerel:{bdm.get('slug') or 'bdm'}"
        self._bdmler[kimlik] = {"temel": temel, "model": str(bdm.get("upstream_model") or "")}
        return kimlik

    async def durdur(self, konteyner_id: str) -> None:
        """Modeli bellekten boşaltır; Ollama sunucusu çalışmaya devam eder.

        Boşaltma isteği `POST {temel}/api/generate {"keep_alive": 0}` ile
        gönderilir. Kayıt yoksa ya da istek başarısız olursa sessizce
        yutulmaz: `SurucuYok` / `UstSaglayiciHatasi` fırlatılır.
        """
        kayit = self._bdmler.get(konteyner_id)
        if kayit is None:
            raise SurucuYok(
                "Bu model için çalışan Ollama kaydı bulunamadı; model bellekten boşaltılamadı.",
                {"konteyner_id": konteyner_id},
            )
        await asyncio.to_thread(self._bosalt, kayit)
        logger.info(
            "Ollama modeli bellekten boşaltıldı: %s (%s)", kayit.get("model"), konteyner_id
        )

    @staticmethod
    def _bosalt(kayit: dict[str, str]) -> None:
        temel = str(kayit.get("temel") or VARSAYILAN_TEMEL)
        model = str(kayit.get("model") or "")
        if not model:
            raise SurucuYok(
                "Kayıtlı model adı olmadığı için Ollama modeli bellekten boşaltılamadı.",
                {"temel_url": temel},
            )
        try:
            yanit = httpx.post(
                f"{temel}/api/generate",
                json={"model": model, "keep_alive": 0, "prompt": ""},
                timeout=ZAMAN_ASIMI,
            )
        except Exception as hata:
            logger.exception("Ollama modeli boşaltılamadı (%s).", temel)
            raise UstSaglayiciHatasi(
                "Ollama sunucusuna ulaşılamadı; model bellekten boşaltılamadı.",
                {"temel_url": temel, "model": model},
            ) from hata
        if yanit.status_code >= 400:
            raise UstSaglayiciHatasi(
                f"Ollama sunucusu model boşaltma isteğine {yanit.status_code} döndü.",
                {"temel_url": temel, "model": model},
            )

    async def sil(self, konteyner_id: str) -> None:
        self._bdmler.pop(konteyner_id, None)

    async def saglik(self, konteyner_id: str) -> SaglikDurumu:
        temel, kaynak = self._adres(konteyner_id)
        erisilebilir, modeller, mesaj = await asyncio.to_thread(self._yokla, temel)
        return SaglikDurumu(
            calisiyor=erisilebilir,
            hazir=erisilebilir,
            mesaj=mesaj,
            ayrinti={
                "konteyner_id": konteyner_id,
                "temel_url": temel,
                "adres_kaynagi": kaynak,
                "modeller": modeller,
            },
        )

    async def gunlukler(self, konteyner_id: str, satir: int = 200) -> AsyncIterator[str]:
        temel, _ = self._adres(konteyner_id)
        yield (
            "Ollama günlükleri REST üzerinden okunamaz; sunucu günlükleri için "
            f"'ollama serve' çıktısına bakın ({temel})."
        )
