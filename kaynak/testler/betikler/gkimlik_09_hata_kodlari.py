"""9) Hata kodlari API.md §1 tablosuyla uyumlu mu? (gecersiz_kimlik_bilgisi dahil)"""

from __future__ import annotations

import pathlib
import re
import sys

sys.path.insert(0, "E:/kutyai-app/kaynak/testler/betikler")
from gkimlik_ortak import *  # noqa: E402

# --- API.md §1 tablosunu ayristir
api_md = pathlib.Path("E:/kutyai-app/kaynak/API.md").read_text(encoding="utf-8")
bolum = api_md.split("## 1. Hata zarfı")[1].split("## 2.")[0]
tablo: dict[int, set[str]] = {}
for satir in bolum.splitlines():
    m = re.match(r"\|\s*(\d{3})\s*\|\s*(.+?)\s*\|", satir)
    if m:
        kodlar = {k.strip().strip("`") for k in m.group(2).split(",")}
        tablo.setdefault(int(m.group(1)), set()).update(kodlar)
print("### API.md §1 tablosu")
for k in sorted(tablo):
    print(f"  {k}: {sorted(tablo[k])}")

c = istemci()
eposta, _, _, _ = kayit_ve_dogrula(c, yeni_eposta("goz-hata"))
_, b = giris(c, eposta)
jeton = b["erisim_jetonu"]

# dogrulanmamis hesap
r_katil = c.post("/kimlik/kayit", json={"eposta": yeni_eposta("goz-dogrulanmamis"),
                                        "ad_soyad": "D", "parola": PAROLA})
yeni_eposta_dogrulanmamis = govde(r_katil)["kullanici"]["eposta"]

senaryolar: list[tuple[int, str, object]] = [
    (400, "gecersiz_istek", lambda: c.post("/kimlik/dogrula", json={"jeton": "yok"})),
    (400, "gecersiz_istek", lambda: c.post("/kimlik/kayit", json={
        "eposta": yeni_eposta(), "ad_soyad": "x", "parola": "kisa"})),
    (400, "dogrulama_hatasi", lambda: c.post("/kimlik/kayit", json={"ad_soyad": "x", "parola": PAROLA})),
    (401, "kimlik_gerekli", lambda: c.get("/kimlik/ben")),
    (401, "jeton_gecersiz", lambda: c.get("/kimlik/ben", headers=yetki("bozuk.jeton"))),
    (401, "gecersiz_kimlik_bilgisi", lambda: c.post(
        "/kimlik/giris", json={"eposta": eposta, "parola": "YanlisParola!"})),
    (401, "gecersiz_kimlik_bilgisi", lambda: c.post(
        "/kimlik/giris", json={"eposta": "hic-yok@ornek.com", "parola": PAROLA})),
    (403, "eposta_dogrulanmadi", lambda: c.post(
        "/kimlik/giris", json={"eposta": yeni_eposta_dogrulanmamis, "parola": PAROLA})),
    (403, "yetki_yok", lambda: c.get("/kullanicilar", headers=yetki(jeton))),
    (404, "bulunamadi", lambda: c.patch("/kullanicilar/999999", headers=yetki(jeton),
                                        json={"durum": "pasif"})),
    (405, "yontem_izinli_degil", lambda: c.get("/kimlik/giris")),
]

sonuclar = []
for beklenen_http, beklenen_kod, cagri in senaryolar:
    r = cagri()
    b = govde(r)
    kod = (b.get("hata") or {}).get("kod") if isinstance(b, dict) else None
    tabloda = kod in tablo.get(r.status_code, set())
    sonuclar.append({
        "senaryo": f"{beklenen_http}/{beklenen_kod}",
        "http": r.status_code,
        "kod": kod,
        "api_md_tablosunda": tabloda,
        "mesaj": (b.get("hata") or {}).get("mesaj") if isinstance(b, dict) else str(b)[:80],
    })

yaz("senaryo sonuclari", sonuclar)

# 409 cakisma
r = c.post("/kimlik/kayit", json={"eposta": eposta, "ad_soyad": "x", "parola": PAROLA})
yaz("409 cakisma", {"http": r.status_code, "govde": govde(r),
                    "tabloda": govde(r)["hata"]["kod"] in tablo.get(409, set())})

print("\n### tabloda OLMAYAN kodlar")
for s in sonuclar:
    if not s["api_md_tablosunda"]:
        print(f"  HTTP {s['http']} kod={s['kod']} (senaryo {s['senaryo']}) mesaj={s['mesaj']}")
