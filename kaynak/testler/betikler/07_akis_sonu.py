"""07 — Docker günlük akışı: son satırdan sonra akış bitiyor mu, bloke mi kalıyor?"""

from __future__ import annotations

import asyncio
import pathlib
import sys

BETIKLER = pathlib.Path(__file__).resolve().parents[1] / "betikler"
sys.path.insert(0, str(BETIKLER.parents[2]))

from arkauc.app.servisler.konteyner_docker import DockerSurucusu  # noqa: E402


async def main() -> None:
    surucu = DockerSurucusu()
    manifest = {"image": "nginx:alpine", "komut": [], "port": 18097, "gpu": False, "bellek_gb": 1, "ortam": {}}
    kimlik = await surucu.baslat({"id": 0, "slug": "akis-sonu", "temel_url": "x", "upstream_model": "x"}, manifest)
    print(f"konteyner = {kimlik[:16]}…")
    try:
        await asyncio.sleep(2)
        akis = surucu.gunlukler(kimlik, 200)
        sayi = 0
        while True:
            try:
                await asyncio.wait_for(anext(akis), timeout=8)
                sayi += 1
            except StopAsyncIteration:
                print(f"SONUÇ: akış {sayi} satırdan sonra BİTTİ (StopAsyncIteration) — asılı kalma yok")
                break
            except asyncio.TimeoutError:
                print(f"SONUÇ: {sayi} satırdan sonra 8 sn boyunca VERİ GELMEDİ ve akış KAPANMADI (bloke)")
                break
        await akis.aclose()
    finally:
        await surucu.durdur(kimlik)
        await surucu.sil(kimlik)

    print("\n-- ek: `tail` sınırından sonra davranış (tail=2) --")
    kimlik = await surucu.baslat({"id": 0, "slug": "akis-sonu-2", "temel_url": "x", "upstream_model": "x"}, manifest)
    try:
        await asyncio.sleep(2)
        akis = surucu.gunlukler(kimlik, 2)
        satirlar = []
        while True:
            try:
                satirlar.append(await asyncio.wait_for(anext(akis), timeout=8))
            except StopAsyncIteration:
                print(f"  tail=2 → {len(satirlar)} satır sonra akış BİTTİ")
                break
            except asyncio.TimeoutError:
                print(f"  tail=2 → {len(satirlar)} satır sonra bloke (veri yok, kapanmadı)")
                break
        await akis.aclose()
    finally:
        await surucu.durdur(kimlik)
        await surucu.sil(kimlik)


if __name__ == "__main__":
    asyncio.run(main())
