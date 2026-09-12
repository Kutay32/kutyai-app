"""KutyAI FastAPI uygulamasi — yonlendirici kesfi ve yasam dongusu (spec §8)."""

from __future__ import annotations

import asyncio
import importlib
import logging
from contextlib import asynccontextmanager, suppress
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from arkauc.app.api.sistem import SURUM
from arkauc.app.cekirdek.ayarlar import ayarlar
from arkauc.app.cekirdek.hatalar import isleyicileri_kur
from arkauc.app.cekirdek.oran_siniri import OranSiniriMiddleware
from bdm_veritabani.oturum import motoru_sifirla, oturum_fabrikasi, tablolari_olustur
from bdm_veritabani.tohum import tohumla

logger = logging.getLogger("kutyai")

# Saklama zamanlayicisi (spec §11): acilistan sonra ve her 24 saatte bir.
SAKLAMA_ILK_BEKLEME_SN = 60
SAKLAMA_ARALIGI_SN = 24 * 60 * 60

# (modul yolu, url oneki, etiket) — DONDURULMUS SOZLESME.
# Dalga ajanlari yalnizca kendi modul dosyalarini olusturur; bu liste degismez.
YONLENDIRICILER: tuple[tuple[str, str, str], ...] = (
    ("arkauc.app.api.kimlik", "/api/v1", "kimlik"),
    ("arkauc.app.api.kullanicilar", "/api/v1", "kullanicilar"),
    ("arkauc.app.api.api_anahtarlari", "/api/v1", "api-anahtarlari"),
    ("arkauc.app.api.modeller", "/api/v1", "modeller"),
    ("arkauc.app.api.kurulum", "/api/v1", "kurulum"),
    ("arkauc.app.api.organizasyonlar", "/api/v1", "organizasyonlar"),
    ("arkauc.app.api.dosyalar", "/api/v1", "dosyalar"),
    ("arkauc.app.api.rag", "/api/v1", "rag"),
    ("arkauc.app.api.araclar", "/api/v1", "araclar"),
    ("arkauc.app.api.medya", "/api/v1", "medya"),
    ("arkauc.app.api.faturalama", "/api/v1", "faturalama"),
    ("arkauc.app.api.sso", "/api/v1", "sso"),
    ("arkauc.app.api.posta_sablonlari", "/api/v1", "posta-sablonlari"),
    ("arkauc.app.api.i18n", "/api/v1", "i18n"),
    ("arkauc.app.api.sohbet", "/api/v1", "sohbet"),
    ("arkauc.app.api.loglar", "/api/v1", "loglar"),
    ("arkauc.app.api.kullanim", "/api/v1", "kullanim"),
    ("arkauc.app.api.ayarlar", "/api/v1", "ayarlar"),
    ("arkauc.app.api.sistem", "/api/v1", "sistem"),
    ("bdm_hazırlama_ucu.uc", "/api/v1/bdm/hazirlama", "hazirlama"),
    ("bdm_yönetim_ucu.uc", "/api/v1/bdm/yonetim", "yonetim"),
)


def yonlendiricileri_yukle(uygulama: FastAPI) -> list[str]:
    """Mevcut router modullerini monte eder; olmayanlari uyarip atlar."""
    yuklenen: list[str] = []
    for modul_yolu, onek, etiket in YONLENDIRICILER:
        try:
            modul = importlib.import_module(modul_yolu)
        except ModuleNotFoundError as hata:
            if hata.name == modul_yolu:
                logger.warning("Yönlendirici henüz yok, atlandı: %s", modul_yolu)
                continue
            raise
        yonlendirici = getattr(modul, "router", None)
        if yonlendirici is None:
            logger.warning("Modülde 'router' bulunamadı, atlandı: %s", modul_yolu)
            continue
        uygulama.include_router(yonlendirici, prefix=onek, tags=[etiket])
        yuklenen.append(modul_yolu)
    return yuklenen


async def _saklama_dongusu(dur: asyncio.Event) -> None:
    """`saklama_gun` sonrasini gunluk olarak temizler."""
    from bdm_konusma_gecmisi.saklama import eski_konusmalari_sil

    try:
        await asyncio.wait_for(dur.wait(), timeout=SAKLAMA_ILK_BEKLEME_SN)
        return
    except asyncio.TimeoutError:
        pass

    while not dur.is_set():
        try:
            async with oturum_fabrikasi()() as oturum:
                silinen = await eski_konusmalari_sil(oturum)
                await oturum.commit()
            if silinen:
                logger.info("Saklama temizliği: %d konuşma silindi.", silinen)
        except Exception:  # pragma: no cover - arka plan gorevi
            logger.exception("Saklama temizliği başarısız oldu.")
        try:
            await asyncio.wait_for(dur.wait(), timeout=SAKLAMA_ARALIGI_SN)
            return
        except asyncio.TimeoutError:
            continue


@asynccontextmanager
async def _yasam_dongusu(uygulama: FastAPI) -> AsyncIterator[None]:
    ayarlar.dogrula()
    await tablolari_olustur()
    await tohumla()

    dur = asyncio.Event()
    saklama_gorevi = asyncio.create_task(_saklama_dongusu(dur), name="kutyai-saklama")
    logger.info(
        "KutyAI %s hazır — %d yönlendirici tanımlı.", SURUM, len(YONLENDIRICILER)
    )
    try:
        yield
    finally:
        dur.set()
        saklama_gorevi.cancel()
        with suppress(asyncio.CancelledError):
            await saklama_gorevi
        await motoru_sifirla()


def uygulama_olustur() -> FastAPI:
    uygulama = FastAPI(
        title="KutyAI API",
        description="Kurumsal BDM platformu — model yönetimi, sohbet ve konuşma kayıtları.",
        version=SURUM,
        lifespan=_yasam_dongusu,
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    # Oran sinirlayici once eklenir; CORS en dista kalir ki 429 yanitlari da
    # tarayici tarafinda okunabilir olsun.
    uygulama.add_middleware(OranSiniriMiddleware)
    uygulama.add_middleware(
        CORSMiddleware,
        allow_origins=ayarlar.cors_listesi,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    isleyicileri_kur(uygulama)
    uygulama.state.yuklenen_yonlendiriciler = yonlendiricileri_yukle(uygulama)
    return uygulama


app = uygulama_olustur()
