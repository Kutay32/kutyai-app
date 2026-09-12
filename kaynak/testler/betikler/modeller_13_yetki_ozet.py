"""Ozet: yetki matrisi — her istek icin HTTP durum kodu (ham cikti)."""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _ortak import istemci, jetonlari_oku  # noqa: E402

k = jetonlari_oku()
kimlikler = {
    "anonim": None,
    "son_kullanici": k["son_kullanici"],
    "operator": k["operator"],
    "yonetici": k["admin"],
}

istekler = [
    ("GET", "/bdm", None),
    ("GET", "/modeller", None),
    ("POST", "/bdm", {"gorunen_ad": "Yetki Denemesi", "saglayici": "openai"}),
    ("DELETE", "/bdm/4", None),
    ("POST", "/bdm/1/kopyala", {"yeni_ad": "Yetki Kopya"}),
]

for etiket, jeton in kimlikler.items():
    for yontem, yol, govde in istekler:
        istemci_ = istemci(jeton)
        yanit = istemci_.request(yontem, yol, json=govde) if govde else istemci_.request(yontem, yol)
        try:
            kod = yanit.json()["hata"]["kod"]
        except Exception:
            kod = "basarili"
        print(f"{yontem:6} {yol:18} [{etiket:13}] -> HTTP {yanit.status_code} {kod}")
