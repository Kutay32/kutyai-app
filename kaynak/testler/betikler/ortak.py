"""Bağımsız gözlem betikleri için ortak yardımcılar.

Ürün koduna dokunmaz; yalnızca canlı HTTP + doğrudan SQLite okuması yapar.
"""

from __future__ import annotations

import json
import pathlib
import sqlite3
import time
from typing import Any

import httpx

KOK = pathlib.Path(__file__).resolve().parents[3]
GECICI = KOK / "kaynak" / "testler" / "gecici"
GECICI.mkdir(parents=True, exist_ok=True)
DB = GECICI / "yonetim.db"
ORTAM = GECICI / "ortam.json"

BASE = "http://127.0.0.1:8104/api/v1"
UC = f"{BASE}/bdm/yonetim"

EPOSTA = "goz@kutyai.example.com"
PAROLA = "Parola123!"


def istemci(timeout: float = 30.0) -> httpx.Client:
    return httpx.Client(base_url=BASE, timeout=timeout)


def kurulum_yap() -> dict[str, Any]:
    """Kurulum sihirbazını çalıştırıp yönetici jetonunu döndürür."""
    govde = {
        "marka_adi": "Gözlem",
        "yonetici": {"eposta": EPOSTA, "ad_soyad": "Gözlem Yönetici", "parola": PAROLA},
        "bdm": {
            "gorunen_ad": "Gözlem Ollama",
            "saglayici": "ollama",
            "temel_url": "http://localhost:11434/v1",
            "upstream_model": "llama3",
            "api_anahtari": "",
            "yerel_mi": True,
            "sistem_istemi": "",
        },
        "dogrula": False,
    }
    with istemci() as c:
        yanit = c.post("/kurulum", json=govde)
        if yanit.status_code == 409:
            print("kurulum zaten tamam (409); mevcut yönetici ile devam ediliyor.")
            return {"kullanici": {}, "jeton": _giris()}
        yanit.raise_for_status()
        veri = yanit.json()
    return {"kullanici": veri["yonetici"], "jeton": _giris()}


def _giris() -> str:
    with istemci() as c:
        yanit = c.post("/kimlik/panel-giris", json={"eposta": EPOSTA, "parola": PAROLA})
        yanit.raise_for_status()
        return yanit.json()["erisim_jetonu"]


def jeton_al() -> str:
    if ORTAM.exists():
        kayit = json.loads(ORTAM.read_text(encoding="utf-8"))
        if kayit.get("jeton"):
            return str(kayit["jeton"])
    return _giris()


def basliklar(jeton: str | None = None) -> dict[str, str]:
    return {"Authorization": f"Bearer {jeton or jeton_al()}"}


def bdm_olustur(
    gorunen_ad: str,
    saglayici: str,
    *,
    temel_url: str = "",
    upstream_model: str = "llama3",
    yerel_mi: bool | None = None,
    jeton: str | None = None,
) -> dict[str, Any]:
    govde = {
        "gorunen_ad": gorunen_ad,
        "saglayici": saglayici,
        "temel_url": temel_url,
        "upstream_model": upstream_model,
        "yerel_mi": yerel_mi,
    }
    with istemci() as c:
        yanit = c.post("/bdm", json=govde, headers=basliklar(jeton))
    if yanit.status_code >= 400:
        raise RuntimeError(f"BDM oluşturulamadı: {yanit.status_code} {yanit.text}")
    return yanit.json()


def durum_yaz(bdm_id: int, durum: str) -> None:
    """Ön koşul düzenlemesi: durumu doğrudan veritabanında ayarlar."""
    with sqlite3.connect(DB) as baglanti:
        baglanti.execute("UPDATE bdm SET durum = ? WHERE id = ?", (durum, bdm_id))
        baglanti.commit()


def sql(sorgu: str, parametreler: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
    with sqlite3.connect(DB) as baglanti:
        return list(baglanti.execute(sorgu, parametreler).fetchall())


def bdm_satiri(bdm_id: int) -> dict[str, Any] | None:
    satirlar = sql("SELECT durum, konteyner, saglayici, yerel_mi FROM bdm WHERE id = ?", (bdm_id,))
    if not satirlar:
        return None
    durum, konteyner, saglayici, yerel_mi = satirlar[0]
    return {
        "durum": durum,
        "konteyner": json.loads(konteyner) if konteyner else None,
        "saglayici": saglayici,
        "yerel_mi": bool(yerel_mi),
    }


def baslik(metin: str) -> None:
    print(f"\n===== {metin} =====", flush=True)


def goster(etiket: str, yanit: httpx.Response) -> None:
    govde = yanit.text
    if len(govde) > 700:
        govde = govde[:700] + "...<kırpıldı>"
    print(f"[{etiket}] HTTP {yanit.status_code} {govde}", flush=True)


def bekle(kosul, *, zaman_asimi: float = 20.0, aralik: float = 0.5) -> bool:
    bitis = time.time() + zaman_asimi
    while time.time() < bitis:
        if kosul():
            return True
        time.sleep(aralik)
    return False
