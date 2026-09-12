"""13) API.md §6 parametreleri (filtre/sayfalama) ve POST /kullanicilar yarisi."""

from __future__ import annotations

import asyncio
import sys

import httpx

sys.path.insert(0, "E:/kutyai-app/kaynak/testler/betikler")
from gkimlik_ortak import *  # noqa: E402

c = istemci()
yon_eposta, _, _, _ = kayit_ve_dogrula(c, yeni_eposta("goz-yon-liste"))
sql_yaz("update kullanici set rol='yonetici' where eposta=?", (yon_eposta,))
_, by = giris(c, yon_eposta, panel=True)
hat = yetki(by["erisim_jetonu"])

# --- filtreler
etiket = "filtre" + __import__("uuid").uuid4().hex[:6]
for rol, ad in (("operator", "Filtre Op"), ("izleyici", "Filtre Iz")):
    r = c.post("/kullanicilar", headers=hat, json={
        "eposta": f"{etiket}-{rol}@ornek.com", "ad_soyad": ad, "parola": PAROLA, "rol": rol})
    print(f"### POST /kullanicilar rol={rol} -> {r.status_code}")

for sorgu in (
    f"?rol=operator&arama={etiket}",
    f"?durum=aktif&arama={etiket}",
    f"?arama={etiket}",
    f"?sayfa=1&boyut=1&arama={etiket}",
    f"?sayfa=0&boyut=0&arama={etiket}",
    f"?sayfa=2&boyut=200&arama={etiket}",
    f"?boyut=1000&arama={etiket}",
    "?rol=gecersiz_rol",
    "?sayfa=abc",
):
    r = c.get(f"/kullanicilar{sorgu}", headers=hat)
    b = govde(r)
    ozet = {"durum": r.status_code}
    if isinstance(b, dict) and "kayitlar" in b:
        ozet.update({"toplam": b["toplam"], "sayfa": b["sayfa"], "boyut": b["boyut"],
                     "kayit_sayisi": len(b["kayitlar"]),
                     "roller": sorted({k["rol"] for k in b["kayitlar"]})})
    else:
        ozet["govde"] = b
    yaz(f"GET /kullanicilar{sorgu}", ozet)

# --- Sayfa<T> alan adlari
r = c.get(f"/kullanicilar?arama={etiket}", headers=hat)
print("### Sayfa<T> alan adlari:", sorted(govde(r).keys()),
      "| Kullanici alanlari:", sorted(govde(r)["kayitlar"][0].keys()))

# --- POST /kullanicilar yarisi (ayni e-posta ile 5 paralel)
YARIS = f"goz-kul-yaris-{__import__('uuid').uuid4().hex[:8]}@ornek.com"


async def main() -> None:
    async with httpx.AsyncClient(base_url=TABAN, timeout=60.0) as ac:
        yanitlar = await asyncio.gather(*[
            ac.post("/kullanicilar", headers=hat, json={
                "eposta": YARIS, "ad_soyad": "Yaris", "parola": PAROLA, "rol": "izleyici"})
            for _ in range(5)], return_exceptions=True)
    print("### POST /kullanicilar ayni e-posta ile 5 paralel")
    for i, y in enumerate(yanitlar):
        print(f"  {i}: {'ISTISNA ' + type(y).__name__ if isinstance(y, Exception) else str(y.status_code) + ' ' + y.text[:160]}")


asyncio.run(main())
