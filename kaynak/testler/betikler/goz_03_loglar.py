"""Gözlem #5/#6/#7 — log listesi/sayfalama, dışa aktarım, silme yetkileri."""

from __future__ import annotations

import asyncio
import json
import sqlite3

import httpx

from goz_ortak import TABAN, basliklar, bekle_hazir, giris, ozet, yaz

YONETICI = "goz-yonetici-1@gozlem.example.com"
OPERATOR = "goz-operator@gozlem.example.com"
IZLEYICI = "goz-izleyici@gozlem.example.com"
DB = "E:/kutyai-app/kaynak/testler/gecici/goz_loglar.db"


async def main() -> None:
    async with httpx.AsyncClient(timeout=30) as istemci:
        await bekle_hazir(istemci)
        yonetici = await giris(istemci, YONETICI)
        operator = await giris(istemci, OPERATOR)
        izleyici = await giris(istemci, IZLEYICI)

        async def al(yol: str, jeton: str = operator):
            yanit = await istemci.get(f"{TABAN}{yol}", headers=basliklar(jeton))
            yaz(f"GET {yol}", ozet(yanit))
            return yanit

        # --- A) liste ve filtreler ---
        temel = await al("/loglar/konusmalar")
        yaz("Liste başlıkları", repr([k["baslik"] for k in temel.json()["kayitlar"]]))
        yaz(
            "Kayıt anahtarları",
            repr(sorted(temel.json()["kayitlar"][0].keys())),
        )

        await al("/loglar/konusmalar?kullanici_id=1")
        await al("/loglar/konusmalar?bdm_id=2")
        await al("/loglar/konusmalar?arama=Docker")
        await al("/loglar/konusmalar?arama=%C3%B6%C4%9Fle")   # 'öğle' küçük harf
        await al("/loglar/konusmalar?arama=%C3%96%C4%9Fle")   # 'Öğle' büyük harf
        await al("/loglar/konusmalar?baslangic=2026-09-04T00:00:00&bitis=2026-09-06T00:00:00")
        await al("/loglar/konusmalar?baslangic=2026-09-06T00:00:00&bitis=2026-09-04T00:00:00")

        # --- B) sayfalama sınırları ---
        await al("/loglar/konusmalar?boyut=10000")
        await al("/loglar/konusmalar?sayfa=0")
        await al("/loglar/konusmalar?sayfa=-3")
        await al("/loglar/konusmalar?boyut=0")
        await al("/loglar/konusmalar?boyut=-5")
        await al("/loglar/konusmalar?sayfa=abc")
        await al("/loglar/konusmalar?boyut=99999999999999999999")
        await al("/loglar/konusmalar?kullanici_id=abc")

        # --- C) detay ---
        await al("/loglar/konusmalar/1")
        await al("/loglar/konusmalar/99999")

        # --- D) dışa aktarım ---
        for bicim in ("json", "md", "csv"):
            yanit = await istemci.get(
                f"{TABAN}/loglar/konusmalar/1/disa-aktar?bicim={bicim}",
                headers=basliklar(operator),
            )
            yaz(
                f"GET disa-aktar bicim={bicim}",
                f"HTTP {yanit.status_code}\n"
                f"content-type={yanit.headers.get('content-type')}\n"
                f"content-disposition={yanit.headers.get('content-disposition')}\n"
                f"bytes={len(yanit.content)}\n{yanit.text[:900]}",
            )
        yanit = await istemci.get(
            f"{TABAN}/loglar/konusmalar/1/disa-aktar?bicim=pdf", headers=basliklar(operator)
        )
        yaz("GET disa-aktar bicim=pdf", ozet(yanit))
        yanit = await istemci.get(
            f"{TABAN}/loglar/konusmalar/1/disa-aktar?bicim=JSON", headers=basliklar(operator)
        )
        yaz("GET disa-aktar bicim=JSON (büyük harf)", ozet(yanit))

        # JSON içeriği gerçekten geçerli mi?
        json_yanit = await istemci.get(
            f"{TABAN}/loglar/konusmalar/1/disa-aktar?bicim=json", headers=basliklar(operator)
        )
        try:
            veri = json.loads(json_yanit.content.decode("utf-8"))
            yaz("JSON çözüldü", f"anahtarlar={sorted(veri.keys())} mesaj={len(veri['mesajlar'])}")
        except Exception as hata:  # noqa: BLE001
            yaz("JSON çözülemedi", repr(hata))

        # --- E) silme yetkileri ---
        sil_op = await istemci.delete(
            f"{TABAN}/loglar/konusmalar/1", headers=basliklar(operator)
        )
        yaz("DELETE /loglar/konusmalar/1 (operator)", f"HTTP {sil_op.status_code} gövde={sil_op.text!r}")

        sil_iz = await istemci.delete(
            f"{TABAN}/loglar/konusmalar/2", headers=basliklar(izleyici)
        )
        yaz("DELETE /loglar/konusmalar/2 (izleyici)", f"HTTP {sil_iz.status_code} gövde={sil_iz.text!r}")

        sil_yok = await istemci.delete(
            f"{TABAN}/loglar/konusmalar/99999", headers=basliklar(yonetici)
        )
        yaz("DELETE /loglar/konusmalar/99999", ozet(sil_yok))

        baglanti = sqlite3.connect(DB)
        yaz(
            "SQL: silme sonrası konuşmalar",
            repr(baglanti.execute("SELECT id,baslik FROM konusma ORDER BY id").fetchall()),
        )
        yaz(
            "SQL: silme sonrası mesajlar",
            repr(baglanti.execute("SELECT id,konusma_id FROM mesaj ORDER BY id").fetchall()),
        )
        baglanti.close()

        # --- F) temizle ---
        temiz_op = await istemci.post(
            f"{TABAN}/loglar/temizle", headers=basliklar(operator), json={"gun": 10}
        )
        yaz("POST /loglar/temizle (operator, gun=10)", ozet(temiz_op))
        temiz_iz = await istemci.post(
            f"{TABAN}/loglar/temizle", headers=basliklar(izleyici), json={"gun": 10}
        )
        yaz("POST /loglar/temizle (izleyici, gun=10)", ozet(temiz_iz))
        temiz_gun0 = await istemci.post(
            f"{TABAN}/loglar/temizle", headers=basliklar(yonetici), json={"gun": 0}
        )
        yaz("POST /loglar/temizle (yonetici, gun=0)", ozet(temiz_gun0))
        temiz_gun3651 = await istemci.post(
            f"{TABAN}/loglar/temizle", headers=basliklar(yonetici), json={"gun": 3651}
        )
        yaz("POST /loglar/temizle (yonetici, gun=3651)", ozet(temiz_gun3651))

        baglanti = sqlite3.connect(DB)
        yaz(
            "SQL: temizle öncesi konuşmalar",
            repr(baglanti.execute("SELECT id,baslik,olusturulma FROM konusma ORDER BY id").fetchall()),
        )
        baglanti.close()

        temiz_ok = await istemci.post(
            f"{TABAN}/loglar/temizle", headers=basliklar(yonetici), json={"gun": 10}
        )
        yaz("POST /loglar/temizle (yonetici, gun=10)", ozet(temiz_ok))
        temiz_bos = await istemci.post(
            f"{TABAN}/loglar/temizle", headers=basliklar(yonetici)
        )
        yaz("POST /loglar/temizle (yonetici, gövdesiz)", ozet(temiz_bos))

        baglanti = sqlite3.connect(DB)
        yaz(
            "SQL: temizle sonrası konuşmalar",
            repr(baglanti.execute("SELECT id,baslik FROM konusma ORDER BY id").fetchall()),
        )
        baglanti.close()

        anonim = await istemci.get(f"{TABAN}/loglar/konusmalar")
        yaz("GET /loglar/konusmalar (jetonsuz)", ozet(anonim))

        # --- G) denetim izi (bağımsız SQL) ---
        baglanti = sqlite3.connect(DB)
        yaz(
            "SQL: log/anahtar/silme işlemlerinin denetim izi",
            "\n".join(
                f"id={r[0]} eylem={r[1]} kullanici_id={r[2]} hedef={r[3]}:{r[4]} ayrinti={r[5]}"
                for r in baglanti.execute(
                    "SELECT id, eylem, kullanici_id, hedef_tur, hedef_id, ayrinti "
                    "FROM islem_kaydi ORDER BY id"
                ).fetchall()
            ),
        )
        baglanti.close()


asyncio.run(main())
