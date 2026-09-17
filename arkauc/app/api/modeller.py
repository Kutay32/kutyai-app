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
    aktif_organizasyon,
    gecerli_istemci,
    gecerli_personel,
    istemci_organizasyonu,
    veritabani_oturumu,
)
from arkauc.app.cekirdek.denetim import islem_kaydet
from arkauc.app.cekirdek.hatalar import GecersizGecis, YetkiYok
from arkauc.app.cekirdek.organizasyon import rol_yetkili_mi, uyelik_getir
from bdm_listesi import (
    BdmGuncelle,
    BdmKopyala,
    BdmOlustur,
    bdm_getir_org,
    bdm_guncelle,
    bdm_kopyala,
    bdm_listele,
    bdm_olustur,
    bdm_sil,
    bdm_sozlugu,
    kullanilabilir_modeller,
    saglayici_listesi,
)
from bdm_veritabani.modeller import (
    BdmDurumu,
    Kullanici,
    Organizasyon,
    Rol,
    UyelikDurumu,
    UyelikRolu,
)

router = APIRouter()

YONETICI_OPERATOR = (Rol.yonetici, Rol.operator)
YALNIZ_YONETICI = (Rol.yonetici,)

# GUV-03: saglayici adresi ve upstream anahtari yalniz yoneticiye aittir.
# Operator bunlari degistirip cozulmus anahtari kendi sunucusuna yonlendiremez.
# Karar global `kullanici.rol` degil aktif organizasyondaki **uyelik** rolu
# uzerinden verilir (spec §2.2).
YONETICI_ALANLARI = ("temel_url", "api_anahtari", "saglayici")
YONETICI_UYELIK_ROLLERI: tuple[UyelikRolu, ...] = (UyelikRolu.yonetici,)
YONETICI_ALANI_MESAJI = "Sağlayıcı adresi ve API anahtarını yalnız yönetici değiştirebilir."

_kimlikli_personel = gecerli_personel()
_duzenleyici_personel = gecerli_personel(YONETICI_OPERATOR)
_yonetici_personel = gecerli_personel(YALNIZ_YONETICI)


def _ip(istek: Request) -> str:
    """Denetim izi icin istemci IP adresi."""
    return istek.client.host if istek.client else ""


async def _upstream_yetkili_mi(
    oturum: AsyncSession, organizasyon_id: int, kullanici_id: int
) -> bool:
    """Aktif organizasyondaki uyelik rolu yonetici/sahip mi (GUV-03, spec §2.2)."""
    uyelik = await uyelik_getir(oturum, organizasyon_id, kullanici_id)
    if uyelik is None or uyelik.durum != UyelikDurumu.aktif:
        return False
    return rol_yetkili_mi(uyelik.rol, YONETICI_UYELIK_ROLLERI)


async def _guncelleme_alanlarini_koru(
    oturum: AsyncSession, govde: BdmGuncelle, kullanici: Kullanici, organizasyon: Organizasyon
) -> None:
    """Guncellemede korumali alanlar yalniz organizasyon yoneticisinde kalir (GUV-03)."""
    verilen = sorted(
        alan for alan in YONETICI_ALANLARI if alan in govde.model_fields_set
    )
    if not verilen:
        return
    if await _upstream_yetkili_mi(oturum, organizasyon.id, kullanici.id):
        return
    raise YetkiYok(YONETICI_ALANI_MESAJI, {"alanlar": verilen})


async def _olusturma_alanlarini_koru(
    oturum: AsyncSession, govde: BdmOlustur, kullanici: Kullanici, organizasyon: Organizasyon
) -> None:
    """Yeni kayitta upstream anahtari organizasyon yoneticisinde kalir (GUV-03).

    `temel_url` serbesttir: yeni kayit mevcut bir anahtari baska adrese
    tasimaz (alan korumasi guncellemede uygulanir).
    """
    if not govde.api_anahtari:
        return
    if await _upstream_yetkili_mi(oturum, organizasyon.id, kullanici.id):
        return
    raise YetkiYok(YONETICI_ALANI_MESAJI, {"alanlar": ["api_anahtari"]})


