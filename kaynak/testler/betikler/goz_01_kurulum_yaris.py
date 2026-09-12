"""Gözlem #1/#2 — kurulum yarış durumu ve tekrar deneme.

Kullanım: python goz_01_kurulum_yaris.py [ayni_eposta]
"""

from __future__ import annotations

import asyncio
import sys

import httpx

from goz_ortak import (
    TABAN,
    baglan,
    basliklar,
    bekle_hazir,
    giris,
    giris_denemesi,
    kurulum,
    ozet,
    yaz,
)

AYNI = len(sys.argv) > 1 and sys.argv[1] == "ayni_eposta"


async def main() -> None:
    async with httpx.AsyncClient(timeout=40) as istemci:
        await bekle_hazir(istemci)

        once = await istemci.get(f"{TABAN}/saglik/kurulum")
        yaz("Baseline GET /saglik/kurulum", ozet(once))

        e1 = "goz-yonetici-1@gozlem.example.com"
        e2 = e1 if AYNI else "goz-yonetici-2@gozlem.example.com"
        yaz("Senaryo", "AYNI E-POSTA" if AYNI else "FARKLI E-POSTA")

        t0 = asyncio.get_event_loop().time()
        y1, y2 = await asyncio.gather(
            kurulum(istemci, eposta=e1, marka="Yaris-1", gorunen_ad="Yaris Model 1"),
            kurulum(istemci, eposta=e2, marka="Yaris-2", gorunen_ad="Yaris Model 2"),
        )
        sure = asyncio.get_event_loop().time() - t0
        yaz(f"İstek 1 (geçen {sure:.2f}s)", ozet(y1))
        yaz(f"İstek 2 (geçen {sure:.2f}s)", ozet(y2))

        sonra = await istemci.get(f"{TABAN}/saglik/kurulum")
        yaz("Sonra GET /saglik/kurulum", ozet(sonra))

        # İkinci kurulum denemesi (senaryo 2)
        tekrar = await kurulum(istemci, eposta="goz-yonetici-3@gozlem.example.com", marka="Tekrar")
        yaz("Kurulum sonrası tekrar POST /kurulum", ozet(tekrar))

        # Giriş denemesi: hangi yönetici(lar) gerçekten oluştu?
        for eposta in (e1, e2, "goz-yonetici-3@gozlem.example.com"):
            yanit = await giris_denemesi(istemci, eposta)
            yaz(f"Panel girişi {eposta}", ozet(yanit))

        yonetici_jetonu = await giris(istemci, e1)
        kullanicilar = await istemci.get(
            f"{TABAN}/kullanicilar?boyut=200", headers=basliklar(yonetici_jetonu)
        )
        kayitlar = kullanicilar.json().get("kayitlar", [])
        yaz(
            f"GET /kullanicilar -> toplam={kullanicilar.json().get('toplam')}",
            "\n".join(
                f"id={k['id']} eposta={k['eposta']} rol={k['rol']} durum={k['durum']}"
                for k in kayitlar
            ),
        )

        bdmlar = await istemci.get(f"{TABAN}/bdm", headers=basliklar(yonetici_jetonu))
        yaz(
            f"GET /bdm -> HTTP {bdmlar.status_code}",
            "\n".join(
                f"id={b['id']} slug={b['slug']} ad={b['gorunen_ad']}"
                for b in (bdmlar.json() if bdmlar.status_code == 200 else [])
            ),
        )

    # Bağımsız SQL doğrulaması (canlı sunucu dışında, ayrı bağlantı)
    baglanti = baglan("goz_loglar")
    yaz(
        "SQL: kullanici tablosu",
        repr(
            baglanti.execute(
                "SELECT id, eposta, rol, durum FROM kullanici ORDER BY id"
            ).fetchall()
        ),
    )
    yaz(
        "SQL: bdm tablosu",
        repr(baglanti.execute("SELECT id, slug, gorunen_ad FROM bdm ORDER BY id").fetchall()),
    )
    yaz(
        "SQL: kurulum ayarları",
        repr(
            baglanti.execute(
                "SELECT anahtar, deger FROM ayar WHERE anahtar IN "
                "('kurulum_tamam','marka_adi','varsayilan_bdm_slug')"
            ).fetchall()
        ),
    )
    yaz(
        "SQL: islem_kaydi",
        repr(
            baglanti.execute(
                "SELECT id, eylem, kullanici_id, hedef_tur, hedef_id FROM islem_kaydi ORDER BY id"
            ).fetchall()
        ),
    )
    baglanti.close()


asyncio.run(main())
