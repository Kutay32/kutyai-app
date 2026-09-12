"""Yerel (manuel tahsilat) odeme surucusu (spec §6).

Saglayici cagrisi yoktur: abonelik ve fatura kayitlari yerelde tutulur,
tahsilat `POST /faturalama/faturalar/{id}/odendi` ile isaretlenir. Offline
ortamda uctan uca calisir.
"""

from __future__ import annotations

from typing import Any, Mapping

from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek.hatalar import GecersizIstek
from bdm_veritabani.modeller import Organizasyon, Plan


class YerelSaglayici:
    ad = "yerel"

    async def abonelik_baslat(
        self, oturum: AsyncSession, *, organizasyon: Organizasyon, plan: Plan
    ) -> dict[str, Any]:
        return {"dis_id": "", "url": None, "saglayici": self.ad}

    async def odeme_oturumu(
        self, oturum: AsyncSession, *, organizasyon: Organizasyon, fatura: Any
    ) -> dict[str, Any]:
        return {"dis_id": "", "url": None, "saglayici": self.ad}

    async def webhook_isle(
        self, oturum: AsyncSession, *, govde: bytes, basliklar: Mapping[str, str]
    ) -> dict[str, Any]:
        raise GecersizIstek(
            "Yerel ödeme sağlayıcısında webhook bulunmaz.",
            {"saglayici": self.ad},
        )
