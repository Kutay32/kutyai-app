"""Gozlem ek: `sistem_istemi` maskelemesi, akis ortasinda kopan upstream, kisa baslik.

Kullanim:
    ./.venv/Scripts/python.exe kaynak/testler/betikler/gozlem_sohbet_ek.py
"""

from __future__ import annotations

import json
import pathlib
import sqlite3

import httpx

DURUM = pathlib.Path("E:/kutyai-app/kaynak/testler/gecici/sohbet-gozlem-durum.json")
KAYIT = pathlib.Path("E:/kutyai-app/kaynak/testler/gecici/sahte_upstream_istekler.jsonl")
DB = pathlib.Path("E:/kutyai-app/kaynak/testler/gecici/sohbet-gozlem.db")

SISTEM = "Kullanicinin e-postasi veli@ornek.com, telefonu 0532 999 88 77"


def baslik(metin: str) -> None:
    print(f"\n=== {metin}")


def sse(istemci: httpx.Client, yol: str, govde: dict, basliklar: dict) -> str:
    metin = ""
    ad = None
    with istemci.stream("POST", yol, json=govde, headers=basliklar) as yanit:
        print("durum:", yanit.status_code, "| content-type:", yanit.headers.get("content-type"))
        for satir in yanit.iter_lines():
            print("  ", satir)
            metin += satir + "\n"
            if satir.startswith("event: "):
                ad = satir[len("event: ") :]
    return metin


def main() -> int:
    durum = json.loads(DURUM.read_text(encoding="utf-8"))
    B = durum["kullanicilar"]["B"]
    b_baslik = {"Authorization": f"Bearer {B['jeton']}"}
    y_baslik = {"Authorization": f"Bearer {durum['yonetici_jetonu']}"} if False else {
        "Authorization": f"Bearer {durum['yonetici_jeton']}"
    }
    bdm1 = durum["bdm_id"]

    with httpx.Client(base_url=durum["taban"], timeout=60.0) as istemci:
        baslik("6.1) Istekteki sistem_istemi maskelenmeden mi gidiyor?")
        yanit = istemci.post(
            "/sohbet",
            json={"bdm_id": bdm1, "mesaj": "Sistem istemi denemesi", "sistem_istemi": SISTEM},
            headers=b_baslik,
        )
        print(yanit.status_code, json.dumps(yanit.json(), ensure_ascii=False))
        konusma_id = yanit.json()["konusma_id"]

        baslik("6.2) Upstream'e giden son govde")
        son = None
        for satir in KAYIT.read_text(encoding="utf-8").strip().splitlines():
            kayit = json.loads(satir)
            if kayit.get("olay") == "istek" and not kayit.get("akis"):
                son = kayit
        print(json.dumps(son["govde"], ensure_ascii=False, indent=2))

        baslik("6.3) DB'de konusma.sistem_istemi (ham)")
        with sqlite3.connect(DB) as baglanti:
            print(baglanti.execute(
                "SELECT id, sistem_istemi FROM konusma WHERE id=?", (konusma_id,)).fetchall())

        baslik("6.4) Kisa mesajda baslik (kirpilmadan)")
        yanit = istemci.post(
            "/sohbet", json={"bdm_id": bdm1, "mesaj": "Kisa"}, headers=b_baslik
        )
        print(yanit.status_code, yanit.json()["konusma_id"])
        kisa_id = yanit.json()["konusma_id"]

        baslik("6.5) Akis ortasinda kopan upstream (model=kir)")
        yanit = istemci.post(
            "/bdm",
            json={
                "gorunen_ad": "Kiran Model",
                "slug": "kiran-model",
                "saglayici": "ozel",
                "temel_url": "http://127.0.0.1:8191/v1",
                "upstream_model": "kir",
                "yerel_mi": True,
            },
            headers=y_baslik,
        )
        kir_id = yanit.json()["id"]
        with sqlite3.connect(DB) as baglanti:
            baglanti.execute("UPDATE bdm SET durum='hazir' WHERE id=?", (kir_id,))
            baglanti.commit()
        print("POST /bdm", yanit.status_code, kir_id)
        sse(istemci, "/sohbet/akis", {"bdm_id": kir_id, "mesaj": "Kopacak"}, b_baslik)

        baslik("6.6) Kisa baslik + kirilan akis sonrasi SQL")
        with sqlite3.connect(DB) as baglanti:
            print("kisa konusma basligi:", baglanti.execute(
                "SELECT id, baslik, length(baslik) FROM konusma WHERE id=?", (kisa_id,)).fetchall())
            print("kirilan akis konusmasi:", baglanti.execute(
                "SELECT id, baslik FROM konusma WHERE bdm_id=?", (kir_id,)).fetchall())
            print("kirilan akis mesajlari:", baglanti.execute(
                "SELECT m.id, m.rol, m.icerik FROM mesaj m JOIN konusma k ON k.id=m.konusma_id"
                " WHERE k.bdm_id=?", (kir_id,)).fetchall())
            print("kirilan akis kullanim kaydi:", baglanti.execute(
                "SELECT id, durum, girdi_token, cikti_token, gecikme_ms FROM kullanim_kaydi"
                " WHERE bdm_id=?", (kir_id,)).fetchall())

        baslik("6.7) Sahte upstream kirilma kaydi")
        for satir in KAYIT.read_text(encoding="utf-8").strip().splitlines():
            kayit = json.loads(satir)
            if kayit.get("olay") in ("akis_ortada_kirildi",):
                print(json.dumps(kayit, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
