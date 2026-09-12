"""BDM yönetim uçları — `/api/v1/bdm/yonetim` (spec §7.6)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek.bagimliliklar import gecerli_personel, veritabani_oturumu
from bdm_listesi import bdm_getir, bdm_sozlugu
from bdm_veritabani.modeller import Kullanici

from . import gunlukler, saglik, surucu_durum, yasam_dongusu

router = APIRouter()


class YolGuncelle(BaseModel):
    """`PATCH /{bdm_id}/yol` gövdesi: takma ad ve yönlendirme önceliği."""

    model_config = ConfigDict(str_strip_whitespace=True)

    oncelik: int | None = Field(default=None, ge=0, le=1000)
    takma_ad: str | None = Field(default=None, min_length=1, max_length=80)


def _ip(istek: Request) -> str:
    return istek.client.host if istek.client else ""


@router.get("/surucu/durum")
async def surucu_durumu(
    kullanici: Kullanici = Depends(gecerli_personel()),
) -> dict[str, object]:
    """Konteyner çalışma zamanının yetenekleri (Docker, GPU, imaj önbelleği)."""
    return await surucu_durum.durum_ozeti()


@router.post("/{bdm_id}/baslat")
async def baslat(
    bdm_id: int,
    istek: Request,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    kullanici: Kullanici = Depends(gecerli_personel()),
) -> dict[str, object]:
    """BDM konteynerini başlatır."""
    bdm = await bdm_getir(oturum, bdm_id)
    return await yasam_dongusu.baslat(oturum, bdm, kullanici_id=kullanici.id, ip=_ip(istek))


@router.post("/{bdm_id}/durdur")
async def durdur(
    bdm_id: int,
    istek: Request,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    kullanici: Kullanici = Depends(gecerli_personel()),
) -> dict[str, object]:
    """Çalışan BDM konteynerini durdurur."""
    bdm = await bdm_getir(oturum, bdm_id)
    return await yasam_dongusu.durdur(oturum, bdm, kullanici_id=kullanici.id, ip=_ip(istek))


@router.post("/{bdm_id}/yeniden-baslat")
async def yeniden_baslat(
    bdm_id: int,
    istek: Request,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    kullanici: Kullanici = Depends(gecerli_personel()),
) -> dict[str, object]:
    """BDM konteynerini durdurup yeniden başlatır."""
    bdm = await bdm_getir(oturum, bdm_id)
    return await yasam_dongusu.yeniden_baslat(
        oturum, bdm, kullanici_id=kullanici.id, ip=_ip(istek)
    )


@router.get("/{bdm_id}/durum")
async def durum(
    bdm_id: int,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    kullanici: Kullanici = Depends(gecerli_personel()),
) -> dict[str, object]:
    """BDM durumu, konteyner kimliği ve sağlık özeti."""
    bdm = await bdm_getir(oturum, bdm_id)
    return await saglik.durum_ozeti(bdm)


@router.get("/{bdm_id}/saglik")
async def bdm_sagligi(
    bdm_id: int,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    kullanici: Kullanici = Depends(gecerli_personel()),
) -> dict[str, object]:
    """Çalışan konteynerin sağlık sondası sonucu."""
    bdm = await bdm_getir(oturum, bdm_id)
    return await saglik.saglik_ozeti(bdm)


@router.get("/{bdm_id}/gunlukler")
async def gunluk_akisi(
    bdm_id: int,
    satir: int = Query(default=200, ge=1, le=2000),
    oturum: AsyncSession = Depends(veritabani_oturumu),
    kullanici: Kullanici = Depends(gecerli_personel()),
) -> StreamingResponse:
    """Konteyner günlüklerini SSE (`event: satir`) olarak akıtır."""
    bdm = await bdm_getir(oturum, bdm_id)
    konteyner_id = yasam_dongusu.konteyner_kimligi(bdm)
    surucu = yasam_dongusu.surucu_sec(bdm)
    return StreamingResponse(
        gunlukler.akis(surucu, konteyner_id, satir),
        media_type="text/event-stream",
        headers=gunlukler.SSE_BASLIKLARI,
    )


@router.patch("/{bdm_id}/yol")
async def yol_guncelle(
    bdm_id: int,
    govde: YolGuncelle,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    kullanici: Kullanici = Depends(gecerli_personel()),
) -> dict[str, object]:
    """BDM'nin takma adını ve yönlendirme önceliğini günceller."""
    bdm = await bdm_getir(oturum, bdm_id)
    konteyner = dict(bdm.konteyner or {})
    yol = dict(konteyner.get("yol") or {})
    if govde.oncelik is not None:
        yol["oncelik"] = govde.oncelik
    if govde.takma_ad is not None:
        yol["takma_ad"] = govde.takma_ad
    konteyner["yol"] = yol
    bdm.konteyner = konteyner
    await oturum.flush()
    return bdm_sozlugu(bdm)
