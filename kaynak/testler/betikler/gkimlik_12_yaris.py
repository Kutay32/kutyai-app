"""12) Eszamanli kayit/dogrulama: ayni e-posta ile paralel kayit 500 uretir mi,
    ayni dogrulama jetonuyla paralel dogrulama cift kullanima izin verir mi?"""

from __future__ import annotations

import asyncio
import sys

import httpx

sys.path.insert(0, "E:/kutyai-app/kaynak/testler/betikler")
from gkimlik_ortak import *  # noqa: E402

EPOSTA = yeni_eposta("goz-yaris")


# --- C icin hazirlik (senkron istemci ile)
with istemci() as sk:
    eposta3, _, _, _ = kayit_ve_dogrula(sk, yeni_eposta("goz-yaris-sifir"))
    rsif = sk.post("/kimlik/sifre-sifirlama-iste", json={"eposta": eposta3})
    sjeton = jeton_baglantidan(govde(rsif)["gelistirme_baglantisi"])


async def main() -> None:
    async with httpx.AsyncClient(base_url=TABAN, timeout=60.0) as ac:
        govdeler = [{"eposta": EPOSTA, "ad_soyad": "Yaris", "parola": PAROLA} for _ in range(5)]
        yanitlar = await asyncio.gather(
            *[ac.post("/kimlik/kayit", json=g) for g in govdeler], return_exceptions=True
        )
        print("### A) ayni e-posta ile 5 paralel kayit")
        for i, y in enumerate(yanitlar):
            if isinstance(y, Exception):
                print(f"  {i}: ISTISNA {type(y).__name__}: {y}")
            else:
                print(f"  {i}: {y.status_code} {y.text[:200]}")

        # Ayni dogrulama jetonuyla paralel dogrulama
        eposta2 = yeni_eposta("goz-yaris-jeton")
        r = await ac.post("/kimlik/kayit", json={
            "eposta": eposta2, "ad_soyad": "Y", "parola": PAROLA})
        jeton = jeton_baglantidan(r.json()["gelistirme_baglantisi"])
        dyn = await asyncio.gather(
            *[ac.post("/kimlik/dogrula", json={"jeton": jeton}) for _ in range(5)],
            return_exceptions=True,
        )
        print("### B) ayni e-posta dogrulama jetonuyla 5 paralel /kimlik/dogrula")
        for i, y in enumerate(dyn):
            if isinstance(y, Exception):
                print(f"  {i}: ISTISNA {type(y).__name__}: {y}")
            else:
                print(f"  {i}: {y.status_code} {y.text[:200]}")

        # Ayni sifirlama jetonuyla paralel sifre sifirla
        syn = await asyncio.gather(
            *[ac.post("/kimlik/sifre-sifirla", json={
                "jeton": sjeton, "yeni_parola": f"ParolaYaris{i:03d}!"}) for i in range(5)],
            return_exceptions=True,
        )
        print("### C) ayni sifirlama jetonuyla 5 paralel /kimlik/sifre-sifirla")
        for i, y in enumerate(syn):
            if isinstance(y, Exception):
                print(f"  {i}: ISTISNA {type(y).__name__}: {y}")
            else:
                print(f"  {i}: {y.status_code} {y.text[:200]}")


asyncio.run(main())
print("### DB: yarış e-postalari")
print(sql("select id, eposta, durum, eposta_dogrulandi from kullanici where eposta like 'goz-yaris%'"))
print("### DB: dogrulama jetonlari")
print(sql("select j.id, j.tur, j.kullanildi from dogrulama_jetonu j join kullanici k "
          "on k.id=j.kullanici_id where k.eposta like 'goz-yaris%'"))
