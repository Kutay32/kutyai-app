"""5) /kimlik/sifre-sifirlama-iste: bilinmeyen e-posta icin de 200/ayni mesaj mi,
   yanit SURESI farkli mi (zamanlama sizintisi)?"""

from __future__ import annotations

import statistics
import sys
import time

sys.path.insert(0, "E:/kutyai-app/kaynak/testler/betikler")
from gkimlik_ortak import *  # noqa: E402

N = 40
c = istemci()
bilinen, _, _, _ = kayit_ve_dogrula(c, yeni_eposta("goz-zaman"))
bilinmeyen = yeni_eposta("goz-yok")

rk = c.post("/kimlik/sifre-sifirlama-iste", json={"eposta": bilinen})
ry = c.post("/kimlik/sifre-sifirlama-iste", json={"eposta": bilinmeyen})
yaz("bilinen e-posta", {"durum": rk.status_code, "govde": govde(rk)})
yaz("bilinmeyen e-posta", {"durum": ry.status_code, "govde": govde(ry)})

# Ayni mesaj mi?
ayni_mesaj = (
    govde(rk).get("mesaj") == govde(ry).get("mesaj")
    and "gelistirme_baglantisi" in govde(rk)
    and "gelistirme_baglantisi" not in govde(ry)
)
print(f"### mesaj ayni mi (bilinmeyende gelistirme_baglantisi yok): {ayni_mesaj}")

sureler = {"bilinen": [], "bilinmeyen": []}
for i in range(N):
    for etiket, eposta in (("bilinen", bilinen), ("bilinmeyen", bilinmeyen)):
        t = time.perf_counter()
        r = c.post("/kimlik/sifre-sifirlama-iste", json={"eposta": eposta})
        sureler[etiket].append((time.perf_counter() - t) * 1000)
        assert r.status_code == 200, (etiket, r.status_code)


def ozet(degerler):
    return {
        "n": len(degerler),
        "ortanca_ms": round(statistics.median(degerler), 3),
        "ortalama_ms": round(statistics.mean(degerler), 3),
        "min_ms": round(min(degerler), 3),
        "maks_ms": round(max(degerler), 3),
        "p90_ms": round(sorted(degerler)[int(len(degerler) * 0.9)], 3),
    }


yaz("sureler", {k: ozet(v) for k, v in sureler.items()})
o = ozet(sureler["bilinen"])["ortanca_ms"]
y = ozet(sureler["bilinmeyen"])["ortanca_ms"]
print(f"### ortanca fark (bilinen - bilinmeyen) = {round(o - y, 3)} ms; oran = {round(o / y, 2)}x")
