"""Curburtme 1 + 2: GET /modeller durum suzgeci ve izinli_modeller suzgeci."""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _ortak import istemci, jetonlari_oku, sql, yaz  # noqa: E402

k = jetonlari_oku()
print("--- bdm tablosu (id, slug, durum)")
print(json.dumps(sql("SELECT id, slug, durum FROM bdm ORDER BY id"), ensure_ascii=False, indent=2))
print()

for etiket, jeton in (
    ("admin JWT", k["admin"]),
    ("operator JWT", k["operator"]),
    ("son_kullanici JWT", k["son_kullanici"]),
    ("api anahtari izinli_modeller=[]", k["anahtar_bos"]),
    ("api anahtari izinli_modeller=['musteri-asistani-cgiosu']", k["anahtar_tek_slug"]),
    ("api anahtari izinli_modeller=['6']", k["anahtar_tek_id"]),
):
    yaz(f"GET /modeller ({etiket})", istemci(jeton).get("/modeller"))

yaz("GET /modeller (kimliksiz)", istemci().get("/modeller"))
