"""Curburtme 2b (devam): /sohbet/akis de ayni suzgeci uyguluyor mu?"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _ortak import istemci, jetonlari_oku, yaz  # noqa: E402

k = jetonlari_oku()
kisitli = istemci(k["anahtar_tek_slug"])

yaz(
    "POST /sohbet/akis bdm_id=6 (izinli_modeller=['musteri-asistani-cgiosu'] anahtari)",
    kisitli.post(
        "/sohbet/akis",
        json={"bdm_id": k["bdm"]["calisan"], "mesaj": "akis testi"},
        headers={"Accept": "text/event-stream"},
    ),
)

# Konusma okuma: kisitli anahtarla, izinli olmayan modelin konusmasi (id=1 -> bdm 6)
yaz("GET /sohbet/konusmalar/1 (kisitli anahtar)", kisitli.get("/sohbet/konusmalar/1"))
yaz("GET /sohbet/konusmalar (kisitli anahtar)", kisitli.get("/sohbet/konusmalar"))
