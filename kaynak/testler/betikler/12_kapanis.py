"""12 — Kapanış kanıtları: yerel sürücü sağlık adresi, denetim izi dökümü."""

from __future__ import annotations

import json
import pathlib
import sys

BETIKLER = pathlib.Path(__file__).resolve().parents[1] / "betikler"
sys.path.insert(0, str(BETIKLER))
sys.path.insert(0, str(BETIKLER.parents[2]))

import ortak  # noqa: E402

BASLIKLAR = ortak.basliklar(ortak.jeton_al())


def main() -> None:
    print("== 1) Yerel sürücü sağlığı: BDM'nin temel_url'u mu, varsayılan mı? ==")
    for satir in ortak.sql("SELECT id, slug, saglayici, temel_url, durum, konteyner FROM bdm ORDER BY id"):
        print(f"  bdm {satir[0]:>2} slug={satir[1]:<22} saglayici={satir[2]:<8} temel_url={satir[3]:<32} durum={satir[4]:<10} konteyner_id={(json.loads(satir[5]) if satir[5] else {}).get('konteyner_id')}")

    print("\n-- sahte Ollama (127.0.0.1:11435) AYAKTA; GET /{id}/saglik --")
    with ortak.istemci() as c:
        for bdm_id in (16, 17):
            ortak.goster(f"GET bdm {bdm_id}/saglik", c.get(f"{ortak.UC}/{bdm_id}/saglik", headers=BASLIKLAR))
            ortak.goster(f"GET bdm {bdm_id}/durum", c.get(f"{ortak.UC}/{bdm_id}/durum", headers=BASLIKLAR))

    print("\n== 2) Sahte Ollama'ya gelen istekler (ham günlük) ==")
    print(pathlib.Path(ortak.GECICI / "fake_ollama.log").read_text(encoding="utf-8").strip() or "(boş)")

    print("\n== 3) Denetim izi dökümü (bdm hedefli) ==")
    for satir in ortak.sql(
        "SELECT id, kullanici_id, eylem, hedef_id, ayrinti, ip FROM islem_kaydi WHERE hedef_tur='bdm' ORDER BY id"
    ):
        print(f"  {satir}")

    print("\n== 4) PATCH /{id}/yol denetim izi yazıyor mu? ==")
    with ortak.istemci() as c:
        yanit = c.patch(f"{ortak.UC}/16/yol", json={"takma_ad": "kapanis"}, headers=BASLIKLAR)
        print(f"  PATCH → HTTP {yanit.status_code}")
    satirlar = ortak.sql("SELECT eylem FROM islem_kaydi WHERE hedef_id = '16' ORDER BY id")
    print(f"  bdm 16 için eylemler = {[s[0] for s in satirlar]}")


if __name__ == "__main__":
    main()
