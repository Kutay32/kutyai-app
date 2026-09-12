"""OpenAI uyumlu ust saglayici istemcisi (spec §7.4).

Tek yanit (`tek_yanit`) ve SSE akisi (`akis_uret`) ayni govdeyi kullanir.
Tasima enjekte edilebilir; testler `httpx.MockTransport` ile sahte saglayici
baglar.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx

from arkauc.app.cekirdek import guvenlik
from arkauc.app.cekirdek.hatalar import UstSaglayiciHatasi
from bdm_veritabani.modeller import Bdm

logger = logging.getLogger("kutyai.upstream")

SOHBET_YOLU = "/chat/completions"
GOVDE_KIRPMA = 400
ZAMAN_ASIMI = httpx.Timeout(connect=10.0, read=180.0, write=30.0, pool=10.0)


def _kirp(metin: str, uzunluk: int = GOVDE_KIRPMA) -> str:
    return " ".join((metin or "").split())[:uzunluk]


def _saglayici_adi(bdm: Bdm) -> str:
    return getattr(bdm.saglayici, "value", str(bdm.saglayici))


def kullanim_sozlugu(ham: dict[str, Any] | None) -> dict[str, int]:
    """OpenAI `usage` nesnesini `{girdi, cikti}` bicimine cevirir."""
    ham = ham or {}
    return {
        "girdi": int(ham.get("prompt_tokens") or 0),
        "cikti": int(ham.get("completion_tokens") or 0),
    }


class UstSaglayici:
    """Saglayiciya bagimsiz sohbet istemcisi (OpenAI sozlesmesi)."""

    def __init__(self, tasima: httpx.AsyncBaseTransport | None = None) -> None:
        self.tasima = tasima

    # -- yardimcilar ---------------------------------------------------------

    def adres(self, bdm: Bdm) -> str:
        return f"{(bdm.temel_url or '').rstrip('/')}{SOHBET_YOLU}"

    def basliklar(self, bdm: Bdm) -> dict[str, str]:
        """Azure `api-key`, diger saglayicilar `Authorization: Bearer` kullanir."""
        basliklar = {"Content-Type": "application/json", "Accept": "application/json"}
        anahtar = ""
        if bdm.api_anahtari_sifreli:
            try:
                anahtar = guvenlik.coz(bdm.api_anahtari_sifreli)
            except Exception:  # pragma: no cover - bozuk sifreli deger
                logger.warning("BDM %s için upstream anahtarı çözülemedi.", bdm.id)
        if anahtar:
            if _saglayici_adi(bdm) == "azure":
                basliklar["api-key"] = anahtar
            else:
                basliklar["Authorization"] = f"Bearer {anahtar}"
        return basliklar

    def govde(
        self,
        bdm: Bdm,
        mesajlar: list[dict[str, str]],
        *,
        sicaklik: float | None,
        maks_token: int | None,
        akis: bool,
    ) -> dict[str, Any]:
        govde: dict[str, Any] = {
            "model": bdm.upstream_model,
            "messages": list(mesajlar),
            "stream": akis,
        }
        if sicaklik is not None:
            govde["temperature"] = float(sicaklik)
        if maks_token:
            govde["max_tokens"] = int(maks_token)
        if akis:
            govde["stream_options"] = {"include_usage": True}
        return govde

    def _istemci(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=self.tasima, timeout=ZAMAN_ASIMI)

    @staticmethod
    def _hata(bdm: Bdm, durum: int, govde: str) -> UstSaglayiciHatasi:
        """Ayrıntıya yalnız durum ve sağlayıcı adı girer; tam gövde günlüğe yazılır."""
        logger.error(
            "Upstream %s yanıtı (BDM %s, sağlayıcı %s): %s",
            durum,
            getattr(bdm, "id", None),
            _saglayici_adi(bdm),
            _kirp(govde, 2000),
        )
        return UstSaglayiciHatasi(
            "Model sağlayıcısı isteği yanıtlayamadı.",
            {"durum": durum, "saglayici": _saglayici_adi(bdm)},
        )

    @staticmethod
    def _tasima_hatasi(bdm: Bdm, hata: Exception) -> UstSaglayiciHatasi:
        """Taşıma istisnası metni istemciye dönmez; sunucu günlüğüne yazılır."""
        logger.error(
            "Upstream taşıma hatası (BDM %s, sağlayıcı %s): %s: %s",
            getattr(bdm, "id", None),
            _saglayici_adi(bdm),
            type(hata).__name__,
            _kirp(str(hata), 400),
        )
        return UstSaglayiciHatasi(
            "Model sağlayıcısına bağlanılamadı.",
            {"durum": 0, "saglayici": _saglayici_adi(bdm)},
        )

    @staticmethod
    def _paket_olaylari(paket: dict[str, Any]) -> list[dict[str, Any]]:
        olaylar: list[dict[str, Any]] = []
        for secim in paket.get("choices") or []:
            delta = secim.get("delta") or {}
            icerik = delta.get("content")
            if isinstance(icerik, str) and icerik:
                olaylar.append({"parca": icerik})
        if paket.get("usage"):
            olaylar.append({"kullanim": kullanim_sozlugu(paket["usage"])})
        return olaylar

    # -- akis ----------------------------------------------------------------

    async def akis_uret(
        self,
        bdm: Bdm,
        mesajlar: list[dict[str, str]],
        *,
        sicaklik: float | None = None,
        maks_token: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """SSE parcalarini `{"parca": str}` / `{"kullanim": {...}}` olarak uretir."""
        govde = self.govde(bdm, mesajlar, sicaklik=sicaklik, maks_token=maks_token, akis=True)
        try:
            async with self._istemci() as istemci:
                async with istemci.stream(
                    "POST", self.adres(bdm), json=govde, headers=self.basliklar(bdm)
                ) as yanit:
                    if yanit.status_code >= 400:
                        ham = (await yanit.aread()).decode("utf-8", "replace")
                        raise self._hata(bdm, yanit.status_code, ham)
                    async for satir in yanit.aiter_lines():
                        temiz = satir.strip()
                        if not temiz.startswith("data:"):
                            continue
                        veri = temiz[len("data:") :].strip()
                        if veri == "[DONE]":
                            break
                        try:
                            paket = json.loads(veri)
                        except ValueError:
                            logger.debug("Upstream SSE satırı çözülemedi: %s", _kirp(veri, 120))
                            continue
                        if not isinstance(paket, dict):
                            continue
                        for olay in self._paket_olaylari(paket):
                            yield olay
        except UstSaglayiciHatasi:
            raise
        except httpx.HTTPError as hata:
            raise self._tasima_hatasi(bdm, hata) from hata

    # -- tek yanit -----------------------------------------------------------

    async def tek_yanit(
        self,
        bdm: Bdm,
        mesajlar: list[dict[str, str]],
        *,
        sicaklik: float | None = None,
        maks_token: int | None = None,
    ) -> dict[str, Any]:
        """`{"icerik": str, "kullanim": {"girdi": int, "cikti": int}}` dondurur."""
        govde = self.govde(bdm, mesajlar, sicaklik=sicaklik, maks_token=maks_token, akis=False)
        try:
            async with self._istemci() as istemci:
                yanit = await istemci.post(
                    self.adres(bdm), json=govde, headers=self.basliklar(bdm)
                )
        except httpx.HTTPError as hata:
            raise self._tasima_hatasi(bdm, hata) from hata
        if yanit.status_code >= 400:
            raise self._hata(bdm, yanit.status_code, yanit.text)
        try:
            paket = yanit.json()
        except ValueError as hata:
            raise self._hata(bdm, yanit.status_code, yanit.text) from hata
        if not isinstance(paket, dict):
            raise self._hata(bdm, yanit.status_code, yanit.text)
        secimler = paket.get("choices") or []
        if not secimler:
            raise self._hata(bdm, yanit.status_code, yanit.text)
        icerik = (secimler[0].get("message") or {}).get("content") or ""
        return {"icerik": str(icerik), "kullanim": kullanim_sozlugu(paket.get("usage"))}
