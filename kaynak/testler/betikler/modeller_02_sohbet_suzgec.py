"""Curburtme 2b: izinli_modeller suzgeci /sohbet uzerinden atlatilabiliyor mu?"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _ortak import istemci, jetonlari_oku, sql, yaz  # noqa: E402

k = jetonlari_oku()
kisitli = istemci(k["anahtar_tek_slug"])
serbest = istemci(k["anahtar_bos"])

mesaj = {"mesaj": "Merhaba", "konusma_id": None}

yaz(
    "POST /sohbet bdm_id=6 (izinli_modeller=['musteri-asistani-cgiosu'] anahtari)",
    kisitli.post("/sohbet", json={**mesaj, "bdm_id": k["bdm"]["calisan"]}),
)
yaz(
    "POST /sohbet bdm_slug=gozlem-calisan (izinli_modeller=['musteri-asistani-cgiosu'] anahtari)",
    kisitli.post("/sohbet", json={**mesaj, "bdm_slug": k["slug"]["calisan"]}),
)
yaz(
    "POST /sohbet bdm_id=3 taslak BDM (izinli_modeller=[] anahtari)",
    serbest.post("/sohbet", json={**mesaj, "bdm_id": k["bdm"]["taslak"]}),
)
yaz(
    "POST /sohbet bdm_id=6 (izinli_modeller=[] anahtari)",
    serbest.post("/sohbet", json={**mesaj, "bdm_id": k["bdm"]["calisan"]}),
)

print("--- konusma tablosu (id, bdm_id, baslik)")
print(json.dumps(sql("SELECT id, bdm_id, baslik FROM konusma ORDER BY id"), ensure_ascii=False, indent=2))
