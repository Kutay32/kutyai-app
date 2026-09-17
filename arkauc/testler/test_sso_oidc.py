"""OIDC SSO testleri (spec §7).

Sahte kimlik sağlayıcısı: keşif belgesi + token ucu `httpx.MockTransport` ile
sunulur; `PyJWKClient` gerçek anahtarı döndüren bir taklitle değiştirilir
(id_token imzası PyJWT ile GERÇEKTEN doğrulanır).
"""

from __future__ import annotations

import json
import time
from types import SimpleNamespace
from typing import Any

import httpx
import jwt
import pytest
import sqlalchemy as sa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from arkauc.app.cekirdek.ayarlar import ayarlar
from arkauc.app.servisler import sso_oidc
from bdm_veritabani.modeller import (
    Kullanici,
    SsoKimlik,
    SsoSaglayici,
    SsoTuru,
    Uyelik,
    UyelikRolu,
)
from bdm_veritabani.oturum import oturum_fabrikasi

ISSUER = "https://idp.ornek.local"
ISTEMCI_ID = "kutyai-test"


@pytest.fixture(scope="module")
def rsa_anahtar():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def idp(monkeypatch, rsa_anahtar):
    """Sahte IdP: keşif + token ucu; JWKS istemcisi taklit edilir."""
    ozel_anahtar_pem = rsa_anahtar.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    durum: dict[str, Any] = {"kod": "kod-1", "nonce": "", "kod_istekleri": []}

    kesif = {
        "issuer": ISSUER,
        "authorization_endpoint": f"{ISSUER}/authorize",
        "token_endpoint": f"{ISSUER}/token",
        "jwks_uri": f"{ISSUER}/jwks",
    }

    def id_token_uret(
        *,
        nonce: str,
        eposta: str = "sso.kullanici@ornek.local",
        sub: str = "sub-1",
        email_verified: bool | None = None,
    ) -> str:
        simdi = int(time.time())
        iddialar: dict[str, Any] = {
            "iss": ISSUER,
            "aud": ISTEMCI_ID,
            "sub": sub,
            "email": eposta,
            "name": "SSO Kullanıcı",
            "nonce": nonce,
            "iat": simdi,
            "exp": simdi + 300,
        }
        if email_verified is not None:
            iddialar["email_verified"] = email_verified
        return jwt.encode(iddialar, ozel_anahtar_pem, algorithm="RS256")

    durum["id_token_uret"] = id_token_uret
    durum["kesif"] = kesif

    async def isleyici(istek: httpx.Request) -> httpx.Response:
        yol = istek.url.path
        if yol.endswith("/.well-known/openid-configuration"):
            return httpx.Response(200, json=kesif)
        if yol.endswith("/token"):
            govde = dict(httpx.QueryParams(istek.content.decode()))
            durum["kod_istekleri"].append(govde)
            if govde.get("code") != durum["kod"]:
                return httpx.Response(400, json={"error": "invalid_grant"})
            return httpx.Response(
                200,
                json={
                    "access_token": "at-1",
                    "id_token": durum["id_token_uret"](nonce=durum["nonce"]),
                    "token_type": "Bearer",
                },
            )
        return httpx.Response(404, json={"error": "yok"})

    tasima = httpx.MockTransport(isleyici)
    monkeypatch.setattr(sso_oidc, "varsayilan_tasima", lambda: tasima)
    monkeypatch.setattr(
        sso_oidc,
        "PyJWKClient",
        lambda _url: SimpleNamespace(
            get_signing_key_from_jwt=lambda _jeton: SimpleNamespace(
                key=rsa_anahtar.public_key()
            )
        ),
    )
    return durum


@pytest.fixture(autouse=True)
def sso_ortami(monkeypatch):
    """Sahte IdP konakları çözümlenemediği için SSO yerel izni açık; state kümesi temiz."""
    monkeypatch.setattr(ayarlar, "sso_yerel_izin", True)
    sso_oidc.durum_kumesini_temizle()
    yield
    sso_oidc.durum_kumesini_temizle()


