"""OIDC (Authorization Code + PKCE) istemcisi (spec §7)."""

from __future__ import annotations

import base64
import hashlib
import logging
import secrets
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt
from jwt import PyJWKClient

from arkauc.app.cekirdek import guvenlik
from arkauc.app.cekirdek.hatalar import GecersizIstek, JetonGecersiz, UstSaglayiciHatasi
from bdm_veritabani.modeller import SsoSaglayici

logger = logging.getLogger("kutyai.sso.oidc")

STATE_TUR = "sso_state"
STATE_OMRU_DK = 10
VARSAYILAN_KAPSAM = "openid email profile"


def varsayilan_tasima() -> httpx.AsyncBaseTransport | None:
    """Testlerin ve önizlemenin taşımayı geçersiz kılması için kanca."""
    return None


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
    """`.well-known/openid-configuration` belgesini okur."""
    issuer = ayar(saglayici, "issuer").rstrip("/")
    if not issuer:
        raise GecersizIstek("sso_yapilandirilmamis", {"alan": "issuer"})
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
    return yanit.json()


def pkce_uret() -> tuple[str, str]:
    """(code_verifier, code_challenge) — S256."""
    dogrulayici = secrets.token_urlsafe(64)[:96]
    ozet = hashlib.sha256(dogrulayici.encode("ascii")).digest()
    meydan = base64.urlsafe_b64encode(ozet).decode("ascii").rstrip("=")
    return dogrulayici, meydan


def state_uret(*, saglayici_id: int, nonce: str, code_verifier: str, donus: str) -> str:
    """Kısa ömürlü, imzalı `state` (tek kullanımlık; DB gerektirmez)."""
    from datetime import datetime, timedelta, timezone

    from arkauc.app.cekirdek.ayarlar import ayarlar

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
    """İmza (JWKS), `iss`, `aud`, `exp`, `nonce` denetimi."""
    jwks_uri = kesif.get("jwks_uri")
    if not jwks_uri:
        raise GecersizIstek("sso_yapilandirilmamis", {"alan": "jwks_uri"})
    istemci_id = ayar(saglayici, "client_id")
    issuer = kesif.get("issuer") or ayar(saglayici, "issuer")

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


def kullanici_bilgisi(saglayici: SsoSaglayici, govde: dict[str, Any]) -> dict[str, str]:
    """id_token'dan kullanıcı alanlarını çıkarır."""
    eposta_claim = ayar(saglayici, "eposta_claim", "email")
    ad_claim = ayar(saglayici, "ad_claim", "name")
    eposta = str(govde.get(eposta_claim) or govde.get("email") or govde.get("preferred_username") or "")
    ad = str(govde.get(ad_claim) or govde.get("name") or "")
    dis_id = str(govde.get("sub") or "")
    if not dis_id:
        raise JetonGecersiz("sso_dogrulanamadi", {"alan": "sub"}, kod="sso_dogrulanamadi")
    return {"dis_id": dis_id, "eposta": eposta.strip().lower(), "ad": ad.strip()}
