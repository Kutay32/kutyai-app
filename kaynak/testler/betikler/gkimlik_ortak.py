"""GozKimlik gozlem betikleri icin ortak yardimcilar (kimlik modulu).

NOT: Bu dosya `kaynak/testler/betikler/` altinda birden fazla gozlemci ajan
calistigi icin `gkimlik_` onekiyle adlandirilmistir.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from urllib.parse import parse_qs, urlparse

import httpx

TABAN = "http://127.0.0.1:8101/api/v1"
DB = "E:/kutyai-app/kaynak/testler/gecici/kimlik-gozlem.db"
PAROLA = "Parola123!"


def istemci(**kwargs) -> httpx.Client:
    return httpx.Client(base_url=TABAN, timeout=30.0, **kwargs)


def govde(yanit: httpx.Response):
    try:
        return yanit.json()
    except Exception:
        return {"_ham": yanit.text[:2000]}


def yaz(baslik: str, deger) -> None:
    print(f"### {baslik}")
    print(json.dumps(deger, ensure_ascii=False, indent=2))


def jeton_baglantidan(baglanti: str) -> str:
    return parse_qs(urlparse(baglanti).query).get("jeton", [""])[0]


def yeni_eposta(on_ek: str = "goz") -> str:
    return f"{on_ek}-{uuid.uuid4().hex[:10]}@ornek.com"


def kayit_ve_dogrula(
    c: httpx.Client,
    eposta: str | None = None,
    *,
    parola: str = PAROLA,
    ad: str = "Gozlem Kullanici",
):
    """Kayit + e-posta dogrulama; (eposta, dogrulama_jetonu, kayit_yaniti, dogrula_yaniti)."""
    eposta = eposta or yeni_eposta()
    r = c.post(
        "/kimlik/kayit",
        json={"eposta": eposta, "ad_soyad": ad, "parola": parola},
    )
    b = govde(r)
    if r.status_code != 201 or not b.get("gelistirme_baglantisi"):
        return eposta, None, r, b
    jeton = jeton_baglantidan(b["gelistirme_baglantisi"])
    d = c.post("/kimlik/dogrula", json={"jeton": jeton})
    return eposta, jeton, r, govde(d)


def giris(c: httpx.Client, eposta: str, parola: str = PAROLA, *, panel: bool = False):
    yol = "/kimlik/panel-giris" if panel else "/kimlik/giris"
    r = c.post(yol, json={"eposta": eposta, "parola": parola})
    return r, govde(r)


def sql(sorgu: str, params: tuple = ()) -> list[dict]:
    with sqlite3.connect(DB, timeout=30) as baglanti:
        baglanti.row_factory = sqlite3.Row
        return [dict(satir) for satir in baglanti.execute(sorgu, params).fetchall()]


def sql_yaz(sorgu: str, params: tuple = ()) -> None:
    with sqlite3.connect(DB, timeout=30) as baglanti:
        baglanti.execute(sorgu, params)
        baglanti.commit()


def yetki(jeton: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {jeton}"}


def kisalt(deger: str | None, n: int = 12) -> str | None:
    if deger is None:
        return None
    return deger if len(deger) <= n * 2 else f"{deger[:n]}...{deger[-n:]}"
