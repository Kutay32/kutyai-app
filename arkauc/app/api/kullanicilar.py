"""Kullanici yonetimi uclari — yalnizca yonetici (API.md §6).

Tum uclar aktif organizasyon kapsamindadir: liste yalniz organizasyonun
uyelerini doner, hedef kullanici organizasyon uyesi degilse `404 bulunamadi`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek.bagimliliklar import (
    aktif_organizasyon,
    gecerli_personel,
    veritabani_oturumu,
)
from arkauc.app.cekirdek.denetim import islem_kaydet
from arkauc.app.cekirdek.hatalar import Bulunamadi, GecersizGecis
from arkauc.app.cekirdek.organizasyon import uyelik_getir
from arkauc.app.servisler import kimlik as kimlik_servisi
from bdm_veritabani.modeller import Kullanici, KullaniciDurumu, Organizasyon, Rol

router = APIRouter(prefix="/kullanicilar", tags=["kullanicilar"])

YONETICI = (Rol.yonetici,)


class KullaniciOlusturIstegi(BaseModel):
    eposta: str
    ad_soyad: str = ""
    parola: str
    rol: Rol = Rol.son_kullanici


class KullaniciGuncelleIstegi(BaseModel):
    rol: Rol | None = None
    durum: KullaniciDurumu | None = None
    ad_soyad: str | None = None


def _ip(istek: Request) -> str:
    return istek.client.host if istek.client else ""


async def _kullanici_getir(
    oturum: AsyncSession, organizasyon_id: int, kullanici_id: int
) -> Kullanici:
    """Hedef kullanici; aktif organizasyonun uyesi degilse yok sayilir."""
    kullanici = await kimlik_servisi.kullanici_getir(oturum, kullanici_id)
    if kullanici is None:
        raise Bulunamadi("Kullanıcı bulunamadı.")
    if await uyelik_getir(oturum, organizasyon_id, kullanici_id) is None:
        raise Bulunamadi("Kullanıcı bulunamadı.")
    return kullanici


@router.get("")
async def kullanicilari_listele(
    rol: Rol | None = None,
    durum: KullaniciDurumu | None = None,
    arama: str | None = None,
    sayfa: int = 1,
    boyut: int = kimlik_servisi.VARSAYILAN_SAYFA_BOYUTU,
    _yonetici: Kullanici = Depends(gecerli_personel(YONETICI)),
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
    oturum: AsyncSession = Depends(veritabani_oturumu),
) -> dict[str, object]:
    """Aktif organizasyonun uyelerini filtreli, sayfali listeler (`Sayfa<Kullanici>`)."""
    return await kimlik_servisi.kullanicilari_listele(
        oturum,
        organizasyon_id=organizasyon.id,
        rol=rol,
        durum=durum,
        arama=arama,
        sayfa=sayfa,
        boyut=boyut,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def kullanici_olustur(
    veri: KullaniciOlusturIstegi,
    istek: Request,
    yonetici: Kullanici = Depends(gecerli_personel(YONETICI)),
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
    oturum: AsyncSession = Depends(veritabani_oturumu),
) -> dict[str, object]:
    """Yonetici tarafindan personel/kullanici daveti; aktif organizasyona uye yazilir."""
    kullanici = await kimlik_servisi.kullanici_olustur(
        oturum,
        organizasyon_id=organizasyon.id,
        eposta=veri.eposta,
        ad_soyad=veri.ad_soyad,
        parola=veri.parola,
        rol=veri.rol,
    )
    await islem_kaydet(
        oturum,
        "kullanici.olustur",
        org_id=organizasyon.id,
        kullanici_id=yonetici.id,
        hedef_tur="kullanici",
        hedef_id=kullanici.id,
        ayrinti={"rol": kullanici.rol.value},
        ip=_ip(istek),
    )
    return kimlik_servisi.kullanici_sozlugu(kullanici)


@router.patch("/{kullanici_id}")
async def kullanici_guncelle(
    kullanici_id: int,
    veri: KullaniciGuncelleIstegi,
    istek: Request,
    yonetici: Kullanici = Depends(gecerli_personel(YONETICI)),
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
    oturum: AsyncSession = Depends(veritabani_oturumu),
) -> dict[str, object]:
    """Rol, durum ve ad soyad guncellemesi; her degisiklik denetime yazilir."""
    kullanici = await _kullanici_getir(oturum, organizasyon.id, kullanici_id)
    degisenler = veri.model_dump(exclude_unset=True)
    if not degisenler:
        return kimlik_servisi.kullanici_sozlugu(kullanici)
    # Yonetici kendi hesabini kilitleyemez (DELETE ile ayni kural).
    if kullanici.id == yonetici.id:
        if veri.durum == KullaniciDurumu.pasif:
            raise GecersizGecis("Kendi hesabınızı pasifleştiremezsiniz.")
        if veri.rol is not None and veri.rol != kullanici.rol:
            raise GecersizGecis("Kendi rolünüzü değiştiremezsiniz.")

    await kimlik_servisi.kullanici_guncelle(
        oturum,
        kullanici,
        rol=veri.rol,
        durum=veri.durum,
        ad_soyad=veri.ad_soyad,
    )
    await islem_kaydet(
        oturum,
        "kullanici.guncelle",
        org_id=organizasyon.id,
        kullanici_id=yonetici.id,
        hedef_tur="kullanici",
        hedef_id=kullanici.id,
        ayrinti={
            anahtar: (deger.value if hasattr(deger, "value") else deger)
            for anahtar, deger in degisenler.items()
        },
        ip=_ip(istek),
    )
    return kimlik_servisi.kullanici_sozlugu(kullanici)


@router.delete("/{kullanici_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def kullanici_pasiflestir(
    kullanici_id: int,
    istek: Request,
    yonetici: Kullanici = Depends(gecerli_personel(YONETICI)),
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
    oturum: AsyncSession = Depends(veritabani_oturumu),
) -> None:
    """Kullaniciyi silmez, pasiflestirir."""
    if kullanici_id == yonetici.id:
        raise GecersizGecis("Kendi hesabınızı pasifleştiremezsiniz.")
    kullanici = await _kullanici_getir(oturum, organizasyon.id, kullanici_id)
    await kimlik_servisi.kullanici_pasiflestir(oturum, kullanici)
    await islem_kaydet(
        oturum,
        "kullanici.pasiflestir",
        org_id=organizasyon.id,
        kullanici_id=yonetici.id,
        hedef_tur="kullanici",
        hedef_id=kullanici.id,
        ip=_ip(istek),
    )
