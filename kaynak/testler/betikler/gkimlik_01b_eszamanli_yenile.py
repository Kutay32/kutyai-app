"""1b) Eszamanli refresh: ayni jetonla 5 paralel cagri cift kullanima yol acar mi?"""

from __future__ import annotations

import asyncio
import sys

import httpx

sys.path.insert(0, "E:/kutyai-app/kaynak/testler/betikler")
from gkimlik_ortak import *  # noqa: E402

EPOSTA = yeni_eposta("goz-es")
with istemci() as c:
    eposta, _, _, _ = kayit_ve_dogrula(c, EPOSTA)
    _, b0 = giris(c, eposta)
yenileme = b0["yenileme_jetonu"]
print(f"### hazirlik: {eposta} girisi tamam, yenileme jetonu = {kisalt(yenileme)}")


async def main() -> None:
    async with httpx.AsyncClient(base_url=TABAN, timeout=60.0) as ac:
        gorevler = [
            ac.post("/kimlik/yenile", json={"yenileme_jetonu": yenileme}) for _ in range(5)
        ]
        yanitlar = await asyncio.gather(*gorevler, return_exceptions=True)
    for i, y in enumerate(yanitlar):
        if isinstance(y, Exception):
            print(f"### eszamanli {i}: ISTISNA {type(y).__name__}: {y}")
        else:
            print(f"### eszamanli {i}: durum={y.status_code} govde={govde(y)}")


asyncio.run(main())
print("### oturum tablosu (son 10)")
for satir in sql(
    "select o.id, o.iptal, o.olusturulma from oturum o join kullanici k on k.id=o.kullanici_id "
    "where k.eposta=? order by o.id",
    (EPOSTA,),
):
    print(satir)
