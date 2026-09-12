"""Organizasyon (kiracı) uçları — spec §2.5."""

from __future__ import annotations

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek.bagimliliklar import gecerli_kullanici, veritabani_oturumu
from arkauc.app.cekirdek.denetim import islem_kaydet
from arkauc.app.cekirdek.hatalar import (
    Cakisma,
    GecersizGecis,
    Bulunamadi,
    GecersizIstek,
    YetkiYok,
)
from arkauc.app.cekirdek.organizasyon import (
    aktif_uyelikler,
    organizasyon_getir,
    rol_yetkili_mi,
    uyelik_getir,
)
from bdm_listesi.katalog import slug_uret
from bdm_veritabani.modeller import (
    ORG_YONETIM_ROLLERI,
    Kullanici,
    Organizasyon,
    OrganizasyonDurumu,
    Uyelik,
    UyelikDurumu,
    UyelikRolu,
)

router = APIRouter(tags=["organizasyonlar"])

#: Organizasyon yonetiminde personel sayilan roller (goruntuleme icin).
GORUNTULEME_ROLLERI: tuple[UyelikRolu, ...] = (
    UyelikRolu.sahip,
    UyelikRolu.yonetici,
    UyelikRolu.operator,
    UyelikRolu.izleyici,
)


class OrganizasyonOlustur(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    ad: str = Field(min_length=2, max_length=160)
    slug: str | None = Field(default=None, max_length=80)


class OrganizasyonGuncelle(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    ad: str | None = Field(default=None, min_length=2, max_length=160)
    durum: OrganizasyonDurumu | None = None


class UyeEkle(BaseModel):
    eposta: str | None = Field(default=None, max_length=320)
    kullanici_id: int | None = None
    rol: UyelikRolu = UyelikRolu.son_kullanici


class UyeGuncelle(BaseModel):
    rol: UyelikRolu | None = None
    durum: UyelikDurumu | None = None


class OrganizasyonSec(BaseModel):
    organizasyon_id: int


def _organizasyon_sozlugu(organizasyon: Organizasyon, rol: UyelikRolu | None = None) -> dict:
    return {
        "id": organizasyon.id,
        "ad": organizasyon.ad,
        "slug": organizasyon.slug,
        "durum": organizasyon.durum.value,
        "rol": rol.value if rol else None,
        "olusturulma": organizasyon.olusturulma.isoformat() if organizasyon.olusturulma else None,
    }


def _uye_sozlugu(uyelik: Uyelik, kullanici: Kullanici | None) -> dict:
    return {
        "kullanici_id": uyelik.kullanici_id,
        "eposta": kullanici.eposta if kullanici else None,
        "ad_soyad": kullanici.ad_soyad if kullanici else None,
        "rol": uyelik.rol.value,
        "durum": uyelik.durum.value,
        "olusturulma": uyelik.olusturulma.isoformat() if uyelik.olusturulma else None,
    }


async def _uyelik_yetkili(
    oturum: AsyncSession,
    *,
    organizasyon_id: int,
    kullanici: Kullanici,
    roller: tuple[UyelikRolu, ...],
) -> Uyelik:
    uyelik = await uyelik_getir(oturum, organizasyon_id, kullanici.id)
    if uyelik is None or uyelik.durum != UyelikDurumu.aktif:
        raise YetkiYok("Bu organizasyona erişiminiz yok.")
    if not rol_yetkili_mi(uyelik.rol, roller):
        raise YetkiYok()
    return uyelik


async def _tekil_slug(oturum: AsyncSession, ad: str, istenen: str | None) -> str:
    taban = slug_uret(istenen or ad)[:72] or "organizasyon"
    aday = taban
    sayac = 2
    while (
        await oturum.execute(sa.select(Organizasyon.id).where(Organizasyon.slug == aday))
    ).scalar_one_or_none() is not None:
        if istenen:
            raise Cakisma(f"'{taban}' slug'ı zaten kullanılıyor.", {"alan": "slug"})
        aday = f"{taban}-{sayac}"
        sayac += 1
        if sayac > 200:  # pragma: no cover - savunma
            raise Cakisma("Uygun bir slug üretilemedi.")
    return aday


@router.get("/organizasyonlar")
async def organizasyonlari_listele(
    oturum: AsyncSession = Depends(veritabani_oturumu),
    kullanici: Kullanici = Depends(gecerli_kullanici),
) -> list[dict]:
    """Kullanicinin uye oldugu organizasyonlar."""
    uyelikler = await aktif_uyelikler(oturum, kullanici.id)
    sonuc: list[dict] = []
    for uyelik in uyelikler:
        organizasyon = await oturum.get(Organizasyon, uyelik.organizasyon_id)
        if organizasyon is not None:
            sonuc.append(_organizasyon_sozlugu(organizasyon, uyelik.rol))
    return sonuc


@router.post("/organizasyonlar", status_code=201)
async def organizasyon_olustur(
    veri: OrganizasyonOlustur,
    istek: Request,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    kullanici: Kullanici = Depends(gecerli_kullanici),
) -> dict:
    """Yeni organizasyon; olusturan kisi `sahip` olur."""
    slug = await _tekil_slug(oturum, veri.ad, veri.slug)
    organizasyon = Organizasyon(ad=veri.ad, slug=slug, durum=OrganizasyonDurumu.aktif)
    oturum.add(organizasyon)
    await oturum.flush()
    oturum.add(
        Uyelik(
            organizasyon_id=organizasyon.id,
            kullanici_id=kullanici.id,
            rol=UyelikRolu.sahip,
            durum=UyelikDurumu.aktif,
        )
    )
    await islem_kaydet(
        oturum,
        "organizasyon.olusturuldu",
        kullanici_id=kullanici.id,
        hedef_tur="organizasyon",
        hedef_id=organizasyon.id,
        ayrinti={"slug": slug},
        ip=istek.client.host if istek.client else "",
    )
    await oturum.flush()
    return _organizasyon_sozlugu(organizasyon, UyelikRolu.sahip)


@router.get("/organizasyonlar/{organizasyon_id}")
async def organizasyon_getir_uc(
    organizasyon_id: int,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    kullanici: Kullanici = Depends(gecerli_kullanici),
) -> dict:
    uyelik = await _uyelik_yetkili(
        oturum,
        organizasyon_id=organizasyon_id,
        kullanici=kullanici,
        roller=GORUNTULEME_ROLLERI,
    )
    organizasyon = await organizasyon_getir(oturum, organizasyon_id)
    return _organizasyon_sozlugu(organizasyon, uyelik.rol)


@router.patch("/organizasyonlar/{organizasyon_id}")
async def organizasyon_guncelle(
    organizasyon_id: int,
    veri: OrganizasyonGuncelle,
    istek: Request,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    kullanici: Kullanici = Depends(gecerli_kullanici),
) -> dict:
    uyelik = await _uyelik_yetkili(
        oturum,
        organizasyon_id=organizasyon_id,
        kullanici=kullanici,
        roller=ORG_YONETIM_ROLLERI,
    )
    organizasyon = await organizasyon_getir(oturum, organizasyon_id)
    ham = veri.model_dump(exclude_unset=True)
    if "ad" in ham and ham["ad"]:
        organizasyon.ad = ham["ad"]
    if "durum" in ham and ham["durum"] is not None:
        organizasyon.durum = ham["durum"]
    await islem_kaydet(
        oturum,
        "organizasyon.guncellendi",
        kullanici_id=kullanici.id,
        hedef_tur="organizasyon",
        hedef_id=organizasyon.id,
        ayrinti={"alanlar": sorted(ham)},
        ip=istek.client.host if istek.client else "",
    )
    await oturum.flush()
    return _organizasyon_sozlugu(organizasyon, uyelik.rol)


@router.get("/organizasyonlar/{organizasyon_id}/uyeler")
async def uyeleri_listele(
    organizasyon_id: int,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    kullanici: Kullanici = Depends(gecerli_kullanici),
) -> list[dict]:
    await _uyelik_yetkili(
        oturum,
        organizasyon_id=organizasyon_id,
        kullanici=kullanici,
        roller=GORUNTULEME_ROLLERI,
    )
    satirlar = (
        await oturum.execute(
            sa.select(Uyelik, Kullanici)
            .join(Kullanici, Kullanici.id == Uyelik.kullanici_id)
            .where(Uyelik.organizasyon_id == organizasyon_id)
            .order_by(Uyelik.id)
        )
    ).all()
    return [_uye_sozlugu(uyelik, uye) for uyelik, uye in satirlar]


@router.post("/organizasyonlar/{organizasyon_id}/uyeler", status_code=201)
async def uye_ekle(
    organizasyon_id: int,
    veri: UyeEkle,
    istek: Request,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    kullanici: Kullanici = Depends(gecerli_kullanici),
) -> dict:
    await _uyelik_yetkili(
        oturum,
        organizasyon_id=organizasyon_id,
        kullanici=kullanici,
        roller=ORG_YONETIM_ROLLERI,
    )
    hedef = await _kullanici_bul(oturum, veri)
    mevcut = await uyelik_getir(oturum, organizasyon_id, hedef.id)
    if mevcut is not None:
        raise Cakisma("Bu kullanıcı zaten organizasyonun üyesi.")
    uyelik = Uyelik(
        organizasyon_id=organizasyon_id,
        kullanici_id=hedef.id,
        rol=veri.rol,
        durum=UyelikDurumu.aktif,
    )
    oturum.add(uyelik)
    await islem_kaydet(
        oturum,
        "uyelik.eklendi",
        kullanici_id=kullanici.id,
        hedef_tur="uyelik",
        hedef_id=f"{organizasyon_id}:{hedef.id}",
        ayrinti={"rol": veri.rol.value},
        ip=istek.client.host if istek.client else "",
    )
    await oturum.flush()
    return _uye_sozlugu(uyelik, hedef)


@router.patch("/organizasyonlar/{organizasyon_id}/uyeler/{kullanici_id}")
async def uye_guncelle(
    organizasyon_id: int,
    kullanici_id: int,
    veri: UyeGuncelle,
    istek: Request,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    kullanici: Kullanici = Depends(gecerli_kullanici),
) -> dict:
    await _uyelik_yetkili(
        oturum,
        organizasyon_id=organizasyon_id,
        kullanici=kullanici,
        roller=ORG_YONETIM_ROLLERI,
    )
    uyelik = await uyelik_getir(oturum, organizasyon_id, kullanici_id)
    if uyelik is None:
        raise Bulunamadi("Üyelik bulunamadı.")

    ham = veri.model_dump(exclude_unset=True)
    sahip_dusuyor = (
        uyelik.rol == UyelikRolu.sahip
        and (
            ("rol" in ham and ham["rol"] is not None and ham["rol"] != UyelikRolu.sahip)
            or ("durum" in ham and ham["durum"] is not None and ham["durum"] != UyelikDurumu.aktif)
        )
    )
    if sahip_dusuyor:
        if uyelik.kullanici_id == kullanici.id:
            raise GecersizGecis("Kendi sahip rolünüzü düşüremezsiniz.")
        kalan = (
            await oturum.execute(
                sa.select(sa.func.count())
                .select_from(Uyelik)
                .where(
                    Uyelik.organizasyon_id == organizasyon_id,
                    Uyelik.rol == UyelikRolu.sahip,
                    Uyelik.durum == UyelikDurumu.aktif,
                )
            )
        ).scalar_one()
        if int(kalan) <= 1:
            raise GecersizGecis("Son sahip düşürülemez veya silinemez.")

    if "rol" in ham and ham["rol"] is not None:
        uyelik.rol = ham["rol"]
    if "durum" in ham and ham["durum"] is not None:
        uyelik.durum = ham["durum"]
    await islem_kaydet(
        oturum,
        "uyelik.guncellendi",
        kullanici_id=kullanici.id,
        hedef_tur="uyelik",
        hedef_id=f"{organizasyon_id}:{kullanici_id}",
        ayrinti={"alanlar": sorted(ham)},
        ip=istek.client.host if istek.client else "",
    )
    await oturum.flush()
    hedef = await oturum.get(Kullanici, kullanici_id)
    return _uye_sozlugu(uyelik, hedef)


@router.delete("/organizasyonlar/{organizasyon_id}/uyeler/{kullanici_id}", status_code=204, response_model=None)
async def uye_sil(
    organizasyon_id: int,
    kullanici_id: int,
    istek: Request,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    kullanici: Kullanici = Depends(gecerli_kullanici),
) -> None:
    await _uyelik_yetkili(
        oturum,
        organizasyon_id=organizasyon_id,
        kullanici=kullanici,
        roller=ORG_YONETIM_ROLLERI,
    )
    uyelik = await uyelik_getir(oturum, organizasyon_id, kullanici_id)
    if uyelik is None:
        raise Bulunamadi("Üyelik bulunamadı.")
    if uyelik.rol == UyelikRolu.sahip:
        if uyelik.kullanici_id == kullanici.id:
            raise GecersizGecis("Kendi sahip üyeliğinizi silemezsiniz.")
        kalan = (
            await oturum.execute(
                sa.select(sa.func.count())
                .select_from(Uyelik)
                .where(
                    Uyelik.organizasyon_id == organizasyon_id,
                    Uyelik.rol == UyelikRolu.sahip,
                    Uyelik.durum == UyelikDurumu.aktif,
                )
            )
        ).scalar_one()
        if int(kalan) <= 1:
            raise GecersizGecis("Son sahip düşürülemez veya silinemez.")
    await oturum.delete(uyelik)
    await islem_kaydet(
        oturum,
        "uyelik.silindi",
        kullanici_id=kullanici.id,
        hedef_tur="uyelik",
        hedef_id=f"{organizasyon_id}:{kullanici_id}",
        ip=istek.client.host if istek.client else "",
    )
    await oturum.flush()


@router.post("/kimlik/organizasyon-sec")
async def organizasyon_sec(
    veri: OrganizasyonSec,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    kullanici: Kullanici = Depends(gecerli_kullanici),
) -> dict:
    """Aktif organizasyonu degistirir ve yeni erisim jetonu doner."""
    from arkauc.app.cekirdek import guvenlik

    uyelik = await _uyelik_yetkili(
        oturum,
        organizasyon_id=veri.organizasyon_id,
        kullanici=kullanici,
        roller=GORUNTULEME_ROLLERI,
    )
    organizasyon = await organizasyon_getir(oturum, veri.organizasyon_id)
    jeton, _ = guvenlik.erisim_jetonu_uret(
        kullanici.id, kullanici.rol.value, org_id=organizasyon.id
    )
    return {
        "erisim_jetonu": jeton,
        "organizasyon": _organizasyon_sozlugu(organizasyon, uyelik.rol),
    }


async def _kullanici_bul(oturum: AsyncSession, veri: UyeEkle) -> Kullanici:
    if veri.kullanici_id is not None:
        kullanici = await oturum.get(Kullanici, veri.kullanici_id)
        if kullanici is None:
            raise Bulunamadi("Kullanıcı bulunamadı.")
        return kullanici
    if not veri.eposta:
        raise GecersizIstek("E-posta veya kullanıcı kimliği zorunludur.")
    kullanici = (
        await oturum.execute(
            sa.select(Kullanici).where(Kullanici.eposta == veri.eposta.strip().lower())
        )
    ).scalar_one_or_none()
    if kullanici is None:
        raise Bulunamadi("Bu e-posta ile kayıtlı kullanıcı yok.")
    return kullanici
