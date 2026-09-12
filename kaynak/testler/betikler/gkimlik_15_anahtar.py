"""15) kuty_ API anahtari kimlik uclarinda nasil davraniyor? (spec §9)"""

from __future__ import annotations

import sys

sys.path.insert(0, "E:/kutyai-app/kaynak/testler/betikler")
from gkimlik_ortak import *  # noqa: E402

import hashlib  # noqa: E402
import secrets  # noqa: E402

c = istemci()
eposta, _, _, _ = kayit_ve_dogrula(c, yeni_eposta("goz-anahtar"))
_, b = giris(c, eposta)
kullanici_id = b["kullanici"]["id"]

tam = "kuty_" + "".join(secrets.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(32))
sql_yaz(
    "insert into api_anahtari (ad, onek, anahtar_hash, son_dort, kullanici_id, durum, "
    "izinli_modeller, olusturulma) values ('Gozlem', ?, ?, ?, ?, 'aktif', '[]', '2026-09-12 00:00:00.000000')",
    (tam[:12], hashlib.sha256(tam.encode()).hexdigest(), tam[-4:], kullanici_id),
)
print("### gecerli kuty_ anahtari olusturuldu:", tam[:14] + "..." + tam[-4:])

for etiket, yanit in (
    ("GET /kimlik/ben", c.get("/kimlik/ben", headers=yetki(tam))),
    ("GET /kullanicilar", c.get("/kullanicilar", headers=yetki(tam))),
):
    print(f"### {etiket} -> {yanit.status_code} {yanit.text[:200]}")

# Gecersiz kuty_ anahtari (sohbet ucu disinda da)
yanit = c.get("/kimlik/ben", headers=yetki("kuty_" + "z" * 32))
print(f"### gecersiz kuty_ -> {yanit.status_code} {yanit.text[:200]}")

# JWT yerine refresh jetonu erisim jetonu gibi kullanilirsa
yanit = c.get("/kimlik/ben", headers=yetki(b["yenileme_jetonu"]))
print(f"### refresh jetonu Bearer olarak -> {yanit.status_code} {yanit.text[:200]}")
