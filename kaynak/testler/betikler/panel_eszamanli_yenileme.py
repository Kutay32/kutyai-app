"""Aynı yenileme jetonuyla eşzamanlı yenileme denemeleri (panel 401 yarışı kanıtı).

Kullanım: ./.venv/Scripts/python.exe kaynak/testler/betikler/panel_eszamanli_yenileme.py
"""
from __future__ import annotations

import asyncio
import json
import sys

import httpx

TABAN = "http://localhost:8108/api/v1"


async def main() -> int:
    async with httpx.AsyncClient(base_url=TABAN, timeout=30.0) as istemci:
        giris = await istemci.post(
            "/kimlik/panel-giris",
            json={"eposta": "admin@acme.com", "parola": "parola1234"},
        )
        yenileme = giris.json()["yenileme_jetonu"]

        cevaplar = await asyncio.gather(
            *[
                istemci.post("/kimlik/yenile", json={"yenileme_jetonu": yenileme})
                for _ in range(6)
            ]
        )
        ozet = [
            {"durum": c.status_code, "kod": (c.json().get("hata") or {}).get("kod")}
            for c in cevaplar
        ]
        print(json.dumps({"giris": giris.status_code, "eszamanli_yenileme": ozet}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
