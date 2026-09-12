"""4) Sifre sifirlama: eski refresh jetonlari ve eski parola gecersiz mi?"""

from __future__ import annotations

import sys

sys.path.insert(0, "E:/kutyai-app/kaynak/testler/betikler")
from gkimlik_ortak import *  # noqa: E402

YENI = "YeniParola456!"
c = istemci()
eposta, _, _, _ = kayit_ve_dogrula(c)
_, b0 = giris(c, eposta)
eski_yenileme = b0["yenileme_jetonu"]
eski_erisim = b0["erisim_jetonu"]
print(f"### hazirlik: {eposta} girisi; erisim={kisalt(eski_erisim)} yenileme={kisalt(eski_yenileme)}")

r1 = c.post("/kimlik/sifre-sifirlama-iste", json={"eposta": eposta})
b1 = govde(r1)
yaz("sifre-sifirlama-iste", {"durum": r1.status_code, "govde": b1})
sifirlama_jetonu = jeton_baglantidan(b1.get("gelistirme_baglantisi", ""))

r2 = c.post("/kimlik/sifre-sifirla", json={"jeton": sifirlama_jetonu, "yeni_parola": YENI})
yaz("sifre-sifirla", {"durum": r2.status_code, "govde": govde(r2)})

r3 = c.post("/kimlik/yenile", json={"yenileme_jetonu": eski_yenileme})
yaz("sifirlama SONRASI eski refresh jetonu ile /yenile", {"durum": r3.status_code, "govde": govde(r3)})

r4, b4 = giris(c, eposta, PAROLA)
yaz("eski parola ile /giris", {"durum": r4.status_code, "govde": b4})

r5, b5 = giris(c, eposta, YENI)
yaz("yeni parola ile /giris", {"durum": r5.status_code, "alanlar": sorted(b5.keys())})

r6 = c.post("/kimlik/sifre-sifirla", json={"jeton": sifirlama_jetonu, "yeni_parola": "BaskaParola789!"})
yaz("AYNI sifirlama jetonu ile 2. sifirla", {"durum": r6.status_code, "govde": govde(r6)})

r7 = c.get("/kimlik/ben", headers=yetki(eski_erisim))
yaz("sifirlama oncesi ERISIM jetonu ile /ben", {"durum": r7.status_code, "govde": govde(r7)})

# yeni oturum acildiktan sonra eski parolayla tekrar sifirlama iste -> jeton uretilir mi
r8 = c.post("/kimlik/sifre-sifirlama-iste", json={"eposta": eposta})
b8 = govde(r8)
yaz("ikinci sifirlama istegi (yeni jeton eski jetonu gecersiz kilar mi testi)", {
    "durum": r8.status_code, "govde": b8})
yeni_sifirlama = jeton_baglantidan(b8.get("gelistirme_baglantisi", ""))
r9 = c.post("/kimlik/sifre-sifirla", json={"jeton": sifirlama_jetonu, "yeni_parola": "UcuncuParola000!"})
yaz("ilk sifirlama jetonu, ikinci istekten sonra", {"durum": r9.status_code, "govde": govde(r9)})
r10 = c.post("/kimlik/sifre-sifirla", json={"jeton": yeni_sifirlama, "yeni_parola": "DorduncuParola111!"})
yaz("ikinci sifirlama jetonu", {"durum": r10.status_code, "govde": govde(r10)})

yaz("oturum tablosu", sql(
    "select o.id, o.iptal from oturum o join kullanici k on k.id=o.kullanici_id where k.eposta=? order by o.id",
    (eposta,),
))
