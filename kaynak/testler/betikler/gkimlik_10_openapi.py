"""10) API.md §5/§6 uclari OpenAPI'de var mi; alan adlari birebir mi?"""

from __future__ import annotations

import sys

sys.path.insert(0, "E:/kutyai-app/kaynak/testler/betikler")
from gkimlik_ortak import *  # noqa: E402

import httpx

r = httpx.get("http://127.0.0.1:8101/api/openapi.json", timeout=30.0)
openapi = govde(r)
print(f"### GET http://127.0.0.1:8101/api/openapi.json -> {r.status_code}")

# --- Uc listesi
yollar = openapi.get("paths", {})
print("### /kimlik ve /kullanicilar yollari")
for yol in sorted(yollar):
    if yol.startswith("/api/v1/kimlik") or yol.startswith("/api/v1/kullanicilar"):
        for yontem in sorted(yollar[yol]):
            op = yollar[yol][yontem]
            print(f"  {yontem.upper():6} {yol}  operationId={op.get('operationId')} "
                  f"tags={op.get('tags')} summary={op.get('summary')!r}")

beklenen = {
    "post /api/v1/kimlik/kayit",
    "post /api/v1/kimlik/dogrula",
    "post /api/v1/kimlik/giris",
    "post /api/v1/kimlik/panel-giris",
    "post /api/v1/kimlik/yenile",
    "post /api/v1/kimlik/cikis",
    "post /api/v1/kimlik/sifre-sifirlama-iste",
    "post /api/v1/kimlik/sifre-sifirla",
    "get /api/v1/kimlik/ben",
    "get /api/v1/kullanicilar",
    "post /api/v1/kullanicilar",
    "patch /api/v1/kullanicilar/{kullanici_id}",
    "delete /api/v1/kullanicilar/{kullanici_id}",
}
mevcut = set()
for yol, icerik in yollar.items():
    for yontem in icerik:
        mevcut.add(f"{yontem} {yol}")
eksik = sorted(beklenen - mevcut)
fazla = sorted(y for y in mevcut - beklenen if "kimlik" in y or "kullanicilar" in y)
print(f"### eksik uclar: {eksik}")
print(f"### API.md'de olmayan fazladan uclar: {fazla}")

# --- Alan adlari: istek semalari ve yanit semalari
semalar = openapi.get("components", {}).get("schemas", {})
print(f"### sema adlari (kimlik/kullanici ile ilgili): "
      f"{sorted(s for s in semalar if any(k in s.lower() for k in ('kayit','giris','dogrula','yenile','cikis','sifir','kullanici','rol','durum')))}")

isimler = {}
for ad in ("KayitIstegi", "GirisIstegi", "YenilemeIstegi", "CikisIstegi",
           "SifirlamaIstegi", "SifreSifirlaIstegi", "DogrulamaIstegi",
           "KullaniciOlusturIstegi", "KullaniciGuncelleIstegi"):
    sema = semalar.get(ad)
    if sema:
        isimler[ad] = list(sema.get("properties", {}).keys())
yaz("istek semalari", isimler)

# --- Yanit semalari var mi?
print("### yanit semalari (200/201 responses -> content schema)")
for yol in ("/api/v1/kimlik/giris", "/api/v1/kimlik/yenile", "/api/v1/kimlik/kayit",
            "/api/v1/kimlik/ben", "/api/v1/kullanicilar"):
    for yontem, op in yollar[yol].items():
        yanitlar = op.get("responses", {})
        for kod, tanim in yanitlar.items():
            icerik = tanim.get("content", {})
            sema = icerik.get("application/json", {}).get("schema")
            print(f"  {yontem.upper()} {yol} -> {kod}: {sema}")

# --- Birebir alan adlari gercek yanitlarda
c = istemci()
eposta, _, _, _ = kayit_ve_dogrula(c, yeni_eposta("goz-openapi"))
rg, bg = giris(c, eposta)
ry = c.post("/kimlik/yenile", json={"yenileme_jetonu": bg["yenileme_jetonu"]})
by = govde(ry)
print("### gercek yanit alan adlari")
print("  /kimlik/giris:", sorted(bg.keys()))
print("  /kimlik/giris.kullanici:", sorted(bg["kullanici"].keys()))
print("  /kimlik/yenile:", sorted(by.keys()))
print("  birebir 'erisim_jetonu' var mi:", "erisim_jetonu" in bg and "erisim_jetonu" in by)
print("  birebir 'yenileme_jetonu' var mi:", "yenileme_jetonu" in bg and "yenileme_jetonu" in by)
rb = c.post("/kimlik/kayit", json={"eposta": yeni_eposta("goz-openapi2"),
                                   "ad_soyad": "O", "parola": PAROLA})
print("  /kimlik/kayit:", sorted(govde(rb).keys()))
print("  birebir 'dogrulama_gerekli' var mi:", "dogrulama_gerekli" in govde(rb))
print("  Kullanici tipi alanlari:", sorted(govde(rb)["kullanici"].keys()))
