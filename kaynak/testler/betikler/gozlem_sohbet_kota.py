"""Gozlem 4 ve 5: kota asimi (429), kullanim kaydi durumlari ve /kullanim/ozet denetimi.

Kullanim:
    ./.venv/Scripts/python.exe kaynak/testler/betikler/gozlem_sohbet_kota.py
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import sqlite3

import httpx

DURUM = pathlib.Path("E:/kutyai-app/kaynak/testler/gecici/sohbet-gozlem-durum.json")
DB = pathlib.Path("E:/kutyai-app/kaynak/testler/gecici/sohbet-gozlem.db")


def baslik(metin: str) -> None:
    print(f"\n=== {metin}")


def say(baglanti: sqlite3.Connection, tablo: str, kosul: str = "1=1") -> int:
    return int(baglanti.execute(f"SELECT count(*) FROM {tablo} WHERE {kosul}").fetchone()[0])


def main() -> int:
    durum = json.loads(DURUM.read_text(encoding="utf-8"))
    A = durum["kullanicilar"]["A"]
    a_baslik = {"Authorization": f"Bearer {A['jeton']}"}
    y_baslik = {"Authorization": f"Bearer {durum['yonetici_jeton']}"}
    bdm1 = durum["bdm_id"]
    simdi = dt.datetime.now(dt.timezone.utc)

    baglanti = sqlite3.connect(DB)
    baslik("3.1) Kota tablosu (baslangic)")
    print(baglanti.execute("SELECT * FROM kota").fetchall())

    baslik("3.2) Kullanici A icin gunluk limit 2 (DB'ye dogrudan satir) — kullanilan=0")
    yarin = (simdi.replace(hour=0, minute=0, second=0, microsecond=0)
             + dt.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S.%f")
    gelecek_ay = (simdi.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                  + dt.timedelta(days=32)).replace(day=1).strftime("%Y-%m-%d %H:%M:%S.%f")
    baglanti.execute(
        "INSERT INTO kota (kapsam, kapsam_id, gunluk_istek, aylik_token, kullanilan_gunluk,"
        " kullanilan_aylik, gun_sifirlanma, ay_sifirlanma) VALUES"
        " ('kullanici', ?, 2, NULL, 0, 0, ?, ?)",
        (A["id"], yarin, gelecek_ay),
    )
    baglanti.commit()
    print(baglanti.execute("SELECT * FROM kota").fetchall())

    with httpx.Client(base_url=durum["taban"], timeout=60.0) as istemci:
        for sira, beklenen in ((1, 200), (2, 200), (3, 429), (4, 429)):
            once_k = say(baglanti, "konusma")
            once_m = say(baglanti, "mesaj")
            yanit = istemci.post(
                "/sohbet",
                json={"bdm_id": bdm1, "mesaj": f"Kota denemesi {sira}"},
                headers=a_baslik,
            )
            baglanti = sqlite3.connect(DB)
            print(
                f"\n-- istek {sira}: HTTP {yanit.status_code} (beklenen {beklenen})"
                f" | konusma {once_k}->{say(baglanti, 'konusma')}"
                f" | mesaj {once_m}->{say(baglanti, 'mesaj')}"
            )
            print(json.dumps(yanit.json(), ensure_ascii=False))

        baslik("3.3) 429 ayrintisindaki sifirlanma gelecekte mi?")
        yanit = istemci.post(
            "/sohbet", json={"bdm_id": bdm1, "mesaj": "Kota denemesi 5"}, headers=a_baslik
        )
        ayrinti = yanit.json()["hata"]["ayrinti"]
        sifirlanma = dt.datetime.fromisoformat(ayrinti["sifirlanma"].replace("Z", "+00:00"))
        print("ayrinti:", ayrinti)
        print("simdi     :", simdi.isoformat())
        print("sifirlanma:", sifirlanma.isoformat())
        print("gelecekte mi:", sifirlanma > simdi)
        print("kapsam:", ayrinti.get("kapsam"), "| bdm_id:", ayrinti.get("bdm_id"))

        baslik("3.4) Kota asimi akis ucunda")
        yanit = istemci.post(
            "/sohbet/akis", json={"bdm_id": bdm1, "mesaj": "Kota akis"}, headers=a_baslik
        )
        print(yanit.status_code, yanit.headers.get("content-type"), yanit.text[:300])

        baslik("3.5) Kota satiri (sonrasi)")
        baglanti = sqlite3.connect(DB)
        print(baglanti.execute("SELECT * FROM kota").fetchall())

        baslik("3.6) API anahtari kapsami: gunluk_istek_siniri=1 olan anahtar")
        yanit = istemci.post(
            "/api-anahtarlari",
            json={"ad": "Kota Anahtari", "gunluk_istek_siniri": 1},
            headers=y_baslik,
        )
        print(yanit.status_code, json.dumps(yanit.json(), ensure_ascii=False)[:300])
        anahtar = yanit.json()["tam_anahtar"]
        a_anahtar = {"Authorization": f"Bearer {anahtar}"}
        for sira in (1, 2):
            yanit = istemci.post(
                "/sohbet",
                json={"bdm_id": bdm1, "mesaj": f"Anahtar kotasi {sira}"},
                headers=a_anahtar,
            )
            print(f"-- anahtar istegi {sira}: {yanit.status_code}",
                  json.dumps(yanit.json(), ensure_ascii=False)[:400])

        baslik("3.7) GET /kullanim/ozet (personel)")
        yanit = istemci.get("/kullanim/ozet?gun=30", headers=y_baslik)
        ozet = yanit.json()
        print(yanit.status_code, json.dumps(ozet, ensure_ascii=False))

    baslik("3.8) Bagimsiz SQL ile karsilastirma (son 30 gun)")
    baglanti = sqlite3.connect(DB)
    esik = (simdi - dt.timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    satirlar = baglanti.execute(
        "SELECT durum, count(*), coalesce(sum(girdi_token),0), coalesce(sum(cikti_token),0)"
        " FROM kullanim_kaydi WHERE olusturulma >= ? GROUP BY durum",
        (esik,),
    ).fetchall()
    print("durum bazinda:", satirlar)
    toplam = baglanti.execute(
        "SELECT count(*), coalesce(sum(girdi_token),0)+coalesce(sum(cikti_token),0)"
        " FROM kullanim_kaydi WHERE olusturulma >= ?",
        (esik,),
    ).fetchone()
    gecikme = baglanti.execute(
        "SELECT sum(gecikme_ms), count(*) FROM kullanim_kaydi"
        " WHERE olusturulma >= ? AND gecikme_ms > 0",
        (esik,),
    ).fetchone()
    print("SQL toplam_istek:", toplam[0], "| SQL toplam_token:", toplam[1])
    print("SQL ortalama_gecikme_ms:", round(gecikme[0] / gecikme[1]) if gecikme[1] else 0,
          f"(sum={gecikme[0]}, adet={gecikme[1]})")
    print("API ozet          :", ozet)
    butun = baglanti.execute(
        "SELECT durum, count(*) FROM kullanim_kaydi GROUP BY durum"
    ).fetchall()
    print("tum zamanlar durum bazinda:", butun)
    print("kota kayitlari:", baglanti.execute("SELECT * FROM kota").fetchall())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
