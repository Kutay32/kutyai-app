"""Curburtme 6 + 7: /saglayicilar sozlesmesi ve yetki matrisi."""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _ortak import istemci, jetonlari_oku, yaz  # noqa: E402

k = jetonlari_oku()
yonetici = istemci(k["admin"])
operator = istemci(k["operator"])
son = istemci(k["son_kullanici"])
anonim = istemci()

# --- /saglayicilar ---------------------------------------------------------
sag = anonim.get("/saglayicilar")
yaz("GET /saglayicilar (kimliksiz)", sag)
veri = sag.json()
print(f"--- kayit sayisi: {len(veri)}")
beklenen = [
    "ad",
    "gorunen_ad",
    "yerel",
    "gpu_gerekir",
    "akis_destegi",
    "api_anahtari_gerekir",
    "varsayilan_temel_url",
    "varsayilan_port",
    "konteyner_image",
    "aciklama",
]
for kayit in veri:
    print(f"{kayit['ad']}: alanlar birebir mi = {list(kayit.keys()) == beklenen} -> {list(kayit.keys())}")
print()

# --- yetki matrisi ---------------------------------------------------------
yaz("GET /bdm (kimliksiz)", anonim.get("/bdm"))
yaz("GET /bdm (son_kullanici)", son.get("/bdm"))
yaz("GET /bdm (operator)", operator.get("/bdm"))
yaz("GET /bdm (yonetici)", yonetici.get("/bdm"))

yaz("POST /bdm (kimliksiz)", anonim.post("/bdm", json={}))
yaz("POST /bdm (son_kullanici)", son.post("/bdm", json={}))
yaz(
    "POST /bdm (operator, gecerli govde)",
    operator.post(
        "/bdm",
        json={
            "gorunen_ad": "Operator Modeli",
            "saglayici": "openai",
            "temel_url": "https://api.openai.com/v1",
            "upstream_model": "gpt-4o-mini",
            "yerel_mi": False,
        },
    ),
)
yaz("PATCH /bdm/1 (operator)", operator.patch("/bdm/1", json={"aciklama": "operator denemesi"}))
yaz("POST /bdm/1/kopyala (operator)", operator.post("/bdm/1/kopyala", json={"yeni_ad": "Operator Kopya"}))
yaz("DELETE /bdm/5 (operator)", operator.delete("/bdm/5"))
yaz("POST /bdm/1/kopyala (son_kullanici)", son.post("/bdm/1/kopyala", json={"yeni_ad": "Son Kopya"}))
yaz("DELETE /bdm/5 (son_kullanici)", son.delete("/bdm/5"))
yaz("DELETE /bdm/5 (kimliksiz)", anonim.delete("/bdm/5"))
yaz("GET /modeller (kimliksiz)", anonim.get("/modeller"))
