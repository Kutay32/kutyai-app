"""7) Parola alani hicbir yanitta donuyor mu? Tum yanitlar ham metin olarak taranir."""

from __future__ import annotations

import json
import re
import sys

sys.path.insert(0, "E:/kutyai-app/kaynak/testler/betikler")
from gkimlik_ortak import *  # noqa: E402

SIZINTI_PAROLALARI = [
    "Parola123!",
    "YeniParola456!",
    "UcuncuParola000!",
    "DorduncuParola111!",
    "BaskaParola789!",
]

c = istemci()
kayitlar: list[tuple[str, str]] = []


def topla(etiket: str, yanit) -> None:
    kayitlar.append((etiket, f"{yanit.status_code}\n{yanit.text}"))


# --- kimlik akisi
eposta = yeni_eposta("goz-tarama")
r = c.post("/kimlik/kayit", json={"eposta": eposta, "ad_soyad": "Tarama", "parola": PAROLA})
topla("POST /kimlik/kayit", r)
b = govde(r)
dogrulama = jeton_baglantidan(b.get("gelistirme_baglantisi", ""))
topla("POST /kimlik/dogrula", c.post("/kimlik/dogrula", json={"jeton": dogrulama}))
rg = c.post("/kimlik/giris", json={"eposta": eposta, "parola": PAROLA})
topla("POST /kimlik/giris", rg)
bg = govde(rg)
topla("POST /kimlik/panel-giris (yanlis kapı)", c.post(
    "/kimlik/panel-giris", json={"eposta": eposta, "parola": PAROLA}))
ry = c.post("/kimlik/yenile", json={"yenileme_jetonu": bg.get("yenileme_jetonu")})
topla("POST /kimlik/yenile", ry)
by = govde(ry)
topla("POST /kimlik/cikis", c.post(
    "/kimlik/cikis", json={"yenileme_jetonu": by.get("yenileme_jetonu")},
    headers=yetki(bg.get("erisim_jetonu"))))
topla("GET /kimlik/ben", c.get("/kimlik/ben", headers=yetki(bg.get("erisim_jetonu"))))
rs = c.post("/kimlik/sifre-sifirlama-iste", json={"eposta": eposta})
topla("POST /kimlik/sifre-sifirlama-iste", rs)
js = jeton_baglantidan(govde(rs).get("gelistirme_baglantisi", ""))
topla("POST /kimlik/sifre-sifirla", c.post(
    "/kimlik/sifre-sifirla", json={"jeton": js, "yeni_parola": "YeniParola456!"}))
topla("POST /kimlik/sifre-sifirla (ayni jeton tekrar)", c.post(
    "/kimlik/sifre-sifirla", json={"jeton": js, "yeni_parola": "UcuncuParola000!"}))
topla("yanlis parola ile /kimlik/giris", c.post(
    "/kimlik/giris", json={"eposta": eposta, "parola": "YanlisParola!"}))
topla("olmayan e-posta ile /kimlik/giris", c.post(
    "/kimlik/giris", json={"eposta": yeni_eposta("goz-yok2"), "parola": PAROLA}))
topla("kisa parola ile /kimlik/kayit", c.post(
    "/kimlik/kayit", json={"eposta": yeni_eposta(), "ad_soyad": "K", "parola": "kisa"}))

# --- kullanici yonetimi
yon_eposta, _, _, _ = kayit_ve_dogrula(c, yeni_eposta("goz-tarama-yon"))
sql_yaz("update kullanici set rol='yonetici' where eposta=?", (yon_eposta,))
_, byon = giris(c, yon_eposta, panel=True)
hat = yetki(byon["erisim_jetonu"])
topla("GET /kullanicilar", c.get("/kullanicilar", headers=hat))
hedef = yeni_eposta("goz-tarama-hedef")
rol = c.post("/kullanicilar", headers=hat, json={
    "eposta": hedef, "ad_soyad": "Hedef Kisi", "parola": "HedefParola999!", "rol": "operator"})
topla("POST /kullanicilar", rol)
hedef_id = govde(rol).get("id")
topla("PATCH /kullanicilar/{id}", c.patch(
    f"/kullanicilar/{hedef_id}", headers=hat, json={"ad_soyad": "Yeni Ad"}))
topla("PATCH /kullanicilar/{id} (rol son_kullanici)", c.patch(
    f"/kullanicilar/{hedef_id}", headers=hat, json={"rol": "son_kullanici"}))
topla("DELETE /kullanicilar/{id}", c.delete(f"/kullanicilar/{hedef_id}", headers=hat))
topla("GET /kullanicilar/{id} yok (404 govdesi)", c.get("/kullanicilar", headers=hat))

print("### taranan yanit sayisi:", len(kayitlar))
print("### taranan desenler: 'parola', 'sifre', 'hash', 'argon2' (JSON anahtari), $argon2 (ham)")


def anahtarlari_tara(veri, yol=""):
    bulunan = []
    if isinstance(veri, dict):
        for k, v in veri.items():
            if re.search(r"parola|sifre|hash|argon2", k, re.I):
                bulunan.append(f"{yol}.{k} = {str(v)[:80]}")
            bulunan += anahtarlari_tara(v, f"{yol}.{k}")
    elif isinstance(veri, list):
        for i, v in enumerate(veri):
            bulunan += anahtarlari_tara(v, f"{yol}[{i}]")
    return bulunan


sorun = 0
for etiket, ham in kayitlar:
    govde_metni = ham.split("\n", 1)[1]
    try:
        veri = json.loads(govde_metni)
    except Exception:
        veri = None
    anahtar_isabetleri = anahtarlari_tara(veri) if veri is not None else []
    ham_isabetleri = re.findall(r"\$argon2[a-z0-9$]*(?:.{0,20})?", govde_metni)
    parola_isabetleri = [p for p in SIZINTI_PAROLALARI if p in govde_metni]
    if anahtar_isabetleri or ham_isabetleri or parola_isabetleri:
        sorun += 1
        yaz(f"ISABET: {etiket}", {
            "anahtarlar": anahtar_isabetleri,
            "argon2_imzasi": ham_isabetleri,
            "duz_metin_parola": parola_isabetleri,
        })

print(f"### parola sizintisi isabeti olan yanit sayisi: {sorun} / {len(kayitlar)}")

# --- Ornek ham yanitlar (kanit)
for etiket, ham in kayitlar[:4]:
    print(f"\n### HAM: {etiket}\n{ham[:700]}")
