"""Stripe odeme surucusu (spec §6).

Checkout oturumu olusturur ve webhook imzasini dogrular. Imza dogrulamasi
`Stripe-Signature: t=<ts>,v1=<hmac>` bicimindedir; HMAC-SHA256 girdisi
`{t}.{govde}`'dir ve zaman toleransi asilirsa reddedilir.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Any, Mapping
from urllib.parse import urlencode

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek.ayarlar import ayarlar
from arkauc.app.cekirdek.hatalar import GecersizIstek, UstSaglayiciHatasi
from bdm_veritabani.modeller import Abonelik, Fatura, Organizasyon, Plan

logger = logging.getLogger("kutyai.odeme.stripe")

STRIPE_API = "https://api.stripe.com/v1"
IMZA_TOLERANSI_SN = 300


class StripeSaglayici:
    ad = "stripe"

    def __init__(self, tasima: httpx.AsyncBaseTransport | None = None) -> None:
        self._tasima = tasima

    # -- dis cagrilar --------------------------------------------------------

    async def _istek(
        self, yol: str, veri: dict[str, Any]
    ) -> dict[str, Any]:
        basliklar = {
            "Authorization": f"Bearer {ayarlar.stripe_gizli_anahtar}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        async with httpx.AsyncClient(
            timeout=20.0, transport=self._tasima
        ) as istemci:
            try:
                yanit = await istemci.post(
                    f"{STRIPE_API}{yol}", content=urlencode(veri), headers=basliklar
                )
            except httpx.HTTPError as hata:
                logger.error("Stripe isteği başarısız (%s): %s", yol, hata)
                raise UstSaglayiciHatasi(
                    "Ödeme sağlayıcısına ulaşılamadı.", {"saglayici": self.ad}
                ) from hata
        if yanit.status_code >= 400:
            logger.error("Stripe %s -> %s: %s", yol, yanit.status_code, yanit.text[:400])
            raise UstSaglayiciHatasi(
                "Ödeme sağlayıcısı isteği reddetti.",
                {"saglayici": self.ad, "durum": yanit.status_code},
            )
        return yanit.json()

    async def abonelik_baslat(
        self,
        oturum: AsyncSession,
        *,
        organizasyon: Organizasyon,
        plan: Plan,
        abonelik: Abonelik,
        fatura: Fatura,
    ) -> dict[str, Any]:
        """Abonelik checkout oturumu acar.

        Oturum `metadata[abonelik_id]`/`metadata[fatura_id]` ve
        `client_reference_id` (organizasyon kimligi) ile etiketlenir: olay
        `dis_id` ile eslesmese bile metadata uzerinden abonelik/fatura
        bulunur. Odeme onaylanana kadar abonelik `deneme` kalir.
        """
        oturum_verisi = await self._istek(
            "/checkout/sessions",
            {
                "mode": "subscription",
                "success_url": f"{ayarlar.panel_url}/faturalama?durum=basarili",
                "cancel_url": f"{ayarlar.panel_url}/faturalama?durum=iptal",
                "client_reference_id": str(organizasyon.id),
                "metadata[abonelik_id]": str(abonelik.id),
                "metadata[fatura_id]": str(fatura.id),
                "line_items[0][quantity]": 1,
                "line_items[0][price_data][currency]": plan.para.lower(),
                "line_items[0][price_data][unit_amount]": plan.aylik_fiyat_kurus,
                "line_items[0][price_data][recurring][interval]": "month",
                "line_items[0][price_data][product_data][name]": plan.ad,
            },
        )
        oturum_id = str(oturum_verisi.get("id", ""))
        # Stripe abonelik kimligini oturum yanitinda verebilir; yoksa esleme
        # icin checkout oturum kimligi saklanir.
        return {
            "dis_id": str(oturum_verisi.get("subscription") or oturum_id),
            "oturum_id": oturum_id,
            "url": oturum_verisi.get("url"),
            "saglayici": self.ad,
            "odeme_bekliyor": True,
        }

    async def odeme_oturumu(
        self, oturum: AsyncSession, *, organizasyon: Organizasyon, fatura: Any
    ) -> dict[str, Any]:
        veri = await self._istek(
            "/checkout/sessions",
            {
                "mode": "payment",
                "success_url": f"{ayarlar.panel_url}/faturalama?durum=basarili",
                "cancel_url": f"{ayarlar.panel_url}/faturalama?durum=iptal",
                "client_reference_id": str(organizasyon.id),
                "metadata[fatura_id]": str(getattr(fatura, "id", "")),
                "line_items[0][quantity]": 1,
                "line_items[0][price_data][currency]": getattr(fatura, "para", "TRY").lower(),
                "line_items[0][price_data][unit_amount]": getattr(fatura, "tutar_kurus", 0),
                "line_items[0][price_data][product_data][name]": f"Fatura #{getattr(fatura, 'id', '')}",
            },
        )
        return {
            "dis_id": str(veri.get("id", "")),
            "url": veri.get("url"),
            "saglayici": self.ad,
        }

    # -- webhook -------------------------------------------------------------

    def imza_dogrula(self, govde: bytes, imza_basligi: str, *, simdi: float | None = None) -> None:
        """`Stripe-Signature` basligini dogrular."""
        sir = (ayarlar.stripe_webhook_sirri or "").strip()
        if not sir:
            raise GecersizIstek(
                "odeme_saglayici_yok", {"saglayici": self.ad}, kod="odeme_saglayici_yok"
            )
        zaman: int | None = None
        imzalar: list[str] = []
        for parca in (imza_basligi or "").split(","):
            anahtar, _, deger = parca.partition("=")
            anahtar = anahtar.strip()
            if anahtar == "t":
                try:
                    zaman = int(deger)
                except ValueError:
                    zaman = None
            elif anahtar == "v1":
                imzalar.append(deger.strip())
        if zaman is None or not imzalar:
            raise UstSaglayiciHatasi(
                "webhook_imzasi_gecersiz",
                {"kod": "webhook_imzasi_gecersiz"},
                kod="webhook_imzasi_gecersiz",
            )
        su_an = time.time() if simdi is None else simdi
        if abs(su_an - zaman) > IMZA_TOLERANSI_SN:
            raise UstSaglayiciHatasi(
                "webhook_imzasi_gecersiz",
                {"kod": "webhook_imzasi_gecersiz", "tolerans_sn": IMZA_TOLERANSI_SN},
                kod="webhook_imzasi_gecersiz",
            )
        beklenen = hmac.new(
            sir.encode("utf-8"), f"{zaman}.".encode("utf-8") + govde, hashlib.sha256
        ).hexdigest()
        if not any(hmac.compare_digest(beklenen, aday) for aday in imzalar):
            raise UstSaglayiciHatasi(
                "webhook_imzasi_gecersiz",
                {"kod": "webhook_imzasi_gecersiz"},
                kod="webhook_imzasi_gecersiz",
            )

    async def webhook_isle(
        self, oturum: AsyncSession, *, govde: bytes, basliklar: Mapping[str, str]
    ) -> dict[str, Any]:
        basliklar_kucuk = {anahtar.lower(): deger for anahtar, deger in basliklar.items()}
        self.imza_dogrula(govde, basliklar_kucuk.get("stripe-signature", ""))

        import json

        try:
            olay = json.loads(govde.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as hata:
            raise GecersizIstek("Webhook gövdesi okunamadı.") from hata

        tur = str(olay.get("type", ""))
        nesne = ((olay.get("data") or {}).get("object") or {})
        # Abonelik olaylarinda metadata abonelik nesnesinden gelebilir
        # (`subscription_details.metadata`); ust duzey metadata onceliklidir.
        metadata = {
            **((nesne.get("subscription_details") or {}).get("metadata") or {}),
            **((nesne.get("metadata") or {})),
        }
        return {
            "tur": tur,
            "nesne_turu": str(nesne.get("object", "")),
            "dis_id": str(nesne.get("id", "")),
            "abonelik_dis_id": str(nesne.get("subscription", "") or ""),
            "abonelik_id": str(metadata.get("abonelik_id", "")),
            "fatura_id": str(metadata.get("fatura_id", "")),
            "org_id": str(nesne.get("client_reference_id", "")),
        }
