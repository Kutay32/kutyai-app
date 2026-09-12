"""2) Kayit tekrari: 409 cakisma mi 500 mu? Buyuk/kucuk harf farki ayni hesap mi?"""

from __future__ import annotations

import sys

sys.path.insert(0, "E:/kutyai-app/kaynak/testler/betikler")
from gkimlik_ortak import *  # noqa: E402

c = istemci()
eposta = f"Goz-Karar-{__import__('uuid').uuid4().hex[:8]}@Ornek.COM"

r1 = c.post("/kimlik/kayit", json={"eposta": eposta, "ad_soyad": "A", "parola": PAROLA})
yaz("1. kayit (karisik harf)", {"durum": r1.status_code, "govde": govde(r1)})

r2 = c.post("/kimlik/kayit", json={"eposta": eposta, "ad_soyad": "A", "parola": PAROLA})
yaz("2. kayit (BIREBIR ayni e-posta)", {"durum": r2.status_code, "govde": govde(r2)})

kucuk = eposta.lower()
r3 = c.post("/kimlik/kayit", json={"eposta": kucuk, "ad_soyad": "A", "parola": PAROLA})
yaz("3. kayit (kucuk harfli ayni e-posta)", {"durum": r3.status_code, "govde": govde(r3)})

buyuk = eposta.upper()
r4 = c.post("/kimlik/kayit", json={"eposta": buyuk, "ad_soyad": "A", "parola": PAROLA})
yaz("4. kayit (BUYUK harfli ayni e-posta)", {"durum": r4.status_code, "govde": govde(r4)})

# bosluklu varyant
r5 = c.post("/kimlik/kayit", json={"eposta": f"  {kucuk}  ", "ad_soyad": "A", "parola": PAROLA})
yaz("5. kayit (bastan/sondan bosluklu)", {"durum": r5.status_code, "govde": govde(r5)})

yaz("kullanici tablosunda bu desen", sql(
    "select id, eposta, durum from kullanici where lower(eposta) like ?", (f"%{kucuk}%",)
))

# Parola politikasi ve zorunlu alan
r6 = c.post("/kimlik/kayit", json={"eposta": yeni_eposta(), "ad_soyad": "A", "parola": "kisa"})
yaz("6. kayit (7 karakter parola)", {"durum": r6.status_code, "govde": govde(r6)})
r7 = c.post("/kimlik/kayit", json={"eposta": "", "ad_soyad": "A", "parola": PAROLA})
yaz("7. kayit (bos e-posta)", {"durum": r7.status_code, "govde": govde(r7)})
r8 = c.post("/kimlik/kayit", json={"ad_soyad": "A", "parola": PAROLA})
yaz("8. kayit (eposta alani yok)", {"durum": r8.status_code, "govde": govde(r8)})
