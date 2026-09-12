"""Gozlem ek: /kullanim/zaman-serisi, yetki denetimleri, dogrulama hatalari.

Kullanim:
    ./.venv/Scripts/python.exe kaynak/testler/betikler/gozlem_sohbet_kullanim.py
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


def main() -> int:
    durum = json.loads(DURUM.read_text(encoding="utf-8"))
    y_baslik = {"Authorization": f"Bearer {durum['yonetici_jeton']}"}
    a_baslik = {"Authorization": f"Bearer {durum['kullanicilar']['A']['jeton']}"}

    with httpx.Client(base_url=durum["taban"], timeout=60.0) as istemci:
        baslik("7.1) GET /kullanim/zaman-serisi?kirilim=bdm")
        yanit = istemci.get("/kullanim/zaman-serisi?gun=30&kirilim=bdm", headers=y_baslik)
        print(yanit.status_code, json.dumps(yanit.json(), ensure_ascii=False))

        baslik("7.2) GET /kullanim/zaman-serisi?kirilim=kullanici")
        yanit = istemci.get("/kullanim/zaman-serisi?gun=30&kirilim=kullanici", headers=y_baslik)
        print(yanit.status_code, json.dumps(yanit.json(), ensure_ascii=False))

        baslik("7.3) Gecersiz kirilim")
        yanit = istemci.get("/kullanim/zaman-serisi?kirilim=xyz", headers=y_baslik)
        print(yanit.status_code, yanit.text[:300])

        baslik("7.4) gun sinirlari")
        for gun in (0, 400):
            yanit = istemci.get(f"/kullanim/ozet?gun={gun}", headers=y_baslik)
            print(gun, yanit.status_code, yanit.text[:200])

        baslik("7.5) Yetkisiz erisim (jeton yok)")
        for yol, yontem, govde in (
            ("/sohbet", "post", {"bdm_id": durum["bdm_id"], "mesaj": "x"}),
            ("/sohbet/konusmalar", "get", None),
            ("/kullanim/ozet", "get", None),
        ):
            yanit = getattr(istemci, yontem)(yol, json=govde) if govde else getattr(
                istemci, yontem)(yol)
            print(yontem.upper(), yol, yanit.status_code, yanit.text[:200])

        baslik("7.6) Son kullanici personel ucuna erisirse")
        yanit = istemci.get("/kullanim/ozet", headers=a_baslik)
        print(yanit.status_code, yanit.text[:200])

        baslik("7.7) Bos mesaj / eksik bdm")
        yanit = istemci.post("/sohbet", json={"bdm_id": durum["bdm_id"], "mesaj": ""},
                             headers=a_baslik)
        print("bos mesaj:", yanit.status_code, yanit.text[:220])
        yanit = istemci.post("/sohbet", json={"mesaj": "merhaba"}, headers=a_baslik)
        print("bdm yok  :", yanit.status_code, yanit.text[:220])
        yanit = istemci.post("/sohbet", json={"bdm_slug": "yok-boyle", "mesaj": "merhaba"},
                             headers=a_baslik)
        print("bilinmeyen slug:", yanit.status_code, yanit.text[:220])

    baslik("7.8) SQL ile zaman serisi karsilastirmasi (bdm kirilimi)")
    baglanti = sqlite3.connect(DB)
    print("SQL:", baglanti.execute(
        "SELECT b.gorunen_ad, count(*), coalesce(sum(k.girdi_token),0)+"
        "coalesce(sum(k.cikti_token),0) FROM kullanim_kaydi k JOIN bdm b ON b.id=k.bdm_id"
        " GROUP BY b.gorunen_ad ORDER BY 3 DESC").fetchall())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
