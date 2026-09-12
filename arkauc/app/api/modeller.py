"""Model katalogu uclari: /modeller, /bdm ve /saglayicilar (spec §7.3, §8).

`/modeller` sohbet istemcisine acik modelleri dondurur (yalniz `hazir` veya
`calisiyor`; API anahtarinin `izinli_modeller` listesi suzulur). `/bdm`
uclari panel icindir ve personel yetkisi ister; silme yalniz yoneticidedir.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek.bagimliliklar import (
    IstemciKimligi,
    gecerli_istemci,
    gecerli_personel,
    veritabani_oturumu,
)
from arkauc.app.cekirdek.denetim import islem_kaydet
from arkauc.app.cekirdek.hatalar import GecersizGecis
from bdm_listesi import (
    BdmGuncelle,
    BdmKopyala,
    BdmOlustur,
    bdm_getir,
    bdm_guncelle,
    bdm_kopyala,
    bdm_listele,
    bdm_olustur,
    bdm_sil,
    bdm_sozlugu,
    kullanilabilir_modeller,
    saglayici_listesi,
)
from bdm_veritabani.modeller import BdmDurumu, Kullanici, Rol

router = APIRouter()

YONETICI_OPERATOR = (Rol.yonetici, Rol.operator)
YALNIZ_YONETICI = (Rol.yonetici,)

_kimlikli_personel = gecerli_personel()
_duzenleyici_personel = gecerli_personel(YONETICI_OPERATOR)
_yonetici_personel = gecerli_personel(YALNIZ_YONETICI)


def _ip(istek: Request) -> str:
    """Denetim izi icin istemci IP adresi."""
    return istek.client.host if istek.client else ""


@router.get("/modeller")
async def modeller(
    kimlik: IstemciKimligi = Depends(gecerli_istemci),
    oturum: AsyncSession = Depends(veritabani_oturumu),
) -> list[dict[str, object]]:
    """Sohbet istemcisine acik modeller listesi."""
    izinli = kimlik.anahtar.izinli_modeller if kimlik.anahtar else None
    return await kullanilabilir_modeller(oturum, izinli)


@router.get("/saglayicilar")
async def saglayicilar() -> list[dict[str, object]]:
    """Desteklenen saglayicilar ve yetenekleri (kimlik gerektirmez)."""
    return saglayici_listesi()


@router.get("/bdm")
async def bdm_listesi(
    arama: str | None = Query(default=None, max_length=160),
    kullanici: Kullanici = Depends(_kimlikli_personel),
    oturum: AsyncSession = Depends(veritabani_oturumu),
) -> list[dict[str, object]]:
    """BDM kayitlarini listeler; `arama` ad ve slug uzerinde calisir."""
    kayitlar = await bdm_listele(oturum, arama=arama)
    return [bdm_sozlugu(kayit) for kayit in kayitlar]


@router.post("/bdm", status_code=status.HTTP_201_CREATED)
async def bdm_olustur_ucu(
    govde: BdmOlustur,
    istek: Request,
    kullanici: Kullanici = Depends(_duzenleyici_personel),
    oturum: AsyncSession = Depends(veritabani_oturumu),
) -> dict[str, object]:
    """Yeni BDM kaydi olusturur (taslak durumunda)."""
    bdm = await bdm_olustur(oturum, govde)
    await islem_kaydet(
        oturum,
        "bdm.olusturuldu",
        kullanici_id=kullanici.id,
        hedef_tur="bdm",
        hedef_id=bdm.id,
        ayrinti={"slug": bdm.slug, "saglayici": bdm.saglayici.value},
        ip=_ip(istek),
    )
    return bdm_sozlugu(bdm)


@router.patch("/bdm/{bdm_id}")
async def bdm_guncelle_ucu(
    bdm_id: int,
    govde: BdmGuncelle,
    istek: Request,
    kullanici: Kullanici = Depends(_duzenleyici_personel),
    oturum: AsyncSession = Depends(veritabani_oturumu),
) -> dict[str, object]:
    """BDM kaydini kismen gunceller."""
    bdm = await bdm_getir(oturum, bdm_id)
    await bdm_guncelle(oturum, bdm, govde)
    await islem_kaydet(
        oturum,
        "bdm.guncellendi",
        kullanici_id=kullanici.id,
        hedef_tur="bdm",
        hedef_id=bdm.id,
        ayrinti={"alanlar": sorted(govde.model_dump(exclude_unset=True))},
        ip=_ip(istek),
    )
    return bdm_sozlugu(bdm)


@router.post("/bdm/{bdm_id}/kopyala", status_code=status.HTTP_201_CREATED)
async def bdm_kopyala_ucu(
    bdm_id: int,
    govde: BdmKopyala,
    istek: Request,
    kullanici: Kullanici = Depends(_yonetici_personel),
    oturum: AsyncSession = Depends(veritabani_oturumu),
) -> dict[str, object]:
    """Var olan BDM'yi yeni ad ve slug ile cogaltir."""
    kaynak = await bdm_getir(oturum, bdm_id)
    yeni = await bdm_kopyala(oturum, kaynak, govde.yeni_ad, govde.yeni_slug)
    await islem_kaydet(
        oturum,
        "bdm.kopyalandi",
        kullanici_id=kullanici.id,
        hedef_tur="bdm",
        hedef_id=yeni.id,
        ayrinti={"kaynak_id": kaynak.id, "slug": yeni.slug},
        ip=_ip(istek),
    )
    return bdm_sozlugu(yeni)


@router.delete("/bdm/{bdm_id}", status_code=status.HTTP_204_NO_CONTENT)
async def bdm_sil_ucu(
    bdm_id: int,
    istek: Request,
    kullanici: Kullanici = Depends(_yonetici_personel),
    oturum: AsyncSession = Depends(veritabani_oturumu),
) -> Response:
    """BDM kaydini siler; calisan bir BDM once durdurulmalidir."""
    bdm = await bdm_getir(oturum, bdm_id)
    if bdm.durum == BdmDurumu.calisiyor:
        raise GecersizGecis(
            "Çalışan bir BDM silinemez. Önce durdurun.",
            {"bdm_id": bdm.id, "durum": bdm.durum.value},
        )
    await islem_kaydet(
        oturum,
        "bdm.silindi",
        kullanici_id=kullanici.id,
        hedef_tur="bdm",
        hedef_id=bdm.id,
        ayrinti={"slug": bdm.slug},
        ip=_ip(istek),
    )
    await bdm_sil(oturum, bdm)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
