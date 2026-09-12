"""6) Rol matrisi: giris kapilari ve /kullanicilar yetkisi."""

from __future__ import annotations

import sys

sys.path.insert(0, "E:/kutyai-app/kaynak/testler/betikler")
from gkimlik_ortak import *  # noqa: E402

c = istemci()

# son_kullanici
son_eposta, _, _, _ = kayit_ve_dogrula(c, yeni_eposta("goz-son"))
r1, b1 = giris(c, son_eposta)
yaz("son_kullanici /kimlik/giris", {"durum": r1.status_code, "alanlar": sorted(b1.keys())})
r2, b2 = giris(c, son_eposta, panel=True)
yaz("son_kullanici /kimlik/panel-giris", {"durum": r2.status_code, "govde": b2})
son_jeton = b1.get("erisim_jetonu", "")

# personel (operator) - dogrudan DB ile rol atanir
per_eposta, _, _, _ = kayit_ve_dogrula(c, yeni_eposta("goz-per"))
sql_yaz("update kullanici set rol='operator' where eposta=?", (per_eposta,))
r3, b3 = giris(c, per_eposta, panel=True)
yaz("operator /kimlik/panel-giris", {"durum": r3.status_code, "alanlar": sorted(b3.keys())})
r4, b4 = giris(c, per_eposta)
yaz("operator /kimlik/giris", {"durum": r4.status_code, "govde": b4})

# izleyici
iz_eposta, _, _, _ = kayit_ve_dogrula(c, yeni_eposta("goz-iz"))
sql_yaz("update kullanici set rol='izleyici' where eposta=?", (iz_eposta,))
r5, b5 = giris(c, iz_eposta, panel=True)
yaz("izleyici /kimlik/panel-giris", {"durum": r5.status_code, "alanlar": sorted(b5.keys())})
iz_jeton = b5.get("erisim_jetonu", "")
r6 = c.get("/kullanicilar", headers=yetki(iz_jeton))
yaz("izleyici /kullanicilar (yonetici beklenir)", {"durum": r6.status_code, "govde": govde(r6)})

# yonetici
yo_eposta, _, _, _ = kayit_ve_dogrula(c, yeni_eposta("goz-yon"))
sql_yaz("update kullanici set rol='yonetici' where eposta=?", (yo_eposta,))
r7, b7 = giris(c, yo_eposta, panel=True)
yaz("yonetici /kimlik/panel-giris", {"durum": r7.status_code, "alanlar": sorted(b7.keys())})
yo_jeton = b7.get("erisim_jetonu", "")
r8 = c.get("/kullanicilar", headers=yetki(yo_jeton))
yb8 = govde(r8)
yaz("yonetici /kullanicilar", {"durum": r8.status_code, "alanlar": sorted(yb8.keys()),
                               "toplam": yb8.get("toplam"), "ilk_kayit_alanlari": sorted(
                                   (yb8.get("kayitlar") or [{}])[0].keys())})

# anonim
r9 = c.get("/kullanicilar")
yaz("anonim /kullanicilar", {"durum": r9.status_code, "govde": govde(r9)})
r10 = c.get("/kimlik/ben")
yaz("anonim /kimlik/ben", {"durum": r10.status_code, "govde": govde(r10)})
r11 = c.get("/kullanicilar", headers={"Authorization": "Bearer kuty_gecersiz"})
yaz("bozuk anahtar ile /kullanicilar", {"durum": r11.status_code, "govde": govde(r11)})

# son_kullanici ile /kullanicilar
r12 = c.get("/kullanicilar", headers=yetki(son_jeton))
yaz("son_kullanici /kullanicilar", {"durum": r12.status_code, "govde": govde(r12)})

# son_kullanici ile POST /kullanicilar
r13 = c.post("/kullanicilar", headers=yetki(son_jeton), json={
    "eposta": yeni_eposta("goz-x"), "ad_soyad": "X", "parola": PAROLA, "rol": "operator"})
yaz("son_kullanici POST /kullanicilar", {"durum": r13.status_code, "govde": govde(r13)})
