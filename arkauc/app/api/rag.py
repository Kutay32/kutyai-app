"""Bilgi tabani (RAG) uclari (spec §5).

Belge ekleme, listeleme, silme, yeniden gomme ve benzerlik aramasi. Tum uclar
aktif organizasyona kapsanir; baska organizasyonun belgesi `404` doner.
"""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek.ayarlar import ayarlar
from arkauc.app.cekirdek.bagimliliklar import (
    aktif_organizasyon,
    gecerli_personel,
    veritabani_oturumu,
)
from arkauc.app.cekirdek.denetim import islem_kaydet
from arkauc.app.cekirdek.hatalar import BdmHazirDegil, Bulunamadi, GecersizIstek
from arkauc.app.servisler.gomme import gomme_uret
from arkauc.app.servisler.vektor import (
    arama_yolu,
    belge_getir,
    belge_olustur,
    belge_sil,
    belgeleri_getir,
    parcala,
    parcalari_getir,
    parcalari_yaz,
    vektor_ara,
)
from bdm_listesi import bdm_getir, bdm_listele
from bdm_veritabani.modeller import (
    Bdm,
    BdmDurumu,
    BelgeKaynagi,
    Kullanici,
    Organizasyon,
    UyelikRolu,
    VektorBelgesi,
    VektorParcasi,
)

router = APIRouter()

#: Belge goruntuleme ve arama personelin tamamina aciktir.
_okuyucu = gecerli_personel()
#: Belge yazma/silme yalniz sahip, yonetici ve operatorun yetkisindedir.
_yazici = gecerli_personel((UyelikRolu.yonetici, UyelikRolu.operator))

#: Gomme uretilebilen BDM durumlari.
KULLANILABILIR_DURUMLAR: tuple[BdmDurumu, ...] = (BdmDurumu.hazir, BdmDurumu.calisiyor)


class BelgeOlustur(BaseModel):
    """`metin` ya da `dosya_id` verilmelidir; gomme modeli `bdm_id`den alinir."""

    model_config = ConfigDict(str_strip_whitespace=True)

    ad: str = Field(min_length=1, max_length=300)
    bdm_id: int
    metin: str | None = None
    dosya_id: int | None = None
    meta: dict[str, Any] | None = None


