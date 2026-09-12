"""11) Ek curutme denemeleri: jeton turu karisimi, cikis sahipligi, kayit kapali,
rol enjeksiyonu, e-posta normalizasyonu, pasif kullanici akislari."""

from __future__ import annotations

import sys

sys.path.insert(0, "E:/kutyai-app/kaynak/testler/betikler")
from gkimlik_ortak import *  # noqa: E402

c = istemci()
eposta, dogrulama_jetonu, _, _ = kayit_ve_dogrula(c, yeni_eposta("goz-karisik"))
_, b = giris(c, eposta)
erisim, yenileme = b["erisim_jetonu"], b["yenileme_jetonu"]

# A) Jeton turu karisimi
rs = c.post("/kimlik/sifre-sifirlama-iste", json={"eposta": eposta})
sifirlama = jeton_baglantidan(govde(rs)["gelistirme_baglantisi"])
yaz("A1 sifirlama jetonu /kimlik/dogrula'ya verilirse", {
    "durum": (r1 := c.post("/kimlik/dogrula", json={"jeton": sifirlama})).status_code,
    "govde": govde(r1)})
yaz("A2 dogrulama jetonu /kimlik/sifre-sifirla'ya verilirse", {
    "durum": (r2 := c.post("/kimlik/sifre-sifirla", json={
        "jeton": dogrulama_jetonu, "yeni_parola": "BaskaParola222!"})).status_code,
    "govde": govde(r2)})

# B) Cikis sahipligi: B kullanicisi A'nin yenileme jetonunu iptal edebilir mi?
eposta_b, _, _, _ = kayit_ve_dogrula(c, yeni_eposta("goz-sahip"))
_, bb = giris(c, eposta_b)
r3 = c.post("/kimlik/cikis", json={"yenileme_jetonu": yenileme},
            headers=yetki(bb["erisim_jetonu"]))
yaz("B1 B, A'nin jetonuyla /kimlik/cikis", {"durum": r3.status_code, "govde": govde(r3)})
r4 = c.post("/kimlik/yenile", json={"yenileme_jetonu": yenileme})
yaz("B2 A'nin jetonu hala gecerli mi", {"durum": r4.status_code, "govde": govde(r4)})
r5 = c.post("/kimlik/cikis", json={"yenileme_jetonu": yenileme}, headers=yetki(erisim))
yaz("B3 A kendi jetonuyla cikis", {"durum": r5.status_code, "govde": govde(r5)})
r6 = c.post("/kimlik/yenile", json={"yenileme_jetonu": yenileme})
yaz("B4 cikis sonrasi A'nin jetonu", {"durum": r6.status_code, "govde": govde(r6)})

# C) Suresi dolmus refresh jetonu
eposta_c, _, _, _ = kayit_ve_dogrula(c, yeni_eposta("goz-suresi"))
_, bc = giris(c, eposta_c)
import hashlib  # noqa: E402

sql_yaz("update oturum set son_kullanma='2020-01-01 00:00:00.000000' where jeton_hash=?",
        (hashlib.sha256(bc["yenileme_jetonu"].encode()).hexdigest(),))
r7 = c.post("/kimlik/yenile", json={"yenileme_jetonu": bc["yenileme_jetonu"]})
yaz("C1 suresi dolmus refresh jetonu", {"durum": r7.status_code, "govde": govde(r7)})
r8 = c.get("/kimlik/ben", headers=yetki(bc["erisim_jetonu"]))
yaz("C2 suresi dolmus oturumun ERISIM jetonu (JWT exp bagimsiz)", {
    "durum": r8.status_code, "govde": govde(r8)})

# D) kayit_acik=false
sql_yaz("update ayar set deger=? where anahtar='kayit_acik'", ("false",))
r9 = c.post("/kimlik/kayit", json={"eposta": yeni_eposta("goz-kapali"),
                                   "ad_soyad": "K", "parola": PAROLA})
