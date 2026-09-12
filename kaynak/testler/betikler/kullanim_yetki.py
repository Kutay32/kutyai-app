"""Kullanım uçlarının yetki kanıtı: son_kullanici jetonuyla 403.

Jetonsuz 401, son kullanıcıyla 403 döner. Bu betik sonucu ham basar.
"""

from __future__ import annotations

import sys

import httpx

TABAN = "http://localhost:8107/api/v1"


def main() -> int:
    with httpx.Client(timeout=15.0) as istemci:
        giris = istemci.post(
            f"{TABAN}/kimlik/giris",
            json={"eposta": "goz.onuc.2@ornek.com", "parola": "yeniParola99"},
        )
        print("POST /kimlik/giris ->", giris.status_code)
        if giris.status_code != 200:
            print(giris.text[:300])
            return 1
        veri = giris.json()
        basliklar = {"Authorization": f"Bearer {veri['erisim_jetonu']}"}
        print("giris rolu:", veri["kullanici"]["rol"])
        for yol in ("/kullanim/ozet?gun=30", "/kullanim/zaman-serisi?gun=30&kirilim=bdm", "/kimlik/ben"):
            y = istemci.get(f"{TABAN}{yol}", headers=basliklar)
            print(f"GET {yol} -> {y.status_code} {y.text[:200]}")
        # personel olmayan jetonla /kullanim denemesi
        return 0


if __name__ == "__main__":
    sys.exit(main())
