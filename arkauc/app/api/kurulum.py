"""Kurulum sihirbazı ucu (API §4).

Tek seferliktir: `ayar.kurulum_tamam` yazıldıktan sonra gelen istekler
`409 kurulum_zaten_tamam` ile reddedilir.
"""

from __future__ import annotations

import inspect

import sqlalchemy as sa
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek.ayarlar_db import ayar_oku, ayar_yaz
from arkauc.app.cekirdek.bagimliliklar import veritabani_oturumu
from arkauc.app.cekirdek.denetim import islem_kaydet
from arkauc.app.cekirdek.guvenlik import sifre_hashle
from arkauc.app.cekirdek.hatalar import Cakisma
from bdm_listesi import BdmOlustur, bdm_olustur, bdm_sozlugu
from bdm_veritabani.modeller import Bdm, Kullanici, KullaniciDurumu, Rol

router = APIRouter()


class YoneticiGirdisi(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    eposta: EmailStr
    ad_soyad: str = Field(min_length=2, max_length=160)
    parola: str = Field(min_length=8, max_length=200)


class KurulumIstegi(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    marka_adi: str = Field(min_length=1, max_length=160)
    yonetici: YoneticiGirdisi
    bdm: BdmOlustur
    dogrula: bool = False


def _kullanici_sozlugu(kullanici: Kullanici) -> dict[str, object]:
    """API §2 `Kullanici` temsili (parola özeti asla dönmez)."""
    return {
        "id": kullanici.id,
        "eposta": kullanici.eposta,
        "ad_soyad": kullanici.ad_soyad,
        "rol": kullanici.rol.value,
        "durum": kullanici.durum.value,
        "eposta_dogrulandi": kullanici.eposta_dogrulandi,
        "olusturulma": kullanici.olusturulma.isoformat() if kullanici.olusturulma else None,
        "son_giris": kullanici.son_giris.isoformat() if kullanici.son_giris else None,
    }


async def _upstream_dogrula(
    oturum: AsyncSession, bdm: Bdm
) -> dict[str, object] | None:
    """Hazırlama ucu hazır olduğunda upstream doğrulamasını çalıştırır.

    `bdm_hazırlama_ucu` paralel geliştirildiği için içe aktarma burada yapılır;
    modül henüz yoksa doğrulama atlanır ve `null` döner.
    """
    try:
        from bdm_hazırlama_ucu.dogrulama import dogrula
    except ImportError:
        return None

    imza = inspect.signature(dogrula)
    adlar = set(imza.parameters)
    konumsal = [
        parametre
        for parametre in imza.parameters.values()
        if parametre.kind
        in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]
    if {"oturum", "bdm"} <= adlar:
        sonuc = await dogrula(oturum=oturum, bdm=bdm)
    elif len(konumsal) >= 2:
        sonuc = await dogrula(oturum, bdm)
    else:
        sonuc = await dogrula(bdm)
    if sonuc is None:
        return None
    if isinstance(sonuc, dict):
        basarili = sonuc.get("basarili")
        mesaj = sonuc.get("mesaj")
    else:
        basarili = getattr(sonuc, "basarili", None)
        mesaj = getattr(sonuc, "mesaj", None)
    return {"basarili": bool(basarili), "mesaj": str(mesaj or "")}


@router.post("/kurulum", status_code=201)
async def kurulumu_tamamla(
    govde: KurulumIstegi,
    oturum: AsyncSession = Depends(veritabani_oturumu),
) -> dict[str, object]:
    """Yöneticiyi ve ilk BDM'i oluşturur, marka ayarlarını yazar."""
    if await ayar_oku(oturum, "kurulum_tamam", False):
        raise Cakisma("Kurulum daha önce tamamlanmış.", kod="kurulum_zaten_tamam")

    eposta = str(govde.yonetici.eposta).lower()
    mevcut = (
        await oturum.execute(sa.select(Kullanici.id).where(Kullanici.eposta == eposta))
    ).scalar_one_or_none()
    if mevcut is not None:
        raise Cakisma("Bu e-posta ile kayıtlı bir kullanıcı var.", {"alan": "eposta"})

    yonetici = Kullanici(
        eposta=eposta,
        ad_soyad=govde.yonetici.ad_soyad,
        sifre_hash=sifre_hashle(govde.yonetici.parola),
        rol=Rol.yonetici,
        durum=KullaniciDurumu.aktif,
        eposta_dogrulandi=True,
    )
    oturum.add(yonetici)
    await oturum.flush()

    bdm = await bdm_olustur(oturum, govde.bdm)

    await ayar_yaz(oturum, "marka_adi", govde.marka_adi)
    await ayar_yaz(oturum, "varsayilan_bdm_slug", bdm.slug)
    await ayar_yaz(oturum, "kurulum_tamam", True)
    await islem_kaydet(
        oturum,
        "kurulum.tamamlandi",
        kullanici_id=yonetici.id,
        hedef_tur="bdm",
        hedef_id=bdm.id,
        ayrinti={"marka_adi": govde.marka_adi, "bdm_slug": bdm.slug},
    )

    dogrulama = await _upstream_dogrula(oturum, bdm) if govde.dogrula else None
    return {
        "yonetici": _kullanici_sozlugu(yonetici),
        "bdm": bdm_sozlugu(bdm),
        "dogrulama": dogrulama,
        "kurulum_tamam": True,
    }
