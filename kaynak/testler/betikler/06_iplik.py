"""06 — SSE akışı terk edildiğinde sunucu iş parçacığı sızıntısı var mı?

`DockerSurucusu.gunlukler` her okumada `asyncio.to_thread(next, akis, None)`
kullanır; istemci bağlantıyı kapatırsa bu iş parçacığı bloke kalabilir.
İş parçacığı sayısı Windows PowerShell ile süreç düzeyinde ölçülür.
"""

from __future__ import annotations

import asyncio
import json
import pathlib
import subprocess
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


def iplik_sayisi(pid: int) -> int:
    cikti = subprocess.run(
        ["powershell", "-NoProfile", "-Command", f"(Get-Process -Id {pid}).Threads.Count"],
        capture_output=True,
        text=True,
        check=False,
    )
    return int(cikti.stdout.strip() or 0)


def konteyner_id_yaz(bdm_id: int, kimlik: str) -> None:
    import sqlite3

    with sqlite3.connect(ortak.DB) as baglanti:
        baglanti.execute(
            "UPDATE bdm SET konteyner = ? WHERE id = ?",
            (json.dumps({"konteyner_id": kimlik, "image": "nginx:alpine"}), bdm_id),
        )
        baglanti.commit()


async def main(pid: int) -> None:
    surucu = DockerSurucusu()
    manifest = {"image": "nginx:alpine", "komut": [], "port": 18098, "gpu": False, "bellek_gb": 1, "ortam": {}}
    kimlik = await surucu.baslat({"id": 0, "slug": "iplik-gozlem", "temel_url": "x", "upstream_model": "x"}, manifest)
    bdm = ortak.bdm_olustur("Iplik Gozlem", "vllm", temel_url="http://127.0.0.1:11435/v1", yerel_mi=True, jeton=JETON)
    ortak.durum_yaz(int(bdm["id"]), "hazir")
    konteyner_id_yaz(int(bdm["id"]), kimlik)
    yol = f"{ortak.UC}/{bdm['id']}/gunlukler?satir=200"

    try:
        zaman = time.sleep
        zaman(3.0)
        taban = iplik_sayisi(pid)
        print(f"konteyner={kimlik[:16]}…  sunucu pid={pid}")
        print(f"T0 taban iş parçacığı sayısı = {taban}")

        for tur in range(1, 4):
            with httpx.Client(base_url=ortak.BASE, timeout=15.0) as c:
                with c.stream("GET", yol, headers=BASLIKLAR) as yanit:
                    ilk = next(yanit.iter_text(), "")
                    print(f"  tur {tur}: HTTP {yanit.status_code}, ilk parça {len(ilk)} bayt; bağlantı TERK EDİLİYOR")
            zaman(1.5)
            print(f"  tur {tur} sonrası iş parçacığı = {iplik_sayisi(pid)}")

        zaman(3.0)
        terk_sonrasi = iplik_sayisi(pid)
        print(f"T1 (3 akış terk edildikten sonra) = {terk_sonrasi} (taban {taban}, fark {terk_sonrasi - taban})")

        with ortak.istemci() as c:
            yanit = c.get(f"{ortak.UC}/surucu/durum", headers=BASLIKLAR)
            print(f"  diğer uç hâlâ çalışıyor mu? HTTP {yanit.status_code}")

        await surucu.durdur(kimlik)
        zaman(3.0)
        print(f"T2 (konteyner durdurulduktan sonra) = {iplik_sayisi(pid)}")
    finally:
        await surucu.sil(kimlik)


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1])))