yaz("D1 kayit_acik=false iken /kimlik/kayit", {"durum": r9.status_code, "govde": govde(r9)})
sql_yaz("update ayar set deger=? where anahtar='kayit_acik'", ("true",))

# E) Rol enjeksiyonu: /kimlik/kayit govdesine rol eklenirse
eposta_e = yeni_eposta("goz-enjeksiyon")
re_ = c.post("/kimlik/kayit", json={"eposta": eposta_e, "ad_soyad": "E", "parola": PAROLA,
                                    "rol": "yonetici", "durum": "aktif",
                                    "eposta_dogrulandi": True})
yaz("E1 /kimlik/kayit ile rol/durum enjeksiyonu", {"durum": re_.status_code, "govde": govde(re_)})
yaz("E2 DB satiri", sql("select rol, durum, eposta_dogrulandi from kullanici where eposta=?",
                        (eposta_e,)))

# F) E-posta normalizasyonu girişte
eposta_f, _, _, _ = kayit_ve_dogrula(c, yeni_eposta("Goz-Buyuk"))
rf1, bf1 = giris(c, eposta_f.upper())
yaz("F1 BUYUK harfli e-posta ile giris", {"durum": rf1.status_code,
                                         "govde": govde(rf1) if rf1.status_code != 200 else "200"})
rf2, bf2 = giris(c, f"  {eposta_f}  ")
yaz("F2 bosluklu e-posta ile giris", {"durum": rf2.status_code,
                                      "govde": govde(rf2) if rf2.status_code != 200 else "200"})

# G) Pasif kullaniciya sifirlama istegi
eposta_g, _, _, _ = kayit_ve_dogrula(c, yeni_eposta("goz-pasif-sifirla"))
sql_yaz("update kullanici set durum='pasif' where eposta=?", (eposta_g,))
rg1 = c.post("/kimlik/sifre-sifirlama-iste", json={"eposta": eposta_g})
yaz("G1 pasif kullaniciya sifirlama istegi", {"durum": rg1.status_code, "govde": govde(rg1)})
rg2, bg2 = giris(c, eposta_g)
yaz("G2 pasif kullanici girisi", {"durum": rg2.status_code, "govde": bg2})

# H) PATCH durum=pasif hedefin oturumlarini iptal ediyor mu?
eposta_h, _, _, _ = kayit_ve_dogrula(c, yeni_eposta("goz-hedef-oturum"))
_, bh = giris(c, eposta_h)
hedef_id = bh["kullanici"]["id"]
eposta_y, _, _, _ = kayit_ve_dogrula(c, yeni_eposta("goz-yon-h"))
sql_yaz("update kullanici set rol='yonetici' where eposta=?", (eposta_y,))
_, by = giris(c, eposta_y, panel=True)
rh = c.patch(f"/kullanicilar/{hedef_id}", headers=yetki(by["erisim_jetonu"]),
             json={"durum": "pasif"})
yaz("H1 hedefi pasiflestir", {"durum": rh.status_code})
rh2 = c.post("/kimlik/yenile", json={"yenileme_jetonu": bh["yenileme_jetonu"]})
yaz("H2 pasiflestirilen hedefin refresh jetonu", {"durum": rh2.status_code, "govde": govde(rh2)})
rh3 = c.get("/kimlik/ben", headers=yetki(bh["erisim_jetonu"]))
yaz("H3 pasiflestirilen hedefin erisim jetonu", {"durum": rh3.status_code, "govde": govde(rh3)})

# I) /kimlik/cikis kimliksiz
ri = c.post("/kimlik/cikis", json={})
yaz("I1 anonim /kimlik/cikis", {"durum": ri.status_code, "govde": govde(ri)})

# J) dogrulama jetonu olmayan (dogrulanmamis) kullanici sohbete girebilir mi?
#    (erisim jetonu uretilemedigi icin API uzerinden test edilemez; atlanir)
