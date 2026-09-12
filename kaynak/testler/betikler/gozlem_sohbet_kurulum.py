"""Gozlem ortami kurulumu (port 8105 backend, port 8191 sahte upstream).

Kullanim:
    ./.venv/Scripts/python.exe kaynak/testler/betikler/gozlem_sohbet_kurulum.py

Yaptigi isler:
  1. /saglik yoklamasi
  2. POST /kurulum ile yonetici + BDM (sahte upstream'e bagli)
  3. BDM durumunu dogrudan SQLite ile `hazir` yapar
  4. A ve B son kullanicilarini kayit+dogrula ile acar ve giris yapar
  5. Iki API anahtari uretir (K1, K2)
  6. Durumu `kaynak/testler/gecici/sohbet-gozlem-durum.json` dosyasina yazar
"""

from __future__ import annotations

import json
import pathlib
import sqlite3
import sys

import httpx

TABAN = "http://127.0.0.1:8105/api/v1"
DB = pathlib.Path("E:/kutyai-app/kaynak/testler/gecici/sohbet-gozlem.db")
DURUM = pathlib.Path("E:/kutyai-app/kaynak/testler/gecici/sohbet-gozlem-durum.json")
PAROLA = "Parola123!"


def baslik(metin: str) -> None:
    print(f"\n=== {metin}")


def main() -> int:
    istemci = httpx.Client(base_url=TABAN, timeout=30.0)

    baslik("1) GET /saglik")
    yanit = istemci.get("/saglik")
    print(yanit.status_code, yanit.text)

    baslik("2) POST /kurulum")
    kurulum = {
        "marka_adi": "Gozlem AI",
        "yonetici": {
            "eposta": "admin@acme.com",
            "ad_soyad": "Gozlem Yonetici",
            "parola": PAROLA,
        },
        "bdm": {
            "gorunen_ad": "Sahte Akis Modeli",
            "slug": "sahte-akis",
            "saglayici": "ozel",
            "temel_url": "http://127.0.0.1:8191/v1",
            "upstream_model": "sahte-akis",
            "api_anahtari": "sk-gozlem-1234567890",
            "yerel_mi": True,
        },
        "dogrula": False,
    }
    yanit = istemci.post("/kurulum", json=kurulum)
    print(yanit.status_code, json.dumps(yanit.json(), ensure_ascii=False)[:600])
    bdm_id = yanit.json()["bdm"]["id"]

    baslik("3) SQLite: BDM durumunu hazir yap")
    with sqlite3.connect(DB) as baglanti:
        baglanti.execute("UPDATE bdm SET durum='hazir' WHERE id=?", (bdm_id,))
        baglanti.commit()
        print("bdm durum:", baglanti.execute(
            "SELECT id, slug, durum, temel_url, upstream_model FROM bdm").fetchall())

    baslik("4) POST /kimlik/panel-giris (yonetici)")
    yanit = istemci.post(
        "/kimlik/panel-giris", json={"eposta": "admin@acme.com", "parola": PAROLA}
    )
    print(yanit.status_code, "erisim_jetonu" in yanit.json(), yanit.text[:200])
    yonetici_jeton = yanit.json()["erisim_jetonu"]
    yonetici_id = yanit.json()["kullanici"]["id"]

    kullanicilar: dict[str, dict[str, object]] = {}
    for etiket, eposta in (("A", "a@acme.com"), ("B", "b@acme.com")):
        baslik(f"5) Kullanici {etiket} kayit + dogrula + giris")
        yanit = istemci.post(
            "/kimlik/kayit",
            json={"eposta": eposta, "ad_soyad": f"Kullanici {etiket}", "parola": PAROLA},
        )
        print(etiket, "kayit", yanit.status_code, yanit.text[:300])
        baglanti = yanit.json()["gelistirme_baglantisi"]
        jeton = baglanti.split("jeton=")[1]
        yanit = istemci.post("/kimlik/dogrula", json={"jeton": jeton})
        print(etiket, "dogrula", yanit.status_code, yanit.text)
        yanit = istemci.post("/kimlik/giris", json={"eposta": eposta, "parola": PAROLA})
        print(etiket, "giris", yanit.status_code)
        kullanicilar[etiket] = {
            "id": yanit.json()["kullanici"]["id"],
            "eposta": eposta,
            "jeton": yanit.json()["erisim_jetonu"],
        }

    baslik("6) API anahtarlari K1, K2")
    anahtarlar: dict[str, str] = {}
    for ad in ("K1", "K2"):
        yanit = istemci.post(
            "/api-anahtarlari",
            json={"ad": f"Gozlem {ad}"},
            headers={"Authorization": f"Bearer {yonetici_jeton}"},
        )
        print(ad, yanit.status_code, yanit.json()["onek"], yanit.json()["son_dort"])
        anahtarlar[ad] = yanit.json()["tam_anahtar"]

    durum = {
        "taban": TABAN,
        "db": str(DB),
        "bdm_id": bdm_id,
        "yonetici_id": yonetici_id,
        "yonetici_jeton": yonetici_jeton,
        "kullanicilar": kullanicilar,
        "anahtarlar": anahtarlar,
    }
    DURUM.write_text(json.dumps(durum, ensure_ascii=False, indent=2), encoding="utf-8")
    baslik("7) Durum dosyasi")
    print(str(DURUM))
    return 0


if __name__ == "__main__":
    sys.exit(main())
