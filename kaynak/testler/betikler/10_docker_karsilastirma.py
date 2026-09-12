"""10 — Docker AÇIK / KAPALI canlı `/surucu/durum` karşılaştırması.

Docker Desktop başlatılır, ayakta olduğu doğrulanır, canlı uçlar yoklanır;
ardından Docker yeniden durdurulur (ortam ilk haline döner).
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
import time

BETIKLER = pathlib.Path(__file__).resolve().parents[1] / "betikler"
sys.path.insert(0, str(BETIKLER))
sys.path.insert(0, str(BETIKLER.parents[2]))

import ortak  # noqa: E402

BASLIKLAR = ortak.basliklar(ortak.jeton_al())


def kabuk(komut: list[str]) -> tuple[int, str]:
    sonuc = subprocess.run(komut, capture_output=True, text=True, check=False)
    return sonuc.returncode, (sonuc.stdout + sonuc.stderr).strip()


def bekle(acik: bool, *, deneme: int = 40) -> bool:
    for i in range(1, deneme + 1):
        kod, _ = kabuk(["docker", "info", "--format", "{{.ServerVersion}}"])
        if (kod == 0) == acik:
            return True
        time.sleep(3)
    return False


def yokla(etiket: str) -> None:
    with ortak.istemci(timeout=20) as c:
        ortak.goster(f"GET /surucu/durum [{etiket}]", c.get(f"{ortak.UC}/surucu/durum", headers=BASLIKLAR))
        ortak.goster(f"GET /saglik/hazir [{etiket}]", c.get("/saglik/hazir"))


def main() -> None:
    print("== Docker başlatılıyor ==")
    print("  docker desktop start →", kabuk(["docker", "desktop", "start"]))
    print("  ayakta mı?", bekle(True))
    kod, cikti = kabuk(["docker", "info", "--format", "{{.ServerVersion}}"])
    print(f"  docker info → çıkış={kod} sunucu sürümü={cikti}")
    kod, cikti = kabuk(["docker", "pull", "nginx:alpine"])
    print(f"  docker pull nginx:alpine → çıkış={kod} son satır={cikti.splitlines()[-1] if cikti else ''}")
    yokla("docker açık")

    print("\n== Docker durduruluyor ==")
    print("  docker desktop stop →", kabuk(["docker", "desktop", "stop"]))
    print("  kapandı mı?", bekle(False))
    kod, cikti = kabuk(["docker", "info"])
    print(f"  docker info → çıkış={kod}")
    print("  ham çıktı son 3 satır:")
    print("\n".join(cikti.splitlines()[-3:]))
    yokla("docker kapalı")


if __name__ == "__main__":
    main()
