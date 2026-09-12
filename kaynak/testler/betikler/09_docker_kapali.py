"""09 — Sürücü durumu ve hata yolları: Docker AÇIK ve Docker KAPALI.

Docker kapatıldıktan sonra canlı HTTP ile 503/200 davranışları ölçülür.
Betik Docker'ı yeniden başlatmaz (ortam başlangıçtaki gibi kapalı bırakılır).
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import time

BETIKLER = pathlib.Path(__file__).resolve().parents[1] / "betikler"
sys.path.insert(0, str(BETIKLER))
sys.path.insert(0, str(BETIKLER.parents[2]))

import ortak  # noqa: E402

JETON = ortak.jeton_al()
BASLIKLAR = ortak.basliklar(JETON)


def kabuk(komut: list[str]) -> tuple[int, str]:
    sonuc = subprocess.run(komut, capture_output=True, text=True, check=False)
    return sonuc.returncode, (sonuc.stdout + sonuc.stderr).strip()


def main() -> None:
    vllm_id = 23
    print("== A) DOCKER AÇIKKEN ==")
    kod, cikti = kabuk(["docker", "info", "--format", "{{.ServerVersion}}"])
    print(f"  docker info → çıkış={kod} çıktı={cikti}")
    with ortak.istemci() as c:
        ortak.goster("GET /surucu/durum (docker açık)", c.get(f"{ortak.UC}/surucu/durum", headers=BASLIKLAR))

    print("\n== B) DOCKER KAPATILIYOR ==")
    kod, cikti = kabuk(["docker", "desktop", "stop"])
    print(f"  docker desktop stop → çıkış={kod} çıktı={cikti[:200]}")
    kapandi = False
    for deneme in range(1, 25):
        kod, cikti = kabuk(["docker", "info"])
        if kod != 0:
            print(f"  deneme {deneme}: docker info başarısız (çıkış={kod})")
            kapandi = True
            break
        time.sleep(5)
        print(f"  deneme {deneme}: hâlâ açık…")
    print("  kapanma gözlemi:", kapandi)
    kod, cikti = kabuk(["docker", "info"])
    print("  --- docker info ham çıktı (son 6 satır) ---")
    print("\n".join(cikti.splitlines()[-6:]))

    print("\n== C) DOCKER KAPALIYKEN canlı uçlar ==")
    with ortak.istemci() as c:
        ortak.goster("GET /surucu/durum", c.get(f"{ortak.UC}/surucu/durum", headers=BASLIKLAR))
        ortak.goster("POST vllm/baslat (durdu→calisiyor)", c.post(f"{ortak.UC}/{vllm_id}/baslat", headers=BASLIKLAR))
        ortak.goster("GET vllm/durum", c.get(f"{ortak.UC}/{vllm_id}/durum", headers=BASLIKLAR))
        ortak.goster("GET vllm/saglik", c.get(f"{ortak.UC}/{vllm_id}/saglik", headers=BASLIKLAR))
        ortak.goster("GET vllm/gunlukler", c.get(f"{ortak.UC}/{vllm_id}/gunlukler", headers=BASLIKLAR))
        ortak.goster("GET saglik/hazir (sistem)", c.get("/saglik/hazir"))
    db = ortak.bdm_satiri(vllm_id)
    print(f"  vllm bdm DB durum={db['durum']} konteyner={json.dumps(db['konteyner'], ensure_ascii=False)}")


if __name__ == "__main__":
    main()
