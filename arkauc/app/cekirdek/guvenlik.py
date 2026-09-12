"""Guvenlik yardimcilari: sifre ozeti, JWT, Fernet, API anahtari (spec §11)."""

from __future__ import annotations

import hashlib
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError, VerificationError
from cryptography.fernet import Fernet, InvalidToken

from arkauc.app.cekirdek.ayarlar import ayarlar
from arkauc.app.cekirdek.hatalar import JetonGecersiz, JetonSuresiDoldu

_ph = PasswordHasher()

API_ONEK = "kuty_"
_ALFABE = string.ascii_letters + string.digits


def sifre_hashle(sifre: str) -> str:
    return _ph.hash(sifre)


def sifre_dogrula(sifre_hash: str, sifre: str) -> tuple[bool, bool]:
    """(dogru_mu, yeniden_hash_gerekli_mi) dondurur."""
    try:
        _ph.verify(sifre_hash, sifre)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False, False
    return True, _ph.check_needs_rehash(sifre_hash)


def rastgele_jeton(uzunluk: int = 32) -> str:
    return secrets.token_urlsafe(uzunluk)


def ozet(deger: str) -> str:
    """Geri donusturulemez ozet (jeton ve API anahtari saklamak icin)."""
    return hashlib.sha256(deger.encode("utf-8")).hexdigest()


# -- JWT ---------------------------------------------------------------------


def erisim_jetonu_uret(
    kullanici_id: int, rol: str, org_id: int | None = None
) -> tuple[str, str]:
    """(jeton, jti) dondurur. `org_id` verilirse `org` claim'i eklenir."""
    jti = rastgele_jeton(16)
    simdi = datetime.now(timezone.utc)
    govde: dict[str, Any] = {
        "sub": str(kullanici_id),
        "rol": rol,
        "jti": jti,
        "tur": "erisim",
        "iat": int(simdi.timestamp()),
        "exp": int((simdi + timedelta(minutes=ayarlar.erisim_omru_dk)).timestamp()),
    }
    if org_id is not None:
        govde["org"] = int(org_id)
    return jwt.encode(govde, ayarlar.gizli_anahtar, algorithm="HS256"), jti


def jeton_coz(jeton: str, beklenen_tur: str = "erisim") -> dict[str, Any]:
    try:
        govde = jwt.decode(jeton, ayarlar.gizli_anahtar, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as hata:
        raise JetonSuresiDoldu() from hata
    except jwt.InvalidTokenError as hata:
        raise JetonGecersiz() from hata
    if govde.get("tur") != beklenen_tur:
        raise JetonGecersiz("Jeton türü bu işlem için uygun değil.")
    return govde


# -- Fernet (upstream API anahtarlari) --------------------------------------


def _fernet() -> Fernet:
    return Fernet(ayarlar.sifreleme_anahtari.encode("utf-8"))


def sifrele(metin: str) -> str:
    return _fernet().encrypt(metin.encode("utf-8")).decode("utf-8")


def coz(sifreli: str) -> str:
    try:
        return _fernet().decrypt(sifreli.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError) as hata:
        raise JetonGecersiz("Şifreli değer çözülemedi.") from hata


def maskele(anahtar: str | None) -> str:
    """Upstream anahtarini kullaniciya gostermeden temsil eder."""
    if not anahtar:
        return ""
    if len(anahtar) <= 8:
        return "***"
    return f"{anahtar[:4]}***{anahtar[-4:]}"


# -- API anahtari ------------------------------------------------------------


def api_anahtari_uret() -> dict[str, str]:
    """Yeni API anahtari uretir. `tam` yalnizca bir kez gosterilir."""
    govde = "".join(secrets.choice(_ALFABE) for _ in range(32))
    tam = f"{API_ONEK}{govde}"
    return {
        "tam": tam,
        "onek": tam[:12],
        "hash": ozet(tam),
        "son_dort": tam[-4:],
    }
