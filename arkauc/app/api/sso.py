"""SSO uçları: OIDC + SAML (spec §7)."""

from __future__ import annotations

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek import guvenlik
from arkauc.app.cekirdek.ayarlar import ayarlar
from arkauc.app.cekirdek.bagimliliklar import (
    aktif_organizasyon,
    gecerli_personel,
    veritabani_oturumu,
)
from arkauc.app.cekirdek.denetim import islem_kaydet
from arkauc.app.cekirdek.hatalar import (
    Bulunamadi,
    Cakisma,
    GecersizIstek,
    JetonGecersiz,
    YetkiYok,
)
from arkauc.app.cekirdek.organizasyon import (
    ORG_BASLIGI,  # noqa: F401  (sözleşme dışa aktarımı)
    organizasyon_getir_slug,
    uyelik_getir,
)
from arkauc.app.servisler import sso_oidc, sso_saml
from bdm_veritabani.modeller import (
    ORG_YONETIM_ROLLERI,
    Kullanici,
    KullaniciDurumu,
    Organizasyon,
    OrganizasyonDurumu,
    Oturum,
    Rol,
    SsoKimlik,
    SsoSaglayici,
    SsoTuru,
    Uyelik,
    UyelikDurumu,
    UyelikRolu,
)

router = APIRouter(tags=["sso"])

KOD_TUR = "sso_kod"
KOD_OMRU_SN = 60


