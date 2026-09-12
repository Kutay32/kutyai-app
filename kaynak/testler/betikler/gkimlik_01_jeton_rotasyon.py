"""1) Refresh jetonu rotasyonu: tek kullanimlik mi?"""

from __future__ import annotations

import sys

sys.path.insert(0, "E:/kutyai-app/kaynak/testler/betikler")
from gkimlik_ortak import *  # noqa: E402

c = istemci()
eposta, _, _, _ = kayit_ve_dogrula(c)
r0, b0 = giris(c, eposta)
yaz("giris", {"durum": r0.status_code, "alanlar": sorted(b0.keys()), "jetonlar": {
    "erisim": kisalt(b0.get("erisim_jetonu")), "yenileme": kisalt(b0.get("yenileme_jetonu"))}})

eski_yenileme = b0["yenileme_jetonu"]
eski_erisim = b0["erisim_jetonu"]

r1 = c.post("/kimlik/yenile", json={"yenileme_jetonu": eski_yenileme})
b1 = govde(r1)
yaz("1. yenile (eski jeton)", {
    "durum": r1.status_code,
    "alanlar": sorted(b1.keys()),
    "yenileme_degisti": b1.get("yenileme_jetonu") != eski_yenileme,
})

r2 = c.post("/kimlik/yenile", json={"yenileme_jetonu": eski_yenileme})
yaz("2. yenile (AYNI eski jeton ile tekrar)", {"durum": r2.status_code, "govde": govde(r2)})

r3 = c.post("/kimlik/yenile", json={"yenileme_jetonu": b1.get("yenileme_jetonu")})
yaz("3. yenile (rotasyondan gelen yeni jeton)", {"durum": r3.status_code, "govde": govde(r3)})

r4 = c.get("/kimlik/ben", headers=yetki(eski_erisim))
yaz("rotasyon oncesi ERISIM jetonu hala gecerli mi", {"durum": r4.status_code, "govde": govde(r4)})

# Veritabani tarafi: kullanicinin tum oturum kayitlari
kullanici_id = b0["kullanici"]["id"]
yaz("oturum tablosu (dogrudan SQLite)", sql(
    "select id, kullanici_id, iptal, son_kullanma, olusturulma from oturum where kullanici_id=? order by id",
    (kullanici_id,),
))
