"""Curburtme 3: upstream API anahtari ham halde siziyor mu (PATCH dahil)?"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _ortak import UPSTREAM_ANAHTAR, istemci, jetonlari_oku, yaz  # noqa: E402

k = jetonlari_oku()
a = istemci(k["admin"])
KISITLI = istemci(k["anahtar_tek_slug"])

ham_yanitlar: list[tuple[str, str]] = []


def kaydet(etiket: str, yanit) -> None:
    yaz(etiket, yanit)
    ham_yanitlar.append((etiket, yanit.text))


kaydet("GET /bdm", a.get("/bdm"))
kaydet("GET /modeller", a.get("/modeller"))
kaydet("GET /saglayicilar", istemci().get("/saglayicilar"))

yeni = a.post(
    "/bdm",
    json={
        "gorunen_ad": "Sizinti Testi",
        "saglayici": "openai",
        "temel_url": "https://api.openai.com/v1",
        "upstream_model": "gpt-4o-mini",
        "api_anahtari": UPSTREAM_ANAHTAR,
        "yerel_mi": False,
    },
)
kaydet("POST /bdm (api_anahtari=sk-cokgizli-...)", yeni)
yeni_id = yeni.json()["id"]

kaydet(
    "PATCH /bdm/{id} (yalniz aciklama)",
    a.patch(f"/bdm/{yeni_id}", json={"aciklama": "maskeli kalmali"}),
)
kaydet(
    "PATCH /bdm/{id} (api_anahtari yeniden yazildi)",
    a.patch(f"/bdm/{yeni_id}", json={"api_anahtari": UPSTREAM_ANAHTAR}),
)
kaydet(
    "PATCH /bdm/{id} (api_anahtari temizlendi)",
    a.patch(f"/bdm/{yeni_id}", json={"api_anahtari": ""}),
)
kaydet(
    "PATCH /bdm/{id} (api_anahtari tekrar dolduruldu)",
    a.patch(f"/bdm/{yeni_id}", json={"api_anahtari": UPSTREAM_ANAHTAR}),
)
kaydet("POST /bdm/{id}/kopyala", a.post(f"/bdm/{yeni_id}/kopyala", json={"yeni_ad": "Sizinti Kopya"}))

kaydet(
    "POST /sohbet (502 govdesi)",
    KISITLI.post("/sohbet", json={"bdm_id": k["bdm"]["musteri"], "mesaj": "test"}),
)

print("=== HAM YANIT TARAMASI ===")
desenler = {
    "HAM_ANAHTAR": UPSTREAM_ANAHTAR,
    "sk-": "sk-",
    "cokgizli": "cokgizli",
    "Bearer": "Bearer",
    "kuty_": "kuty_",
}
for etiket, govde in ham_yanitlar:
    bulunan = [ad for ad, desen in desenler.items() if desen in govde]
    print(f"{etiket}: {bulunan or 'temiz'}")

print()
print("--- bdm tablosu (id, slug, api_anahtari_sifreli)")
import sqlite3  # noqa: E402

from _ortak import DB  # noqa: E402

baglanti = sqlite3.connect(DB)
for satir in baglanti.execute("SELECT id, slug, api_anahtari_sifreli FROM bdm ORDER BY id"):
    print(satir)
baglanti.close()
