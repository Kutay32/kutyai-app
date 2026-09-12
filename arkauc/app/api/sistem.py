"""Sistem uclari: canlilik, hazirlik, kurulum durumu (spec §7.8)."""

from __future__ import annotations

from datetime import datetime, timezone

import sqlalchemy as sa
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek.ayarlar import ayarlar
from arkauc.app.cekirdek.ayarlar_db import ayar_oku
from arkauc.app.cekirdek.bagimliliklar import veritabani_oturumu
from arkauc.app.cekirdek.hatalar import BdmHazirDegil
from arkauc.app.servisler.konteyner import surucu_al

router = APIRouter(tags=["sistem"])

SURUM = "0.1.0"


@router.get("/saglik")
async def saglik() -> dict[str, object]:
    """Canlilik sondasi."""
    return {
        "durum": "ayakta",
        "surum": SURUM,
        "ortam": ayarlar.ortam,
        "zaman": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/saglik/hazir")
async def hazir(oturum: AsyncSession = Depends(veritabani_oturumu)) -> dict[str, object]:
    """Hazirlik sondasi: veritabani + konteyner surucusu."""
    try:
        await oturum.execute(sa.text("SELECT 1"))
    except Exception as hata:  # pragma: no cover - altyapi arizasi
        raise BdmHazirDegil(
            "Veritabanına ulaşılamıyor.", {"neden": type(hata).__name__}, kod="veritabani_yok"
        ) from hata

    try:
        durum = await surucu_al("ozel", True).durum()
        surucu = {
            "ad": durum.surucu_adi,
            "docker": durum.docker_var,
            "gpu": durum.gpu_var,
            "mesaj": durum.mesaj,
        }
    except Exception as hata:
        surucu = {"ad": "yok", "docker": False, "gpu": False, "mesaj": str(hata)}

    return {"durum": "hazir", "veritabani": "tamam", "surucu": surucu, "surum": SURUM}


@router.get("/saglik/kurulum")
async def kurulum(oturum: AsyncSession = Depends(veritabani_oturumu)) -> dict[str, object]:
    """Kurulum sihirbazinin durumu (kimlik gerekmez)."""
    return {
        "kurulum_tamam": bool(await ayar_oku(oturum, "kurulum_tamam", False)),
        "marka_adi": await ayar_oku(oturum, "marka_adi", "KutyAI"),
        "surum": SURUM,
    }