@router.get("/modeller")
async def modeller(
    kimlik: IstemciKimligi = Depends(gecerli_istemci),
    organizasyon: Organizasyon = Depends(istemci_organizasyonu),
    oturum: AsyncSession = Depends(veritabani_oturumu),
) -> list[dict[str, object]]:
    """Sohbet istemcisine acik modeller listesi (aktif organizasyon kapsaminda)."""
    izinli = kimlik.anahtar.izinli_modeller if kimlik.anahtar else None
    return await kullanilabilir_modeller(oturum, izinli, org_id=organizasyon.id)


@router.get("/saglayicilar")
async def saglayicilar() -> list[dict[str, object]]:
    """Desteklenen saglayicilar ve yetenekleri (kimlik gerektirmez)."""
    return saglayici_listesi()


@router.get("/bdm")
async def bdm_listesi(
    arama: str | None = Query(default=None, max_length=160),
    kullanici: Kullanici = Depends(_kimlikli_personel),
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
    oturum: AsyncSession = Depends(veritabani_oturumu),
) -> list[dict[str, object]]:
    """BDM kayitlarini listeler; `arama` ad ve slug uzerinde calisir."""
    kayitlar = await bdm_listele(oturum, org_id=organizasyon.id, arama=arama)
    return [bdm_sozlugu(kayit) for kayit in kayitlar]


@router.post("/bdm", status_code=status.HTTP_201_CREATED)
async def bdm_olustur_ucu(
    govde: BdmOlustur,
    istek: Request,
    kullanici: Kullanici = Depends(_duzenleyici_personel),
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
    oturum: AsyncSession = Depends(veritabani_oturumu),
) -> dict[str, object]:
    """Yeni BDM kaydi olusturur (taslak durumunda)."""
    await _olusturma_alanlarini_koru(oturum, govde, kullanici, organizasyon)
    bdm = await bdm_olustur(oturum, govde, org_id=organizasyon.id)
    await islem_kaydet(
        oturum,
        "bdm.olusturuldu",
        org_id=organizasyon.id,
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
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
    oturum: AsyncSession = Depends(veritabani_oturumu),
) -> dict[str, object]:
    """BDM kaydini kismen gunceller."""
    await _guncelleme_alanlarini_koru(oturum, govde, kullanici, organizasyon)
    bdm = await bdm_getir_org(oturum, organizasyon.id, bdm_id)
    await bdm_guncelle(oturum, bdm, govde)
    await islem_kaydet(
        oturum,
        "bdm.guncellendi",
        org_id=organizasyon.id,
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
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
    oturum: AsyncSession = Depends(veritabani_oturumu),
) -> dict[str, object]:
    """Var olan BDM'yi yeni ad ve slug ile cogaltir."""
    kaynak = await bdm_getir_org(oturum, organizasyon.id, bdm_id)
    yeni = await bdm_kopyala(oturum, kaynak, govde.yeni_ad, govde.yeni_slug)
    await islem_kaydet(
        oturum,
        "bdm.kopyalandi",
        org_id=organizasyon.id,
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
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
    oturum: AsyncSession = Depends(veritabani_oturumu),
) -> Response:
    """BDM kaydini siler; calisan bir BDM once durdurulmalidir."""
    bdm = await bdm_getir_org(oturum, organizasyon.id, bdm_id)
    if bdm.durum == BdmDurumu.calisiyor:
        raise GecersizGecis(
            "Çalışan bir BDM silinemez. Önce durdurun.",
            {"bdm_id": bdm.id, "durum": bdm.durum.value},
        )
    await islem_kaydet(
        oturum,
        "bdm.silindi",
        org_id=organizasyon.id,
        kullanici_id=kullanici.id,
        hedef_tur="bdm",
        hedef_id=bdm.id,
        ayrinti={"slug": bdm.slug},
        ip=_ip(istek),
    )
    await bdm_sil(oturum, bdm)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
