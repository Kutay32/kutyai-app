"""14) Zaman damgasi bicimi tutarliligi ve dokuman uclari."""

from __future__ import annotations

import sys

import httpx

sys.path.insert(0, "E:/kutyai-app/kaynak/testler/betikler")
from gkimlik_ortak import *  # noqa: E402

c = istemci()
yon_eposta, _, _, _ = kayit_ve_dogrula(c, yeni_eposta("goz-yon-bicim"))
sql_yaz("update kullanici set rol='yonetici' where eposta=?", (yon_eposta,))
_, by = giris(c, yon_eposta, panel=True)
hat = yetki(by["erisim_jetonu"])
print("### /kimlik/panel-giris yanitindaki damgalar:",
      {k: by["kullanici"][k] for k in ("olusturulma", "son_giris")})

eposta = yeni_eposta("goz-bicim")
r1 = c.post("/kullanicilar", headers=hat, json={
    "eposta": eposta, "ad_soyad": "Bicim", "parola": PAROLA, "rol": "izleyici"})
print("### POST /kullanicilar (hemen sonra):", govde(r1)["olusturulma"])

r2 = c.get(f"/kullanicilar?arama={eposta}", headers=hat)
kayit = govde(r2)["kayitlar"][0]
print("### GET /kullanicilar (DB'den okuma):", kayit["olusturulma"])

r3 = c.get("/kimlik/ben", headers=yetki(by["erisim_jetonu"]))
print("### GET /kimlik/ben:", {k: govde(r3)[k] for k in ("olusturulma", "son_giris")})

r4, b4 = giris(c, eposta, "Parola123!")
print(f"### /kimlik/giris -> {r4.status_code}", "| e-posta dogrulanmamis olabilir")

# Yonetici kendi olusturdugu kullanici ile giris yapamaz mi? (durum aktif, dogrulandi)
# izleyici personel -> panel-giris
r5, b5 = giris(c, eposta, panel=True)
print("### /kimlik/panel-giris (izleyici) ->", r5.status_code,
      {k: b5["kullanici"][k] for k in ("olusturulma", "son_giris")} if r5.status_code == 200 else b5)

print("### GET /api/docs ->", httpx.get("http://127.0.0.1:8101/api/docs", timeout=30).status_code)
print("### GET /api/openapi.json ->",
      httpx.get("http://127.0.0.1:8101/api/openapi.json", timeout=30).status_code)
print("### GET /api/v1/openapi.json (API.md'de taban adres altinda degil) ->",
      c.get("/openapi.json").status_code)
