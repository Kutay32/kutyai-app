"""OIDC (Authorization Code + PKCE) istemcisi (spec §7).

Güvenlik kuralları (pazarlık yok):
- IdP adresleri (`issuer`) `https` olmalıdır; keşif belgesindeki `issuer`
  alanı yapılandırılanla birebir eşleşir (mix-up savunması).
- `state` imzalıdır, **tek kullanımlıktır** (`jti` süreç içi kümede tutulur)
  ve 10 dakika sonra düşer.
- E-posta ile hesap birleştirme kararı `email_verified` iddiasına duyarlıdır
  (bkz. `kullanici_bilgisi`).
"""

from __future__ import annotations

import base64
import hashlib
import logging
import secrets
import time
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt
from jwt import PyJWKClient

from arkauc.app.cekirdek import guvenlik
from arkauc.app.cekirdek.ayarlar import ayarlar
from arkauc.app.cekirdek.hatalar import GecersizIstek, JetonGecersiz, UstSaglayiciHatasi
from bdm_listesi.sema import _adres_dogrula
from bdm_veritabani.modeller import SsoSaglayici

logger = logging.getLogger("kutyai.sso.oidc")

STATE_TUR = "sso_state"
STATE_OMRU_DK = 10
VARSAYILAN_KAPSAM = "openid email profile"

#: {state jti: gorulme_zamani} — `state` tek kullanım kümesi (süreç içi).
_kullanilan_durumlar: dict[str, float] = {}


def varsayilan_tasima() -> httpx.AsyncBaseTransport | None:
    """Testlerin ve önizlemenin taşımayı geçersiz kılması için kanca."""
    return None


def adres_denetle(adres: str, *, alan: str) -> str:
    """IdP adresini şema ve SSRF kurallarına göre denetler.

    `https` zorunludur; `KUTYAI_SSO_YEREL_IZIN=true` iken (geliştirme, şirket
    içi IdP) `http` ve yerel/özel adresler de kabul edilir. Katı modda
    metadata/loopback/özel ağ adresleri reddedilir (`bdm_listesi.sema` tek
    kural kaynağıdır). Reddedilen adres `400 sso_yapilandirilmamis` üretir.
    """
    yerel = bool(ayarlar.sso_yerel_izin)
    kucuk = adres.strip().lower()
    if not (kucuk.startswith("https://") or (yerel and kucuk.startswith("http://"))):
        raise GecersizIstek("sso_yapilandirilmamis", {"alan": alan})
    try:
        return _adres_dogrula(adres, yerel_izin=yerel)
    except ValueError as hata:
        logger.warning("SSO IdP adresi reddedildi (%s): %s", alan, hata)
        raise GecersizIstek("sso_yapilandirilmamis", {"alan": alan}) from hata


def ayar(saglayici: SsoSaglayici, anahtar: str, varsayilan: str = "") -> str:
    return str((saglayici.ayarlar or {}).get(anahtar, varsayilan) or varsayilan)


def istemci_sirri(saglayici: SsoSaglayici) -> str:
    if not saglayici.sir_sifreli:
        return ""
    try:
        return guvenlik.coz(saglayici.sir_sifreli)
    except Exception:  # pragma: no cover - bozuk kayit
        logger.error("SSO sırrı çözülemedi: saglayici=%s", saglayici.id)
        return ""


async def kesif_getir(
    saglayici: SsoSaglayici, *, tasima: httpx.AsyncBaseTransport | None = None
) -> dict[str, Any]:
    """`.well-known/openid-configuration` belgesini okur.

    Yapılandırılan `issuer` `https` olmalıdır ve keşif belgesindeki `issuer`
    alanıyla birebir eşleşmelidir (mix-up saldırılarına karşı).
    """
    issuer = ayar(saglayici, "issuer").strip()
    if not issuer:
        raise GecersizIstek("sso_yapilandirilmamis", {"alan": "issuer"})
    issuer = adres_denetle(issuer, alan="issuer").rstrip("/")
    adres = f"{issuer}/.well-known/openid-configuration"
    async with httpx.AsyncClient(timeout=15.0, transport=tasima) as istemci:
        try:
            yanit = await istemci.get(adres)
        except httpx.HTTPError as hata:
            raise UstSaglayiciHatasi(
                "Kimlik sağlayıcısına ulaşılamadı.", {"saglayici": saglayici.slug}
            ) from hata
    if yanit.status_code >= 400:
        raise UstSaglayiciHatasi(
            "Kimlik sağlayıcısı keşif belgesini reddetti.",
            {"saglayici": saglayici.slug, "durum": yanit.status_code},
        )
    try:
        belge = yanit.json()
    except ValueError as hata:
        raise UstSaglayiciHatasi(
            "Kimlik sağlayıcısı geçersiz keşif belgesi döndü.", {"saglayici": saglayici.slug}
        ) from hata
    if not isinstance(belge, dict):
        raise UstSaglayiciHatasi(
            "Kimlik sağlayıcısı geçersiz keşif belgesi döndü.", {"saglayici": saglayici.slug}
        )
    belge_issuer = str(belge.get("issuer") or "").strip().rstrip("/")
    if belge_issuer != issuer:
        logger.warning(
            "Keşif `issuer` alanı yapılandırmayla uyuşmuyor: saglayici=%s", saglayici.slug
        )
        raise GecersizIstek(
            "sso_yapilandirilmamis", {"alan": "issuer", "neden": "kesif_uyusmazligi"}
        )
    return belge


