"""Ek kontroller: arama parametresi, 404/400 kenar durumlari, iptal edilmis anahtar."""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _ortak import istemci, jetonlari_oku, yaz  # noqa: E402

k = jetonlari_oku()
a = istemci(k["admin"])

yanit = a.get("/bdm", params={"arama": "Slug Catismasi"})
yaz("GET /bdm?arama=Slug Catismasi (API.md §8'de boyle bir parametre yok)", yanit)
print(f"--- arama sonucu kayit sayisi: {len(yanit.json())}")
print()

yaz("DELETE /bdm/9999", a.delete("/bdm/9999"))
yaz("PATCH /bdm/9999", a.patch("/bdm/9999", json={"aciklama": "yok"}))
yaz("POST /bdm/9999/kopyala", a.post("/bdm/9999/kopyala", json={"yeni_ad": "Yok"}))
yaz(
    "POST /bdm bilinmeyen saglayici",
    a.post("/bdm", json={"gorunen_ad": "X Y", "saglayici": "hicbir-saglayici"}),
)
yaz("POST /bdm cok kisa gorunen_ad", a.post("/bdm", json={"gorunen_ad": "A", "saglayici": "openai"}))

# Iptal edilmis anahtar
uretim = a.post("/api-anahtarlari", json={"ad": "Gozlem Iptal", "izinli_modeller": []})
iptal = a.post(f"/api-anahtarlari/{uretim.json()['id']}/iptal")
yaz("POST /api-anahtarlari/{id}/iptal", iptal)
yaz("GET /modeller (iptal edilmis anahtar)", istemci(uretim.json()["tam_anahtar"]).get("/modeller"))
yaz("GET /modeller (gecersiz anahtar)", istemci("kuty_" + "x" * 32).get("/modeller"))

print("--- islem_kaydi (eylem, hedef_id) — bdm islemleri")
import sqlite3  # noqa: E402

from _ortak import DB  # noqa: E402

baglanti = sqlite3.connect(DB)
print(
    json.dumps(
        baglanti.execute(
            "SELECT eylem, hedef_id FROM islem_kaydi WHERE hedef_tur='bdm' ORDER BY id"
        ).fetchall(),
        ensure_ascii=False,
        indent=2,
    )
)
baglanti.close()
