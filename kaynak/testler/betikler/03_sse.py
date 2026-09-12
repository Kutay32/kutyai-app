"""03 — `GET /{id}/gunlukler` SSE davranışı: 503, olay biçimi, askıda kalma.

Docker ayaktayken gerçek bir konteyner (`nginx:alpine`) kullanılır.
"""

from __future__ import annotations

import asyncio
import json
import pathlib
import sys
import time

BETIKLER = pathlib.Path(__file__).resolve().parents[1] / "betikler"
sys.path.insert(0, str(BETIKLER))
sys.path.insert(0, str(BETIKLER.parents[2]))

import httpx  # noqa: E402

import ortak  # noqa: E402
from arkauc.app.servisler.konteyner_docker import DockerSurucusu  # noqa: E402

JETON = ortak.jeton_al()
BASLIKLAR = ortak.basliklar(JETON)


def yeni_bdm(ad: str, saglayici: str, durum: str = "hazir", *, yerel: bool = True) -> int:
    kayit = ortak.bdm_olustur(
        ad, saglayici, temel_url="http://127.0.0.1:11435/v1", upstream_model="llama3", yerel_mi=yerel, jeton=JETON
    )
    ortak.durum_yaz(int(kayit["id"]), durum)
    return int(kayit["id"])


def konteyner_id_yaz(bdm_id: int, kimlik: str, ek: dict | None = None) -> None:
    import sqlite3

    govde = dict(ek or {})
    govde["konteyner_id"] = kimlik
    with sqlite3.connect(ortak.DB) as baglanti:
        baglanti.execute("UPDATE bdm SET konteyner = ? WHERE id = ?", (json.dumps(govde), bdm_id))
        baglanti.commit()


def akis_oku(bdm_id: int, *, satir: int = 200, zaman_asimi: float = 10.0) -> None:
    baslangic = time.time()
    olaylar: list[str] = []
    try:
        with httpx.Client(base_url=ortak.BASE, timeout=zaman_asimi) as c:
            with c.stream("GET", f"{ortak.UC}/{bdm_id}/gunlukler?satir={satir}", headers=BASLIKLAR) as yanit:
                print(f"  HTTP {yanit.status_code} content-type={yanit.headers.get('content-type')}")
                print(f"  başlıklar: cache-control={yanit.headers.get('cache-control')} x-accel-buffering={yanit.headers.get('x-accel-buffering')}")
                try:
                    for parca in yanit.iter_text():
                        olaylar.append(parca)
                        if time.time() - baslangic > zaman_asimi:
                            break
                except httpx.HTTPError as hata:
                    print(f"  AKIŞ HATASI ({type(hata).__name__}): {hata}")
    except httpx.HTTPError as hata:
        print(f"  İSTEK HATASI ({type(hata).__name__}): {hata}")
    gecen = time.time() - baslangic
    print(f"  geçen süre = {gecen:.2f} sn, parça sayısı = {len(olaylar)}")
    for parca in olaylar[:8]:
        print(f"  | {parca!r}")
    if olaylar:
        print(f"  olay sayısı (event: satir) = {''.join(olaylar).count('event: satir')}")


async def main() -> None:
    print("== 1) konteyner kaydı YOKKEN ==")
    b = yeni_bdm("SSE Kayitsiz", "ollama")
    akis_oku(b)

    print("\n== 2) kayıt var, sürücü 'yerel' (olmayan Ollama) ==")
    b2 = yeni_bdm("SSE Yerel", "ollama")
    konteyner_id_yaz(b2, "yerel:sse-yerel")
    akis_oku(b2)

    print("\n== 3) kayıt var ama konteyner Docker'da YOK (vllm/yel) ==")
    b3 = yeni_bdm("SSE Yok Konteyner", "vllm")
    konteyner_id_yaz(b3, "boyle-bir-konteyner-yok")
    akis_oku(b3)

    print("\n== 4) gerçek Docker konteyneri ile akış ==")
    surucu = DockerSurucusu()
    manifest = {"image": "nginx:alpine", "komut": [], "port": 18099, "gpu": False, "bellek_gb": 1, "ortam": {}}
    kimlik = await surucu.baslat({"id": 0, "slug": "sse-gercek", "temel_url": "x", "upstream_model": "x"}, manifest)
    print(f"  gerçek konteyner = {kimlik[:20]}…")
    b4 = yeni_bdm("SSE Gercek", "vllm")
    konteyner_id_yaz(b4, kimlik, {"image": "nginx:alpine", "port": 18099})
    try:
        akis_oku(b4, satir=5, zaman_asimi=10.0)
    finally:
        await surucu.durdur(kimlik)
        await surucu.sil(kimlik)
        print("  konteyner durduruldu ve silindi")

    print("\n== 5) satir parametresi doğrulaması ==")
    with ortak.istemci() as c:
        for deger in ("0", "5000", "abc"):
            yanit = c.get(f"{ortak.UC}/{b2}/gunlukler?satir={deger}", headers=BASLIKLAR)
            print(f"  satir={deger:<5} → HTTP {yanit.status_code} {yanit.text[:120]}")


if __name__ == "__main__":
    asyncio.run(main())
