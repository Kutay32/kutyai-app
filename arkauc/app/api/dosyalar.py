"""Dosya uçlari (API §15, spec §3).

Multipart yükleme, sayfalanabilir/aranabilir listeleme, meta, indirme ve silme.
Hepsi `gecerli_personel()` ister ve aktif organizasyonla sinirlidir; baska
organizasyonun dosyasi `404 bulunamadi` doner.

Boyut siniri asildiginda gövde diske yazilmaz: baytlar blok blok sayilir ve
sinir asildigi anda `413 dosya_cok_buyuk` ile reddedilir.
"""

from __future__ import annotations

from urllib.parse import quote

import sqlalchemy as sa
from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek.ayarlar import ayarlar
from arkauc.app.cekirdek.bagimliliklar import (
    aktif_organizasyon,
    gecerli_personel,
    veritabani_oturumu,
)
from arkauc.app.cekirdek.denetim import islem_kaydet
from arkauc.app.cekirdek.hatalar import DosyaCokBuyuk
from arkauc.app.servisler import dosya as dosya_servisi
from bdm_konusma_gecmisi.sorgu import EN_BUYUK_SAYFA_BOYUTU, VARSAYILAN_SAYFA_BOYUTU
from bdm_veritabani.modeller import Dosya, Kullanici, Organizasyon

router = APIRouter()

#: Yukleme sirasinda tek seferde okunan blok boyutu (bayt).
OKUMA_BLOGU = 64 * 1024


def _ip(istek: Request) -> str:
    return istek.client.host if istek.client else ""


def _ozet(dosya: Dosya, *, metin: bool = False) -> dict[str, object]:
    kayit: dict[str, object] = {
        "id": dosya.id,
        "ad": dosya.ad,
        "mime": dosya.mime,
        "boyut": dosya.boyut,
        "sha256": dosya.sha256,
        "metin_uzunluk": len(dosya.metin or ""),
        "kullanici_id": dosya.kullanici_id,
        "olusturulma": dosya.olusturulma.isoformat() if dosya.olusturulma else None,
    }
    if metin:
        kayit["metin"] = dosya.metin or ""
    return kayit


def _icerik_serligi(ad: str) -> str:
    """Rusya disi karakterleri de tasiyan `Content-Disposition` degeri (RFC 5987)."""
    yedek = ad.encode("ascii", "ignore").decode("ascii").replace('"', "").strip() or "dosya"
    return f"attachment; filename=\"{yedek}\"; filename*=UTF-8''{quote(ad, safe='')}"


async def _icerik_oku(yukleme: UploadFile) -> bytes:
    """Yuklemeyi blok blok okur; sinir asilirsa diske yazmadan reddeder."""
    sinir = max(0, int(ayarlar.dosya_maks_mb)) * 1024 * 1024
    parcalar: list[bytes] = []
    okunan = 0
    while True:
        blok = await yukleme.read(OKUMA_BLOGU)
        if not blok:
            break
        okunan += len(blok)
        if sinir and okunan > sinir:
            raise DosyaCokBuyuk(
                "dosya_cok_buyuk",
                {"sinir_mb": ayarlar.dosya_maks_mb, "okunan_bayt": okunan},
            )
        parcalar.append(blok)
    return b"".join(parcalar)


@router.post("/dosyalar", status_code=201)
async def dosya_yukle(
    istek: Request,
    dosya: UploadFile = File(...),
    oturum: AsyncSession = Depends(veritabani_oturumu),
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
    personel: Kullanici = Depends(gecerli_personel()),
) -> dict[str, object]:
    """Multipart dosya yukler; MIME ve boyut denetiminden gecirir."""
    ad = (dosya.filename or "dosya").strip() or "dosya"
    mime = dosya_servisi.mime_coz(dosya.content_type, ad)
    icerik = await _icerik_oku(dosya)

    kayit = await dosya_servisi.dosya_kaydet(
        oturum,
        org_id=organizasyon.id,
        kullanici_id=personel.id,
        ad=ad,
        mime=mime,
        icerik=icerik,
    )
    await islem_kaydet(
        oturum,
        "dosya.yuklendi",
        org_id=organizasyon.id,
        kullanici_id=personel.id,
        hedef_tur="dosya",
        hedef_id=kayit.id,
        ayrinti={"ad": kayit.ad, "mime": kayit.mime, "boyut": kayit.boyut},
        ip=_ip(istek),
    )
    return _ozet(kayit, metin=True)


@router.get("/dosyalar")
async def dosyalari_listele(
    arama: str | None = Query(default=None),
    sayfa: int = Query(default=1, ge=1),
    boyut: int = Query(default=VARSAYILAN_SAYFA_BOYUTU, ge=1, le=EN_BUYUK_SAYFA_BOYUTU),
    oturum: AsyncSession = Depends(veritabani_oturumu),
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
    _personel: Kullanici = Depends(gecerli_personel()),
) -> dict[str, object]:
    """Aktif organizasyonun dosyalarini en yeni once listeler."""
    kosullar: list[sa.ColumnElement[bool]] = [Dosya.org_id == organizasyon.id]
    if arama and arama.strip():
        kosullar.append(Dosya.ad.ilike(f"%{arama.strip()}%"))

    toplam = (
        await oturum.execute(sa.select(sa.func.count()).select_from(Dosya).where(*kosullar))
    ).scalar_one()
    satirlar = (
        await oturum.execute(
            sa.select(Dosya)
            .where(*kosullar)
            .order_by(Dosya.olusturulma.desc(), Dosya.id.desc())
            .offset((sayfa - 1) * boyut)
            .limit(boyut)
        )
    ).scalars().all()
    return {
        "toplam": int(toplam),
        "sayfa": sayfa,
        "boyut": boyut,
        "kayitlar": [_ozet(satir) for satir in satirlar],
    }


@router.get("/dosyalar/{dosya_id}")
async def dosya_detayi(
    dosya_id: int,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
    _personel: Kullanici = Depends(gecerli_personel()),
) -> dict[str, object]:
    """Dosya metasini (cikarilmis maskeli metinle birlikte) dondurur."""
    kayit = await dosya_servisi.dosya_getir(oturum, organizasyon.id, dosya_id)
    return _ozet(kayit, metin=True)


@router.get("/dosyalar/{dosya_id}/icerik")
async def dosya_indir(
    dosya_id: int,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
    _personel: Kullanici = Depends(gecerli_personel()),
) -> Response:
    """Ham icerigi `Content-Disposition: attachment` ile indirir."""
    kayit = await dosya_servisi.dosya_getir(oturum, organizasyon.id, dosya_id)
    return Response(
        content=dosya_servisi.baytlari_oku(kayit),
        media_type=kayit.mime or "application/octet-stream",
        headers={"Content-Disposition": _icerik_serligi(kayit.ad)},
    )


@router.delete("/dosyalar/{dosya_id}", status_code=204, response_model=None)
async def dosya_sil(
    istek: Request,
    dosya_id: int,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
    personel: Kullanici = Depends(gecerli_personel()),
) -> None:
    """Kaydi ve diskteki kopyayi siler."""
    kayit = await dosya_servisi.dosya_getir(oturum, organizasyon.id, dosya_id)
    ad = kayit.ad
    await oturum.delete(kayit)
    await oturum.flush()
    dosya_servisi.diskten_sil(kayit)
    await islem_kaydet(
        oturum,
        "dosya.silindi",
        org_id=organizasyon.id,
        kullanici_id=personel.id,
        hedef_tur="dosya",
        hedef_id=dosya_id,
        ayrinti={"ad": ad},
        ip=_ip(istek),
    )
