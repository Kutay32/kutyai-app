"""Ortak yardimcilar: canli backend'e HTTP istemcisi ve ham cikti yazdirma."""

from __future__ import annotations

import json
import pathlib
import sqlite3

import httpx

KOK = pathlib.Path(__file__).resolve().parents[3]
GECICI = KOK / "kaynak" / "testler" / "gecici"
DB = GECICI / "modeller.db"
TABAN = "http://127.0.0.1:8102/api/v1"
TOKEN_DOSYASI = GECICI / "oturum.json"

ADMIN_EPOSTA = "admin@gozlem.example.com"
ADMIN_PAROLA = "gozlem-parola-123"
OPERATOR_EPOSTA = "operator@gozlem.example.com"
SON_EPOSTA = "son@gozlem.example.com"
ORTAK_PAROLA = "gozlem-parola-123"
UPSTREAM_ANAHTAR = "sk-cokgizli-GOZLEM-1234567890"


def istemci(jeton: str | None = None) -> httpx.Client:
    basliklar = {"Authorization": f"Bearer {jeton}"} if jeton else {}
    return httpx.Client(base_url=TABAN, timeout=30.0, headers=basliklar)


def yaz(baslik: str, yanit: httpx.Response) -> None:
    """Ham HTTP ciktisini degistirmeden yazdirir."""
    print(f"--- {baslik}")
    print(f"HTTP {yanit.status_code}")
    try:
        print(json.dumps(yanit.json(), ensure_ascii=False, indent=2))
    except Exception:
        print(repr(yanit.text))
    print()


def jetonlari_oku() -> dict[str, str]:
    return json.loads(TOKEN_DOSYASI.read_text(encoding="utf-8"))


def sql(ifade: str, parametreler: tuple[object, ...] = ()) -> list[tuple[object, ...]]:
    """Gecici SQLite veritabaninda dogrudan sorgu (yalniz test fiksturu)."""
    baglanti = sqlite3.connect(DB)
    try:
        imlec = baglanti.execute(ifade, parametreler)
        satirlar = imlec.fetchall()
        baglanti.commit()
        return satirlar
    finally:
        baglanti.close()
