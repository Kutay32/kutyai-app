"""Gözlem #8/#9/#10 — ayarlar, SMTP şifresi, bakım modu, denetim izi."""

from __future__ import annotations

import asyncio
import sqlite3

import httpx

from goz_ortak import TABAN, basliklar, bekle_hazir, giris, ozet, yaz

YONETICI = "goz-yonetici-1@gozlem.example.com"
OPERATOR = "goz-operator@gozlem.example.com"
IZLEYICI = "goz-izleyici@gozlem.example.com"
DB = "E:/kutyai-app/kaynak/testler/gecici/goz_loglar.db"
SIFRE = "GozlemSmtpParolasi!42"


async def main() -> None:
    async with httpx.AsyncClient(timeout=30) as istemci:
        await bekle_hazir(istemci)
        yonetici = await giris(istemci, YONETICI)
        operator = await giris(istemci, OPERATOR)
        izleyici = await giris(istemci, IZLEYICI)

        async def put(govde, jeton=yonetici):
            yanit = await istemci.put(
                f"{TABAN}/ayarlar", headers=basliklar(jeton), json=govde
            )
            yaz(f"PUT /ayarlar {govde!r}", ozet(yanit))
            return yanit

        await put({})  # boş gövde
        await put(
            {
                "marka_adi": "Gözlem A.Ş.",
                "saklama_gun": 30,
                "maskeleme_aktif": False,
                "kayit_acik": True,
                "smtp_host": "smtp.gozlem.example.com",
                "smtp_port": 587,
                "smtp_kullanici": "gozlem",
                "smtp_sifre": SIFRE,
                "smtp_gonderen": "KutyAI <bildirim@gozlem.example.com>",
                "smtp_tls": True,
                "bakim_modu": False,
            }
        )

        get_ayarlar = await istemci.get(f"{TABAN}/ayarlar", headers=basliklar(yonetici))
        yaz("GET /ayarlar (ham)", f"HTTP {get_ayarlar.status_code}\n{get_ayarlar.text}")
        yaz("GET /ayarlar içinde SMTP parolası var mı?", repr(SIFRE in get_ayarlar.text))
        yaz("GET /ayarlar alanları", repr(sorted(get_ayarlar.json().keys())))

        baglanti = sqlite3.connect(DB)
        yaz(
            "SQL: smtp_sifre ham değeri",
            repr(baglanti.execute("SELECT deger FROM ayar WHERE anahtar='smtp_sifre'").fetchone()),
        )
        yaz(
            "SQL: smtp ile ilgili ayarlar",
            repr(
                baglanti.execute(
                    "SELECT anahtar, substr(deger,1,60) FROM ayar WHERE anahtar LIKE 'smtp%'"
                ).fetchall()
            ),
        )
        baglanti.close()

        # --- sınır değerler ---
        await put({"saklama_gun": 0})
        await put({"saklama_gun": 3651})
        await put({"saklama_gun": 3650})
        await put({"marka_adi": ""})
        await put({"smtp_port": 0})
        await put({"smtp_port": 70000})
        await put({"bilinmeyen_alan": "x", "kayit_acik": False})
        await put({"smtp_sifre": ""})  # temizleme

        baglanti = sqlite3.connect(DB)
        yaz(
            "SQL: smtp_sifre temizleme sonrası",
            repr(baglanti.execute("SELECT deger FROM ayar WHERE anahtar='smtp_sifre'").fetchone()),
        )
        baglanti.close()

        # şifreyi geri koy (bakım modu testinden sonra denetim izi incelemesi için)
        await put({"smtp_sifre": SIFRE})

        # --- yetkiler ---
        op_ayar = await istemci.get(f"{TABAN}/ayarlar", headers=basliklar(operator))
        yaz("GET /ayarlar (operator)", ozet(op_ayar))
        iz_ayar = await istemci.put(
            f"{TABAN}/ayarlar", headers=basliklar(izleyici), json={"marka_adi": "X"}
        )
        yaz("PUT /ayarlar (izleyici)", ozet(iz_ayar))
        anonim = await istemci.get(f"{TABAN}/ayarlar")
        yaz("GET /ayarlar (jetonsuz)", ozet(anonim))

        # --- marka adı /saglik/kurulum'a yansıyor mu? ---
        saglik = await istemci.get(f"{TABAN}/saglik/kurulum")
        yaz("GET /saglik/kurulum (marka sonrası)", ozet(saglik))

        # --- bakım modu ---
        await put({"bakim_modu": True})
        bakim_get = await istemci.get(f"{TABAN}/ayarlar", headers=basliklar(yonetici))
        yaz("GET /ayarlar (bakım açık)", ozet(bakim_get))

        sohbet = await istemci.post(
            f"{TABAN}/sohbet",
            headers=basliklar(yonetici),
            json={"bdm_id": 1, "mesaj": "Bakım modunda mıyız?"},
        )
        yaz("POST /sohbet (bakım açık)", ozet(sohbet))
        modeller = await istemci.get(f"{TABAN}/modeller", headers=basliklar(yonetici))
        yaz("GET /modeller (bakım açık)", ozet(modeller))
        loglar = await istemci.get(f"{TABAN}/loglar/konusmalar", headers=basliklar(yonetici))
        yaz("GET /loglar/konusmalar (bakım açık)", ozet(loglar))

        await put({"bakim_modu": False})

        # --- denetim izi ---
        baglanti = sqlite3.connect(DB)
        yaz(
            "SQL: ayar.guncellendi denetim kayıtları",
            "\n".join(
                f"id={r[0]} kullanici_id={r[1]} ayrinti={r[2]}"
                for r in baglanti.execute(
                    "SELECT id, kullanici_id, ayrinti FROM islem_kaydi "
                    "WHERE eylem='ayar.guncellendi' ORDER BY id"
                ).fetchall()
            ),
        )
        yaz(
            "SQL: denetim izinde SMTP parolası geçiyor mu?",
            repr(
                baglanti.execute(
                    "SELECT count(*) FROM islem_kaydi WHERE ayrinti LIKE ?", (f"%{SIFRE}%",)
                ).fetchone()
            ),
        )
        baglanti.close()


asyncio.run(main())
