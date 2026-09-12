"""8) PATCH /kullanicilar/{id}: kendini pasif yapma + rol degisikligi denetim izi."""

from __future__ import annotations

import sys

sys.path.insert(0, "E:/kutyai-app/kaynak/testler/betikler")
from gkimlik_ortak import *  # noqa: E402

c = istemci()


def yonetici(ad: str):
    eposta, _, _, _ = kayit_ve_dogrula(c, yeni_eposta(ad))
    sql_yaz("update kullanici set rol='yonetici' where eposta=?", (eposta,))
    _, b = giris(c, eposta, panel=True)
    return eposta, b["kullanici"]["id"], b["erisim_jetonu"]


y1_eposta, y1_id, y1_jeton = yonetici("goz-yon-denetim")
hat = yetki(y1_jeton)
print(f"### yonetici Y1 id={y1_id} eposta={y1_eposta}")

# --- Hedef kullanici olustur, rolunu yukselt, denetim izini sorgula
hedef = c.post("/kullanicilar", headers=hat, json={
    "eposta": yeni_eposta("goz-hedef"), "ad_soyad": "Hedef", "parola": PAROLA,
    "rol": "son_kullanici"})
hedef_id = govde(hedef)["id"]
yaz("POST /kullanicilar", {"durum": hedef.status_code, "id": hedef_id, "govde": govde(hedef)})

onceki = sql("select count(*) as n from islem_kaydi where eylem='kullanici.guncelle'")
r1 = c.patch(f"/kullanicilar/{hedef_id}", headers=hat,
             json={"rol": "operator", "ad_soyad": "Hedef Yeni"})
yaz("PATCH hedef rol=operator", {"durum": r1.status_code, "govde": govde(r1)})

izler = sql(
    "select id, kullanici_id, eylem, hedef_tur, hedef_id, ayrinti, ip from islem_kaydi "
    "where eylem='kullanici.guncelle' and hedef_id=? order by id", (hedef_id,))
yaz("islem_kaydi (kullanici.guncelle, hedef)", izler)
sonraki = sql("select count(*) as n from islem_kaydi where eylem='kullanici.guncelle'")
print(f"### kullanici.guncelle kayit sayisi once={onceki[0]['n']} sonra={sonraki[0]['n']}")
yaz("hedefin DB satiri", sql("select id, rol, durum, ad_soyad from kullanici where id=?", (hedef_id,)))

r2 = c.patch(f"/kullanicilar/{hedef_id}", headers=hat, json={"durum": "pasif"})
yaz("PATCH hedef durum=pasif", {"durum": r2.status_code, "govde": govde(r2)})
yaz("hedefin DB satiri (pasif sonrasi)", sql(
    "select id, rol, durum from kullanici where id=?", (hedef_id,)))

# --- Kendini pasif yapma
r3 = c.patch(f"/kullanicilar/{y1_id}", headers=hat, json={"durum": "pasif"})
yaz("PATCH KENDINI durum=pasif", {"durum": r3.status_code, "govde": govde(r3)})
yaz("Y1 DB satiri", sql("select id, rol, durum from kullanici where id=?", (y1_id,)))
r4 = c.get("/kullanicilar", headers=hat)
yaz("pasif sonrasi Y1 jetonu ile /kullanicilar", {"durum": r4.status_code, "govde": govde(r4)})
r5 = c.post("/kimlik/panel-giris", json={"eposta": y1_eposta, "parola": PAROLA})
yaz("pasif sonrasi Y1 ile panel-giris", {"durum": r5.status_code, "govde": govde(r5)})
yaz("Y1 kullanici.guncelle/kullanici.pasiflestir izleri", sql(
    "select eylem, hedef_id, ayrinti from islem_kaydi where kullanici_id=? order by id", (y1_id,)))

# --- Kendi rolunu dusurme (ikinci yonetici)
y2_eposta, y2_id, y2_jeton = yonetici("goz-yon-rol")
r6 = c.patch(f"/kullanicilar/{y2_id}", headers=yetki(y2_jeton), json={"rol": "izleyici"})
yaz("PATCH KENDI ROLUNU izleyici yap", {"durum": r6.status_code, "govde": govde(r6)})
yaz("Y2 DB satiri", sql("select id, rol, durum from kullanici where id=?", (y2_id,)))

# --- Kendini DELETE
y3_eposta, y3_id, y3_jeton = yonetici("goz-yon-sil")
r7 = c.delete(f"/kullanicilar/{y3_id}", headers=yetki(y3_jeton))
yaz("DELETE KENDINI", {"durum": r7.status_code, "govde": govde(r7) if r7.status_code != 204 else None})

# --- Olmayan id ve gecersiz enum (taze yonetici)
_, _, y4_jeton = yonetici("goz-yon-404")
r8 = c.patch("/kullanicilar/999999", headers=yetki(y4_jeton), json={"durum": "pasif"})
yaz("PATCH olmayan id", {"durum": r8.status_code, "govde": govde(r8)})

r9 = c.patch(f"/kullanicilar/{hedef_id}", headers=yetki(y4_jeton), json={"durum": "silinmis"})
yaz("PATCH gecersiz durum degeri", {"durum": r9.status_code, "govde": govde(r9)})
