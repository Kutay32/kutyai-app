"""Konuşma logları uçları (API §12).

Liste, detay, dışa aktarma, silme ve saklama temizliği; hepsi personel içindir.
Silme ve temizleme yazma yetkisi ister: silme `yonetici`/`operator`, temizleme
yalnız `yonetici`. `izleyici` salt okunur kalır.

Sayfalama sınırları: `sayfa >= 1`, `1 <= boyut <= 200`; aralık dışı değerler
kırpılmak yerine `400 dogrulama_hatasi` ile reddedilir. `baslangic > bitis`
tutarsız bir aralıktır ve `400 gecersiz_istek` döner.
"""

from __future__ import annotations

from datetime import datetime, timezone

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek.bagimliliklar import (
    aktif_organizasyon,
    gecerli_personel,
    veritabani_oturumu,
)
from arkauc.app.cekirdek.denetim import islem_kaydet
from arkauc.app.cekirdek.hatalar import Bulunamadi, GecersizIstek
from bdm_konusma_gecmisi import (
    disa_aktar,
    eski_konusmalari_sil,
    konusma_detayi,
    konusmalari_listele,
)
from bdm_konusma_gecmisi.sorgu import EN_BUYUK_SAYFA_BOYUTU
from bdm_veritabani.modeller import IslemKaydi, Konusma, Kullanici, Organizasyon, Rol

router = APIRouter()

YAZMA_ROLLERI = (Rol.yonetici, Rol.operator)


class TemizleIstegi(BaseModel):
    gun: int | None = Field(default=None, ge=1, le=3650)


def _kiyaslanabilir(an: datetime) -> datetime:
    """Bilinçsiz damgayı UTC kabul ederek karşılaştırmayı güvenli kılar."""
    return an if an.tzinfo is not None else an.replace(tzinfo=timezone.utc)


def _araligi_dogrula(baslangic: datetime | None, bitis: datetime | None) -> None:
    """Ters tarih aralığını reddeder."""
    if (
        baslangic is not None
        and bitis is not None
        and _kiyaslanabilir(baslangic) > _kiyaslanabilir(bitis)
    ):
        raise GecersizIstek(
            "Başlangıç tarihi bitiş tarihinden sonra olamaz.", {"alan": "baslangic"}
        )


async def _konusma_getir(oturum: AsyncSession, org_id: int, konusma_id: int) -> Konusma:
    """Konusmayi organizasyon kapsaminda getirir; baska organizasyonunki `404`."""
    konusma = await oturum.get(Konusma, konusma_id)
    if konusma is None or konusma.org_id != org_id:
        raise Bulunamadi("Konuşma bulunamadı.", {"konusma_id": konusma_id})
    return konusma


@router.get("/loglar/konusmalar")
async def konusma_loglari(
    kullanici_id: int | None = Query(default=None),
    bdm_id: int | None = Query(default=None),
    baslangic: datetime | None = Query(default=None),
    bitis: datetime | None = Query(default=None),
    arama: str | None = Query(default=None),
    sayfa: int = Query(default=1, ge=1),
    boyut: int = Query(default=25, ge=1, le=EN_BUYUK_SAYFA_BOYUTU),
    oturum: AsyncSession = Depends(veritabani_oturumu),
    _personel: Kullanici = Depends(gecerli_personel()),
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
) -> dict[str, object]:
    """Filtrelenebilir ve sayfalanabilir konuşma listesi (aktif organizasyon)."""
    _araligi_dogrula(baslangic, bitis)
    return await konusmalari_listele(
        oturum,
        org_id=organizasyon.id,
        kullanici_id=kullanici_id,
        bdm_id=bdm_id,
        baslangic=baslangic,
        bitis=bitis,
        arama=arama,
        sayfa=sayfa,
        boyut=boyut,
    )


