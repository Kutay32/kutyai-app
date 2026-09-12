"""Gozlem 9: istemci akisi yarida keserse ne olur?

Kullanim:
    ./.venv/Scripts/python.exe kaynak/testler/betikler/gozlem_sohbet_iptal.py
"""

from __future__ import annotations

import json
import pathlib
import sqlite3
import time

import httpx

DURUM = pathlib.Path("E:/kutyai-app/kaynak/testler/gecici/sohbet-gozlem-durum.json")
KAYIT = pathlib.Path("E:/kutyai-app/kaynak/testler/gecici/sahte_upstream_istekler.jsonl")
DB = pathlib.Path("E:/kutyai-app/kaynak/testler/gecici/sohbet-gozlem.db")


def baslik(metin: str) -> None:
    print(f"\n=== {metin}")


def main() -> int:
    durum = json.loads(DURUM.read_text(encoding="utf-8"))
    B = durum["kullanicilar"]["B"]
    b_baslik = {"Authorization": f"Bearer {B['jeton']}"}
    y_baslik = {"Authorization": f"Bearer {durum['yonetici_jeton']}"}

    with httpx.Client(base_url=durum["taban"], timeout=60.0) as istemci:
        baslik("5.1) Yavas BDM olustur (upstream_model=yavas, 10 x 0.5 sn)")
        yanit = istemci.post(
            "/bdm",
            json={
                "gorunen_ad": "Yavas Model",
                "slug": "yavas-model",
                "saglayici": "ozel",
                "temel_url": "http://127.0.0.1:8191/v1",
                "upstream_model": "yavas",
                "yerel_mi": True,
            },
            headers=y_baslik,
        )
        print("POST /bdm", yanit.status_code, yanit.json()["id"], yanit.json()["durum"])
        yavas_id = yanit.json()["id"]
        with sqlite3.connect(DB) as baglanti:
            baglanti.execute("UPDATE bdm SET durum='hazir' WHERE id=?", (yavas_id,))
            baglanti.commit()

        baslik("5.2) Akisi oku, ilk parcalardan sonra baglantiyi kapat")
        govde = {"bdm_id": yavas_id, "mesaj": "Yarida kesecegim"}
        okunan: list[str] = []
        baslangic = time.perf_counter()
        with istemci.stream("POST", "/sohbet/akis", json=govde, headers=b_baslik) as yanit:
            print("durum:", yanit.status_code)
            for satir in yanit.iter_lines():
                okunan.append(satir)
                print(f"{time.perf_counter() - baslangic:6.2f}s | {satir}")
                if len(okunan) >= 6:
                    print("--- baglanti kapatiliyor ---")
                    break
        print(f"kapatma aninda gecen sure: {time.perf_counter() - baslangic:.2f}s")

        konusma_id = None
        for indeks, satir in enumerate(okunan):
            if satir.startswith("data: "):
                veri = json.loads(satir[len("data: ") :])
                if "konusma_id" in veri:
                    konusma_id = veri["konusma_id"]
        print("konusma_id:", konusma_id)

        print("... 4 sn bekleniyor (upstream iptal edildi mi?) ...")
        time.sleep(4.0)

        baslik("5.3) Veritabani durumu (bagimsiz SQL)")
        baglanti = sqlite3.connect(DB)
        print("mesajlar:", baglanti.execute(
            "SELECT id, rol, icerik FROM mesaj WHERE konusma_id=? ORDER BY id",
            (konusma_id,)).fetchall())
        print("kullanim_kaydi:", baglanti.execute(
            "SELECT id, durum, girdi_token, cikti_token FROM kullanim_kaydi"
            " WHERE konusma_id=?", (konusma_id,)).fetchall())

        baslik("5.4) Sahte upstream kaydi: iptal edildi mi?")
        for satir in KAYIT.read_text(encoding="utf-8").strip().splitlines():
            kayit = json.loads(satir)
            if kayit.get("model") == "yavas":
                print(json.dumps(kayit, ensure_ascii=False)[:400])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
