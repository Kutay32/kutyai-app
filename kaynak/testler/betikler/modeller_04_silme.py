"""Curburtme 4: DELETE /bdm/{id} — calisan BDM ve konusmasi olan BDM."""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _ortak import istemci, jetonlari_oku, sql, yaz  # noqa: E402

k = jetonlari_oku()
a = istemci(k["admin"])
KISITLI = istemci(k["anahtar_tek_slug"])


def tablo(baslik: str) -> None:
    print(f"--- {baslik}")
    print(
        json.dumps(
            sql(
                "SELECT k.id, k.bdm_id, k.baslik, (SELECT COUNT(*) FROM mesaj m WHERE m.konusma_id = k.id) "
                "FROM konusma k ORDER BY k.id"
            ),
            ensure_ascii=False,
            indent=2,
        )
    )
    print(json.dumps(sql("SELECT id, slug, durum FROM bdm ORDER BY id"), ensure_ascii=False, indent=2))
    print()


yaz("DELETE /bdm/6 (durum=calisiyor)", a.delete("/bdm/6"))

# 2 numarali (hazir) BDM icin konusma olustur: kisitli anahtar izinli
yaz(
    "POST /sohbet bdm_id=2 (konusma uretir)",
    KISITLI.post("/sohbet", json={"bdm_id": k["bdm"]["musteri"], "mesaj": "silme testi"}),
)
tablo("SILME ONCESI: konusma / bdm tablolari")

yaz("DELETE /bdm/2 (konusmasi olan BDM)", a.delete("/bdm/2"))
tablo("SILME SONRASI: konusma / bdm tablolari")

print("--- yetim (orphan) konusma satirlari: bdm_id'si olmayan")
print(
    json.dumps(
        sql(
            "SELECT k.id, k.bdm_id FROM konusma k LEFT JOIN bdm b ON b.id = k.bdm_id WHERE b.id IS NULL"
        ),
        ensure_ascii=False,
        indent=2,
    )
)
print()

yaz("DELETE /bdm/3 (taslak, iliskisiz BDM)", a.delete("/bdm/3"))

print("--- PRAGMA foreign_keys (uygulamanin kullandigi motor ile)")
import asyncio  # noqa: E402

import sqlalchemy as sa  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

motor = create_async_engine("sqlite+aiosqlite:///E:/kutyai-app/kaynak/testler/gecici/modeller.db")


async def pragma_oku() -> None:
    async with motor.connect() as baglanti:
        sonuc = await baglanti.execute(sa.text("PRAGMA foreign_keys"))
        print(f"PRAGMA foreign_keys = {sonuc.scalar()}")
    await motor.dispose()


asyncio.run(pragma_oku())
