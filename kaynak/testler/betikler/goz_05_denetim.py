"""Gözlem #10 (devam) — kullanıcı/rol değişikliklerinin denetim izi."""

from __future__ import annotations

import asyncio
import sqlite3

import httpx

from goz_ortak import TABAN, basliklar, bekle_hazir, giris, ozet, yaz

YONETICI = "goz-yonetici-1@gozlem.example.com"
DB = "E:/kutyai-app/kaynak/testler/gecici/goz_loglar.db"


async def main() -> None:
    async with httpx.AsyncClient(timeout=30) as istemci:
        await bekle_hazir(istemci)
        yonetici = await giris(istemci, YONETICI)

        yanit = await istemci.patch(
            f"{TABAN}/kullanicilar/3", headers=basliklar(yonetici), json={"rol": "operator"}
        )
        yaz("PATCH /kullanicilar/3 {rol: operator}", ozet(yanit))

        yanit = await istemci.delete(f"{TABAN}/kullanicilar/3", headers=basliklar(yonetici))
        yaz("DELETE /kullanicilar/3", f"HTTP {yanit.status_code} gövde={yanit.text!r}")

        yanit = await istemci.patch(
            f"{TABAN}/api-anahtarlari/3", headers=basliklar(yonetici), json={}
        )
        yaz("PATCH /api-anahtarlari/3 (yok olan yöntem)", ozet(yanit))

    baglanti = sqlite3.connect(DB)
    yaz(
        "SQL: kullanıcı/rol denetim kayıtları",
        "\n".join(
            f"id={r[0]} eylem={r[1]} kullanici_id={r[2]} hedef={r[3]}:{r[4]} ayrinti={r[5]}"
            for r in baglanti.execute(
                "SELECT id, eylem, kullanici_id, hedef_tur, hedef_id, ayrinti FROM islem_kaydi "
                "WHERE eylem LIKE 'kullanici%' ORDER BY id"
            ).fetchall()
        ) or "(kayıt yok)",
    )
    baglanti.close()


asyncio.run(main())