async def _saglayici_ekle(
    org_id: int, *, slug: str = "test-idp", etkin: bool = True, issuer: str = ISSUER
) -> SsoSaglayici:
    from arkauc.app.cekirdek import guvenlik

    async with oturum_fabrikasi()() as oturum:
        saglayici = SsoSaglayici(
            org_id=org_id,
            tur=SsoTuru.oidc,
            ad="Test IdP",
            slug=slug,
            etkin=etkin,
            ayarlar={
                "issuer": issuer,
                "client_id": ISTEMCI_ID,
                "kapsamlar": "openid email profile",
            },
            sir_sifreli=guvenlik.sifrele("istemci-sirri"),
        )
        oturum.add(saglayici)
        await oturum.commit()
        await oturum.refresh(saglayici)
        return saglayici


async def test_saglayici_crud_ve_sir_gizleme(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    organizasyon = await yardimci.organizasyon(sahibi=yonetici)
    basliklar = yardimci.org_basliklari(yonetici, organizasyon)

    olustur = await istemci.post(
        "/api/v1/sso/saglayicilar",
        json={
            "tur": "oidc",
            "ad": "Kurumsal IdP",
            "ayarlar": {"issuer": ISSUER, "client_id": ISTEMCI_ID},
            "sir": "cok-gizli",
        },
        headers=basliklar,
    )
    assert olustur.status_code == 201, olustur.text
    govde = olustur.json()
    assert govde["slug"] == "kurumsal-idp"
    assert govde["sir_tanimli"] is True
    assert "cok-gizli" not in olustur.text

    tekrar = await istemci.post(
        "/api/v1/sso/saglayicilar",
        json={"tur": "oidc", "ad": "Kurumsal IdP"},
        headers=basliklar,
    )
    assert tekrar.status_code == 409

    liste = await istemci.get("/api/v1/sso/saglayicilar", headers=basliklar)
    assert liste.status_code == 200
    assert len(liste.json()) == 1

    guncelle = await istemci.patch(
        f"/api/v1/sso/saglayicilar/{govde['id']}",
        json={"etkin": False, "ayarlar": {"client_id": "yeni-id"}},
        headers=basliklar,
    )
    assert guncelle.status_code == 200
    assert guncelle.json()["etkin"] is False
    assert guncelle.json()["ayarlar"]["client_id"] == "yeni-id"

    sil = await istemci.delete(f"/api/v1/sso/saglayicilar/{govde['id']}", headers=basliklar)
    assert sil.status_code == 204


async def test_oidc_uctan_uca_giris(istemci, yardimci, idp):
    yonetici = await yardimci.yonetici()
    organizasyon = await yardimci.organizasyon(sahibi=yonetici)
    saglayici = await _saglayici_ekle(organizasyon.id)

    baslat = await istemci.get(
        f"/api/v1/sso/{organizasyon.slug}/{saglayici.slug}/baslat", follow_redirects=False
    )
    assert baslat.status_code == 302
    hedef = baslat.headers["location"]
    assert hedef.startswith(f"{ISSUER}/authorize")
    parametreler = httpx.QueryParams(hedef.split("?", 1)[1])
    assert parametreler["client_id"] == ISTEMCI_ID
    assert parametreler["code_challenge_method"] == "S256"
    assert parametreler["state"]
    idp["nonce"] = parametreler["nonce"]

    donus = await istemci.get(
        f"/api/v1/sso/{organizasyon.slug}/{saglayici.slug}/donus",
        params={"code": idp["kod"], "state": parametreler["state"]},
    )
    assert donus.status_code == 200, donus.text
    govde = donus.json()
    assert govde["erisim_jetonu"]
    assert govde["yenileme_jetonu"]
    assert govde["kullanici"]["eposta"] == "sso.kullanici@ornek.local"
    assert govde["organizasyon"]["slug"] == organizasyon.slug

    # PKCE doğrulayıcı token ucuna gitti
    assert idp["kod_istekleri"][-1]["code_verifier"]

    async with oturum_fabrikasi()() as oturum:
        kullanici = (
            await oturum.execute(
                sa.select(Kullanici).where(Kullanici.eposta == "sso.kullanici@ornek.local")
            )
        ).scalar_one()
        assert kullanici.eposta_dogrulandi is True
        baglanti = (
            await oturum.execute(
                sa.select(SsoKimlik).where(SsoKimlik.kullanici_id == kullanici.id)
            )
        ).scalar_one()
        assert baglanti.dis_id == "sub-1"
        uyelik = (
            await oturum.execute(
                sa.select(Uyelik).where(Uyelik.kullanici_id == kullanici.id)
            )
        ).scalar_one()
        assert uyelik.rol == UyelikRolu.son_kullanici

    # İkinci giriş: aynı kullanıcı, yeni üyelik yok
    baslat2 = await istemci.get(
        f"/api/v1/sso/{organizasyon.slug}/{saglayici.slug}/baslat", follow_redirects=False
    )
    parametreler2 = httpx.QueryParams(baslat2.headers["location"].split("?", 1)[1])
    idp["nonce"] = parametreler2["nonce"]
    await istemci.get(
        f"/api/v1/sso/{organizasyon.slug}/{saglayici.slug}/donus",
        params={"code": idp["kod"], "state": parametreler2["state"]},
    )
    async with oturum_fabrikasi()() as oturum:
        adet = (
            await oturum.execute(sa.select(sa.func.count()).select_from(Kullanici))
        ).scalar_one()
        assert int(adet) == 2  # yönetici + sso kullanıcısı


async def test_gecersiz_state_reddedilir(istemci, yardimci, idp):
    yonetici = await yardimci.yonetici()
    organizasyon = await yardimci.organizasyon(sahibi=yonetici)
    saglayici = await _saglayici_ekle(organizasyon.id)

    yanit = await istemci.get(
        f"/api/v1/sso/{organizasyon.slug}/{saglayici.slug}/donus",
        params={"code": "kod-1", "state": "bozuk-state"},
    )
    assert yanit.status_code == 401
    assert yanit.json()["hata"]["kod"] == "oidc_durum_gecersiz"


async def test_nonce_uyusmazligi_reddedilir(istemci, yardimci, idp, monkeypatch):
    yonetici = await yardimci.yonetici()
    organizasyon = await yardimci.organizasyon(sahibi=yonetici)
    saglayici = await _saglayici_ekle(organizasyon.id)

    baslat = await istemci.get(
        f"/api/v1/sso/{organizasyon.slug}/{saglayici.slug}/baslat", follow_redirects=False
    )
    parametreler = httpx.QueryParams(baslat.headers["location"].split("?", 1)[1])
    idp["nonce"] = "baska-nonce"

    yanit = await istemci.get(
        f"/api/v1/sso/{organizasyon.slug}/{saglayici.slug}/donus",
        params={"code": idp["kod"], "state": parametreler["state"]},
    )
    assert yanit.status_code == 401
    assert yanit.json()["hata"]["kod"] == "sso_dogrulanamadi"


async def test_yanlis_imzali_id_token_reddedilir(istemci, yardimci, idp):
    yonetici = await yardimci.yonetici()
    organizasyon = await yardimci.organizasyon(sahibi=yonetici)
    saglayici = await _saglayici_ekle(organizasyon.id)

    baslat = await istemci.get(
        f"/api/v1/sso/{organizasyon.slug}/{saglayici.slug}/baslat", follow_redirects=False
    )
    parametreler = httpx.QueryParams(baslat.headers["location"].split("?", 1)[1])
    idp["nonce"] = parametreler["nonce"]

    # Sahte anahtarla imzalanmış jeton
    sahte_anahtar = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    sahte_pem = sahte_anahtar.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    simdi = int(time.time())
    sahte = jwt.encode(
        {
            "iss": ISSUER,
            "aud": ISTEMCI_ID,
            "sub": "sub-1",
            "email": "sahte@ornek.local",
            "nonce": parametreler["nonce"],
            "iat": simdi,
            "exp": simdi + 300,
        },
        sahte_pem,
        algorithm="RS256",
    )
    orijinal = idp["id_token_uret"]
    idp["id_token_uret"] = lambda **_k: sahte
    try:
        yanit = await istemci.get(
            f"/api/v1/sso/{organizasyon.slug}/{saglayici.slug}/donus",
            params={"code": idp["kod"], "state": parametreler["state"]},
        )
    finally:
        idp["id_token_uret"] = orijinal

    assert yanit.status_code == 401
    assert yanit.json()["hata"]["kod"] == "sso_dogrulanamadi"


async def test_pasif_saglayici_ve_bilinmeyen_org(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    organizasyon = await yardimci.organizasyon(sahibi=yonetici)
    await _saglayici_ekle(organizasyon.id, slug="kapali", etkin=False)

    kapali = await istemci.get(f"/api/v1/sso/{organizasyon.slug}/kapali/baslat")
    assert kapali.status_code == 400
    assert kapali.json()["hata"]["kod"] == "sso_yapilandirilmamis"

    yok = await istemci.get("/api/v1/sso/olmayan-org/olmayan/baslat")
    assert yok.status_code == 404


async def test_yetki_matrisi(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    organizasyon = await yardimci.organizasyon(sahibi=yonetici)

    anonim = await istemci.get("/api/v1/sso/saglayicilar")
    assert anonim.status_code == 401

    izleyici = await yardimci.kullanici_ekle()
    await yardimci.uye_yap(organizasyon, izleyici, UyelikRolu.izleyici)
    izleyici_basliklar = yardimci.org_basliklari(izleyici, organizasyon)

    okuma = await istemci.get("/api/v1/sso/saglayicilar", headers=izleyici_basliklar)
    assert okuma.status_code == 200

    yazma = await istemci.post(
        "/api/v1/sso/saglayicilar",
        json={"tur": "saml", "ad": "Yasak"},
        headers=izleyici_basliklar,
    )
    assert yazma.status_code == 403


async def test_otomatik_uyelik_kapaliysa_403(istemci, yardimci, idp, monkeypatch):
    monkeypatch.setattr(ayarlar, "sso_otomatik_uyelik", False)
    yonetici = await yardimci.yonetici()
    organizasyon = await yardimci.organizasyon(sahibi=yonetici)
    saglayici = await _saglayici_ekle(organizasyon.id)

    baslat = await istemci.get(
        f"/api/v1/sso/{organizasyon.slug}/{saglayici.slug}/baslat", follow_redirects=False
    )
    parametreler = httpx.QueryParams(baslat.headers["location"].split("?", 1)[1])
    idp["nonce"] = parametreler["nonce"]

    yanit = await istemci.get(
        f"/api/v1/sso/{organizasyon.slug}/{saglayici.slug}/donus",
        params={"code": idp["kod"], "state": parametreler["state"]},
    )
    assert yanit.status_code == 403
    assert yanit.json()["hata"]["kod"] == "yetki_yok"


async def test_yonlendirme_akisi_tek_kullanimlik_kod(istemci, yardimci, idp, monkeypatch):
    monkeypatch.setattr(ayarlar, "sso_yeniden_yonlendirme", "http://localhost:3000/sso/donus")
    yonetici = await yardimci.yonetici()
    organizasyon = await yardimci.organizasyon(sahibi=yonetici)
    saglayici = await _saglayici_ekle(organizasyon.id)

    baslat = await istemci.get(
        f"/api/v1/sso/{organizasyon.slug}/{saglayici.slug}/baslat", follow_redirects=False
    )
    parametreler = httpx.QueryParams(baslat.headers["location"].split("?", 1)[1])
    idp["nonce"] = parametreler["nonce"]

    yanit = await istemci.get(
        f"/api/v1/sso/{organizasyon.slug}/{saglayici.slug}/donus",
        params={"code": idp["kod"], "state": parametreler["state"]},
        follow_redirects=False,
    )
    assert yanit.status_code == 302
    hedef = yanit.headers["location"]
    assert hedef.startswith("http://localhost:3000/sso/donus?kod=")
    kod = hedef.split("kod=", 1)[1]

    degis = await istemci.post("/api/v1/sso/kod-degistir", json={"kod": kod})
    assert degis.status_code == 200
    assert degis.json()["erisim_jetonu"]

    bozuk = await istemci.post("/api/v1/sso/kod-degistir", json={"kod": "abc"})
    assert bozuk.status_code == 401


def test_kullanici_bilgisi_claim_eslemesi():
    saglayici = SsoSaglayici(
        org_id=1,
        tur=SsoTuru.oidc,
        ad="x",
        slug="x",
        ayarlar={"eposta_claim": "preferred_username", "ad_claim": "name"},
    )
    bilgi = sso_oidc.kullanici_bilgisi(
        saglayici, {"sub": "s1", "preferred_username": "Ali@Ornek.Local", "name": "Ali Veli"}
    )
    assert bilgi["dis_id"] == "s1"
    assert bilgi["eposta"] == "ali@ornek.local"
    assert bilgi["ad"] == "Ali Veli"
    # `email_verified` iddiası yoksa e-posta eşleşmesi kısıtlanmaz.
    assert bilgi["eposta_dogrulandi"] == ""


@pytest.mark.parametrize(
    ("iddia", "beklenen"),
    [(True, "true"), (False, "false"), ("false", "false"), ("belirsiz", "")],
)
def test_kullanici_bilgisi_email_verified_iddiasi(iddia, beklenen):
    saglayici = SsoSaglayici(org_id=1, tur=SsoTuru.oidc, ad="x", slug="x", ayarlar={})
    bilgi = sso_oidc.kullanici_bilgisi(
        saglayici, {"sub": "s1", "email": "a@ornek.local", "email_verified": iddia}
    )
    assert bilgi["eposta_dogrulandi"] == beklenen


def test_state_tek_kullanimlik_ve_sureli():
    from arkauc.app.cekirdek.hatalar import JetonGecersiz

    jeton = sso_oidc.state_uret(saglayici_id=5, nonce="n", code_verifier="v", donus="d")
    govde = sso_oidc.state_coz(jeton)
    assert govde["sid"] == 5 and govde["nonce"] == "n" and govde["cv"] == "v"

    # `jti` tek kullanımlık: ilk tüketim geçer, ikincisi reddedilir.
    sso_oidc.durum_tuket(govde)
    with pytest.raises(JetonGecersiz) as hata:
        sso_oidc.durum_tuket(govde)
    assert hata.value.kod == "oidc_durum_gecersiz"

    with pytest.raises(JetonGecersiz):
        sso_oidc.state_coz(jeton + "bozuk")


async def _akis_baslat(istemci, organizasyon, saglayici) -> httpx.QueryParams:
    """`/baslat` → 302 yönlendirmesinin sorgu parametreleri."""
    baslat = await istemci.get(
        f"/api/v1/sso/{organizasyon.slug}/{saglayici.slug}/baslat", follow_redirects=False
    )
    assert baslat.status_code == 302, baslat.text
    return httpx.QueryParams(baslat.headers["location"].split("?", 1)[1])


async def _id_token_ile_don(istemci, idp, organizasyon, saglayici, parametreler, **iddialar):
    """Sahte IdP'nin ürettiği id_token ile `/donus` çağrısı (iddialar ezilebilir)."""
    idp["nonce"] = parametreler["nonce"]
    orijinal = idp["id_token_uret"]
    idp["id_token_uret"] = lambda **_k: orijinal(nonce=idp["nonce"], **iddialar)
    try:
        return await istemci.get(
            f"/api/v1/sso/{organizasyon.slug}/{saglayici.slug}/donus",
            params={"code": idp["kod"], "state": parametreler["state"]},
        )
    finally:
        idp["id_token_uret"] = orijinal


async def test_ayni_organizasyon_uyesi_eposta_ile_birlesir(istemci, yardimci, idp):
    """Spec §7: e-posta adımı, üye olan mevcut kullanıcıyı yeni hesap açmadan kullanır."""
    yonetici = await yardimci.yonetici()
    organizasyon = await yardimci.organizasyon(sahibi=yonetici)
    mevcut = await yardimci.kullanici_ekle(eposta="mevcut@ornek.local")
    await yardimci.uye_yap(organizasyon, mevcut, UyelikRolu.son_kullanici)
    saglayici = await _saglayici_ekle(organizasyon.id)

    parametreler = await _akis_baslat(istemci, organizasyon, saglayici)
    yanit = await _id_token_ile_don(
        istemci,
        idp,
        organizasyon,
        saglayici,
        parametreler,
        eposta="mevcut@ornek.local",
        sub="sub-mevcut",
        email_verified=True,
    )

    assert yanit.status_code == 200, yanit.text
    assert yanit.json()["kullanici"]["id"] == mevcut.id
    async with oturum_fabrikasi()() as oturum:
        adet = (await oturum.execute(sa.select(sa.func.count()).select_from(Kullanici))).scalar_one()
        assert int(adet) == 2  # yönetici + mevcut kullanıcı


async def test_baska_organizasyon_kullanicisi_eposta_ile_devralinamaz(istemci, yardimci, idp):
    """SEC-SSO-001: e-posta eşleşmesi, sağlayıcının organizasyonunda üye olmayanı bağlamaz."""
    kurban = await yardimci.kullanici_ekle(eposta="kurban@ornek.local")
    await yardimci.organizasyon("Kurban Organizasyon", sahibi=kurban)
    yonetici = await yardimci.yonetici()
    organizasyon = await yardimci.organizasyon("Saldırgan Organizasyon", sahibi=yonetici)
    saglayici = await _saglayici_ekle(organizasyon.id)

    parametreler = await _akis_baslat(istemci, organizasyon, saglayici)
    yanit = await _id_token_ile_don(
        istemci,
        idp,
        organizasyon,
        saglayici,
        parametreler,
        eposta="kurban@ornek.local",
        sub="sub-kurban",
    )

    assert yanit.status_code == 403
    assert yanit.json()["hata"]["kod"] == "yetki_yok"
    assert "erisim_jetonu" not in yanit.text
    async with oturum_fabrikasi()() as oturum:
        baglanti = (
            await oturum.execute(sa.select(SsoKimlik).where(SsoKimlik.kullanici_id == kurban.id))
        ).scalar_one_or_none()
        assert baglanti is None


async def test_dogrulanmamis_eposta_eslesmeyi_engeller(istemci, yardimci, idp):
    """SEC-SSO-001: `email_verified=false` iken e-posta ile mevcut hesaba bağlanılmaz."""
    yonetici = await yardimci.yonetici()
    organizasyon = await yardimci.organizasyon(sahibi=yonetici)
    mevcut = await yardimci.kullanici_ekle(eposta="mevcut@ornek.local")
    await yardimci.uye_yap(organizasyon, mevcut, UyelikRolu.son_kullanici)
    saglayici = await _saglayici_ekle(organizasyon.id)

    parametreler = await _akis_baslat(istemci, organizasyon, saglayici)
    yanit = await _id_token_ile_don(
        istemci,
        idp,
        organizasyon,
        saglayici,
        parametreler,
        eposta="mevcut@ornek.local",
        sub="sub-mevcut",
        email_verified=False,
    )

    assert yanit.status_code == 401
    assert yanit.json()["hata"]["kod"] == "sso_dogrulanamadi"
    assert "erisim_jetonu" not in yanit.text


async def test_ayni_oidc_state_ikinci_kez_kullanilamaz(istemci, yardimci, idp):
    """SEC-OIDC-001: `state` tek kullanımlıktır."""
    yonetici = await yardimci.yonetici()
    organizasyon = await yardimci.organizasyon(sahibi=yonetici)
    saglayici = await _saglayici_ekle(organizasyon.id)

    parametreler = await _akis_baslat(istemci, organizasyon, saglayici)
    idp["nonce"] = parametreler["nonce"]
    donus = f"/api/v1/sso/{organizasyon.slug}/{saglayici.slug}/donus"
    istek = {"code": idp["kod"], "state": parametreler["state"]}

    ilk = await istemci.get(donus, params=istek)
    assert ilk.status_code == 200, ilk.text

    ikinci = await istemci.get(donus, params=istek)
    assert ikinci.status_code == 401
    assert ikinci.json()["hata"]["kod"] == "oidc_durum_gecersiz"


async def test_http_issuer_reddedilir(istemci, yardimci, idp, monkeypatch):
    """SEC-OIDC-001: `issuer` https olmalı; yerel izin kapalıyken http reddedilir."""
    monkeypatch.setattr(ayarlar, "sso_yerel_izin", False)
    yonetici = await yardimci.yonetici()
    organizasyon = await yardimci.organizasyon(sahibi=yonetici)
    saglayici = await _saglayici_ekle(organizasyon.id, issuer="http://idp.ornek.local")
    yol = f"/api/v1/sso/{organizasyon.slug}/{saglayici.slug}/baslat"

    reddedildi = await istemci.get(yol, follow_redirects=False)
    assert reddedildi.status_code == 400
    assert reddedildi.json()["hata"]["kod"] == "sso_yapilandirilmamis"

    # Yerel izin açıkken (geliştirme, şirket içi IdP) http kabul edilir.
    monkeypatch.setattr(ayarlar, "sso_yerel_izin", True)
    idp["kesif"]["issuer"] = "http://idp.ornek.local"
    idp["kesif"]["authorization_endpoint"] = "http://idp.ornek.local/authorize"
    izinli = await istemci.get(yol, follow_redirects=False)
    assert izinli.status_code == 302, izinli.text
    assert izinli.headers["location"].startswith("http://idp.ornek.local/authorize")


async def test_katida_metadata_adresi_issuer_olamaz(istemci, yardimci, monkeypatch):
    """Katı modda (yerel izin kapalı) bulut metadata adresi IdP olarak kullanılamaz."""
    monkeypatch.setattr(ayarlar, "sso_yerel_izin", False)
    yonetici = await yardimci.yonetici()
    organizasyon = await yardimci.organizasyon(sahibi=yonetici)
    saglayici = await _saglayici_ekle(organizasyon.id, issuer="https://169.254.169.254")

    yanit = await istemci.get(
        f"/api/v1/sso/{organizasyon.slug}/{saglayici.slug}/baslat", follow_redirects=False
    )
    assert yanit.status_code == 400
    assert yanit.json()["hata"]["kod"] == "sso_yapilandirilmamis"
    assert yanit.json()["hata"]["ayrinti"]["alan"] == "issuer"


async def test_kesif_issuer_uyusmazligi_reddedilir():
    """Keşif belgesindeki `issuer` yapılandırılanla birebir eşleşmelidir."""
    from arkauc.app.cekirdek.hatalar import GecersizIstek

    saglayici = SsoSaglayici(
        org_id=1,
        tur=SsoTuru.oidc,
        ad="x",
        slug="x",
        ayarlar={"issuer": ISSUER, "client_id": ISTEMCI_ID},
    )

    async def isleyici(_istek: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"issuer": "https://baska.local"})

    with pytest.raises(GecersizIstek) as hata:
        await sso_oidc.kesif_getir(saglayici, tasima=httpx.MockTransport(isleyici))
    assert hata.value.kod == "sso_yapilandirilmamis"
    assert hata.value.ayrinti["alan"] == "issuer"
