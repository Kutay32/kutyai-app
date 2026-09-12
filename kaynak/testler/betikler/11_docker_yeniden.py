"""11 — GERÇEK Docker ile `yeniden-baslat`: eski konteyner gerçekten kaldırılıyor mu?"""

from __future__ import annotations

import json
import pathlib
import sqlite3
import subprocess
import sys
import time

BETIKLER = pathlib.Path(__file__).resolve().parents[1] / "betikler"
sys.path.insert(0, str(BETIKLER))
sys.path.insert(0, str(BETIKLER.parents[2]))

import ortak  # noqa: E402

BASLIKLAR = ortak.basliklar(ortak.jeton_al())
PORT = 18810


def kabuk(komut: list[str]) -> tuple[int, str]:
    sonuc = subprocess.run(komut, capture_output=True, text=True, check=False)
    return sonuc.returncode, (sonuc.stdout + sonuc.stderr).strip()


def bekle_docker(deneme: int = 40) -> bool:
    for _ in range(deneme):
        if kabuk(["docker", "info", "--format", "x"])[0] == 0:
            return True
        time.sleep(3)
    return False


def main() -> None:
    print("== Docker başlatılıyor ==")
    print("  start →", kabuk(["docker", "desktop", "start"])[1])
    print("  ayakta mı?", bekle_docker())
    print("  tag →", kabuk(["docker", "tag", "nginx:alpine", "vllm/vllm-openai:latest"]))

    kayit = ortak.bdm_olustur(
        "Docker Yeniden", "vllm", temel_url="http://127.0.0.1:8000/v1",
        upstream_model="mistralai/Mistral-7B-Instruct-v0.2", jeton=ortak.jeton_al(),
    )
    bdm_id = int(kayit["id"])
    with sqlite3.connect(ortak.DB) as baglanti:
        baglanti.execute(
            "UPDATE bdm SET konteyner = ?, durum = 'hazir' WHERE id = ?",
            (json.dumps({"port": PORT}), bdm_id),
        )
        baglanti.commit()
    print(f"bdm_id={bdm_id} port={PORT}")

    print("\n== baslat ==")
    with ortak.istemci(timeout=120) as c:
        yanit = c.post(f"{ortak.UC}/{bdm_id}/baslat", headers=BASLIKLAR)
    print(f"  HTTP {yanit.status_code} {yanit.text[:160]}")
    ilk = yanit.json()["konteyner_id"]
    print("  ilk konteyner çalışıyor mu (docker inspect):", kabuk(["docker", "inspect", "-f", "{{.State.Status}}", ilk]))

    print("\n== yeniden-baslat ==")
    with ortak.istemci(timeout=120) as c:
        yanit = c.post(f"{ortak.UC}/{bdm_id}/yeniden-baslat", headers=BASLIKLAR)
    print(f"  HTTP {yanit.status_code} {yanit.text[:160]}")
    ikinci = yanit.json()["konteyner_id"]
    print(f"  yeni konteyner kimliği farklı mı? {ilk != ikinci}")
    kod, cikti = kabuk(["docker", "inspect", "-f", "{{.State.Status}}", ilk])
    print(f"  eski konteyner inspect → çıkış={kod} çıktı={cikti[:160]}")
    print("  yeni konteyner durumu:", kabuk(["docker", "inspect", "-f", "{{.State.Status}}", ikinci]))
    db = ortak.bdm_satiri(bdm_id)
    print(f"  DB konteyner = {json.dumps(db['konteyner'], ensure_ascii=False)}")
    print(f"  DB'deki kimlik yeni mi? {db['konteyner']['konteyner_id'] == ikinci}")

    print("\n== denetim izi ==")
    for satir in ortak.sql(
        "SELECT eylem, ayrinti FROM islem_kaydi WHERE hedef_tur='bdm' AND hedef_id=? ORDER BY id",
        (str(bdm_id),),
    ):
        print(f"  {satir}")

    print("\n== temizlik ==")
    print(" ", kabuk(["docker", "rm", "-f", ikinci])[1])
    print(" ", kabuk(["docker", "rmi", "vllm/vllm-openai:latest"])[1])
    print("  docker desktop stop →", kabuk(["docker", "desktop", "stop"])[1])
    for _ in range(30):
        if kabuk(["docker", "info"])[0] != 0:
            break
        time.sleep(3)
    print("  docker kapalı mı?", kabuk(["docker", "info"])[0] != 0)


if __name__ == "__main__":
    main()
