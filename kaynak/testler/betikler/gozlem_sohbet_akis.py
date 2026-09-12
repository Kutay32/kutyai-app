"""Gozlem 1-3: akis olay sirasi, maskeleme, baslik uretimi.

Kullanim:
    ./.venv/Scripts/python.exe kaynak/testler/betikler/gozlem_sohbet_akis.py
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

MESAJ = (
    "Merhaba, bana ayse@acme.com adresinden ulasin; telefonum 0532 123 45 67 "
    "ve TCKN 12345678901. Bu mesaj 60 karakterden uzun olmali ki baslik kirpilsin."
)


def baslik(metin: str) -> None:
    print(f"\n=== {metin}")


def main() -> int:
    durum = json.loads(DURUM.read_text(encoding="utf-8"))
    A = durum["kullanicilar"]["A"]
    basliklar = {"Authorization": f"Bearer {A['jeton']}"}
    govde = {"bdm_id": durum["bdm_id"], "mesaj": MESAJ}

    with httpx.Client(base_url=durum["taban"], timeout=60.0) as istemci:
        baslik("POST /sohbet/akis — ham SSE akisi")
        olaylar: list[tuple[str, dict]] = []
        baslangic = time.perf_counter()
        with istemci.stream("POST", "/sohbet/akis", json=govde, headers=basliklar) as yanit:
            print("durum:", yanit.status_code)
            print("basliklar:", dict(yanit.headers))
            olay_adi = None
            for satir in yanit.iter_lines():
                print(f"{time.perf_counter() - baslangic:7.3f}s | {satir}")
                if satir.startswith("event: "):
                    olay_adi = satir[len("event: ") :]
                elif satir.startswith("data: ") and olay_adi:
                    olaylar.append((olay_adi, json.loads(satir[len("data: ") :])))
                    olay_adi = None

        baslik("Olay sirasi")
        print([ad for ad, _ in olaylar])

        baslik("Parcalarin birlestirilmesi")
        parcalar = "".join(veri["icerik"] for ad, veri in olaylar if ad == "parca")
        print("parca sayisi:", sum(1 for ad, _ in olaylar if ad == "parca"))
        print("birlesik :", parcalar)
        print("beklenen :", "YANIT: " + MESAJ.replace(
            "ayse@acme.com", "[MASKELENDI:eposta]"
        ).replace("0532 123 45 67", "[MASKELENDI:telefon]").replace(
            "12345678901", "[MASKELENDI:tckn]"
        ) + " | iletisim: ayse@acme.com | tel: 0532 123 45 67")

        konusma_id = olaylar[0][1]["konusma_id"]
        baslik("GET /sohbet/konusmalar/{id} — DB'ye yazilan icerik")
        detay = istemci.get(f"/sohbet/konusmalar/{konusma_id}", headers=basliklar)
        print(detay.status_code, json.dumps(detay.json(), ensure_ascii=False, indent=2))

        baslik("GET /sohbet/konusmalar — baslik listesi")
        print(json.dumps(istemci.get("/sohbet/konusmalar", headers=basliklar).json(),
                         ensure_ascii=False, indent=2))

    baslik("SQLite: mesaj satirlari (ham)")
    with sqlite3.connect(DB) as baglanti:
        for satir in baglanti.execute(
            "SELECT id, konusma_id, rol, icerik, token_sayisi FROM mesaj ORDER BY id"
        ):
            print(satir)
        print("baslik:", baglanti.execute(
            "SELECT id, baslik, length(baslik) FROM konusma").fetchall())

    baslik("Sahte upstream'e GIDEN son istek govdesi (ham JSONL satiri)")
    satirlar = KAYIT.read_text(encoding="utf-8").strip().splitlines()
    for satir in satirlar[-3:]:
        print(satir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
