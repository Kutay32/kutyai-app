"""Gozlem 7 ve 10: konusma sahipligi ve PATCH/DELETE davranisi.

Kullanim:
    ./.venv/Scripts/python.exe kaynak/testler/betikler/gozlem_sohbet_sahiplik.py
"""

from __future__ import annotations

import json
import pathlib
import sqlite3

import httpx

DURUM = pathlib.Path("E:/kutyai-app/kaynak/testler/gecici/sohbet-gozlem-durum.json")
DB = pathlib.Path("E:/kutyai-app/kaynak/testler/gecici/sohbet-gozlem.db")


def baslik(metin: str) -> None:
    print(f"\n=== {metin}")


def ozet(yanit: httpx.Response) -> str:
    return f"{yanit.status_code} {yanit.text[:220]}"


def main() -> int:
    durum = json.loads(DURUM.read_text(encoding="utf-8"))
    A = durum["kullanicilar"]["A"]
    B = durum["kullanicilar"]["B"]
    a_baslik = {"Authorization": f"Bearer {A['jeton']}"}
    b_baslik = {"Authorization": f"Bearer {B['jeton']}"}
    y_baslik = {"Authorization": f"Bearer {durum['yonetici_jeton']}"}
    k1_baslik = {"Authorization": f"Bearer {durum['anahtarlar']['K1']}"}
    k2_baslik = {"Authorization": f"Bearer {durum['anahtarlar']['K2']}"}
    bdm1 = durum["bdm_id"]

    baglanti = sqlite3.connect(DB)
    baglanti.execute("DELETE FROM kota WHERE kapsam='kullanici' AND kapsam_id=?", (A["id"],))
    baglanti.commit()
    print("A kotasi silindi; kalan kota satirlari:", baglanti.execute("SELECT * FROM kota").fetchall())

    with httpx.Client(base_url=durum["taban"], timeout=60.0) as istemci:
        baslik("4.1) A kendi konusmasini acar")
        yanit = istemci.post(
            "/sohbet", json={"bdm_id": bdm1, "mesaj": "A'nin ozel konusmasi"}, headers=a_baslik
        )
        print(ozet(yanit))
        konusma_a = yanit.json()["konusma_id"]

        baslik("4.2) B kullanicisi A'nin konusmasina erismeye calisir")
        print("GET    ->", ozet(istemci.get(f"/sohbet/konusmalar/{konusma_a}", headers=b_baslik)))
        print("PATCH  ->", ozet(istemci.patch(
            f"/sohbet/konusmalar/{konusma_a}", json={"baslik": "ele gecirildi"}, headers=b_baslik)))
        print("DELETE ->", ozet(istemci.delete(f"/sohbet/konusmalar/{konusma_a}", headers=b_baslik)))
        print("POST /sohbet (konusma_id) ->", ozet(istemci.post(
            "/sohbet",
            json={"bdm_id": bdm1, "konusma_id": konusma_a, "mesaj": "B'nin mesaji"},
            headers=b_baslik,
        )))

        baslik("4.3) B'nin konusma listesi")
        print(json.dumps(istemci.get("/sohbet/konusmalar", headers=b_baslik).json(),
                         ensure_ascii=False, indent=2))

        baslik("4.4) A'nin konusmasi hala duruyor mu?")
        print("GET (A) ->", ozet(istemci.get(f"/sohbet/konusmalar/{konusma_a}", headers=a_baslik)))
        baglanti = sqlite3.connect(DB)
        print("DB baslik:", baglanti.execute(
            "SELECT id, baslik FROM konusma WHERE id=?", (konusma_a,)).fetchall())

        baslik("4.5) K1 anahtari kendi konusmasini acar; K2 ve panel yoneticisi erismeye calisir")
        yanit = istemci.post(
            "/sohbet", json={"bdm_id": bdm1, "mesaj": "K1 konusmasi"}, headers=k1_baslik
        )
        print("K1 POST ->", ozet(yanit))
        konusma_k1 = yanit.json()["konusma_id"]
        print("K1 GET  ->", ozet(istemci.get(f"/sohbet/konusmalar/{konusma_k1}", headers=k1_baslik)))
        print("K2 GET  ->", ozet(istemci.get(f"/sohbet/konusmalar/{konusma_k1}", headers=k2_baslik)))
        print("K2 PATCH->", ozet(istemci.patch(
            f"/sohbet/konusmalar/{konusma_k1}", json={"baslik": "K2"}, headers=k2_baslik)))
        print("K2 DEL  ->", ozet(istemci.delete(
            f"/sohbet/konusmalar/{konusma_k1}", headers=k2_baslik)))
        print("A JWT   ->", ozet(istemci.get(f"/sohbet/konusmalar/{konusma_k1}", headers=a_baslik)))
        print("A JWT (yeni mesaj) ->", ozet(istemci.post(
            "/sohbet",
            json={"bdm_id": bdm1, "konusma_id": konusma_k1, "mesaj": "A"},
            headers=a_baslik,
        )))
        print("K2 listesi:", json.dumps(
            istemci.get("/sohbet/konusmalar", headers=k2_baslik).json(), ensure_ascii=False))

        baslik("4.6) A'nin kendi konusmasi: PATCH baslik")
        yanit = istemci.patch(
            f"/sohbet/konusmalar/{konusma_a}", json={"baslik": "Yeni Baslik"}, headers=a_baslik
        )
        print("PATCH ->", ozet(yanit))
        print("GET   ->", ozet(istemci.get(f"/sohbet/konusmalar/{konusma_a}", headers=a_baslik)))
        baglanti = sqlite3.connect(DB)
        print("DB baslik:", baglanti.execute(
            "SELECT baslik FROM konusma WHERE id=?", (konusma_a,)).fetchall())

        baslik("4.7) A'nin konusmasini sil (mesajlar da siliniyor mu?)")
        baglanti = sqlite3.connect(DB)
        once = baglanti.execute(
            "SELECT count(*) FROM mesaj WHERE konusma_id=?", (konusma_a,)).fetchone()[0]
        yanit = istemci.delete(f"/sohbet/konusmalar/{konusma_a}", headers=a_baslik)
        print("DELETE ->", yanit.status_code, repr(yanit.text))
        baglanti = sqlite3.connect(DB)
        sonra = baglanti.execute(
            "SELECT count(*) FROM mesaj WHERE konusma_id=?", (konusma_a,)).fetchone()[0]
        print(f"mesaj sayisi: {once} -> {sonra}")
        print("konusma satiri:", baglanti.execute(
            "SELECT count(*) FROM konusma WHERE id=?", (konusma_a,)).fetchone()[0])
        print("GET (silindikten sonra) ->", ozet(
            istemci.get(f"/sohbet/konusmalar/{konusma_a}", headers=a_baslik)))

    baslik("4.8) Oksuz mesaj var mi? (bagimsiz SQL)")
    baglanti = sqlite3.connect(DB)
    print("oksuz mesaj:", baglanti.execute(
        "SELECT count(*) FROM mesaj m LEFT JOIN konusma k ON k.id = m.konusma_id"
        " WHERE k.id IS NULL").fetchone()[0])
    print("kullanim_kaydi'nda silinmis konusmaya bagli kayit:", baglanti.execute(
        "SELECT count(*) FROM kullanim_kaydi kk LEFT JOIN konusma k ON k.id = kk.konusma_id"
        " WHERE kk.konusma_id IS NOT NULL AND k.id IS NULL").fetchone()[0])
    print("konusmalar:", baglanti.execute(
        "SELECT id, kullanici_id, api_anahtari_id, baslik FROM konusma ORDER BY id").fetchall())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
