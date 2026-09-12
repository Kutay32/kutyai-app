"""Gozlem 6 ve 8: tek yanit, upstream 500/400 -> 502, akista hata olayi, hazir olmayan BDM.

Kullanim:
    ./.venv/Scripts/python.exe kaynak/testler/betikler/gozlem_sohbet_hata.py
"""

from __future__ import annotations

import json
import pathlib
import sqlite3

import httpx

DURUM = pathlib.Path("E:/kutyai-app/kaynak/testler/gecici/sohbet-gozlem-durum.json")
KAYIT = pathlib.Path("E:/kutyai-app/kaynak/testler/gecici/sahte_upstream_istekler.jsonl")
DB = pathlib.Path("E:/kutyai-app/kaynak/testler/gecici/sohbet-gozlem.db")


def baslik(metin: str) -> None:
    print(f"\n=== {metin}")


def sse_oku(istemci: httpx.Client, govde: dict, basliklar: dict) -> list[tuple[str, str]]:
    olaylar: list[tuple[str, str]] = []
    ad = None
    with istemci.stream("POST", "/sohbet/akis", json=govde, headers=basliklar) as yanit:
        print("durum:", yanit.status_code, "| content-type:", yanit.headers.get("content-type"))
        for satir in yanit.iter_lines():
            print("  ", satir)
            if satir.startswith("event: "):
                ad = satir[len("event: ") :]
            elif satir.startswith("data: ") and ad:
                olaylar.append((ad, satir[len("data: ") :]))
                ad = None
    return olaylar


def main() -> int:
    durum = json.loads(DURUM.read_text(encoding="utf-8"))
    A = durum["kullanicilar"]["A"]
    a_baslik = {"Authorization": f"Bearer {A['jeton']}"}
    y_baslik = {"Authorization": f"Bearer {durum['yonetici_jeton']}"}
    bdm1 = durum["bdm_id"]

    with httpx.Client(base_url=durum["taban"], timeout=60.0) as istemci:
        baslik("2.1) POST /sohbet (tek yanit) — kullanici mesaji ve yanit")
        yanit = istemci.post(
            "/sohbet",
            json={"bdm_id": bdm1, "mesaj": "Tek yanit denemesi: ahmet@ornek.com"},
            headers=a_baslik,
        )
        print(yanit.status_code, json.dumps(yanit.json(), ensure_ascii=False))
        konusma_id = yanit.json()["konusma_id"]

        baslik("2.2) Ayni konusmada ikinci istek (konusma_id ile)")
        yanit = istemci.post(
            "/sohbet",
            json={"bdm_id": bdm1, "konusma_id": konusma_id, "mesaj": "Ikinci soru"},
            headers=a_baslik,
        )
        print(yanit.status_code, json.dumps(yanit.json(), ensure_ascii=False))

        baslik("2.3) Upstream'e giden govdeler (rol alanlari dahil)")
        for satir in KAYIT.read_text(encoding="utf-8").strip().splitlines():
            kayit = json.loads(satir)
            if kayit.get("olay") != "istek":
                continue
            if not kayit.get("akis"):
                print(json.dumps(kayit["govde"], ensure_ascii=False))

        baslik("2.4) Kati (OpenAI rol dogrulamasi yapan) BDM olustur")
        yanit = istemci.post(
            "/bdm",
            json={
                "gorunen_ad": "Kati Saglayici",
                "slug": "kati-saglayici",
                "saglayici": "ozel",
                "temel_url": "http://127.0.0.1:8191/v1",
                "upstream_model": "kati",
                "yerel_mi": True,
            },
            headers=y_baslik,
        )
        print("POST /bdm", yanit.status_code, yanit.json().get("slug"), yanit.json().get("durum"))
        kati_id = yanit.json()["id"]

        baslik("2.5) Taslak BDM olustur (hazir degil)")
        yanit = istemci.post(
            "/bdm",
            json={
                "gorunen_ad": "Taslak Model",
                "slug": "taslak-model",
                "saglayici": "ozel",
                "temel_url": "http://127.0.0.1:8191/v1",
                "upstream_model": "sahte-akis",
                "yerel_mi": True,
            },
            headers=y_baslik,
        )
        print("POST /bdm", yanit.status_code, yanit.json().get("slug"), yanit.json().get("durum"))
        taslak_id = yanit.json()["id"]

        with sqlite3.connect(DB) as baglanti:
            baglanti.execute("UPDATE bdm SET durum='hazir' WHERE id=?", (kati_id,))
            baglanti.commit()
        print("kati bdm durum:",
              sqlite3.connect(DB).execute("SELECT id,slug,durum FROM bdm").fetchall())

        baslik("2.6) POST /sohbet — upstream 400 donduren kati saglayici")
        yanit = istemci.post(
            "/sohbet",
            json={"bdm_slug": "kati-saglayici", "mesaj": "Merhaba"},
            headers=a_baslik,
        )
        print(yanit.status_code, json.dumps(yanit.json(), ensure_ascii=False, indent=2))

        baslik("2.7) POST /sohbet/akis — upstream 400 (hata olayi)")
        sse_oku(istemci, {"bdm_slug": "kati-saglayici", "mesaj": "Merhaba"}, a_baslik)

        baslik("2.8) POST /sohbet — upstream 500 donduren BDM ayarla (sqlite)")
        with sqlite3.connect(DB) as baglanti:
            baglanti.execute("UPDATE bdm SET upstream_model='hata-500' WHERE id=?", (kati_id,))
            baglanti.commit()
        yanit = istemci.post(
            "/sohbet",
            json={"bdm_slug": "kati-saglayici", "mesaj": "Merhaba"},
            headers=a_baslik,
        )
        print(yanit.status_code, json.dumps(yanit.json(), ensure_ascii=False, indent=2))

        yanit = istemci.post(
            "/sohbet/akis",
            json={"bdm_slug": "kati-saglayici", "mesaj": "Merhaba"},
            headers=a_baslik,
        )
        print(yanit.status_code, yanit.headers.get("content-type"))

        baslik("2.9) POST /sohbet/akis — upstream 500 (hata olayi)")
        sse_oku(istemci, {"bdm_slug": "kati-saglayici", "mesaj": "Merhaba"}, a_baslik)

        baslik("2.10) POST /sohbet — hazir olmayan (taslak) BDM")
        yanit = istemci.post(
            "/sohbet",
            json={"bdm_id": taslak_id, "mesaj": "Merhaba"},
            headers=a_baslik,
        )
        print(yanit.status_code, json.dumps(yanit.json(), ensure_ascii=False, indent=2))
        yanit = istemci.post(
            "/sohbet/akis",
            json={"bdm_id": taslak_id, "mesaj": "Merhaba"},
            headers=a_baslik,
        )
        print("akis:", yanit.status_code, yanit.text[:200])

        baslik("2.11) GET /kullanim/ozet (personel) — ham")
        yanit = istemci.get("/kullanim/ozet", headers=y_baslik)
        print(yanit.status_code, json.dumps(yanit.json(), ensure_ascii=False))

    baslik("2.12) SQLite: kullanim_kaydi satirlari")
    with sqlite3.connect(DB) as baglanti:
        for satir in baglanti.execute(
            "SELECT id, bdm_id, kullanici_id, api_anahtari_id, konusma_id, girdi_token,"
            " cikti_token, durum FROM kullanim_kaydi ORDER BY id"
        ):
            print(satir)
        print("konusma sayisi:",
              baglanti.execute("SELECT count(*) FROM konusma").fetchone())
        print("mesaj sayisi:", baglanti.execute("SELECT count(*) FROM mesaj").fetchone())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
