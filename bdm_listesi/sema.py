"""BDM katalog semalari (girdi modelleri) — spec §4.5, §8.

`temel_url` dogrulanir: sunucu bu adrese istek atip cozulmus upstream API
anahtarini gonderdigi icin sema kisiti guvenlik siniridir (yalniz http/https;
loopback/ozel/ULA/link-local/multicast adresler ile bulut metadata konaklari
reddedilir — ayrinti icin `_adres_dogrula`). `upstream_model` konteyner
argv'sine girdiginden bayrak enjeksiyonunu engelleyen desenle dogrulanir.
"""

from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator

from bdm_veritabani.modeller import Saglayici

GECERLI_SEMALAR = ("http", "https")

# Bulut metadata servisleri: SSRF ile kimlik bilgisi sizdirma hedefi.
YASAKLI_KONAKLAR = ("169.254.169.254", "100.100.100.200", "metadata.google.internal")

_URL_DESENI = re.compile(r"^https?://[^\s]+$", re.IGNORECASE)
_MODEL_DESENI = re.compile(r"^[A-Za-z0-9._\-/:]{1,200}$")
# Eski IPv4 yazimlari (`2852039166`, `0xA9FEA9FE`, `0177.0.0.1`) yalnizca
# `inet_aton` ile cozulur; bu desen onlari alan adi sayilmaktan kurtarir.
_SAYISAL_KONAK_DESENI = re.compile(r"^[0-9A-Fa-fxX.]+$")

# Cozulemeyen konak adlari: `.local` son eki Windows'ta saniyeler suren bir
# DNS beklemesi yaratir. Yalnizca BASARISIZ cozumler hatirlanir; basarili
# cozumler her seferinde yenilenir (DNS yeniden baglama karari bozmasin).
_cozulemeyen_konaklar: set[str] = set()
_COZULEMEYEN_SINIRI = 512


def _konak_normalize(konak: str) -> str:
    """Konak adini kucuk harfe indirir ve sondaki noktalari kirpar.

    Normalizasyon sart: `metadata.google.internal.` gibi tam nitelikli
    yazimlar kara listeye ancak boyle takilir.
    """
    return konak.lower().rstrip(".")


