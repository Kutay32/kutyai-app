"""08 — Canlı HTTP üzerinden GERÇEK Docker konteyneri ile yaşam döngüsü.

Büyük imaj indirmemek için `nginx:alpine` yerel olarak `vllm/vllm-openai:latest`
diye etiketlenir; böylece `baslat` gerçek bir Docker konteyneri oluşturur.
Konteyner içindeki `vllm` komutu bulunmadığı için süreç hemen çıkar; bu, kendi
kendine ölen bir konteynerde durum/denetim davranışını da gözlemlemeyi sağlar.
"""

from __future__ import annotations

import json
import pathlib
import sqlite3
import subprocess
import sys

BETIKLER = pathlib.Path(__file__).resolve().parents[1] / "betikler"
sys.path.insert(0, str(BETIKLER))
sys.path.insert(0, str(BETIKLER.parents[2]))

import ortak  # noqa: E402
from arkauc.app.servisler.konteyner_docker import DockerSurucusu  # noqa: E402

JETON = ortak.jeton_al()
BASLIKLAR = ortak.basliklar(JETON)
PORT = 18800


def kabuk(komut: list[str]) -> str:
    sonuc = subprocess.run(komut, capture_output=True, text=True, check=False)
    return (sonuc.stdout + sonuc.stderr).strip()


def konteyner_yaz(bdm_id: int, govde: dict | None) -> None:
    with sqlite3.connect(ortak.DB) as baglanti:
        baglanti.execute(
            "UPDATE bdm SET konteyner = ?, durum = 'hazir' WHERE id = ?",
            (json.dumps(govde) if govde is not None else None, bdm_id),
        )
        baglanti.commit()


def main() -> None:
    print("== 0) imajı yerel etiketle ==")
    print(kabuk(["docker", "tag", "nginx:alpine", "vllm/vllm-openai:latest"]))
    print(kabuk(["docker", "images", "--format", "{{.Repository}}:{{.Tag}}", "vllm/vllm-openai:latest"]))

    kayit = ortak.bdm_olustur(
        "Docker VLLM", "vllm", temel_url="http://127.0.0.1:8000/v1",
        upstream_model="mistralai/Mistral-7B-Instruct-v0.2", jeton=JETON,
    )
    bdm_id = int(kayit["id"])
    konteyner_yaz(bdm_id, {"port": PORT})
    print(f"bdm_id={bdm_id} (durum=hazir, konteyner.port={PORT})")

    print("\n== 1) POST /baslat (gerçek Docker) ==")
    with ortak.istemci(timeout=120) as c:
        yanit = c.post(f"{ortak.UC}/{bdm_id}/baslat", headers=BASLIKLAR)
    ortak.goster("POST baslat", yanit)
    if yanit.status_code != 200:
        print("  başlatılamadı; çıkılıyor")
        return
    konteyner_id = yanit.json()["konteyner_id"]
    db = ortak.bdm_satiri(bdm_id)
    print(f"  DB durum={db['durum']} konteyner={json.dumps(db['konteyner'], ensure_ascii=False)}")
    print(f"  KALICI Mİ? {db['konteyner'].get('konteyner_id') == konteyner_id}")

    print("\n== 2) docker inspect ile doğrulama ==")
    ham = json.loads(kabuk(["docker", "inspect", konteyner_id]))[0]
    print("  Image        =", ham["Config"]["Image"])
    print("  Cmd          =", json.dumps(ham["Config"]["Cmd"]))
    print("  Labels       =", json.dumps(ham["Config"]["Labels"]))
    print("  PortBindings =", json.dumps(ham["HostConfig"]["PortBindings"]))
    print("  DeviceRequests =", json.dumps(ham["HostConfig"].get("DeviceRequests")))
    print("  Memory       =", ham["HostConfig"]["Memory"])
    print("  State        =", json.dumps({"status": ham["State"]["Status"], "exit": ham["State"]["ExitCode"]}))
    print("  günlük satırları =", json.dumps(kabuk(["docker", "logs", "--tail", "3", konteyner_id])))

    print("\n== 3) GET /durum ve /saglik (kendi kendine ölmüş konteyner) ==")
    with ortak.istemci() as c:
        ortak.goster("GET durum", c.get(f"{ortak.UC}/{bdm_id}/durum", headers=BASLIKLAR))
        ortak.goster("GET saglik", c.get(f"{ortak.UC}/{bdm_id}/saglik", headers=BASLIKLAR))

    print("\n== 4) GET /gunlukler (gerçek konteyner günlükleri) ==")
    with ortak.istemci(timeout=15) as c:
        with c.stream("GET", f"{ortak.UC}/{bdm_id}/gunlukler?satir=20", headers=BASLIKLAR) as yanit:
            print(f"  HTTP {yanit.status_code} {yanit.headers.get('content-type')}")
            for parca in yanit.iter_text():
                print(f"  | {parca!r}")
                if "not found" in parca or parca.count("event: satir") >= 20:
                    break

    print("\n== 5) POST /durdur (konteyner zaten çıkmış durumda) ==")
    with ortak.istemci(timeout=60) as c:
        ortak.goster("POST durdur", c.post(f"{ortak.UC}/{bdm_id}/durdur", headers=BASLIKLAR))
    db = ortak.bdm_satiri(bdm_id)
    print(f"  DB durum={db['durum']}")

    print("\n== 6) denetim izi satırları ==")
    for satir in ortak.sql(
        "SELECT eylem, ayrinti, ip, olusturulma FROM islem_kaydi WHERE hedef_tur='bdm' AND hedef_id=? ORDER BY id",
        (str(bdm_id),),
    ):
        print(f"  {satir}")

    print("\n== 7) temizlik ==")
    print(kabuk(["docker", "rm", "-f", konteyner_id]))
    print(kabuk(["docker", "rmi", "vllm/vllm-openai:latest"]))
    print(kabuk(["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"]))


if __name__ == "__main__":
    main()
