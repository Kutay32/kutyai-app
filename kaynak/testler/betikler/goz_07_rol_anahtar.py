"""Gözlem #7 (ek) — izleyici rolünün anahtar iptal yetkisi."""

from __future__ import annotations

import asyncio

import httpx

from goz_ortak import PAROLA, TABAN, basliklar, bekle_hazir, giris, ozet, yaz

YONETICI = "goz-yonetici-1@gozlem.example.com"


async def main() -> None:
    async with httpx.AsyncClient(timeout=30) as istemci:
        await bekle_hazir(istemci)
        yonetici = await giris(istemci, YONETICI)
        yanit = await istemci.post(
            f"{TABAN}/kullanicilar",
            headers=basliklar(yonetici),
            json={
                "eposta": "goz-izleyici2@gozlem.example.com",
                "ad_soyad": "Izleyici 2",
                "parola": PAROLA,
                "rol": "izleyici",
            },
        )
        yaz("POST /kullanicilar izleyici (2)", ozet(yanit))
        izleyici = await giris(istemci, "goz-izleyici2@gozlem.example.com")

        uret = await istemci.post(
            f"{TABAN}/api-anahtarlari", headers=basliklar(izleyici), json={"ad": "Izleyici-2 Anahtar"}
        )
        yaz("POST /api-anahtarlari (izleyici2)", ozet(uret))
        yeni_id = uret.json()["id"]

        iptal = await istemci.post(
            f"{TABAN}/api-anahtarlari/{yeni_id}/iptal", headers=basliklar(izleyici)
        )
        yaz("POST /api-anahtarlari/{id}/iptal (izleyici2)", ozet(iptal))

        uret2 = await istemci.post(
            f"{TABAN}/api-anahtarlari", headers=basliklar(izleyici), json={"ad": "Izleyici-2 Anahtar B"}
        )
        tam = uret2.json()["tam_anahtar"]
        modeller = await istemci.get(
            f"{TABAN}/modeller", headers={"Authorization": f"Bearer {tam}"}
        )
        yaz("GET /modeller (izleyicinin ürettiği anahtarla)", ozet(modeller))
        sohbet = await istemci.post(
            f"{TABAN}/sohbet",
            headers={"Authorization": f"Bearer {tam}"},
            json={"bdm_id": 1, "mesaj": "Yetki testi"},
        )
        yaz("POST /sohbet (izleyicinin ürettiği anahtarla)", ozet(sohbet))


asyncio.run(main())
