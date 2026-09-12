"""SSE cerceveleme ve sohbet akisi (spec §7.4, §6).

Olay sirasi: `baslangic` → `parca`* → `kullanim` → `bitti`. Hata durumunda
`hata` olayi hata zarfini tasir ve ardindan her zaman `bitti` gonderilir.
Istemci koptugunda upstream istegi iptal edilir ve kismi yanit kaydedilmez;
gunluk istek kotasi akis baslamadan rezerve edildigi icin rezervasyon kalir,
yanit sonunda yalnizca token sayaci artar.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek.hatalar import KutyaiHatasi, SunucuHatasi
from arkauc.app.servisler.kota import kota_token_ekle
from arkauc.app.servisler.upstream import UstSaglayici
from bdm_konusma_gecmisi import kullanim_yaz, mesaj_ekle
from bdm_veritabani.modeller import (
    Bdm,
    KullanimDurumu,
    Konusma,
    Mesaj,
    MesajRolu,
)

logger = logging.getLogger("kutyai.akis")

TOKEN_BOLEN = 4


def tahmin_token(metin: str) -> int:
    """Upstream `usage` yoksa kaba token tahmini (spec §7.4)."""
    return len(metin or "") // TOKEN_BOLEN


def sse_olay(event: str, veri: object) -> str:
    """SSE cercevesi uretir; sozlukler JSON olarak serilestirilir."""
    govde = veri if isinstance(veri, str) else json.dumps(veri, ensure_ascii=False)
    return f"event: {event}\ndata: {govde}\n\n"


async def sohbet_akisi(
    oturum: AsyncSession,
    *,
    ust: UstSaglayici,
    bdm: Bdm,
    konusma: Konusma,
    kullanici_mesaji: Mesaj,
    mesajlar: list[dict[str, str]],
    kullanici_id: int | None,
    api_anahtari_id: int | None,
    sicaklik: float,
    maks_token: int,
) -> AsyncIterator[str]:
    """Kullanici mesaji yazilmis bir konusma icin SSE akisini uretir."""
    baslangic = time.perf_counter()
    tahmini_girdi = kullanici_mesaji.token_sayisi or tahmin_token(kullanici_mesaji.icerik)
    parcalar: list[str] = []
    upstream_kullanim: dict[str, int] = {}
    akis = ust.akis_uret(bdm, mesajlar, sicaklik=sicaklik, maks_token=maks_token)

    yield sse_olay(
        "baslangic", {"konusma_id": konusma.id, "mesaj_id": kullanici_mesaji.id}
    )

    try:
        async for olay in akis:
            if "parca" in olay:
                parca = str(olay["parca"])
                parcalar.append(parca)
                yield sse_olay("parca", {"icerik": parca})
            elif "kullanim" in olay:
                upstream_kullanim = olay["kullanim"]
    except asyncio.CancelledError:
        logger.info("İstemci koptu; kısmi yanıt kaydedilmedi (konuşma %s).", konusma.id)
        raise
    except KutyaiHatasi as hata:
        await _hatali_kaydet(
            oturum,
            bdm=bdm,
            konusma=konusma,
            kullanici_id=kullanici_id,
            api_anahtari_id=api_anahtari_id,
            gecikme_ms=_gecen_ms(baslangic),
        )
        yield sse_olay("hata", hata.govde())
        yield sse_olay("bitti", {})
        return
    except Exception as hata:  # pragma: no cover - beklenmeyen altyapi hatasi
        logger.exception("Sohbet akışı beklenmedik hata verdi: %s", hata)
        await _hatali_kaydet(
            oturum,
            bdm=bdm,
            konusma=konusma,
            kullanici_id=kullanici_id,
            api_anahtari_id=api_anahtari_id,
            gecikme_ms=_gecen_ms(baslangic),
        )
        yield sse_olay("hata", SunucuHatasi().govde())
        yield sse_olay("bitti", {})
        return
    finally:
        await akis.aclose()

    icerik = "".join(parcalar)
    girdi = int(upstream_kullanim.get("girdi") or 0) or tahmini_girdi
    cikti = int(upstream_kullanim.get("cikti") or 0) or tahmin_token(icerik)
    gecikme_ms = _gecen_ms(baslangic)
    yield sse_olay(
        "kullanim",
        {"token_girdi": girdi, "token_cikti": cikti, "gecikme_ms": gecikme_ms},
    )

    try:
        await _tamamla(
            oturum,
            bdm=bdm,
            konusma=konusma,
            kullanici_mesaji=kullanici_mesaji,
            icerik=icerik,
            girdi=girdi,
            cikti=cikti,
            tahmini_girdi=tahmini_girdi,
            gecikme_ms=gecikme_ms,
            kullanici_id=kullanici_id,
            api_anahtari_id=api_anahtari_id,
        )
    except Exception as hata:  # pragma: no cover - kalici kayit arizasi
        logger.exception("Sohbet kaydı yazılamadı: %s", hata)
        yield sse_olay("hata", SunucuHatasi().govde())
        yield sse_olay("bitti", {})
        return

    yield sse_olay("bitti", {})


def _gecen_ms(baslangic: float) -> int:
    return max(0, int((time.perf_counter() - baslangic) * 1000))


async def _tamamla(
    oturum: AsyncSession,
    *,
    bdm: Bdm,
    konusma: Konusma,
    kullanici_mesaji: Mesaj,
    icerik: str,
    girdi: int,
    cikti: int,
    tahmini_girdi: int,
    gecikme_ms: int,
    kullanici_id: int | None,
    api_anahtari_id: int | None,
) -> None:
    """Asistan mesajini, kullanim kaydini ve kota sayaclarini yazar."""
    if girdi != tahmini_girdi:
        konusma.token_girdi = max(0, (konusma.token_girdi or 0) + (girdi - tahmini_girdi))
        kullanici_mesaji.token_sayisi = girdi
    await mesaj_ekle(
        oturum,
        konusma=konusma,
        rol=MesajRolu.asistan,
        icerik=icerik,
        token_sayisi=cikti,
        gecikme_ms=gecikme_ms,
        model=bdm.upstream_model,
    )
    await kullanim_yaz(
        oturum,
        bdm_id=bdm.id,
        kullanici_id=kullanici_id,
        api_anahtari_id=api_anahtari_id,
        konusma_id=konusma.id,
        girdi_token=girdi,
        cikti_token=cikti,
        gecikme_ms=gecikme_ms,
        durum=KullanimDurumu.basarili,
    )
    await kota_token_ekle(
        oturum,
        kullanici_id=kullanici_id,
        api_anahtari_id=api_anahtari_id,
        token=girdi + cikti,
    )
    await oturum.commit()


async def _hatali_kaydet(
    oturum: AsyncSession,
    *,
    bdm: Bdm,
    konusma: Konusma,
    kullanici_id: int | None,
    api_anahtari_id: int | None,
    gecikme_ms: int,
) -> None:
    """Basarisiz istegi kullanim kaydina isler (kismi yanit yazilmaz)."""
    try:
        await kullanim_yaz(
            oturum,
            bdm_id=bdm.id,
            kullanici_id=kullanici_id,
            api_anahtari_id=api_anahtari_id,
            konusma_id=konusma.id,
            gecikme_ms=gecikme_ms,
            durum=KullanimDurumu.hata,
        )
        await oturum.commit()
    except Exception as hata:  # pragma: no cover - kayit arizasi
        logger.warning("Hatalı istek kaydedilemedi: %s", hata)