def _adres_coz(konak: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    """Konak adini sistem cozucusuyle cozumler (testler bu noktayi taklit eder)."""
    adresler: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    for bilgi in socket.getaddrinfo(konak, None):
        ham = str(bilgi[4][0]).split("%", 1)[0]  # IPv6 kapsam kimligini at
        adresler.append(ipaddress.ip_address(ham))
    return adresler


def _konak_adresleri(konak: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address] | None:
    """Konağı çözer; çözülemeyen adlar için `None` döner ve adı hatırlar."""
    if konak in _cozulemeyen_konaklar:
        return None
    try:
        return _adres_coz(konak)
    except (OSError, UnicodeError):
        if len(_cozulemeyen_konaklar) >= _COZULEMEYEN_SINIRI:  # pragma: no cover - savunma
            _cozulemeyen_konaklar.clear()
        _cozulemeyen_konaklar.add(konak)
        return None


def _ip_dene(konak: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    """Konağı IP olarak çözer; eski sayisal IPv4 yazimlarini da kapsar."""
    try:
        return ipaddress.ip_address(konak)
    except ValueError:
        pass
    if not _SAYISAL_KONAK_DESENI.match(konak):
        return None
    try:
        return ipaddress.IPv4Address(socket.inet_aton(konak))
    except (OSError, ValueError):
        return None


def _adres_yasakli(
    adres: ipaddress.IPv4Address | ipaddress.IPv6Address, *, yerel_izin: bool
) -> bool:
    """SSRF icin kullanilabilecek adres araliklarini denetler.

    Link-local (`169.254.0.0/16`, `fe80::/10` — bulut metadata), multicast,
    tanimsiz ve bilinen metadata adresleri `yerel_izin`den bagimsiz yasaktir.
    Geri kalan loopback/ozel/ULA/ayrilmis adresler yalnizca `yerel_izin=True`
    iken kabul edilir; `::ffff:` eslemeleri IPv4 kurallariyla denetlenir.
    """
    if isinstance(adres, ipaddress.IPv6Address) and adres.ipv4_mapped is not None:
        adres = adres.ipv4_mapped
    if (
        adres.is_link_local
        or adres.is_multicast
        or adres.is_unspecified
        or str(adres) in YASAKLI_KONAKLAR
    ):
        return True
    if yerel_izin:
        return False
    return adres.is_loopback or adres.is_private or adres.is_reserved


def _adres_dogrula(deger: str, *, yerel_izin: bool = False) -> str:
    """http/https semasini ve SSRF acisindan riskli hedefleri denetler.

    Konak kucuk harfe indirilip sondaki noktalar kirpilir. Literal IP'ler
    (eski sayisal IPv4 yazimlari dahil) dogrudan, alan adlari ise
    `socket.getaddrinfo` ile COZUMLENEN tum adresler uzerinden denetlenir.
    Link-local, multicast, tanimsiz ve metadata adresleri her kosulda
    reddedilir. Kati kipte (`yerel_izin=False`) loopback/ozel/ULA/ayrilmis
    adresler ve cozulemeyen konak adlari da reddedilir; `yerel_izin=True`
    (operatorun yerel ag izni) iken bunlar kabul edilir — yerel model
    sunuculari loopback/ozel agda calisir. Sema kisiti gevsetilmez: `http`
    mi `https` mi zorunlu olduguna cagiran katman karar verir.

    Cozulemeyen (bozuk) adresler yine reddedilmez: kayit olusturulabilir ve
    saglik/dogrulama katmani kullaniciya Turkce sonuc doner.
    """
    temiz = deger.strip()
    if not temiz:
        return temiz
    if not _URL_DESENI.match(temiz):
        raise ValueError("Temel adres http:// veya https:// ile başlamalıdır.")
    try:
        ayrilan = urlparse(temiz)
        konak = _konak_normalize(ayrilan.hostname or "")
        sema = ayrilan.scheme.lower()
    except ValueError:
        return temiz.rstrip("/")
    if sema not in GECERLI_SEMALAR:
        raise ValueError("Yalnız http ve https adresleri kullanılabilir.")
    if not konak:
        return temiz.rstrip("/")
    if konak in YASAKLI_KONAKLAR:
        raise ValueError("Bu adres güvenlik nedeniyle kullanılamaz.")
    ip = _ip_dene(konak)
    if ip is not None:
        if _adres_yasakli(ip, yerel_izin=yerel_izin):
            raise ValueError("Bu adres güvenlik nedeniyle kullanılamaz.")
        return temiz.rstrip("/")
    cozulenler = _konak_adresleri(konak)
    if cozulenler is None:
        if not yerel_izin:
            raise ValueError("Konak adı çözümlenemedi.")
        return temiz.rstrip("/")
    for cozulen in cozulenler:
        if _adres_yasakli(cozulen, yerel_izin=yerel_izin):
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
        # Operator yapilandirmasidir: yerel model sunuculari (ollama/vllm/tgi
        # varsayilanlari) loopback/ozel agda calisir, bu yuzden yerel aga izin
        # verilir; link-local ve bulut metadata adresleri yine reddedilir.
        return _adres_dogrula(deger, yerel_izin=True)

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
        # `BdmOlustur` ile ayni kural: operator yerel aga isaret edebilir.
        return _adres_dogrula(deger, yerel_izin=True) if deger is not None else None

    @field_validator("upstream_model")
    @classmethod
    def _model_temizle(cls, deger: str | None) -> str | None:
        return _model_dogrula(deger) if deger is not None else None


class BdmKopyala(BaseModel):
    yeni_ad: str = Field(min_length=2, max_length=160)
    yeni_slug: str | None = Field(default=None, max_length=80)
