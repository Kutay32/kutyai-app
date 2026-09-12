"""Bağımsız gözlem betikleri için ortak yardımcılar (loglar modülü).

Kullanım: `from goz_ortak import ...` — betikler aynı klasörden çalıştırılır.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from typing import Any

import httpx

TABAN = os.environ.get("GOZ_TABAN", "http://127.0.0.1:8106/api/v1")
PAROLA = "Gozlem1234!"


def yaz(baslik: str, govde: str) -> None:
    """Ham çıktı bloğu biçiminde ekrana basar."""
    print(f"\n=== {baslik} ===")
    print(govde)
    sys.stdout.flush()


def ozet(yanit: httpx.Response) -> str:
    return f"HTTP {yanit.status_code} {yanit.headers.get('content-type', '')}\n{yanit.text[:1500]}"


async def kurulum(
    istemci: httpx.AsyncClient,
    *,
    eposta: str,
    marka: str = "Gözlem Marka",
    gorunen_ad: str = "Gözlem Model",
    slug: str | None = None,
    dogrula: bool = False,
) -> httpx.Response:
    govde: dict[str, Any] = {
        "marka_adi": marka,
        "yonetici": {"eposta": eposta, "ad_soyad": "Gözlem Yönetici", "parola": PAROLA},
        "bdm": {
            "gorunen_ad": gorunen_ad,
            "saglayici": "ollama",
            "temel_url": "http://127.0.0.1:11434/v1",
            "upstream_model": "llama3",
            "api_anahtari": "",
            "yerel_mi": True,
        },
        "dogrula": dogrula,
    }
    if slug:
        govde["bdm"]["slug"] = slug
    return await istemci.post(f"{TABAN}/kurulum", json=govde)


async def giris_denemesi(
    istemci: httpx.AsyncClient,
    eposta: str,
    parola: str = PAROLA,
    yol: str = "/kimlik/panel-giris",
) -> httpx.Response:
    return await istemci.post(f"{TABAN}{yol}", json={"eposta": eposta, "parola": parola})


async def giris(istemci: httpx.AsyncClient, eposta: str, parola: str = PAROLA) -> str:
    yanit = await giris_denemesi(istemci, eposta, parola)
    yanit.raise_for_status()
    return yanit.json()["erisim_jetonu"]


def basliklar(jeton: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {jeton}"}


async def bekle_hazir(istemci: httpx.AsyncClient, saniye: float = 30.0) -> None:
    bitis = time.monotonic() + saniye
    while time.monotonic() < bitis:
        try:
            yanit = await istemci.get(f"{TABAN}/saglik")
            if yanit.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        await asyncio.sleep(0.3)
    raise RuntimeError("Sunucu hazır olmadı.")


def db(ad: str) -> str:
    return f"E:/kutyai-app/kaynak/testler/gecici/{ad}.db"


def baglan(ad: str):
    """Geçici SQLite veritabanına doğrudan (senkron) bağlantı açar."""
    import sqlite3

    return sqlite3.connect(db(ad))
