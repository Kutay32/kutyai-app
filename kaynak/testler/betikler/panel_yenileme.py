"""Yenileme jetonu rotasyonunu ve panelin çoklu yenileme yarışını kanıtlar.

Kullanım: ./.venv/Scripts/python.exe kaynak/testler/betikler/panel_yenileme.py
"""
from __future__ import annotations

import json
import sys

import httpx

TABAN = "http://localhost:8108/api/v1"


def main() -> int:
    cikti: dict[str, object] = {}
    with httpx.Client(base_url=TABAN, timeout=20.0) as istemci:
        giris = istemci.post(
            "/kimlik/panel-giris",
            json={"eposta": "admin@acme.com", "parola": "parola1234"},
        )
        govde = giris.json()
        cikti["giris"] = {"durum": giris.status_code, "rol": govde["kullanici"]["rol"]}
        yenileme = govde["yenileme_jetonu"]

        ilk = istemci.post("/kimlik/yenile", json={"yenileme_jetonu": yenileme})
        cikti["yenile_1"] = {"durum": ilk.status_code, "erisim_var": "erisim_jetonu" in ilk.json()}

        # Aynı (artık döndürülmüş) yenileme jetonuyla ikinci deneme
        ikinci = istemci.post("/kimlik/yenile", json={"yenileme_jetonu": yenileme})
        cikti["yenile_2_ayni_jeton"] = {"durum": ikinci.status_code, "govde": ikinci.json()}

        # Panelin bozuk erişim jetonu senaryosunda kullanacağı taze çift
        taze = ikinci if ikinci.status_code == 200 else ilk
        if taze.status_code == 200:
            yeni_yenileme = taze.json()["yenileme_jetonu"]
            erisim = taze.json()["erisim_jetonu"]
            cikti["erisim_ornek"] = erisim[:24] + "..."
            cikti["yenileme_ornek"] = yeni_yenileme[:16] + "..."

    print(json.dumps(cikti, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
