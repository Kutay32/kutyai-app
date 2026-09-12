"""3) E-posta dogrulama jetonu: tekrar kullanim ve suresi gecmis jeton."""

from __future__ import annotations

import sys

sys.path.insert(0, "E:/kutyai-app/kaynak/testler/betikler")
from gkimlik_ortak import *  # noqa: E402

c = istemci()
eposta, jeton, rk, rd = kayit_ve_dogrula(c)
yaz("kayit+dogrula", {"kayit": rk.status_code, "dogrula": rd, "jeton": kisalt(jeton)})

r2 = c.post("/kimlik/dogrula", json={"jeton": jeton})
yaz("AYNI dogrulama jetonu ile 2. cagri", {"durum": r2.status_code, "govde": govde(r2)})

r3 = c.post("/kimlik/dogrula", json={"jeton": "uydurma-jeton-degeri"})
yaz("uydurma jeton", {"durum": r3.status_code, "govde": govde(r3)})

# --- Suresi gecmis jeton: dogrudan DB'de son_kullanma geriye cekilir
eposta2 = yeni_eposta("goz-sure")
r4 = c.post("/kimlik/kayit", json={"eposta": eposta2, "ad_soyad": "S", "parola": PAROLA})
b4 = govde(r4)
jeton2 = jeton_baglantidan(b4["gelistirme_baglantisi"])
sql_yaz(
    "update dogrulama_jetonu set son_kullanma=? where jeton_hash=?",
    ("2020-01-01 00:00:00.000000", __import__("hashlib").sha256(jeton2.encode()).hexdigest()),
)
yaz("DB'de son_kullanma 2020'ye cekildi", sql(
    "select tur, kullanildi, son_kullanma from dogrulama_jetonu where jeton_hash=?",
    (__import__("hashlib").sha256(jeton2.encode()).hexdigest(),),
))
r5 = c.post("/kimlik/dogrula", json={"jeton": jeton2})
yaz("suresi gecmis jeton ile dogrula", {"durum": r5.status_code, "govde": govde(r5)})

yaz("dogrulama_jetonu tablosu (bu kullanicilar)", sql(
    "select j.id, j.kullanici_id, j.tur, j.kullanildi, j.son_kullanma from dogrulama_jetonu j "
    "join kullanici k on k.id=j.kullanici_id where k.eposta in (?, ?) order by j.id",
    (eposta, eposta2),
))

# Dogrulama sonrasi giris yapilabiliyor mu (jeton gercekten tuketildi mi)
r6, b6 = giris(c, eposta)
yaz("dogrulama sonrasi giris", {"durum": r6.status_code, "alanlar": sorted(b6.keys())})

# Ayni kullanici icin yeni kayit denemesi (dogrulanmis hesap) -> cakisma
r7 = c.post("/kimlik/kayit", json={"eposta": eposta, "ad_soyad": "S", "parola": PAROLA})
yaz("dogrulanmis hesapla tekrar kayit", {"durum": r7.status_code, "govde": govde(r7)})
