"""Posta sablonu uclari (spec §9)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek.bagimliliklar import gecerli_personel, veritabani_oturumu
from arkauc.app.cekirdek.denetim import islem_kaydet
from arkauc.app.cekirdek.hatalar import Bulunamadi, GecersizIstek
from arkauc.app.cekirdek.organizasyon import ORG_BASLIGI  # noqa: F401  (sozlesme disa aktarimi)
from arkauc.app.servisler.posta_sablon import (
    KODLAR,
    onizle,
    sablon_getir,
    sablon_yaz,
    sablonlari_listele,
)
from bdm_veritabani.modeller import (
    ORG_YONETIM_ROLLERI,
    Kullanici,
    Organizasyon,
)

from arkauc.app.cekirdek.bagimliliklar import aktif_organizasyon

router = APIRouter(tags=["posta-sablonlari"])

DILLER = ("tr", "en")


class SablonGuncelle(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    kod: str = Field(min_length=2, max_length=60)
    dil: str = Field(default="tr", max_length=5)
    konu: str = Field(min_length=1, max_length=300)
    govde_metin: str = Field(default="", max_length=20000)
    govde_html: str = Field(default="", max_length=40000)


class OnizlemeIstegi(BaseModel):
    degiskenler: dict[str, str] | None = None
    dil: str = "tr"


@router.get("/posta-sablonlari")
async def sablonlari_getir(
    oturum: AsyncSession = Depends(veritabani_oturumu),
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
    _personel: Kullanici = Depends(gecerli_personel()),
) -> list[dict]:
    """Tum sablon kodlari (TR/EN), organizasyon ozeli isaretli."""
    return await sablonlari_listele(oturum, organizasyon.id)


@router.put("/posta-sablonlari")
async def sablon_kaydet(
    veri: SablonGuncelle,
    istek: Request,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
    personel: Kullanici = Depends(gecerli_personel(ORG_YONETIM_ROLLERI)),
) -> dict:
    """Sablonu olusturur veya gunceller (kod + dil)."""
    if veri.kod not in KODLAR:
        raise GecersizIstek(
            "Geçersiz şablon kodu.", {"gecerli_kodlar": list(KODLAR)}
        )
    if veri.dil not in DILLER:
        raise GecersizIstek("Geçersiz dil.", {"gecerli_diller": list(DILLER)})

    satir = await sablon_yaz(
        oturum,
        organizasyon.id,
        kod=veri.kod,
        dil=veri.dil,
        konu=veri.konu,
        govde_metin=veri.govde_metin,
        govde_html=veri.govde_html,
    )
    await islem_kaydet(
        oturum,
        "posta_sablonu.guncellendi",
        org_id=organizasyon.id,
        kullanici_id=personel.id,
        hedef_tur="posta_sablonu",
        hedef_id=f"{veri.kod}:{veri.dil}",
        ip=istek.client.host if istek.client else "",
    )
    await oturum.flush()
    return {
        "kod": satir.kod,
        "dil": satir.dil,
        "konu": satir.konu,
        "govde_metin": satir.govde_metin,
        "govde_html": satir.govde_html,
        "ozel": True,
    }


@router.post("/posta-sablonlari/{kod}/onizle")
async def sablon_onizle(
    kod: str,
    veri: OnizlemeIstegi,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
    _personel: Kullanici = Depends(gecerli_personel()),
) -> dict:
    """Ornek degiskenlerle onizleme."""
    if kod not in KODLAR:
        raise Bulunamadi("Posta şablonu bulunamadı.", {"kod": kod})
    dil = veri.dil if veri.dil in DILLER else "tr"
    sablon = await sablon_getir(oturum, organizasyon.id, kod, dil)
    return {"kod": kod, "dil": dil, **onizle(sablon, veri.degiskenler)}
