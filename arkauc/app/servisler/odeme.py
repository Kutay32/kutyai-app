"""Odeme saglayici sozlesmesi ve surucu secimi (spec §6)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Protocol

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek.ayarlar import ayarlar
from arkauc.app.cekirdek.hatalar import GecersizIstek
from bdm_veritabani.modeller import (
    Abonelik,
    AbonelikDurumu,
    Kota,
    KotaKapsami,
    Organizasyon,
    Plan,
)


class OdemeSaglayici(Protocol):
    """Tum odeme suruculerinin uymasi gereken sozlesme."""

    ad: str

    async def abonelik_baslat(
        self, oturum: AsyncSession, *, organizasyon: Organizasyon, plan: Plan
    ) -> dict[str, Any]:
        """Abonelik kaydini saglayicida baslatir: `{dis_id, url|None}`."""
        ...

    async def odeme_oturumu(
        self, oturum: AsyncSession, *, organizasyon: Organizasyon, fatura: Any
    ) -> dict[str, Any]:
        """Fatura icin odeme oturumu: `{dis_id, url|None}`."""
        ...

    async def webhook_isle(
        self,
        oturum: AsyncSession | None,
        *,
        govde: bytes,
        basliklar: Mapping[str, str],
    ) -> dict[str, Any]:
        """Saglayici webhook'unu dogrular ve durum guncellemesi dondurur.

        `oturum` None olabilir: dogrulama veritabani gerektirmez.
        """
        ...


def saglayici_sec() -> OdemeSaglayici:
    """`KUTYAI_ODEME_SAGLAYICI` ayarina gore surucu."""
    ad = (ayarlar.odeme_saglayici or "yerel").strip().lower()
    if ad == "stripe":
        from arkauc.app.servisler.odeme_stripe import StripeSaglayici

        if not (ayarlar.stripe_gizli_anahtar or "").strip():
            raise GecersizIstek(
                "odeme_saglayici_yok", {"saglayici": "stripe"}, kod="odeme_saglayici_yok"
            )
        return StripeSaglayici()
    if ad == "yerel":
        from arkauc.app.servisler.odeme_yerel import YerelSaglayici

        return YerelSaglayici()
    raise GecersizIstek("odeme_saglayici_yok", {"saglayici": ad}, kod="odeme_saglayici_yok")


async def aktif_abonelik(oturum: AsyncSession, org_id: int) -> Abonelik | None:
    return (
        await oturum.execute(
            sa.select(Abonelik)
            .where(Abonelik.org_id == org_id)
            .order_by(Abonelik.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def abonelik_durumu(
    oturum: AsyncSession, org_id: int
) -> AbonelikDurumu | None:
    """Sohbet uclari icin: org'un abonelik durumu (yoksa None)."""
    abonelik = await aktif_abonelik(oturum, org_id)
    return abonelik.durum if abonelik else None


def erisim_var_mi(durum: AbonelikDurumu | None) -> bool:
    """`gecikmis` ve `iptal` disinda erisim serbest."""
    if durum is None:
        return True
    return durum in (AbonelikDurumu.deneme, AbonelikDurumu.aktif)


async def plan_kotasini_uygula(
    oturum: AsyncSession, *, org_id: int, plan: Plan
) -> Kota:
    """Plan limitlerini organizasyon kotasina yazar (sayaçlari sifirlar)."""
    simdi = datetime.now(timezone.utc)
    kota = (
        await oturum.execute(
            sa.select(Kota).where(
                Kota.kapsam == KotaKapsami.organizasyon, Kota.kapsam_id == org_id
            )
        )
    ).scalar_one_or_none()
    if kota is None:
        kota = Kota(kapsam=KotaKapsami.organizasyon, kapsam_id=org_id)
        oturum.add(kota)
    kota.gunluk_istek = plan.dahil_istek
    kota.aylik_token = plan.dahil_token
    kota.kullanilan_gunluk = 0
    kota.kullanilan_aylik = 0
    kota.gun_sifirlanma = simdi + timedelta(days=1)
    kota.ay_sifirlanma = simdi + timedelta(days=30)
    await oturum.flush()
    return kota


def donem_sonu(gun: int = 30) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=max(1, min(int(gun), 3650)))


def kurus_bicimle(kurus: int, para: str = "TRY") -> str:
    """`99000` -> `TRY 990,00`."""
    tam, kalan = divmod(int(kurus), 100)
    return f"{para} {tam:,}".replace(",", ".") + f",{kalan:02d}"
