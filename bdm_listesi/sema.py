"""BDM katalog semalari (girdi modelleri) — spec §4.5, §8.

`temel_url` dogrulanir: sunucu bu adrese istek atip cozulmus upstream API
anahtarini gonderdigi icin sema kisiti guvenlik siniridir (yalniz http/https,
bulut metadata adresleri reddedilir). `upstream_model` konteyner argv'sine
girdiginden bayrak enjeksiyonunu engelleyen desenle dogrulanir.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator

from bdm_veritabani.modeller import Saglayici

GECERLI_SEMALAR = ("http", "https")

# Bulut metadata servisleri: SSRF ile kimlik bilgisi sizdirma hedefi.
YASAKLI_KONAKLAR = ("169.254.169.254", "100.100.100.200", "metadata.google.internal")

_URL_DESENI = re.compile(r"^https?://[^\s]+$", re.IGNORECASE)
_MODEL_DESENI = re.compile(r"^[A-Za-z0-9._\-/:]{1,200}$")


def _adres_dogrula(deger: str) -> str:
    """http/https semasini ve yasakli konaklari denetler.

    Cozulemeyen (bozuk) adresler burada reddedilmez: kayit olusturulabilir ve
    saglık/ dogrulama katmani kullaniciya Turkce sonuc doner. Burada amac,
    SSRF icin kullanilabilecek sema ve bilinen metadata konaklarini kesmektir.
    """
    temiz = deger.strip()
    if not temiz:
        return temiz
    if not _URL_DESENI.match(temiz):
        raise ValueError("Temel adres http:// veya https:// ile başlamalıdır.")
    try:
        ayrilan = urlparse(temiz)
        konak = (ayrilan.hostname or "").lower()
        sema = ayrilan.scheme.lower()
    except ValueError:
        return temiz.rstrip("/")
    if sema not in GECERLI_SEMALAR:
        raise ValueError("Yalnız http ve https adresleri kullanılabilir.")
    if not konak:
        return temiz.rstrip("/")
    if konak in YASAKLI_KONAKLAR:
        raise ValueError("Bu adres güvenlik nedeniyle kullanılamaz.")
    return temiz.rstrip("/")


def _model_dogrula(deger: str) -> str:
    """Konteyner argv'sine giren model adini bayrak enjeksiyonundan korur."""
    temiz = deger.strip()
    if not temiz:
        return temiz
    if temiz.startswith("-") or not _MODEL_DESENI.match(temiz):
        raise ValueError(
            "Model adı yalnız harf, rakam ve . _ - / : karakterlerini içerebilir."
        )
    return temiz


class BdmOlustur(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    gorunen_ad: str = Field(min_length=2, max_length=160)
    slug: str | None = Field(default=None, max_length=80)
    aciklama: str = Field(default="", max_length=2000)
    saglayici: Saglayici
    temel_url: str = Field(default="", max_length=400)
    upstream_model: str = Field(default="", max_length=200)
    api_anahtari: str = Field(default="", max_length=400)
    baglam_penceresi: int = Field(default=8192, ge=128, le=2_000_000)
    maks_cikti: int = Field(default=2048, ge=16, le=200_000)
    sicaklik_varsayilan: float = Field(default=0.7, ge=0.0, le=2.0)
    sistem_istemi: str = Field(default="", max_length=8000)
    yerel_mi: bool | None = None
    yetenekler: dict[str, bool] | None = None

    @field_validator("temel_url")
    @classmethod
    def _url_temizle(cls, deger: str) -> str:
        return _adres_dogrula(deger)

    @field_validator("upstream_model")
    @classmethod
    def _model_temizle(cls, deger: str) -> str:
        return _model_dogrula(deger)


class BdmGuncelle(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    gorunen_ad: str | None = Field(default=None, min_length=2, max_length=160)
    aciklama: str | None = Field(default=None, max_length=2000)
    saglayici: Saglayici | None = None
    temel_url: str | None = Field(default=None, max_length=400)
    upstream_model: str | None = Field(default=None, max_length=200)
    api_anahtari: str | None = Field(default=None, max_length=400)
    baglam_penceresi: int | None = Field(default=None, ge=128, le=2_000_000)
    maks_cikti: int | None = Field(default=None, ge=16, le=200_000)
    sicaklik_varsayilan: float | None = Field(default=None, ge=0.0, le=2.0)
    sistem_istemi: str | None = Field(default=None, max_length=8000)
    yerel_mi: bool | None = None
    yetenekler: dict[str, bool] | None = None

    @field_validator("temel_url")
    @classmethod
    def _url_temizle(cls, deger: str | None) -> str | None:
        return _adres_dogrula(deger) if deger is not None else None

    @field_validator("upstream_model")
    @classmethod
    def _model_temizle(cls, deger: str | None) -> str | None:
        return _model_dogrula(deger) if deger is not None else None


class BdmKopyala(BaseModel):
    yeni_ad: str = Field(min_length=2, max_length=160)
    yeni_slug: str | None = Field(default=None, max_length=80)
