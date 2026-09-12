"""Model indirme akisi (spec §7.5).

Ollama yerel API'sinin `POST {temel}/api/pull` NDJSON akisi `{yuzde, mesaj}`
olaylarina cevrilir; `temel_url` icindeki `/v1` eki kirpilir. Diger
saglayicilarda indirme desteklenmez: `GecersizIstek` firlatilir.

Akis sirasinda olusan tasima/adres hatalari `akis_hatasi` ile Turkce hata
zarfina cevrilir; HTTP katmani (`uc._sse`) bunu `event: hata` olarak akitir.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx

from arkauc.app.cekirdek.hatalar import (
    GecersizIstek,
    KutyaiHatasi,
    SunucuHatasi,
    UstSaglayiciHatasi,
)
from bdm_hazırlama_ucu.dogrulama import BAGLANTI_MESAJI
from bdm_veritabani.modeller import Bdm, Saglayici

logger = logging.getLogger("kutyai.hazirlama")

ZAMAN_ASIMI_SN = 30.0
DESTEKLENMEYEN_MESAJ = "Bu sağlayıcı için model indirme desteklenmiyor."

# Adres/tasima kaynakli istisnalar: `httpx.InvalidURL`, `httpx.UnsupportedProtocol`
# disinda IDNA hatalari (`UnicodeError`) ve bozuk adres degerleri (`ValueError`)
# da `httpx.HTTPError` hiyerarsisinde degildir; ayrica yakalanmalari gerekir.
AG_HATALARI: tuple[type[Exception], ...] = (
    httpx.InvalidURL,
    httpx.UnsupportedProtocol,
    httpx.HTTPError,
    UnicodeError,
    ValueError,
)

# Ollama durum metinlerinin Turkce karsiliklari.
DURUM_CEVIRILERI: dict[str, str] = {
    "pulling manifest": "Manifest indiriliyor",
    "downloading": "Model indiriliyor",
    "verifying sha256 digest": "Bütünlük imzası doğrulanıyor",
    "writing manifest": "Manifest yazılıyor",
    "removing any unused layers": "Kullanılmayan katmanlar temizleniyor",
    "success": "Model hazır",
}


def varsayilan_tasima() -> httpx.AsyncBaseTransport | None:
    """Varsayilan ag tasimasi; testler sahte tasima enjekte etmek icin ezer."""
    return None


def akis_hatasi(hata: BaseException) -> KutyaiHatasi:
    """Indirme akisini kesen istisnayi Turkce hata zarfina cevirir.

    Tasima/adres kaynakli hatalar saglayici hatasi olarak bildirilir; beklenmeyen
    hatalar sunucu hatasina duser. Cagiran taraf sonucu `event: hata` olarak akitir.
    """
    if isinstance(hata, AG_HATALARI):
        logger.warning("Model indirme akisi kesildi: %s", hata)
        return UstSaglayiciHatasi(
            BAGLANTI_MESAJI, {"neden": type(hata).__name__}
        )
    logger.exception("Model indirme akisinda beklenmeyen hata.", exc_info=hata)
    return SunucuHatasi()


def cek_destegi_denetle(bdm: Bdm) -> None:
    """Saglayicinin model indirmeyi destekleyip desteklemedigini denetler."""
    if bdm.saglayici is not Saglayici.ollama:
        raise GecersizIstek(
            DESTEKLENMEYEN_MESAJ, {"saglayici": bdm.saglayici.value}
        )


def ollama_temeli(temel_url: str) -> str:
    """`/v1` ile biten OpenAI uyumlu adresten Ollama kokunu uretir."""
    temel = (temel_url or "").rstrip("/")
    if temel.endswith("/v1"):
        temel = temel[:-3].rstrip("/")
    return temel


def _olaya_cevir(satir: str, onceki_yuzde: int) -> dict[str, Any] | None:
    satir = satir.strip()
    if not satir:
        return None
    try:
        kayit = json.loads(satir)
    except ValueError:
        logger.debug("Ollama akisinda cozulemeyen satir: %s", satir[:200])
        return None
    if not isinstance(kayit, dict):
        return None

    ham_durum = str(kayit.get("status") or "").strip()
    toplam = kayit.get("total")
    tamamlanan = kayit.get("completed")
    if isinstance(toplam, int) and toplam > 0 and isinstance(tamamlanan, int):
        yuzde = max(0, min(100, int(tamamlanan / toplam * 100)))
    elif ham_durum == "success":
        yuzde = 100
    else:
        yuzde = onceki_yuzde

    mesaj = DURUM_CEVIRILERI.get(ham_durum, ham_durum or "Model indiriliyor")
    return {"yuzde": yuzde, "mesaj": mesaj}


async def cek_akisi(
    bdm: Bdm, *, tasima: httpx.AsyncBaseTransport | None = None
) -> AsyncIterator[dict[str, Any]]:
    """Ollama model indirmesini `{yuzde, mesaj}` olaylari olarak akitir."""
    cek_destegi_denetle(bdm)
    temel = ollama_temeli(bdm.temel_url)
    if not temel:
        raise GecersizIstek("Model adresi tanımlı değil. Lütfen temel adresi girin.")
    if not bdm.upstream_model:
        raise GecersizIstek("İndirilecek model adı tanımlı değil.")

    etkin_tasima = tasima if tasima is not None else varsayilan_tasima()
    async with httpx.AsyncClient(transport=etkin_tasima, timeout=ZAMAN_ASIMI_SN) as istemci:
        async with istemci.stream(
            "POST",
            f"{temel}/api/pull",
            json={"model": bdm.upstream_model, "stream": True},
        ) as yanit:
            if yanit.status_code != 200:
                raise UstSaglayiciHatasi(
                    f"Model indirme isteği {yanit.status_code} koduyla reddedildi.",
                    {"saglayici": bdm.saglayici.value, "model": bdm.upstream_model},
                )
            yuzde = 0
            async for satir in yanit.aiter_lines():
                olay = _olaya_cevir(satir, yuzde)
                if olay is None:
                    continue
                yuzde = olay["yuzde"]
                yield olay
