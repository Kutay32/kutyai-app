"""Sozlesme alan kumesi denetimi: Bdm ve BdmOzet (API.md §2, §8)."""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _ortak import istemci, jetonlari_oku  # noqa: E402

k = jetonlari_oku()
a = istemci(k["admin"])

BDM_ALANLARI = [
    "id",
    "slug",
    "gorunen_ad",
    "aciklama",
    "saglayici",
    "temel_url",
    "upstream_model",
    "api_anahtari_maskeli",
    "baglam_penceresi",
    "maks_cikti",
    "sicaklik_varsayilan",
    "sistem_istemi",
    "yetenekler",
    "durum",
    "yerel_mi",
    "konteyner",
    "olusturulma",
    "guncellenme",
]
BDM_OZET_ALANLARI = [
    "id",
    "slug",
    "gorunen_ad",
    "aciklama",
    "saglayici",
    "baglam_penceresi",
    "yetenekler",
    "durum",
]

bdmler = a.get("/bdm").json()
ozetler = istemci(k["anahtar_bos"]).get("/modeller").json()
print(f"GET /bdm kayit sayisi: {len(bdmler)}")
print(f"Bdm alan kumesi birebir: {all(list(b.keys()) == BDM_ALANLARI for b in bdmler)}")
print(f"ornek: {list(bdmler[0].keys())}")
print()
print(f"GET /modeller kayit sayisi: {len(ozetler)}")
print(f"BdmOzet alan kumesi birebir: {all(list(o.keys()) == BDM_OZET_ALANLARI for o in ozetler)}")
print(f"ornek: {list(ozetler[0].keys())}")
print()
print(f"durum kumesi (modeller): {sorted({o['durum'] for o in ozetler})}")
print(f"durum kumesi (bdm): {sorted({b['durum'] for b in bdmler})}")
