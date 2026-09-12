"""Gözlem #6 (ek) — dışa aktarım uç durumları: boş konuşma, CSV kaçışlama/formül enjeksiyonu."""

from __future__ import annotations

import asyncio
import sqlite3

import httpx

from goz_ortak import TABAN, basliklar, bekle_hazir, giris, ozet, yaz

YONETICI = "goz-yonetici-1@gozlem.example.com"
DB = "E:/kutyai-app/kaynak/testler/gecici/goz_loglar.db"


def tohumla() -> None:
    baglanti = sqlite3.connect(DB)
    kid = baglanti.execute("SELECT coalesce(max(id),0)+1 FROM konusma").fetchone()[0]
    baglanti.execute("DELETE FROM konusma WHERE baslik IN ('Mesajsız konuşma','Kaçış testi')")
    kid = baglanti.execute("SELECT coalesce(max(id),0)+1 FROM konusma").fetchone()[0]
    baglanti.execute(
        "INSERT INTO konusma (id, kullanici_id, api_anahtari_id, bdm_id, baslik, "
        "sistem_istemi, token_girdi, token_cikti, arsivlendi, olusturulma, guncellenme) "
        f"VALUES ({kid},1,NULL,1,'Mesajsız konuşma','',0,0,0,'2026-09-12 08:00:00.000000',"
        "'2026-09-12 08:00:00.000000')"
    )
    kid2 = kid + 1
    baglanti.execute(
        "INSERT INTO konusma (id, kullanici_id, api_anahtari_id, bdm_id, baslik, "
        "sistem_istemi, token_girdi, token_cikti, arsivlendi, olusturulma, guncellenme) "
        f"VALUES ({kid2},1,NULL,1,'Kaçış testi','',1,1,0,'2026-09-12 08:05:00.000000',"
        "'2026-09-12 08:05:00.000000')"
    )
    mid = baglanti.execute("SELECT coalesce(max(id),0)+1 FROM mesaj").fetchone()[0]
    baglanti.execute(
        "INSERT INTO mesaj (id, konusma_id, rol, icerik, token_sayisi, gecikme_ms, model, hata, "
        f"olusturulma) VALUES ({mid},{kid2},'kullanici',"
        "'=HYPERLINK(\"http://kotu.example\",\"tıkla\")',1,0,'llama3',NULL,"
        "'2026-09-12 08:05:00.000000')"
    )
    baglanti.execute(
        "INSERT INTO mesaj (id, konusma_id, rol, icerik, token_sayisi, gecikme_ms, model, hata, "
        f"olusturulma) VALUES ({mid + 1},{kid2},'asistan',"
        "'İki satır;\nvirgüllü, \"alıntılı\" yanıt',1,0,'llama3',NULL,"
        "'2026-09-12 08:05:01.000000')"
    )
    baglanti.commit()
    baglanti.close()
    print(f"ek konuşmalar eklendi: {kid} (mesajsız), {kid2} (kaçış)")
    with open("goz_06_id.txt", "w", encoding="utf-8") as dosya:
        dosya.write(f"{kid} {kid2}")


async def main() -> None:
    tohumla()
    kid, kid2 = (int(x) for x in open("goz_06_id.txt", encoding="utf-8").read().split())
    async with httpx.AsyncClient(timeout=30) as istemci:
        await bekle_hazir(istemci)
        jeton = await giris(istemci, YONETICI)
        for hedef in (kid, kid2):
            for bicim in ("json", "md", "csv"):
                yanit = await istemci.get(
                    f"{TABAN}/loglar/konusmalar/{hedef}/disa-aktar?bicim={bicim}",
                    headers=basliklar(jeton),
                )
                yaz(
                    f"disa-aktar konusma={hedef} bicim={bicim}",
                    f"HTTP {yanit.status_code}\n"
                    f"content-disposition={yanit.headers.get('content-disposition')}\n"
                    f"bytes={len(yanit.content)}\n--- içerik ---\n{yanit.text}",
                )
        yok = await istemci.get(
            f"{TABAN}/loglar/konusmalar/999/disa-aktar?bicim=csv", headers=basliklar(jeton)
        )
        yaz("disa-aktar olmayan konuşma", ozet(yok))


asyncio.run(main())