def pkce_uret() -> tuple[str, str]:
    """(code_verifier, code_challenge) — S256."""
    dogrulayici = secrets.token_urlsafe(64)[:96]
    ozet = hashlib.sha256(dogrulayici.encode("ascii")).digest()
    meydan = base64.urlsafe_b64encode(ozet).decode("ascii").rstrip("=")
    return dogrulayici, meydan


def state_uret(*, saglayici_id: int, nonce: str, code_verifier: str, donus: str) -> str:
    """Kısa ömürlü, imzalı `state`; `jti` alanı tek kullanımı sağlar."""
    from datetime import datetime, timedelta, timezone

    simdi = datetime.now(timezone.utc)
    govde = {
        "tur": STATE_TUR,
        "sid": int(saglayici_id),
        "nonce": nonce,
        "cv": code_verifier,
        "donus": donus,
        "jti": guvenlik.rastgele_jeton(12),
        "exp": int((simdi + timedelta(minutes=STATE_OMRU_DK)).timestamp()),
    }
    return jwt.encode(govde, ayarlar.gizli_anahtar, algorithm="HS256")


def state_coz(jeton: str) -> dict[str, Any]:
    try:
        govde = guvenlik.jeton_coz(jeton, beklenen_tur=STATE_TUR)
    except JetonGecersiz as hata:
        raise JetonGecersiz("oidc_durum_gecersiz", kod="oidc_durum_gecersiz") from hata
    return govde


def durum_tuket(govde: dict[str, Any]) -> None:
    """`state`'i tek kullanımlık yapar (SAML tekrar kümesiyle aynı desen).

    Aynı `jti` ikinci kez görülürse `401 oidc_durum_gecersiz` yükseltilir;
    kayıtlar `STATE_OMRU_DK` sonra düşer. Küme süreç belleğindedir ve çok
    replikada paylaşılmaz (varsayılan dağıtım tek süreçtir).
    """
    su_an = time.time()
    suresi_gecenler = [
        anahtar
        for anahtar, zaman in _kullanilan_durumlar.items()
        if su_an - zaman > STATE_OMRU_DK * 60
    ]
    for anahtar in suresi_gecenler:
        _kullanilan_durumlar.pop(anahtar, None)
    jti = str(govde.get("jti") or "")
    if not jti or jti in _kullanilan_durumlar:
        raise JetonGecersiz("oidc_durum_gecersiz", kod="oidc_durum_gecersiz")
    _kullanilan_durumlar[jti] = su_an


def durum_kumesini_temizle() -> None:
    """Testler arası izolasyon."""
    _kullanilan_durumlar.clear()


