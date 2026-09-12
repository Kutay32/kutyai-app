"""Medya uclari: gorsel uretimi, ses uretimi ve ses cozumu (spec §8).

Uretim kaynak tukettigi icin uclar yazma yetkili personelle sinirlidir
(`sahip`/`yonetici`/`operator`; `izleyici` ve `son_kullanici` 403 alir).
Uretilenler aktif organizasyon kapsaminda `dosya` tablosuna yazilir; her
deneme (basarili ya da hatali) `kullanim_kaydi`'na islenir.

Tasima `varsayilan_tasima` bagimliligi ile enjekte edilir; testler bunu
`httpx.MockTransport` ile gecersiz kilar.
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek.bagimliliklar import (
    aktif_organizasyon,
    gecerli_personel,
    veritabani_oturumu,
)
from arkauc.app.cekirdek.hatalar import Bulunamadi, KutyaiHatasi
from arkauc.app.servisler import medya
from arkauc.app.servisler.dosya import dosya_kaydet, icerik_oku
from bdm_konusma_gecmisi import kullanim_yaz
from bdm_listesi import bdm_getir
from bdm_veritabani.modeller import (
    Bdm,
    Dosya,
    KullanimDurumu,
    Kullanici,
    Organizasyon,
    UyelikRolu,
)

router = APIRouter(tags=["medya"])

#: Medya uretimi kaynak tukettigi icin yalniz yazma yetkili roller.
MEDYA_ROLLERI: tuple[UyelikRolu, ...] = (
    UyelikRolu.sahip,
    UyelikRolu.yonetici,
    UyelikRolu.operator,
)

_personel = gecerli_personel(MEDYA_ROLLERI)

#: OpenAI `size` alani: "1024x1024" biciminde iki sayi.
BOYUT_DESENI = re.compile(r"^\d{2,5}x\d{2,5}$")


class GorselIstegi(BaseModel):
    """`POST /medya/gorsel` govdesi."""

    model_config = ConfigDict(str_strip_whitespace=True)

    bdm_id: int
    istem: str = Field(min_length=1, max_length=4000)
    boyut: str = Field(default=medya.VARSAYILAN_BOYUT, max_length=20)
    adet: int = Field(default=1, ge=1, le=10)

    @field_validator("boyut")
    @classmethod
    def _boyut_dogrula(cls, deger: str) -> str:
        if not BOYUT_DESENI.match(deger):
            raise ValueError("Boyut '1024x1024' biciminde olmalidir.")
        return deger


class SesIstegi(BaseModel):
    """`POST /medya/ses` govdesi."""

    model_config = ConfigDict(str_strip_whitespace=True)

    bdm_id: int
    metin: str = Field(min_length=1, max_length=4096)
    ses: str = Field(default=medya.VARSAYILAN_SES, max_length=40)
    bicim: str = Field(default=medya.VARSAYILAN_BICIM, max_length=10)

    @field_validator("bicim")
    @classmethod
    def _bicim_dogrula(cls, deger: str) -> str:
        if deger.lower() not in medya.SES_BICIMLERI:
            raise ValueError("Desteklenen bicimler: " + ", ".join(medya.SES_BICIMLERI))
        return deger.lower()


class CozumIstegi(BaseModel):
    """`POST /medya/coz` govdesi."""

    bdm_id: int
    dosya_id: int


def varsayilan_tasima() -> httpx.AsyncBaseTransport | None:
    """Varsayilan ag tasimasi; testler `MockTransport` ile gecersiz kilar."""
    return None


def _zaman_damgasi() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S%f")


def _gecen_ms(baslangic: float) -> int:
    return max(0, int((time.perf_counter() - baslangic) * 1000))


def _dosya_sozlugu(dosya: Dosya) -> dict[str, object]:
    """Uretilen dosyanin istemciye donen ozeti."""
    return {
        "dosya_id": dosya.id,
        "ad": dosya.ad,
        "mime": dosya.mime,
        "boyut": dosya.boyut,
    }


async def _bdm_coz(oturum: AsyncSession, organizasyon: Organizasyon, bdm_id: int) -> Bdm:
    """BDM'yi aktif organizasyon kapsaminda cozer; org disi kayit 404 doner."""
    bdm = await bdm_getir(oturum, bdm_id)
    if bdm.org_id != organizasyon.id:
        raise Bulunamadi("BDM kaydı bulunamadı.", {"bdm_id": bdm_id})
    return bdm


async def _kullanimi_kaydet(
    oturum: AsyncSession,
    *,
    bdm: Bdm,
    organizasyon: Organizasyon,
    kullanici: Kullanici,
    baslangic: float,
    durum: KullanimDurumu,
) -> None:
    """Kullanim kaydini yazar ve commit eder (her deneme islenir)."""
    await kullanim_yaz(
        oturum,
        bdm_id=bdm.id,
        org_id=organizasyon.id,
        kullanici_id=kullanici.id,
        gecikme_ms=_gecen_ms(baslangic),
        durum=durum,
    )
    await oturum.commit()


