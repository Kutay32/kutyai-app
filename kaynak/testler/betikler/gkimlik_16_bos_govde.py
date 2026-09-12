"""16) PATCH /kullanicilar/{id} bos govde ve denetim kaydi davranisi."""

from __future__ import annotations

import sys

sys.path.insert(0, "E:/kutyai-app/kaynak/testler/betikler")
from gkimlik_ortak import *  # noqa: E402

c = istemci()
yon_eposta, _, _, _ = kayit_ve_dogrula(c, yeni_eposta("goz-yon-bos"))
sql_yaz("update kullanici set rol='yonetici' where eposta=?", (yon_eposta,))
_, by = giris(c, yon_eposta, panel=True)
hat = yetki(by["erisim_jetonu"])
hedef = c.post("/kullanicilar", headers=hat, json={
    "eposta": yeni_eposta("goz-hedef-bos"), "ad_soyad": "Bos", "parola": PAROLA,
    "rol": "izleyici"})
hedef_id = govde(hedef)["id"]

once = sql("select count(*) as n from islem_kaydi where eylem='kullanici.guncelle'")[0]["n"]
r1 = c.patch(f"/kullanicilar/{hedef_id}", headers=hat, json={})
sonra = sql("select count(*) as n from islem_kaydi where eylem='kullanici.guncelle'")[0]["n"]
yaz("PATCH bos govde", {"durum": r1.status_code, "govde": govde(r1),
                        "islem_kaydi_once": once, "islem_kaydi_sonra": sonra})

r2 = c.patch(f"/kullanicilar/{hedef_id}", headers=hat, json={})
yaz("PATCH bos govde (tekrar)", {"durum": r2.status_code, "govde": govde(r2)})

# sayfa urun: Sayfa<T> toplam alani filtre ile tutarli mi
r3 = c.get("/kullanicilar?rol=izleyici&boyut=1", headers=hat)
b3 = govde(r3)
yaz("sayfa/sayfa-boyutu tutarliligi", {"toplam": b3["toplam"], "boyut": b3["boyut"],
                                       "kayit": len(b3["kayitlar"]), "durum": r3.status_code})
