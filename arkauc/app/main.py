"""KutyAI FastAPI uygulamasi — yonlendirici kesfi ve yasam dongusu (spec §8)."""

from __future__ import annotations

import importlib
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from arkauc.app.api.sistem import SURUM
from arkauc.app.cekirdek.ayarlar import ayarlar
from arkauc.app.cekirdek.hatalar import isleyicileri_kur
from bdm_veritabani.oturum import motoru_sifirla, tablolari_olustur
from bdm_veritabani.tohum import tohumla

logger = logging.getLogger("kutyai")

# (modul yolu, url oneki, etiket) — DONDURULMUS SOZLESME.
# Dalga ajanlari yalnizca kendi modul dosyalarini olusturur; bu liste degismez.
YONLENDIRICILER: tuple[tuple[str, str, str], ...] = (
    ("arkauc.app.api.kimlik", "/api/v1", "kimlik"),
    ("arkauc.app.api.kullanicilar", "/api/v1", "kullanicilar"),
    ("arkauc.app.api.api_anahtarlari", "/api/v1", "api-anahtarlari"),
    ("arkauc.app.api.modeller", "/api/v1", "modeller"),
    ("arkauc.app.api.kurulum", "/api/v1", "kurulum"),
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


@asynccontextmanager
async def _yasam_dongusu(uygulama: FastAPI) -> AsyncIterator[None]:
    ayarlar.dogrula()
    await tablolari_olustur()
    await tohumla()
    yuklenen = [y for y, _, _ in YONLENDIRICILER]  # bilgi amacli
    logger.info("KutyAI %s hazır — %d yönlendirici tanımlı.", SURUM, len(yuklenen))
    try:
        yield
    finally:
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