@router.post("/medya/gorsel")
async def gorsel_uret_ucu(
    istek: GorselIstegi,
    kullanici: Kullanici = Depends(_personel),
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
    oturum: AsyncSession = Depends(veritabani_oturumu),
    tasima: httpx.AsyncBaseTransport | None = Depends(varsayilan_tasima),
) -> list[dict[str, object]]:
    """Gorsel uretir; her gorseli `dosya` tablosuna yazar."""
    bdm = await _bdm_coz(oturum, organizasyon, istek.bdm_id)
    baslangic = time.perf_counter()
    try:
        gorseller = await medya.gorsel_uret(
            bdm, istek.istem, boyut=istek.boyut, adet=istek.adet, tasima=tasima
        )
    except KutyaiHatasi:
        await _kullanimi_kaydet(
            oturum,
            bdm=bdm,
            organizasyon=organizasyon,
            kullanici=kullanici,
            baslangic=baslangic,
            durum=KullanimDurumu.hata,
        )
        raise
    damga = _zaman_damgasi()
    kayitlar: list[dict[str, object]] = []
    for sira, icerik in enumerate(gorseller, start=1):
        uzanti, mime = medya.gorsel_mime(icerik)
        dosya = await dosya_kaydet(
            oturum,
            org_id=organizasyon.id,
            kullanici_id=kullanici.id,
            ad=f"gorsel-{bdm.slug}-{damga}-{sira}.{uzanti}",
            mime=mime,
            icerik=icerik,
        )
        kayitlar.append(_dosya_sozlugu(dosya))
    await _kullanimi_kaydet(
        oturum,
        bdm=bdm,
        organizasyon=organizasyon,
        kullanici=kullanici,
        baslangic=baslangic,
        durum=KullanimDurumu.basarili,
    )
    return kayitlar


@router.post("/medya/ses")
async def ses_uret_ucu(
    istek: SesIstegi,
    kullanici: Kullanici = Depends(_personel),
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
    oturum: AsyncSession = Depends(veritabani_oturumu),
    tasima: httpx.AsyncBaseTransport | None = Depends(varsayilan_tasima),
) -> dict[str, object]:
    """Metni sese cevirir; sonucu `dosya` tablosuna yazar."""
    bdm = await _bdm_coz(oturum, organizasyon, istek.bdm_id)
    baslangic = time.perf_counter()
    try:
        icerik = await medya.ses_uret(
            bdm, istek.metin, ses=istek.ses, bicim=istek.bicim, tasima=tasima
        )
    except KutyaiHatasi:
        await _kullanimi_kaydet(
            oturum,
            bdm=bdm,
            organizasyon=organizasyon,
            kullanici=kullanici,
            baslangic=baslangic,
            durum=KullanimDurumu.hata,
        )
        raise
    uzanti, mime = medya.SES_BICIMLERI[istek.bicim]
    dosya = await dosya_kaydet(
        oturum,
        org_id=organizasyon.id,
        kullanici_id=kullanici.id,
        ad=f"ses-{bdm.slug}-{_zaman_damgasi()}.{uzanti}",
        mime=mime,
        icerik=icerik,
    )
    await _kullanimi_kaydet(
        oturum,
        bdm=bdm,
        organizasyon=organizasyon,
        kullanici=kullanici,
        baslangic=baslangic,
        durum=KullanimDurumu.basarili,
    )
    return {"dosya_id": dosya.id}


@router.post("/medya/coz")
async def ses_coz_ucu(
    istek: CozumIstegi,
    kullanici: Kullanici = Depends(_personel),
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
    oturum: AsyncSession = Depends(veritabani_oturumu),
    tasima: httpx.AsyncBaseTransport | None = Depends(varsayilan_tasima),
) -> dict[str, str]:
    """Organizasyondaki bir ses dosyasini metne cevirir."""
    bdm = await _bdm_coz(oturum, organizasyon, istek.bdm_id)
    dosya, icerik = await icerik_oku(oturum, organizasyon.id, istek.dosya_id)
    baslangic = time.perf_counter()
    try:
        metin = await medya.ses_coz(bdm, dosya.ad, icerik, tasima=tasima)
    except KutyaiHatasi:
        await _kullanimi_kaydet(
            oturum,
            bdm=bdm,
            organizasyon=organizasyon,
            kullanici=kullanici,
            baslangic=baslangic,
            durum=KullanimDurumu.hata,
        )
        raise
    await _kullanimi_kaydet(
        oturum,
        bdm=bdm,
        organizasyon=organizasyon,
        kullanici=kullanici,
        baslangic=baslangic,
        durum=KullanimDurumu.basarili,
    )
    return {"metin": metin}
