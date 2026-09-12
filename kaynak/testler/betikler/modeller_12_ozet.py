"""Ozet: /modeller yanitlarinin (id, slug, durum) izdusumu — ham cikti."""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _ortak import istemci, jetonlari_oku  # noqa: E402

k = jetonlari_oku()
krediler = [
    ("admin JWT", k["admin"]),
    ("operator JWT", k["operator"]),
    ("son_kullanici JWT", k["son_kullanici"]),
    ("anahtar izinli_modeller=[]", k["anahtar_bos"]),
    ("anahtar izinli_modeller=['musteri-asistani-cgiosu']", k["anahtar_tek_slug"]),
    ("anahtar izinli_modeller=['6']", k["anahtar_tek_id"]),
    ("kimliksiz", None),
]
for etiket, jeton in krediler:
    yanit = istemci(jeton).get("/modeller")
    govde = yanit.json()
    if isinstance(govde, list):
        ozet = [(m["id"], m["slug"], m["durum"]) for m in govde]
    else:
        ozet = govde
    print(f"GET /modeller [{etiket}] -> HTTP {yanit.status_code} {ozet}")

print()
yanit = istemci(k["admin"]).get("/bdm")
print(
    "GET /bdm [admin] -> HTTP "
    f"{yanit.status_code} {[(b['id'], b['slug'], b['durum']) for b in yanit.json()]}"
)
