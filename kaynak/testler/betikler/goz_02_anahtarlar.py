"""Gözlem #3/#4 — API anahtarı sızması, iptal ve izinli_modeller doğrulaması."""

from __future__ import annotations

import asyncio
import re
import sqlite3

import httpx

from goz_ortak import PAROLA, TABAN, baglan, basliklar, bekle_hazir, giris, ozet, yaz

YONETICI = "goz-yonetici-1@gozlem.example.com"


async def kullanici_olustur(istemci, jeton, eposta, rol):
    yanit = await istemci.post(
        f"{TABAN}/kullanicilar",
        headers=basliklar(jeton),
        json={"eposta": eposta, "ad_soyad": f"Goz {rol}", "parola": PAROLA, "rol": rol},
    )
    yaz(f"POST /kullanicilar rol={rol}", ozet(yanit))
    return yanit


def kuty_gecenler(metin: str) -> list[str]:
    return re.findall(r"kuty_[A-Za-z0-9]{8,}", metin)


async def main() -> None:
    async with httpx.AsyncClient(timeout=30) as istemci:
        await bekle_hazir(istemci)
        yonetici = await giris(istemci, YONETICI)

        # --- personel hesapları ---
        await kullanici_olustur(istemci, yonetici, "goz-operator@gozlem.example.com", "operator")
        await kullanici_olustur(istemci, yonetici, "goz-izleyici@gozlem.example.com", "izleyici")
        operator = await giris(istemci, "goz-operator@gozlem.example.com")
        izleyici = await giris(istemci, "goz-izleyici@gozlem.example.com")

        # --- bir BDM'i 'hazir' yap (SQL ile, canlı DB) ---
        baglanti = baglan("goz_loglar")
        baglanti.execute("UPDATE bdm SET durum='hazir' WHERE id=1")
        baglanti.execute(
            "INSERT INTO bdm (slug, gorunen_ad, aciklama, saglayici, temel_url, "
            "upstream_model, baglam_penceresi, maks_cikti, sicaklik_varsayilan, "
            "sistem_istemi, yetenekler, durum, yerel_mi, olusturulma, guncellenme) "
            "VALUES ('goz-ikinci-model','Goz Ikinci Model','','ollama',"
            "'http://127.0.0.1:11434/v1','llama3',8192,2048,0.7,'',"
            "'{\"akis\":true,\"gorsel\":false,\"arac\":false}','hazir',1,"
            "datetime('now'),datetime('now'))"
        )
        baglanti.commit()
        yaz(
            "SQL: BDM durumları",
            repr(baglanti.execute("SELECT id,slug,durum FROM bdm ORDER BY id").fetchall()),
        )
        baglanti.close()

        # --- 1) anahtar oluştur ---
        olustur = await istemci.post(
            f"{TABAN}/api-anahtarlari",
            headers=basliklar(yonetici),
            json={"ad": "Goz Anahtar", "izinli_modeller": ["yaris-model-1"]},
        )
        yaz("POST /api-anahtarlari (geçerli)", ozet(olustur))
        anahtar_kaydi = olustur.json()
        anahtar_id = anahtar_kaydi["id"]
        tam = anahtar_kaydi.get("tam_anahtar", "")
        yaz(
            "Oluşturma yanıtında kuty_ geçenler",
            repr(kuty_gecenler(olustur.text)),
        )

        # --- 2) liste sızması ---
        liste = await istemci.get(f"{TABAN}/api-anahtarlari", headers=basliklar(yonetici))
        yaz("GET /api-anahtarlari (ham)", liste.text)
        yaz(
            "Liste yanıtında kuty_ geçenler",
            repr(kuty_gecenler(liste.text)),
        )
        yaz(
            "Tam anahtar listede var mı?",
            repr(tam in liste.text),
        )
        yaz(
            "Liste alanları",
            repr(sorted(liste.json()[0].keys())) if liste.json() else "boş",
        )

        # --- 3) geçersiz model slug ---
        gecersiz = await istemci.post(
            f"{TABAN}/api-anahtarlari",
            headers=basliklar(yonetici),
            json={"ad": "Gecersiz Model", "izinli_modeller": ["yok-boyle-model"]},
        )
        yaz("POST /api-anahtarlari izinli_modeller=[yok-boyle-model]", ozet(gecersiz))

        gecersiz2 = await istemci.post(
            f"{TABAN}/api-anahtarlari",
            headers=basliklar(yonetici),
            json={"ad": "Gecersiz Karma", "izinli_modeller": ["yaris-model-1", "yok-2"]},
        )
        yaz("POST /api-anahtarlari izinli_modeller=[gecerli,yok-2]", ozet(gecersiz2))

        gecersiz3 = await istemci.post(
            f"{TABAN}/api-anahtarlari",
            headers=basliklar(yonetici),
            json={"ad": "Gecersiz Sayisal", "izinli_modeller": ["999999"]},
        )
        yaz("POST /api-anahtarlari izinli_modeller=[999999]", ozet(gecersiz3))

        # --- 4) anahtarla /modeller (izinli süzme) ---
        modeller = await istemci.get(
            f"{TABAN}/modeller", headers={"Authorization": f"Bearer {tam}"}
        )
        yaz("GET /modeller anahtarla (izinli=[yaris-model-1])", ozet(modeller))

        # --- 5) iptal ve sonrası ---
        iptal = await istemci.post(
            f"{TABAN}/api-anahtarlari/{anahtar_id}/iptal", headers=basliklar(yonetici)
        )
        yaz("POST /api-anahtarlari/{id}/iptal", ozet(iptal))

        iptal_sonrasi_modeller = await istemci.get(
            f"{TABAN}/modeller", headers={"Authorization": f"Bearer {tam}"}
        )
        yaz("GET /modeller iptal sonrası", ozet(iptal_sonrasi_modeller))

        iptal_sonrasi_sohbet = await istemci.post(
            f"{TABAN}/sohbet",
            headers={"Authorization": f"Bearer {tam}"},
            json={"bdm_id": 1, "mesaj": "Merhaba"},
        )
        yaz("POST /sohbet iptal sonrası", ozet(iptal_sonrasi_sohbet))

        iptal_sonrasi_liste = await istemci.get(f"{TABAN}/api-anahtarlari", headers=basliklar(yonetici))
        yaz("GET /api-anahtarlari iptal sonrası (durum)", ozet(iptal_sonrasi_liste))

        # --- 6) rol/yetki gözlemi ---
        izleyici_anahtar = await istemci.post(
            f"{TABAN}/api-anahtarlari",
            headers=basliklar(izleyici),
            json={"ad": "Izleyici Anahtari"},
        )
        yaz("POST /api-anahtarlari (izleyici ile)", ozet(izleyici_anahtar))

        operator_anahtar = await istemci.post(
            f"{TABAN}/api-anahtarlari",
            headers=basliklar(operator),
            json={"ad": "Operator Anahtari"},
        )
        yaz("POST /api-anahtarlari (operator ile)", ozet(operator_anahtar))

        anonim = await istemci.get(f"{TABAN}/api-anahtarlari")
        yaz("GET /api-anahtarlari (jetonsuz)", ozet(anonim))

        # --- 7) yok olan anahtarın iptali ---
        yok = await istemci.post(
            f"{TABAN}/api-anahtarlari/999999/iptal", headers=basliklar(yonetici)
        )
        yaz("POST /api-anahtarlari/999999/iptal", ozet(yok))

    baglanti = sqlite3.connect("E:/kutyai-app/kaynak/testler/gecici/goz_loglar.db")
    yaz(
        "SQL: api_anahtari (ham)",
        repr(
            baglanti.execute(
                "SELECT id, ad, onek, son_dort, durum, izinli_modeller, substr(anahtar_hash,1,12) "
                "FROM api_anahtari ORDER BY id"
            ).fetchall()
        ),
    )
    baglanti.close()


asyncio.run(main())
