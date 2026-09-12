"""Ortam hazırlık sondası: backend sağlık + kurulum durumu."""

import json
import sys

import httpx

TABAN = "http://localhost:8107/api/v1"


def main() -> int:
    with httpx.Client(timeout=10.0) as istemci:
        for yol in ("/saglik", "/saglik/kurulum"):
            y = istemci.get(f"{TABAN}{yol}")
            print(f"GET {yol} -> {y.status_code} {y.text[:400]}")
        # kayıt açık mı? sahte kayıt denemesi
        y = istemci.post(
            f"{TABAN}/kimlik/kayit",
            json={"eposta": "sonda@ornek.com", "ad_soyad": "Sonda", "parola": "parola1234"},
        )
        print(f"POST /kimlik/kayit -> {y.status_code} {y.text[:600]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
