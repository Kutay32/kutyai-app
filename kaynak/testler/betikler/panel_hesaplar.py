"""Panel giriş senaryoları için test hesapları oluşturur (gözlem yardımcı betiği).

Kullanım: ./.venv/Scripts/python.exe kaynak/testler/betikler/panel_hesaplar.py
"""
from __future__ import annotations

import json
import sys

import httpx

TABAN = "http://localhost:8108/api/v1"


def main() -> int:
    cikti: dict[str, object] = {}
    with httpx.Client(base_url=TABAN, timeout=20.0) as istemci:
        # 1) Doğrulanmamış son kullanıcı
        cevap = istemci.post(
            "/kimlik/kayit",
            json={"eposta": "gozlem-dogrulanmamis@ornek.com", "ad_soyad": "Gozlem Dogrulanmamis", "parola": "parola1234"},
        )
        cikti["kayit_dogrulanmamis"] = {"durum": cevap.status_code, "govde": cevap.json()}

        # 2) Doğrulanmış son kullanıcı (gelistirme baglantisi ile)
        cevap2 = istemci.post(
            "/kimlik/kayit",
            json={"eposta": "gozlem-sonkullanici@ornek.com", "ad_soyad": "Gozlem Son Kullanici", "parola": "parola1234"},
        )
        govde2 = cevap2.json()
        cikti["kayit_son_kullanici"] = {"durum": cevap2.status_code, "govde": govde2}
        baglanti = govde2.get("gelistirme_baglantisi") or ""
        jeton = baglanti.rsplit("jeton=", 1)[-1] if "jeton=" in baglanti else ""
        cevap3 = istemci.post("/kimlik/dogrula", json={"jeton": jeton})
        cikti["dogrula"] = {"durum": cevap3.status_code, "govde": cevap3.json() if cevap3.content else None}
        cikti["dogrulama_jetonu"] = jeton

    print(json.dumps(cikti, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