class AramaIstegi(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    sorgu: str = Field(min_length=1, max_length=4000)
    ust_k: int | None = Field(default=None, ge=1, le=50)
    belge_idleri: list[int] | None = None
    bdm_id: int | None = None


class YenidenGomIstegi(BaseModel):
    bdm_id: int | None = None


def gomme_tasimasi() -> httpx.AsyncBaseTransport | None:
    """Gomme isteklerinin tasimasi; testler `httpx.MockTransport` ile ezer."""
    return None


def _ip(istek: Request) -> str:
    return istek.client.host if istek.client else ""


def _belge_sozlugu(belge: VektorBelgesi) -> dict[str, object]:
    return {
        "id": belge.id,
        "ad": belge.ad,
        "kaynak": belge.kaynak.value,
        "dosya_id": belge.dosya_id,
        "meta": belge.belge_meta or {},
        "parca_sayisi": belge.parca_sayisi,
        "olusturulma": belge.olusturulma.isoformat() if belge.olusturulma else None,
    }


def _parca_sozlugu(parca: VektorParcasi) -> dict[str, object]:
    return {"sira": parca.sira, "icerik": parca.icerik, "token_sayisi": parca.token_sayisi}


def _org_denetle(bdm: Bdm, organizasyon: Organizasyon) -> None:
    """Baska organizasyonun BDM'i yok gibi davranir (`404`)."""
    if bdm.org_id != organizasyon.id:
        raise Bulunamadi(ayrinti={"bdm_id": bdm.id})


def _hazir_mi(bdm: Bdm) -> None:
    if bdm.durum not in KULLANILABILIR_DURUMLAR:
        raise BdmHazirDegil(
            "Seçilen model şu anda kullanıma hazır değil.",
            {"bdm_id": bdm.id, "durum": bdm.durum.value},
        )
    if not (bdm.gomme_modeli or "").strip():
        raise GecersizIstek("gomme_modeli_yok", {"bdm_id": bdm.id}, kod="gomme_modeli_yok")


async def _gomme_bdmi(
    oturum: AsyncSession, organizasyon: Organizasyon, bdm_id: int | None
) -> Bdm:
    """Gomme icin BDM secer: verilen `bdm_id` ya da org'un ilk hazir modeli."""
    if bdm_id is not None:
        bdm = await bdm_getir(oturum, bdm_id)
    else:
        adaylar = await bdm_listele(
            oturum, org_id=organizasyon.id, durumlar=KULLANILABILIR_DURUMLAR
        )
        if not adaylar:
            raise BdmHazirDegil(
                "Gömme için kullanıma hazır bir model yok.", {"org_id": organizasyon.id}
            )
        bdm = adaylar[0]
    _org_denetle(bdm, organizasyon)
    _hazir_mi(bdm)
    return bdm


async def _kaynak_metni(
    govde: BelgeOlustur, organizasyon: Organizasyon, oturum: AsyncSession
) -> tuple[str, BelgeKaynagi]:
    """Govdedeki `metin` ya da `dosya_id`den belge metnini cozer."""
    if govde.metin is not None and govde.metin.strip():
        return govde.metin, BelgeKaynagi.metin
    if govde.dosya_id is None:
        raise GecersizIstek("belge_kaynak_gerekli", {"alanlar": ["metin", "dosya_id"]})
    # Dosya servisi ayri dalga gorevidir; gec baglariz ki bu modul bagimsiz yuklenebilsin.
    from arkauc.app.servisler.dosya import dosya_getir, metin_cikar

    dosya = await dosya_getir(oturum, organizasyon.id, govde.dosya_id)
    metin, _gerekce = await metin_cikar(dosya)
    if not (metin or "").strip():
        raise GecersizIstek("dosya_metni_cikarilamadi", {"dosya_id": govde.dosya_id})
    return metin, BelgeKaynagi.dosya


@router.get("/rag/belgeler")
async def belgeleri_listele(
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
    _kullanici: Kullanici = Depends(_okuyucu),
    oturum: AsyncSession = Depends(veritabani_oturumu),
) -> list[dict[str, object]]:
    """Aktif organizasyonun bilgi tabani belgelerini listeler."""
    kayitlar = await belgeleri_getir(oturum, organizasyon.id)
    return [_belge_sozlugu(belge) for belge in kayitlar]


@router.post("/rag/belgeler", status_code=status.HTTP_201_CREATED)
async def belge_ekle(
    govde: BelgeOlustur,
    istek: Request,
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
    kullanici: Kullanici = Depends(_yazici),
    oturum: AsyncSession = Depends(veritabani_oturumu),
    tasima: httpx.AsyncBaseTransport | None = Depends(gomme_tasimasi),
) -> dict[str, object]:
    """Belgeyi parcalar, gomer ve bilgi tabanina yazar."""
    icerik, kaynak = await _kaynak_metni(govde, organizasyon, oturum)
    bdm = await _gomme_bdmi(oturum, organizasyon, govde.bdm_id)
    parcalar = parcala(icerik)
    if not parcalar:
        raise GecersizIstek("belge_metni_bos", {"ad": govde.ad})
    vektorler = await gomme_uret(bdm, parcalar, tasima=tasima)
    belge = await belge_olustur(
        oturum,
        org_id=organizasyon.id,
        ad=govde.ad,
        kaynak=kaynak,
        dosya_id=govde.dosya_id if kaynak is BelgeKaynagi.dosya else None,
        meta=govde.meta,
    )
    await parcalari_yaz(
        oturum,
        org_id=organizasyon.id,
        belge_id=belge.id,
        parcalar=parcalar,
        vektorler=vektorler,
    )
    await islem_kaydet(
        oturum,
        "rag.belge_eklendi",
        org_id=organizasyon.id,
        kullanici_id=kullanici.id,
        hedef_tur="vektor_belgesi",
        hedef_id=belge.id,
        ayrinti={"ad": belge.ad, "kaynak": kaynak.value, "parca_sayisi": len(parcalar)},
        ip=_ip(istek),
    )
    return _belge_sozlugu(belge)


@router.get("/rag/belgeler/{belge_id}")
async def belge_detayi(
    belge_id: int,
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
    _kullanici: Kullanici = Depends(_okuyucu),
    oturum: AsyncSession = Depends(veritabani_oturumu),
) -> dict[str, object]:
    """Belgeyi parcalariyla birlikte dondurur."""
    belge = await belge_getir(oturum, organizasyon.id, belge_id)
    parcalar = await parcalari_getir(oturum, organizasyon.id, belge.id)
    return {**_belge_sozlugu(belge), "parcalar": [_parca_sozlugu(parca) for parca in parcalar]}


@router.delete("/rag/belgeler/{belge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def belge_kaldir(
    belge_id: int,
    istek: Request,
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
    kullanici: Kullanici = Depends(_yazici),
    oturum: AsyncSession = Depends(veritabani_oturumu),
) -> Response:
    """Belgeyi ve parcalarini siler."""
    belge = await belge_getir(oturum, organizasyon.id, belge_id)
    await belge_sil(oturum, organizasyon.id, belge.id)
    await islem_kaydet(
        oturum,
        "rag.belge_silindi",
        org_id=organizasyon.id,
        kullanici_id=kullanici.id,
        hedef_tur="vektor_belgesi",
        hedef_id=belge.id,
        ayrinti={"ad": belge.ad},
        ip=_ip(istek),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/rag/ara")
async def ara(
    govde: AramaIstegi,
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
    _kullanici: Kullanici = Depends(_okuyucu),
    oturum: AsyncSession = Depends(veritabani_oturumu),
    tasima: httpx.AsyncBaseTransport | None = Depends(gomme_tasimasi),
) -> dict[str, object]:
    """Sorguya en benzer parcalari dondurur; `ayrinti.yol` secilen yolu bildirir."""
    bdm = await _gomme_bdmi(oturum, organizasyon, govde.bdm_id)
    vektorler = await gomme_uret(bdm, [govde.sorgu], tasima=tasima)
    ust_k = govde.ust_k if govde.ust_k is not None else ayarlar.rag_ust_k
    sonuclar = await vektor_ara(
        oturum,
        org_id=organizasyon.id,
        sorgu_vektoru=vektorler[0],
        ust_k=ust_k,
        belge_idleri=govde.belge_idleri,
    )
    return {
        "sonuclar": sonuclar,
        "ayrinti": {"yol": await arama_yolu(oturum), "ust_k": ust_k},
    }


@router.post("/rag/belgeler/{belge_id}/yeniden-gom")
async def yeniden_gom(
    belge_id: int,
    istek: Request,
    govde: YenidenGomIstegi | None = None,
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
    kullanici: Kullanici = Depends(_yazici),
    oturum: AsyncSession = Depends(veritabani_oturumu),
    tasima: httpx.AsyncBaseTransport | None = Depends(gomme_tasimasi),
) -> dict[str, object]:
    """Belgenin parcalarini guncel gomme modeliyle yeniden vektorler."""
    belge = await belge_getir(oturum, organizasyon.id, belge_id)
    parcalar = await parcalari_getir(oturum, organizasyon.id, belge.id)
    if not parcalar:
        raise GecersizIstek("belge_parcasi_yok", {"belge_id": belge.id})
    bdm = await _gomme_bdmi(oturum, organizasyon, govde.bdm_id if govde else None)
    icerikler = [parca.icerik for parca in parcalar]
    vektorler = await gomme_uret(bdm, icerikler, tasima=tasima)
    await parcalari_yaz(
        oturum,
        org_id=organizasyon.id,
        belge_id=belge.id,
        parcalar=icerikler,
        vektorler=vektorler,
    )
    await islem_kaydet(
        oturum,
        "rag.yeniden_gomuldu",
        org_id=organizasyon.id,
        kullanici_id=kullanici.id,
        hedef_tur="vektor_belgesi",
        hedef_id=belge.id,
        ayrinti={"parca_sayisi": len(icerikler), "bdm_id": bdm.id},
        ip=_ip(istek),
    )
    await oturum.refresh(belge)
    return _belge_sozlugu(belge)