def yetkilendirme_url(
    saglayici: SsoSaglayici,
    kesif: dict[str, Any],
    *,
    state: str,
    nonce: str,
    code_challenge: str,
    yonlendirme: str,
) -> str:
    uc = kesif.get("authorization_endpoint")
    istemci_id = ayar(saglayici, "client_id")
    if not uc or not istemci_id:
        raise GecersizIstek(
            "sso_yapilandirilmamis", {"alan": "authorization_endpoint" if not uc else "client_id"}
        )
    parametreler = {
        "response_type": "code",
        "client_id": istemci_id,
        "redirect_uri": yonlendirme,
        "scope": ayar(saglayici, "kapsamlar", VARSAYILAN_KAPSAM),
        "state": state,
        "nonce": nonce,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{uc}?{urlencode(parametreler)}"


async def kod_degistir(
    saglayici: SsoSaglayici,
    kesif: dict[str, Any],
    *,
    kod: str,
    code_verifier: str,
    yonlendirme: str,
    tasima: httpx.AsyncBaseTransport | None = None,
) -> dict[str, Any]:
    uc = kesif.get("token_endpoint")
    istemci_id = ayar(saglayici, "client_id")
    if not uc or not istemci_id:
        raise GecersizIstek("sso_yapilandirilmamis", {"alan": "token_endpoint"})
    veri = {
        "grant_type": "authorization_code",
        "code": kod,
        "redirect_uri": yonlendirme,
        "client_id": istemci_id,
        "code_verifier": code_verifier,
    }
    sir = istemci_sirri(saglayici)
    basliklar: dict[str, str] = {"Accept": "application/json"}
    if sir:
        temel = base64.b64encode(f"{istemci_id}:{sir}".encode()).decode()
        basliklar["Authorization"] = f"Basic {temel}"
    async with httpx.AsyncClient(timeout=15.0, transport=tasima) as istemci:
        try:
            yanit = await istemci.post(uc, data=veri, headers=basliklar)
        except httpx.HTTPError as hata:
            raise UstSaglayiciHatasi(
                "Kimlik sağlayıcısına ulaşılamadı.", {"saglayici": saglayici.slug}
            ) from hata
    if yanit.status_code >= 400:
        logger.error("OIDC token hatası: %s %s", yanit.status_code, yanit.text[:300])
        raise JetonGecersiz("sso_dogrulanamadi", kod="sso_dogrulanamadi")
    return yanit.json()


async def id_jetonu_dogrula(
    saglayici: SsoSaglayici,
    kesif: dict[str, Any],
    id_token: str,
    *,
    nonce: str,
    tasima: httpx.AsyncBaseTransport | None = None,
) -> dict[str, Any]:
    """İmza (JWKS), `iss`, `aud`, `exp`, `nonce` denetimi.

    Beklenen `iss` daima yapılandırılan `issuer`'dır (keşif belgesiyle
    eşleştiği `kesif_getir`'de doğrulanır); keşiften gelen değere güvenilmez.
    """
    jwks_uri = kesif.get("jwks_uri")
    if not jwks_uri:
        raise GecersizIstek("sso_yapilandirilmamis", {"alan": "jwks_uri"})
    istemci_id = ayar(saglayici, "client_id")
    issuer = ayar(saglayici, "issuer").strip().rstrip("/")

    try:
        anahtar_istemcisi = PyJWKClient(jwks_uri)
        imza_anahtari = anahtar_istemcisi.get_signing_key_from_jwt(id_token)
        govde = jwt.decode(
            id_token,
            imza_anahtari.key,
            algorithms=["RS256", "RS384", "RS512", "ES256", "ES384"],
            audience=istemci_id,
            issuer=issuer,
            options={"require": ["exp", "iat", "aud", "iss"]},
        )
    except Exception as hata:  # PyJWT hata hiyerarşisi geniş
        logger.warning("OIDC id_token doğrulanamadı: %s", hata)
        raise JetonGecersiz("sso_dogrulanamadi", kod="sso_dogrulanamadi") from hata

    if nonce and govde.get("nonce") != nonce:
        raise JetonGecersiz("sso_dogrulanamadi", {"alan": "nonce"}, kod="sso_dogrulanamadi")
    return govde


def _bayrak_metni(deger: Any) -> str:
    """`email_verified` benzeri iddiayı `"true"` / `"false"` / `""` yapar.

    İddia hiç yoksa ya da tanınmayan bir değerse `""` döner: e-posta
    eşleşmesi bu durumda kısıtlanmaz (iddia yokluğu `false` sayılmaz).
    """
    if isinstance(deger, bool):
        return "true" if deger else "false"
    metin = str(deger).strip().lower() if deger is not None else ""
    if metin in {"true", "1"}:
        return "true"
    if metin in {"false", "0"}:
        return "false"
    return ""


def kullanici_bilgisi(saglayici: SsoSaglayici, govde: dict[str, Any]) -> dict[str, str]:
    """id_token'dan kullanıcı alanlarını çıkarır.

    `eposta_dogrulandi`, IdP'nin `email_verified` iddiasını taşır; `"false"`
    ise e-posta ile mevcut hesaba bağlanılmaz (`_kullanici_esle`).
    """
    eposta_claim = ayar(saglayici, "eposta_claim", "email")
    ad_claim = ayar(saglayici, "ad_claim", "name")
    eposta = str(govde.get(eposta_claim) or govde.get("email") or govde.get("preferred_username") or "")
    ad = str(govde.get(ad_claim) or govde.get("name") or "")
    dis_id = str(govde.get("sub") or "")
    if not dis_id:
        raise JetonGecersiz("sso_dogrulanamadi", {"alan": "sub"}, kod="sso_dogrulanamadi")
    return {
        "dis_id": dis_id,
        "eposta": eposta.strip().lower(),
        "ad": ad.strip(),
        "eposta_dogrulandi": _bayrak_metni(govde.get("email_verified")),
    }
