"""Araç uçları (spec §4).

* `GET/POST /araclar`, `PATCH/DELETE /araclar/{id}` — CRUD (yazma: yönetici/operatör).
* `POST /araclar/{id}/dene` — argümanlarla çalıştırma; webhook hatasında `502 arac_hatasi`.
* `GET /araclar/cagrilar` — sayfalanabilir, filtrelenebilir çağrı günlüğü.

Tüm kayıtlar aktif organizasyonla sınırlıdır; başka organizasyonun aracı `404`
döner, `slug` organizasyon içinde tekildir. Webhook başlıkları Fernet ile
şifreli saklanır ve yanıtlarda maskelenir.
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek.bagimliliklar import (
    aktif_organizasyon,
    gecerli_personel,
    veritabani_oturumu,
)
from arkauc.app.cekirdek.denetim import islem_kaydet
from arkauc.app.cekirdek.hatalar import (
    AracHatasi,
    Bulunamadi,
    Cakisma,
    GecersizIstek,
)
from arkauc.app.servisler import arac as arac_servisi
from bdm_konusma_gecmisi.sorgu import EN_BUYUK_SAYFA_BOYUTU
from bdm_listesi.katalog import slug_uret
from bdm_veritabani.modeller import (
    Arac,
    AracCagrisi,
    AracCagrisiDurumu,
    AracTuru,
    Kullanici,
    Organizasyon,
    Rol,
)

router = APIRouter()

#: Yazma uçlarında izinli roller (`sahip` her zaman yetkilidir).
YAZMA_ROLLERI = (Rol.yonetici, Rol.operator)

#: `/dene` ucunda 400 sayılan hata kodları; kalan hatalar `502 arac_hatasi`.
ISTEMCI_HATALARI = frozenset(
    {"gecersiz_istek", "gecersiz_ifade", "arac_yerlesik_bilinmiyor"}
)


class AracOlustur(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    ad: str = Field(min_length=2, max_length=120)
    slug: str | None = Field(default=None, max_length=60)
    aciklama: str = Field(default="", max_length=2000)
    json_sema: dict[str, Any] = Field(default_factory=dict)
    tur: AracTuru = AracTuru.webhook
    uc_noktasi: str = Field(default="", max_length=400)
    basliklar: dict[str, str] = Field(default_factory=dict)
    etkin: bool = True


class AracGuncelle(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    ad: str | None = Field(default=None, min_length=2, max_length=120)
    slug: str | None = Field(default=None, max_length=60)
    aciklama: str | None = Field(default=None, max_length=2000)
    json_sema: dict[str, Any] | None = None
    tur: AracTuru | None = None
    uc_noktasi: str | None = Field(default=None, max_length=400)
    basliklar: dict[str, str] | None = None
    etkin: bool | None = None


class DenemeIstegi(BaseModel):
    """Deneme gövdesi.

    Tercih edilen biçim `{"argumanlar": {...}}`; kısa yol olarak gövdenin
    kendisi de argüman sözlüğü sayılır.
    """

    model_config = ConfigDict(extra="allow")

    argumanlar: dict[str, Any] | None = None

    def cozulen(self) -> dict[str, Any]:
        if self.argumanlar is not None:
            return self.argumanlar
        return dict(self.model_extra or {})


def _sozluk(arac: Arac) -> dict[str, Any]:
    """Aracı sırları maskeleyerek temsil eder."""
    return {
        "id": arac.id,
        "ad": arac.ad,
        "slug": arac.slug,
        "aciklama": arac.aciklama or "",
        "json_sema": arac.json_sema or {},
        "tur": arac.tur.value,
        "uc_noktasi": arac.uc_noktasi or "",
        "basliklar": arac_servisi.basliklari_maskele(arac),
        "etkin": bool(arac.etkin),
        "olusturulma": arac.olusturulma.isoformat() if arac.olusturulma else None,
        "guncellenme": arac.guncellenme.isoformat() if arac.guncellenme else None,
    }


def _cagri_sozluk(kayit: AracCagrisi) -> dict[str, Any]:
    return {
        "id": kayit.id,
        "arac_id": kayit.arac_id,
        "ad": kayit.ad,
        "konusma_id": kayit.konusma_id,
        "mesaj_id": kayit.mesaj_id,
        "argumanlar": kayit.argumanlar or {},
        "sonuc": kayit.sonuc or {},
        "durum": kayit.durum.value,
        "gecikme_ms": kayit.gecikme_ms,
        "hata": kayit.hata,
        "olusturulma": kayit.olusturulma.isoformat() if kayit.olusturulma else None,
    }


async def _arac_getir(oturum: AsyncSession, org_id: int, arac_id: int) -> Arac:
    arac = (
        await oturum.execute(
            sa.select(Arac).where(Arac.id == arac_id, Arac.org_id == org_id)
        )
    ).scalar_one_or_none()
    if arac is None:
        raise Bulunamadi(
            "arac_bulunamadi", {"arac_id": arac_id}, kod="arac_bulunamadi"
        )
    return arac


async def _slug_dogrula(
    oturum: AsyncSession, org_id: int, slug: str, *, haric_id: int | None = None
) -> str:
    """Verilen slug org içinde boş mu? Değilse `409` (yerleşik slug'lar korunur)."""
    kosullar = [Arac.org_id == org_id, Arac.slug == slug]
    if haric_id is not None:
        kosullar.append(Arac.id != haric_id)
    var = (await oturum.execute(sa.select(Arac.id).where(*kosullar))).scalar_one_or_none()
    if var is not None:
        raise Cakisma("arac_slug_kullaniliyor", {"slug": slug}, ceviriler={"slug": slug})
    return slug


async def _slug_sec(
    oturum: AsyncSession,
    org_id: int,
    ad: str,
    istenen: str | None,
    *,
    haric_id: int | None = None,
    normalestir: bool = True,
) -> str:
    """Org içinde tekil slug üretir; açıkça istenen slug çakışırsa `409`.

    `normalestir=False` yalnız yerleşik araç slug'ları için kullanılır: onlar
    birebir eşleşmek zorundadır (`hesap_makinesi` gibi).
    """
    if istenen:
        aday = istenen
        if normalestir:
            # Slug upstream `function.name` olur; yalnız [a-z0-9-] güvenli.
            aday = (slug_uret(istenen)[:60] or "arac").strip("-") or "arac"
        return await _slug_dogrula(oturum, org_id, aday, haric_id=haric_id)
    taban = (slug_uret(ad)[:60] or "arac").strip("-") or "arac"
    aday = taban
    sayac = 2
    while True:
        kosullar = [Arac.org_id == org_id, Arac.slug == aday]
        if haric_id is not None:
            kosullar.append(Arac.id != haric_id)
        var = (
            await oturum.execute(sa.select(Arac.id).where(*kosullar))
        ).scalar_one_or_none()
        if var is None:
            return aday
        aday = f"{taban}-{sayac}"
        sayac += 1
        if sayac > 500:  # pragma: no cover - savunma
            raise Cakisma("arac_slug_kullaniliyor", {"slug": taban}, ceviriler={"slug": taban})


def _konfigurasyon_dogrula(tur: AracTuru, slug: str, uc_noktasi: str) -> str:
    """Tür/slug/uç noktası tutarlılığını denetler; saklanacak adresi döndürür."""
    if tur == AracTuru.yerlesik:
        if slug not in arac_servisi.YERLESIK_SLUGLAR:
            raise GecersizIstek(
                "arac_yerlesik_bilinmiyor", {"slug": slug}, ceviriler={"slug": slug}
            )
        return ""
    return arac_servisi.uc_noktasi_dogrula(uc_noktasi)


def _sema_sec(tur: AracTuru, slug: str, sema: dict[str, Any]) -> dict[str, Any]:
    if sema:
        return sema
    if tur == AracTuru.yerlesik:
        return dict(arac_servisi.YERLESIK_SEMALAR.get(slug, {}))
    return {}


@router.get("/araclar")
async def araclari_listele(
    etkin: bool | None = Query(default=None),
    oturum: AsyncSession = Depends(veritabani_oturumu),
    _personel: Kullanici = Depends(gecerli_personel()),
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
) -> list[dict[str, Any]]:
    """Aktif organizasyonun araçları."""
    kosullar: list[sa.ColumnElement[bool]] = [Arac.org_id == organizasyon.id]
    if etkin is not None:
        kosullar.append(Arac.etkin.is_(etkin))
    satirlar = (
        await oturum.execute(
            sa.select(Arac).where(*kosullar).order_by(Arac.id)
        )
    ).scalars().all()
    return [_sozluk(arac) for arac in satirlar]


@router.get("/araclar/cagrilar")
async def cagrilari_listele(
    arac_id: int | None = Query(default=None),
    durum: AracCagrisiDurumu | None = Query(default=None),
    sayfa: int = Query(default=1, ge=1),
    boyut: int = Query(default=25, ge=1, le=EN_BUYUK_SAYFA_BOYUTU),
    oturum: AsyncSession = Depends(veritabani_oturumu),
    _personel: Kullanici = Depends(gecerli_personel()),
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
) -> dict[str, Any]:
    """Çağrı günlüğü: yeni kayıt önce, `arac_id` ve `durum` ile süzülebilir."""
    kosullar: list[sa.ColumnElement[bool]] = [AracCagrisi.org_id == organizasyon.id]
    if arac_id is not None:
        kosullar.append(AracCagrisi.arac_id == arac_id)
    if durum is not None:
        kosullar.append(AracCagrisi.durum == durum)

    toplam = (
        await oturum.execute(
            sa.select(sa.func.count()).select_from(AracCagrisi).where(*kosullar)
        )
    ).scalar_one()
    satirlar = (
        await oturum.execute(
            sa.select(AracCagrisi)
            .where(*kosullar)
            .order_by(AracCagrisi.olusturulma.desc(), AracCagrisi.id.desc())
            .offset((sayfa - 1) * boyut)
            .limit(boyut)
        )
    ).scalars().all()
    return {
        "toplam": int(toplam),
        "sayfa": sayfa,
        "boyut": boyut,
        "kayitlar": [_cagri_sozluk(kayit) for kayit in satirlar],
    }


@router.post("/araclar", status_code=201)
async def arac_olustur(
    veri: AracOlustur,
    istek: Request,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    personel: Kullanici = Depends(gecerli_personel(YAZMA_ROLLERI)),
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
) -> dict[str, Any]:
    """Yeni araç tanımlar (webhook ya da yerleşik)."""
    if veri.tur == AracTuru.yerlesik:
        if not veri.slug or veri.slug not in arac_servisi.YERLESIK_SLUGLAR:
            raise GecersizIstek(
                "arac_yerlesik_bilinmiyor",
                {"slug": veri.slug or ""},
                ceviriler={"slug": veri.slug or ""},
            )
        slug = await _slug_dogrula(oturum, organizasyon.id, veri.slug)
    else:
        slug = await _slug_sec(oturum, organizasyon.id, veri.ad, veri.slug)
    uc_noktasi = _konfigurasyon_dogrula(veri.tur, slug, veri.uc_noktasi)

    arac = Arac(
        org_id=organizasyon.id,
        ad=veri.ad,
        slug=slug,
        aciklama=veri.aciklama,
        json_sema=_sema_sec(veri.tur, slug, veri.json_sema),
        tur=veri.tur,
        uc_noktasi=uc_noktasi,
        basliklar_sifreli=arac_servisi.basliklari_sifrele(veri.basliklar),
        etkin=veri.etkin,
    )
    oturum.add(arac)
    try:
        await oturum.flush()
    except IntegrityError as hata:
        raise Cakisma(
            "arac_slug_kullaniliyor", {"slug": slug}, ceviriler={"slug": slug}
        ) from hata

    await islem_kaydet(
        oturum,
        "arac.olusturuldu",
        org_id=organizasyon.id,
        kullanici_id=personel.id,
        hedef_tur="arac",
        hedef_id=arac.id,
        ayrinti={"slug": slug, "tur": veri.tur.value},
        ip=istek.client.host if istek.client else "",
    )
    return _sozluk(arac)


@router.patch("/araclar/{arac_id}")
async def arac_guncelle(
    arac_id: int,
    veri: AracGuncelle,
    istek: Request,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    personel: Kullanici = Depends(gecerli_personel(YAZMA_ROLLERI)),
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
) -> dict[str, Any]:
    """Aracı kısmen günceller."""
    arac = await _arac_getir(oturum, organizasyon.id, arac_id)
    ham = veri.model_dump(exclude_unset=True)

    yeni_tur = ham.get("tur") or arac.tur
    yeni_slug = arac.slug
    if "slug" in ham and ham["slug"] and ham["slug"] != arac.slug:
        yeni_slug = await _slug_sec(
            oturum,
            organizasyon.id,
            arac.ad,
            ham["slug"],
            haric_id=arac.id,
            normalestir=yeni_tur != AracTuru.yerlesik,
        )

    yeni_uc = ham["uc_noktasi"] if "uc_noktasi" in ham else arac.uc_noktasi
    if yeni_tur == AracTuru.yerlesik:
        yeni_uc = _konfigurasyon_dogrula(yeni_tur, yeni_slug, "")
    elif "tur" in ham or "uc_noktasi" in ham or "slug" in ham:
        yeni_uc = _konfigurasyon_dogrula(yeni_tur, yeni_slug, yeni_uc or "")

    if "ad" in ham and ham["ad"]:
        arac.ad = ham["ad"]
    arac.slug = yeni_slug
    if "aciklama" in ham and ham["aciklama"] is not None:
        arac.aciklama = ham["aciklama"]
    if "tur" in ham and ham["tur"] is not None:
        arac.tur = yeni_tur
    arac.uc_noktasi = yeni_uc
    if "json_sema" in ham and ham["json_sema"] is not None:
        arac.json_sema = _sema_sec(yeni_tur, yeni_slug, ham["json_sema"])
    if "basliklar" in ham and ham["basliklar"] is not None:
        arac.basliklar_sifreli = arac_servisi.basliklari_sifrele(ham["basliklar"])
    if "etkin" in ham and ham["etkin"] is not None:
        arac.etkin = bool(ham["etkin"])

    try:
        await oturum.flush()
    except IntegrityError as hata:
        raise Cakisma(
            "arac_slug_kullaniliyor", {"slug": arac.slug}, ceviriler={"slug": arac.slug}
        ) from hata

    await islem_kaydet(
        oturum,
        "arac.guncellendi",
        org_id=organizasyon.id,
        kullanici_id=personel.id,
        hedef_tur="arac",
        hedef_id=arac.id,
        ayrinti={"alanlar": sorted(ham)},
        ip=istek.client.host if istek.client else "",
    )
    return _sozluk(arac)


@router.delete("/araclar/{arac_id}", status_code=204, response_model=None)
async def arac_sil(
    arac_id: int,
    istek: Request,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    personel: Kullanici = Depends(gecerli_personel(YAZMA_ROLLERI)),
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
) -> None:
    """Aracı siler; geçmiş çağrı kayıtları korunur (`arac_id` boşalır)."""
    arac = await _arac_getir(oturum, organizasyon.id, arac_id)
    await oturum.delete(arac)
    await oturum.flush()
    await islem_kaydet(
        oturum,
        "arac.silindi",
        org_id=organizasyon.id,
        kullanici_id=personel.id,
        hedef_tur="arac",
        hedef_id=arac_id,
        ayrinti={"slug": arac.slug},
        ip=istek.client.host if istek.client else "",
    )


@router.post("/araclar/{arac_id}/dene")
async def arac_dene(
    arac_id: int,
    veri: DenemeIstegi,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    _personel: Kullanici = Depends(gecerli_personel(YAZMA_ROLLERI)),
    organizasyon: Organizasyon = Depends(aktif_organizasyon),
) -> dict[str, Any]:
    """Aracı verilen argümanlarla çalıştırır.

    Argüman şema ihlali `400 gecersiz_istek`; çalıştırma hatası
    `502 arac_hatasi`. Çağrı kaydı her durumda saklanır.
    """
    arac = await _arac_getir(oturum, organizasyon.id, arac_id)
    sonuc = await arac_servisi.arac_calistir(
        oturum, org_id=organizasyon.id, arac=arac, argumanlar=veri.cozulen()
    )
    if sonuc["durum"] != AracCagrisiDurumu.basarili.value:
        # Çağrı günlüğü hata yolunda da kalıcı olsun diye önce yaz.
        await oturum.commit()
        kod = sonuc.get("kod")
        if kod in ISTEMCI_HATALARI:
            raise GecersizIstek(kod, {"arac_id": arac.id})
        raise AracHatasi("arac_hatasi", {"arac_id": arac.id, "neden": sonuc["hata"]})
    return {
        "arac_id": arac.id,
        "ad": arac.slug,
        "durum": sonuc["durum"],
        "sonuc": sonuc["sonuc"],
        "gecikme_ms": sonuc["gecikme_ms"],
    }
