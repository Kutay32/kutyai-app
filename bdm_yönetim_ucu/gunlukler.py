"""Konteyner günlüklerinin SSE akışı (spec §7.6)."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator

from arkauc.app.cekirdek.hatalar import KutyaiHatasi, SunucuHatasi
from arkauc.app.servisler.konteyner import KonteynerSurucusu

logger = logging.getLogger("kutyai.yonetim.gunlukler")

SSE_BASLIKLARI = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
}

# İlk satır için bekleme: sürücü hatası (konteyner yok, Docker kapalı) bu süre
# içinde ortaya çıkar ve akış başlamadan normal hata zarfı olarak döner.
ILK_SATIR_ZAMAN_ASIMI = 2.0
# Akış askıda kalmasın diye gönderilen `: nabız` yorum satırının aralığı (saniye).
NABIZ_SANIYE = 10.0
NABIZ = ": nabız\n\n"


def cerceve(olay: str, veri: dict[str, object]) -> str:
    """Tek bir SSE olayı üretir."""
    return f"event: {olay}\ndata: {json.dumps(veri, ensure_ascii=False)}\n\n"


async def _sonraki(kaynak: AsyncIterator[str]) -> str | None:
    """Bir sonraki günlük satırını döndürür; akış bittiyse `None`."""
    try:
        return await anext(kaynak)
    except StopAsyncIteration:
        return None


async def _kapat(kaynak: AsyncIterator[str], bekleyen: asyncio.Future[str | None] | None) -> None:
    """Bekleyen okumayı iptal edip kaynak akışı kapatır; askıda bırakmaz."""
    if bekleyen is not None:
        bekleyen.cancel()
        try:
            await bekleyen
        except BaseException:  # iptal ya da okuma hatası: kapanışı engelleme
            pass
    try:
        await kaynak.aclose()
    except RuntimeError:  # pragma: no cover - okuma hâlâ sürüyorsa iptal yeterli
        pass


async def akis(
    surucu: KonteynerSurucusu, konteyner_id: str, satir: int
) -> AsyncIterator[str]:
    """SSE gövdesini hazırlar ve döndürür.

    Konteyner yokluğu gibi sürücü hataları ilk satır beklenirken ortaya çıkar ve
    burada fırlatılır; böylece istemci `200 text/event-stream` alıp bağlantının
    ortasında kopmaz, `503 surucu_yok` hata zarfını alır. İlk satır
    `ILK_SATIR_ZAMAN_ASIMI` içinde gelmezse (konteyner sessiz) akış yine başlar
    ve sürücü yanıtı beklenirken `: nabız` gönderilir.
    """
    kaynak = surucu.gunlukler(konteyner_id, satir)
    gorev = asyncio.ensure_future(_sonraki(kaynak))
    try:
        bitti, _ = await asyncio.wait({gorev}, timeout=ILK_SATIR_ZAMAN_ASIMI)
        ilk = gorev.result() if bitti else None
    except BaseException:
        await _kapat(kaynak, gorev)
        raise
    return _govde(kaynak, None if bitti else gorev, ilk)


async def _govde(
    kaynak: AsyncIterator[str], bekleyen: asyncio.Future[str | None] | None, ilk: str | None
) -> AsyncIterator[str]:
    """`event: satir` olaylarını üretir; akış ortasında hata olursa `event: hata`."""
    if ilk is not None:
        yield cerceve("satir", {"metin": ilk})
    try:
        while True:
            if bekleyen is None:
                bekleyen = asyncio.ensure_future(_sonraki(kaynak))
            bitti, _ = await asyncio.wait({bekleyen}, timeout=NABIZ_SANIYE)
            if not bitti:
                yield NABIZ
                continue
            metin = bekleyen.result()
            bekleyen = None
            if metin is None:
                break
            yield cerceve("satir", {"metin": metin})
    except KutyaiHatasi as hata:
        yield cerceve("hata", hata.govde())
    except Exception as hata:  # pragma: no cover - beklenmeyen akış hatası
        logger.exception("Günlük akışı beklenmeyen hatayla kesildi: %s", hata)
        yield cerceve("hata", SunucuHatasi().govde())
    finally:
        await _kapat(kaynak, bekleyen)