class SaglayiciOlustur(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    tur: SsoTuru
    ad: str = Field(min_length=2, max_length=120)
    slug: str | None = Field(default=None, max_length=60)
    etkin: bool = True
    ayarlar: dict[str, str] = Field(default_factory=dict)
    sir: str | None = Field(default=None, max_length=500)


class SaglayiciGuncelle(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    ad: str | None = Field(default=None, min_length=2, max_length=120)
    etkin: bool | None = None
    ayarlar: dict[str, str] | None = None
    sir: str | None = Field(default=None, max_length=500)


class KodDegistirIstegi(BaseModel):
    kod: str


def _saglayici_sozlugu(saglayici: SsoSaglayici) -> dict:
    ayarlar_kopya = {
        anahtar: deger
        for anahtar, deger in (saglayici.ayarlar or {}).items()
        if "secret" not in anahtar and "sifre" not in anahtar
    }
    return {
        "id": saglayici.id,
        "tur": saglayici.tur.value,
        "ad": saglayici.ad,
        "slug": saglayici.slug,
        "etkin": saglayici.etkin,
        "ayarlar": ayarlar_kopya,
        "sir_tanimli": bool(saglayici.sir_sifreli),
        "giris_yolu": f"/api/v1/sso/{{org}}/{saglayici.slug}/baslat",
        "olusturulma": saglayici.olusturulma.isoformat() if saglayici.olusturulma else None,
    }


async def _saglayici_getir(oturum: AsyncSession, org_id: int, saglayici_id: int) -> SsoSaglayici:
    saglayici = await oturum.get(SsoSaglayici, saglayici_id)
    if saglayici is None or saglayici.org_id != org_id:
        raise Bulunamadi("bulunamadi", {"saglayici_id": saglayici_id})
    return saglayici


async def _saglayici_slug_ile(
    oturum: AsyncSession, org_slug: str, saglayici_slug: str
) -> tuple[Organizasyon, SsoSaglayici]:
    organizasyon = await organizasyon_getir_slug(oturum, org_slug)
    if organizasyon is None or organizasyon.durum != OrganizasyonDurumu.aktif:
        raise Bulunamadi("bulunamadi", {"organizasyon": org_slug})
    saglayici = (
        await oturum.execute(
            sa.select(SsoSaglayici).where(
                SsoSaglayici.org_id == organizasyon.id,
                SsoSaglayici.slug == saglayici_slug,
            )
        )
    ).scalar_one_or_none()
    if saglayici is None or not saglayici.etkin:
        raise GecersizIstek("sso_yapilandirilmamis", {"saglayici": saglayici_slug})
    return organizasyon, saglayici


def _api_tabani(istek: Request) -> str:
    return str(istek.base_url).rstrip("/") + "/api/v1"


# -- sağlayıcı yönetimi --------------------------------------------------------


@router.get("/sso/saglayicilar")
async def saglayicilari_listele(
    oturum: AsyncSession = Depends(veritabani_oturumu),
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
    _personel: Kullanici = Depends(gecerli_personel()),
) -> list[dict]:
    satirlar = (
        await oturum.execute(
            sa.select(SsoSaglayici)
            .where(SsoSaglayici.org_id == organizasyon.id)
            .order_by(SsoSaglayici.id)
        )
    ).scalars().all()
    return [_saglayici_sozlugu(saglayici) for saglayici in satirlar]


@router.post("/sso/saglayicilar", status_code=201)
async def saglayici_olustur(
    veri: SaglayiciOlustur,
    istek: Request,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
    personel: Kullanici = Depends(gecerli_personel(ORG_YONETIM_ROLLERI)),
) -> dict:
    from bdm_listesi.katalog import slug_uret

    slug = slug_uret(veri.slug or veri.ad)[:60] or "sso"
    mevcut = (
        await oturum.execute(
            sa.select(SsoSaglayici.id).where(
                SsoSaglayici.org_id == organizasyon.id, SsoSaglayici.slug == slug
            )
        )
    ).scalar_one_or_none()
    if mevcut is not None:
        raise Cakisma(f"'{slug}' slug'ı zaten kullanılıyor.", {"alan": "slug"})

    saglayici = SsoSaglayici(
        org_id=organizasyon.id,
        tur=veri.tur,
        ad=veri.ad,
        slug=slug,
        etkin=veri.etkin,
        ayarlar=veri.ayarlar,
        sir_sifreli=guvenlik.sifrele(veri.sir) if veri.sir else None,
    )
    oturum.add(saglayici)
    await islem_kaydet(
        oturum,
        "sso.saglayici_olusturuldu",
        org_id=organizasyon.id,
        kullanici_id=personel.id,
        hedef_tur="sso_saglayici",
        hedef_id=saglayici.slug,
        ayrinti={"tur": veri.tur.value},
        ip=istek.client.host if istek.client else "",
    )
    await oturum.flush()
    return _saglayici_sozlugu(saglayici)


@router.patch("/sso/saglayicilar/{saglayici_id}")
async def saglayici_guncelle(
    saglayici_id: int,
    veri: SaglayiciGuncelle,
    istek: Request,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
    personel: Kullanici = Depends(gecerli_personel(ORG_YONETIM_ROLLERI)),
) -> dict:
    saglayici = await _saglayici_getir(oturum, organizasyon.id, saglayici_id)
    ham = veri.model_dump(exclude_unset=True)
    if "ad" in ham and ham["ad"]:
        saglayici.ad = ham["ad"]
    if "etkin" in ham and ham["etkin"] is not None:
        saglayici.etkin = ham["etkin"]
    if "ayarlar" in ham and ham["ayarlar"] is not None:
        saglayici.ayarlar = {**(saglayici.ayarlar or {}), **ham["ayarlar"]}
    if "sir" in ham and ham["sir"]:
        saglayici.sir_sifreli = guvenlik.sifrele(ham["sir"])
    await islem_kaydet(
        oturum,
        "sso.saglayici_guncellendi",
        org_id=organizasyon.id,
        kullanici_id=personel.id,
        hedef_tur="sso_saglayici",
        hedef_id=saglayici.id,
        ayrinti={"alanlar": sorted(ham)},
        ip=istek.client.host if istek.client else "",
    )
    await oturum.flush()
    return _saglayici_sozlugu(saglayici)


@router.delete("/sso/saglayicilar/{saglayici_id}", status_code=204, response_model=None)
async def saglayici_sil(
    saglayici_id: int,
    istek: Request,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
    personel: Kullanici = Depends(gecerli_personel(ORG_YONETIM_ROLLERI)),
) -> None:
    saglayici = await _saglayici_getir(oturum, organizasyon.id, saglayici_id)
    await oturum.delete(saglayici)
    await islem_kaydet(
        oturum,
        "sso.saglayici_silindi",
        org_id=organizasyon.id,
        kullanici_id=personel.id,
        hedef_tur="sso_saglayici",
        hedef_id=saglayici_id,
        ip=istek.client.host if istek.client else "",
    )
    await oturum.flush()


# -- giriş akışı ---------------------------------------------------------------


@router.get("/sso/{org_slug}/{saglayici_slug}/baslat")
async def giris_baslat(
    org_slug: str,
    saglayici_slug: str,
    istek: Request,
    oturum: AsyncSession = Depends(veritabani_oturumu),
) -> RedirectResponse:
    organizasyon, saglayici = await _saglayici_slug_ile(oturum, org_slug, saglayici_slug)
    taban = _api_tabani(istek)

    if saglayici.tur == SsoTuru.oidc:
        nonce = guvenlik.rastgele_jeton(24)
        dogrulayici, meydan = sso_oidc.pkce_uret()
        donus = f"{taban}/sso/{organizasyon.slug}/{saglayici.slug}/donus"
        state = sso_oidc.state_uret(
            saglayici_id=saglayici.id,
            nonce=nonce,
            code_verifier=dogrulayici,
            donus=donus,
        )
        kesif = await sso_oidc.kesif_getir(saglayici, tasima=sso_oidc.varsayilan_tasima())
        url = sso_oidc.yetkilendirme_url(
            saglayici,
            kesif,
            state=state,
            nonce=nonce,
            code_challenge=meydan,
            yonlendirme=donus,
        )
        return RedirectResponse(url, status_code=302)

    acs = f"{taban}/sso/{organizasyon.slug}/{saglayici.slug}/saml/acs"
    state = sso_oidc.state_uret(
        saglayici_id=saglayici.id, nonce="", code_verifier="", donus=acs
    )
    url, _istek_id = sso_saml.authn_istegi_uret(saglayici, acs_url=acs, relay_state=state)
    return RedirectResponse(url, status_code=302)


@router.get("/sso/{org_slug}/{saglayici_slug}/donus", response_model=None)
async def oidc_donus(
    org_slug: str,
    saglayici_slug: str,
    istek: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    oturum: AsyncSession = Depends(veritabani_oturumu),
) -> JSONResponse | RedirectResponse:
    organizasyon, saglayici = await _saglayici_slug_ile(oturum, org_slug, saglayici_slug)
    if saglayici.tur != SsoTuru.oidc:
        raise GecersizIstek("sso_yapilandirilmamis", {"saglayici": saglayici.slug})
    if error:
        raise JetonGecersiz("sso_dogrulanamadi", {"hata": error}, kod="sso_dogrulanamadi")
    if not code or not state:
        raise GecersizIstek("oidc_durum_gecersiz", kod="oidc_durum_gecersiz")

    govde = sso_oidc.state_coz(state)
    if int(govde.get("sid", 0)) != saglayici.id:
        raise JetonGecersiz("oidc_durum_gecersiz", kod="oidc_durum_gecersiz")

    kesif = await sso_oidc.kesif_getir(saglayici, tasima=sso_oidc.varsayilan_tasima())
    jetonlar = await sso_oidc.kod_degistir(
        saglayici,
        kesif,
        kod=code,
        code_verifier=str(govde.get("cv", "")),
        yonlendirme=str(govde.get("donus", "")),
        tasima=sso_oidc.varsayilan_tasima(),
    )
    id_token = jetonlar.get("id_token")
    if not id_token:
        raise JetonGecersiz("sso_dogrulanamadi", {"alan": "id_token"}, kod="sso_dogrulanamadi")
    dogrulanmis = await sso_oidc.id_jetonu_dogrula(
        saglayici, kesif, id_token, nonce=str(govde.get("nonce", ""))
    )
    bilgi = sso_oidc.kullanici_bilgisi(saglayici, dogrulanmis)
    return await _girisi_tamamla(istek, oturum, organizasyon, saglayici, bilgi)


@router.post("/sso/{org_slug}/{saglayici_slug}/saml/acs", response_model=None)
async def saml_acs(
    org_slug: str,
    saglayici_slug: str,
    istek: Request,
    SAMLResponse: str = Form(...),
    RelayState: str | None = Form(default=None),
    oturum: AsyncSession = Depends(veritabani_oturumu),
) -> JSONResponse | RedirectResponse:
    organizasyon, saglayici = await _saglayici_slug_ile(oturum, org_slug, saglayici_slug)
    if saglayici.tur != SsoTuru.saml:
        raise GecersizIstek("sso_yapilandirilmamis", {"saglayici": saglayici.slug})

    import base64 as _b64

    try:
        xml_metni = _b64.b64decode(SAMLResponse).decode("utf-8")
    except Exception as hata:
        raise JetonGecersiz(
            "saml_yanit_gecersiz", {"neden": "base64"}, kod="saml_yanit_gecersiz"
        ) from hata

    beklenen = None
    if RelayState:
        try:
            beklenen = str(sso_oidc.state_coz(RelayState).get("jti", "")) or None
        except JetonGecersiz:
            beklenen = None

    acs = f"{_api_tabani(istek)}/sso/{organizasyon.slug}/{saglayici.slug}/saml/acs"
    bilgi = sso_saml.yanit_dogrula(
        saglayici, saml_yaniti=xml_metni, acs_url=acs, beklenen_istek_id=None
    )
    return await _girisi_tamamla(istek, oturum, organizasyon, saglayici, bilgi)


@router.post("/sso/kod-degistir")
async def kod_degistir(
    veri: KodDegistirIstegi,
    oturum: AsyncSession = Depends(veritabani_oturumu),
) -> dict:
    """Tek kullanımlık kod ile jetonları alır (yönlendirme akışı sonrası)."""
    govde = guvenlik.jeton_coz(veri.kod, beklenen_tur=KOD_TUR)
    return await _jetonlari_uret(
        oturum,
        kullanici_id=int(govde["sub"]),
        organizasyon_id=int(govde["org"]),
        ip="",
    )


# -- ortak ----------------------------------------------------------------


async def _girisi_tamamla(
    istek: Request,
    oturum: AsyncSession,
    organizasyon: Organizasyon,
    saglayici: SsoSaglayici,
    bilgi: dict[str, str],
) -> JSONResponse | RedirectResponse:
    kullanici = await _kullanici_esle(oturum, organizasyon, saglayici, bilgi)
    await _uyelik_sagla(oturum, organizasyon, kullanici)
    await islem_kaydet(
        oturum,
        "kimlik.sso_giris",
        org_id=organizasyon.id,
        kullanici_id=kullanici.id,
        hedef_tur="sso_saglayici",
        hedef_id=saglayici.slug,
        ip=istek.client.host if istek.client else "",
    )
    await oturum.commit()

    hedef = (ayarlar.sso_yeniden_yonlendirme or "").strip()
    if hedef:
        kod = _tek_kullanimlik_kod(kullanici.id, organizasyon.id)
        ayirici = "&" if "?" in hedef else "?"
        return RedirectResponse(f"{hedef}{ayirici}kod={kod}", status_code=302)

    return JSONResponse(
        await _jetonlari_uret(
            oturum,
            kullanici_id=kullanici.id,
            organizasyon_id=organizasyon.id,
            ip=istek.client.host if istek.client else "",
        )
    )


async def _kullanici_esle(
    oturum: AsyncSession,
    organizasyon: Organizasyon,
    saglayici: SsoSaglayici,
    bilgi: dict[str, str],
) -> Kullanici:
    """Önce `sso_kimlik`, sonra e-posta; yoksa kullanıcı oluşturur."""
    dis_id = bilgi.get("dis_id") or ""
    eposta = (bilgi.get("eposta") or "").lower()
    ad = bilgi.get("ad") or ""

    baglanti = (
        await oturum.execute(
            sa.select(SsoKimlik).where(
                SsoKimlik.saglayici_id == saglayici.id, SsoKimlik.dis_id == dis_id
            )
        )
    ).scalar_one_or_none()
    if baglanti is not None:
        kullanici = await oturum.get(Kullanici, baglanti.kullanici_id)
        if kullanici is None:
            raise Bulunamadi("bulunamadi", {"kullanici_id": baglanti.kullanici_id})
        return kullanici

    kullanici = None
    if eposta:
        kullanici = (
            await oturum.execute(sa.select(Kullanici).where(Kullanici.eposta == eposta))
        ).scalar_one_or_none()

    if kullanici is None:
        if not eposta:
            raise JetonGecersiz(
                "sso_dogrulanamadi", {"alan": "eposta"}, kod="sso_dogrulanamadi"
            )
        kullanici = Kullanici(
            eposta=eposta,
            ad_soyad=ad or eposta.split("@")[0],
            sifre_hash=guvenlik.sifre_hashle(guvenlik.rastgele_jeton(32)),
            rol=Rol.son_kullanici,
            durum=KullaniciDurumu.aktif,
            eposta_dogrulandi=True,
        )
        oturum.add(kullanici)
        await oturum.flush()

    if kullanici.durum == KullaniciDurumu.pasif:
        raise YetkiYok("yetki_yok")

    oturum.add(
        SsoKimlik(
            kullanici_id=kullanici.id,
            saglayici_id=saglayici.id,
            dis_id=dis_id,
            eposta=eposta,
        )
    )
    await oturum.flush()
    return kullanici


async def _uyelik_sagla(
    oturum: AsyncSession, organizasyon: Organizasyon, kullanici: Kullanici
) -> None:
    uyelik = await uyelik_getir(oturum, organizasyon.id, kullanici.id)
    if uyelik is not None:
        if uyelik.durum == UyelikDurumu.pasif:
            raise YetkiYok("yetki_yok")
        return
    if not ayarlar.sso_otomatik_uyelik:
        raise YetkiYok("yetki_yok")
    oturum.add(
        Uyelik(
            organizasyon_id=organizasyon.id,
            kullanici_id=kullanici.id,
            rol=UyelikRolu.son_kullanici,
            durum=UyelikDurumu.aktif,
        )
    )
    await oturum.flush()


def _tek_kullanimlik_kod(kullanici_id: int, organizasyon_id: int) -> str:
    from datetime import datetime, timedelta, timezone

    import jwt

    simdi = datetime.now(timezone.utc)
    govde = {
        "sub": str(kullanici_id),
        "org": int(organizasyon_id),
        "tur": KOD_TUR,
        "jti": guvenlik.rastgele_jeton(12),
        "exp": int((simdi + timedelta(seconds=KOD_OMRU_SN)).timestamp()),
    }
    return jwt.encode(govde, ayarlar.gizli_anahtar, algorithm="HS256")


async def _jetonlari_uret(
    oturum: AsyncSession, *, kullanici_id: int, organizasyon_id: int, ip: str
) -> dict:
    from datetime import datetime, timedelta, timezone

    kullanici = await oturum.get(Kullanici, kullanici_id)
    organizasyon = oturum.get(Organizasyon, organizasyon_id)
    if kullanici is None:
        raise Bulunamadi("bulunamadi", {"kullanici_id": kullanici_id})
    organizasyon = await organizasyon

    erisim, _ = guvenlik.erisim_jetonu_uret(
        kullanici.id, kullanici.rol.value, org_id=organizasyon_id
    )
    yenileme = guvenlik.rastgele_jeton(48)
    oturum.add(
        Oturum(
            kullanici_id=kullanici.id,
            jeton_hash=guvenlik.ozet(yenileme),
            son_kullanma=datetime.now(timezone.utc)
            + timedelta(days=ayarlar.yenileme_omru_gun),
            ip=ip,
        )
    )
    kullanici.son_giris = datetime.now(timezone.utc)
    await oturum.flush()
    return {
        "erisim_jetonu": erisim,
        "yenileme_jetonu": yenileme,
        "kullanici": {
            "id": kullanici.id,
            "eposta": kullanici.eposta,
            "ad_soyad": kullanici.ad_soyad,
            "rol": kullanici.rol.value,
            "durum": kullanici.durum.value,
            "eposta_dogrulandi": kullanici.eposta_dogrulandi,
        },
        "organizasyon": {
            "id": organizasyon.id,
            "ad": organizasyon.ad,
            "slug": organizasyon.slug,
        }
        if organizasyon
        else None,
    }
