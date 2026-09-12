"""Konuşma logları uçları (API §12).

Liste, detay, dışa aktarma, silme ve saklama temizliği; hepsi personel içindir.
Temizleme yalnızca yöneticiye açıktır.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek.bagimliliklar import gecerli_personel, veritabani_oturumu
from arkauc.app.cekirdek.denetim import islem_kaydet
from arkauc.app.cekirdek.hatalar import Bulunamadi
from bdm_konusma_gecmisi import (
    disa_aktar,
    eski_konusmalari_sil,
    konusma_detayi,
    konusmalari_listele,
)
from bdm_veritabani.modeller import Konusma, Kullanici, Rol

router = APIRouter()


class TemizleIstegi(BaseModel):
    gun: int | None = Field(default=None, ge=1, le=3650)


async def _konusma_getir(oturum: AsyncSession, konusma_id: int) -> Konusma:
    konusma = await oturum.get(Konusma, konusma_id)
    if konusma is None:
        raise Bulunamadi("Konuşma bulunamadı.", {"konusma_id": konusma_id})
    return konusma


@router.get("/loglar/konusmalar")
async def konusma_loglari(
    kullanici_id: int | None = Query(default=None),
    bdm_id: int | None = Query(default=None),
    baslangic: datetime | None = Query(default=None),
    bitis: datetime | None = Query(default=None),
    arama: str | None = Query(default=None),
    sayfa: int = Query(default=1),
    boyut: int = Query(default=25),
    oturum: AsyncSession = Depends(veritabani_oturumu),
    _personel: Kullanici = Depends(gecerli_personel()),
) -> dict[str, object]:
    """Filtrelenebilir ve sayfalanabilir konuşma listesi."""
    return await konusmalari_listele(
        oturum,
        kullanici_id=kullanici_id,
        bdm_id=bdm_id,
        baslangic=baslangic,
        bitis=bitis,
        arama=arama,
        sayfa=sayfa,
        boyut=boyut,
    )


@router.get("/loglar/konusmalar/{konusma_id}")
async def konusma_log_detayi(
    konusma_id: int,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    _personel: Kullanici = Depends(gecerli_personel()),
) -> dict[str, object]:
    """Konuşmayı mesajlarıyla birlikte döndürür."""
    konusma = await _konusma_getir(oturum, konusma_id)
    return await konusma_detayi(oturum, konusma)


@router.get("/loglar/konusmalar/{konusma_id}/disa-aktar")
async def konusma_disa_aktar(
    konusma_id: int,
    bicim: str = Query(default="json"),
    oturum: AsyncSession = Depends(veritabani_oturumu),
    _personel: Kullanici = Depends(gecerli_personel()),
) -> Response:
    """Konuşmayı json/md/csv olarak indirir."""
    konusma = await _konusma_getir(oturum, konusma_id)
    detay = await konusma_detayi(oturum, konusma)
    icerik, medya_turu, dosya_adi = disa_aktar(konusma, detay, bicim)
    return Response(
        content=icerik.encode("utf-8"),
        media_type=medya_turu,
        headers={"Content-Disposition": f'attachment; filename="{dosya_adi}"'},
    )


@router.delete("/loglar/konusmalar/{konusma_id}", status_code=204)
async def konusma_sil(
    konusma_id: int,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    personel: Kullanici = Depends(gecerli_personel()),
) -> None:
    """Konuşmayı mesajlarıyla birlikte kalıcı olarak siler."""
    konusma = await _konusma_getir(oturum, konusma_id)
    await oturum.delete(konusma)
    await oturum.flush()
    await islem_kaydet(
        oturum,
        "konusma.silindi",
        kullanici_id=personel.id,
        hedef_tur="konusma",
        hedef_id=konusma_id,
        ayrinti={"baslik": konusma.baslik},
    )


@router.post("/loglar/temizle")
async def loglari_temizle(
    govde: TemizleIstegi | None = None,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    personel: Kullanici = Depends(gecerli_personel((Rol.yonetici,))),
) -> dict[str, int]:
    """Saklama süresini aşan konuşmaları siler (yalnız yönetici)."""
    gun = govde.gun if govde else None
    silinen = await eski_konusmalari_sil(oturum, gun)
    await islem_kaydet(
        oturum,
        "loglar.temizlendi",
        kullanici_id=personel.id,
        hedef_tur="konusma",
        ayrinti={"gun": gun, "silinen": silinen},
    )
    return {"silinen": silinen}
