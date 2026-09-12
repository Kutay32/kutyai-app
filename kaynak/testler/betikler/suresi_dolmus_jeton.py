"""Süresi geçmiş ama imzası geçerli bir erişim jetonu üretir (401 yenileme senaryosu).

Kullanım:
    python kaynak/testler/betikler/suresi_dolmus_jeton.py <kullanici_id> <rol>
"""

import sys
from datetime import datetime, timedelta, timezone

import jwt

GIZLI = "gozlem-gizli-anahtar"


def main() -> int:
    kullanici_id = sys.argv[1] if len(sys.argv) > 1 else "2"
    rol = sys.argv[2] if len(sys.argv) > 2 else "son_kullanici"
    simdi = datetime.now(timezone.utc)
    govde = {
        "sub": str(kullanici_id),
        "rol": rol,
        "jti": "gozlem-suresi-dolmus",
        "tur": "erisim",
        "iat": int((simdi - timedelta(hours=3)).timestamp()),
        "exp": int((simdi - timedelta(hours=2)).timestamp()),
    }
    print(jwt.encode(govde, GIZLI, algorithm="HS256"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