@router.get("/islem-kayitlari")
async def islem_kayitlari(
    eylem: str | None = Query(default=None),
    kullanici_id: int | None = Query(default=None),
    baslangic: datetime | None = Query(default=None),
    bitis: datetime | None = Query(default=None),
    sayfa: int = Query(default=1, ge=1),
    boyut: int = Query(default=25, ge=1, le=EN_BUYUK_SAYFA_BOYUTU),
    oturum: AsyncSession = Depends(veritabani_oturumu),
    _personel: Kullanici = Depends(gecerli_personel()),
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
) -> dict[str, object]:
    """Denetim izini en yeni kayıt önce listeler; tüm personel okuyabilir.

    Yalnız aktif organizasyonun kayıtları ve organizasyonsuz sistem kayıtları
    (`org_id IS NULL`) döner.
    """
    _araligi_dogrula(baslangic, bitis)

    kosullar: list[sa.ColumnElement[bool]] = [
        sa.or_(IslemKaydi.org_id == organizasyon.id, IslemKaydi.org_id.is_(None))
    ]
    if eylem:
        kosullar.append(IslemKaydi.eylem == eylem)
    if kullanici_id is not None:
        kosullar.append(IslemKaydi.kullanici_id == kullanici_id)
    if baslangic is not None:
        kosullar.append(IslemKaydi.olusturulma >= baslangic)
    if bitis is not None:
        kosullar.append(IslemKaydi.olusturulma <= bitis)

    toplam = (
        await oturum.execute(
            sa.select(sa.func.count()).select_from(IslemKaydi).where(*kosullar)
        )
    ).scalar_one()
    satirlar = (
        await oturum.execute(
            sa.select(IslemKaydi, Kullanici.eposta)
            .outerjoin(Kullanici, Kullanici.id == IslemKaydi.kullanici_id)
            .where(*kosullar)
            .order_by(IslemKaydi.olusturulma.desc(), IslemKaydi.id.desc())
            .offset((sayfa - 1) * boyut)
            .limit(boyut)
        )
    ).all()

    kayitlar = [
        {
            "id": kayit.id,
            "kullanici_id": kayit.kullanici_id,
            "kullanici_eposta": eposta,
            "eylem": kayit.eylem,
            "hedef_tur": kayit.hedef_tur,
            "hedef_id": kayit.hedef_id,
            "ayrinti": kayit.ayrinti or {},
            "ip": kayit.ip,
            "olusturulma": kayit.olusturulma.isoformat(),
        }
        for kayit, eposta in satirlar
    ]
    return {"toplam": int(toplam), "sayfa": sayfa, "boyut": boyut, "kayitlar": kayitlar}


@router.get("/loglar/konusmalar/{konusma_id}")
async def konusma_log_detayi(
    konusma_id: int,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    _personel: Kullanici = Depends(gecerli_personel()),
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
) -> dict[str, object]:
    """Konuşmayı mesajlarıyla birlikte döndürür."""
    konusma = await _konusma_getir(oturum, organizasyon.id, konusma_id)
    return await konusma_detayi(oturum, konusma)


@router.get("/loglar/konusmalar/{konusma_id}/disa-aktar")
async def konusma_disa_aktar(
    konusma_id: int,
    bicim: str = Query(default="json"),
    oturum: AsyncSession = Depends(veritabani_oturumu),
    _personel: Kullanici = Depends(gecerli_personel()),
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
) -> Response:
    """Konuşmayı json/md/csv olarak indirir."""
    konusma = await _konusma_getir(oturum, organizasyon.id, konusma_id)
    detay = await konusma_detayi(oturum, konusma)
    icerik, medya_turu, dosya_adi = disa_aktar(konusma, detay, bicim)
    return Response(
        content=icerik.encode("utf-8"),
        media_type=medya_turu,
        headers={"Content-Disposition": f'attachment; filename="{dosya_adi}"'},
    )


@router.delete("/loglar/konusmalar/{konusma_id}", status_code=204, response_model=None)
async def konusma_sil(
    konusma_id: int,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    personel: Kullanici = Depends(gecerli_personel(YAZMA_ROLLERI)),
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
) -> None:
    """Konuşmayı mesajlarıyla birlikte kalıcı olarak siler (yönetici/operatör)."""
    konusma = await _konusma_getir(oturum, organizasyon.id, konusma_id)
    await oturum.delete(konusma)
    await oturum.flush()
    await islem_kaydet(
        oturum,
        "konusma.silindi",
        org_id=organizasyon.id,
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
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
) -> dict[str, int]:
    """Saklama süresini aşan konuşmaları siler (yalnız yönetici)."""
    gun = govde.gun if govde else None
    silinen = await eski_konusmalari_sil(oturum, gun, org_id=organizasyon.id)
    await islem_kaydet(
        oturum,
        "loglar.temizlendi",
        org_id=organizasyon.id,
        kullanici_id=personel.id,
        hedef_tur="konusma",
        ayrinti={"gun": gun, "silinen": silinen},
    )
    return {"silinen": silinen}
