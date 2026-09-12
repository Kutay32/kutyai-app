"""Ozet: slug uretimi ve cakisma (ham, kompakt cikti) + kapsam disi 401 kodu kontrolu."""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _ortak import ADMIN_EPOSTA, istemci, jetonlari_oku  # noqa: E402

k = jetonlari_oku()
a = istemci(k["admin"])

denemeler = [
    ("slug=gozlem-cakisma (1. kez)", {"gorunen_ad": "Slug Catismasi", "slug": "gozlem-cakisma-uc"}),
    ("slug=gozlem-cakisma (2. kez)", {"gorunen_ad": "Slug Catismasi", "slug": "gozlem-cakisma-uc"}),
    ("Turkce ad (slug yok): Şirket Dışı Çözüm Aracı", {"gorunen_ad": "Şirket Dışı Çözüm Aracı"}),
    ("Turkce ad (slug yok): ĞÜŞİÖÇ ıİğüşöç", {"gorunen_ad": "ĞÜŞİÖÇ ıİğüşöç Deneme"}),
    ("ayni ad 2. kez (slug yok)", {"gorunen_ad": "Şirket Dışı Çözüm Aracı"}),
]
for etiket, ek in denemeler:
    govde = {
        "saglayici": "openai",
        "temel_url": "https://api.openai.com/v1",
        "upstream_model": "gpt-4o-mini",
        "yerel_mi": False,
        **ek,
    }
    yanit = a.post("/bdm", json=govde)
    veri = yanit.json()
    ozet = veri.get("slug") or veri["hata"]["kod"]
    print(f"POST /bdm [{etiket}] -> HTTP {yanit.status_code} slug/kod={ozet!r}")

print()
yanit = istemci().post("/kimlik/panel-giris", json={"eposta": ADMIN_EPOSTA, "parola": "yanlis-parola"})
print("POST /kimlik/panel-giris (yanlis parola) -> HTTP", yanit.status_code)
print(json.dumps(yanit.json(), ensure_ascii=False))
