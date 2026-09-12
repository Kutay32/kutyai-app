"""BDM katalog islemleri — spec §4.5, §7.3."""

from __future__ import annotations

import json
import pathlib
import unicodedata

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek import guvenlik
from arkauc.app.cekirdek.hatalar import Bulunamadi, Cakisma, GecersizGecis, GecersizIstek
from bdm_listesi.saglayicilar import (
    GPU_GEREKEN_SAGLAYICILAR,
    YEREL_SAGLAYICILAR,
    saglayici_bilgisi,
)
from bdm_listesi.sema import BdmGuncelle, BdmOlustur
from bdm_veritabani.modeller import Bdm, BdmDurumu, Saglayici

_KOK = pathlib.Path(__file__).resolve().parents[1]
TOHUM_DOSYASI = _KOK / "bdm_listesi" / "tohum_katalog.json"

_TR_HARFLER = str.maketrans(
    {
        "ı": "i",
        "İ": "i",
        "ş": "s",
        "Ş": "s",
        "ğ": "g",
        "Ğ": "g",
        "ü": "u",
        "Ü": "u",
        "ö": "o",
        "Ö": "o",
        "ç": "c",
        "Ç": "c",
    }
)


def slug_uret(ad: str) -> str:
    """Türkçe adlardan URL dostu slug üretir."""
    sade = ad.translate(_TR_HARFLER)
    sade = unicodedata.normalize("NFKD", sade)
    sade = "".join(k for k in sade if not unicodedata.combining(k))
    sade = "".join(k if k.isalnum() else "-" for k in sade.lower())
    while "--" in sade:
        sade = sade.replace("--", "-")
    return sade.strip("-")[:72] or "bdm"


def bdm_sozlugu(bdm: Bdm, *, tam_anahtar: bool = False) -> dict[str, object]:
    """API yanıtı için BDM sözlüğü; upstream anahtarı asla çözülmez."""
    anahtar = ""
    if bdm.api_anahtari_sifreli:
        try:
            cozulmus = guvenlik.coz(bdm.api_anahtari_sifreli)
            anahtar = cozulmus if tam_anahtar else guvenlik.maskele(cozulmus)
        except Exception:  # pragma: no cover - bozuk şifreli değer
            anahtar = "***"
    return {
        "id": bdm.id,
        "slug": bdm.slug,
        "gorunen_ad": bdm.gorunen_ad,
        "aciklama": bdm.aciklama,
        "saglayici": bdm.saglayici.value,
        "temel_url": bdm.temel_url,
        "upstream_model": bdm.upstream_model,
        "api_anahtari_maskeli": anahtar,
        "baglam_penceresi": bdm.baglam_penceresi,
        "maks_cikti": bdm.maks_cikti,
        "sicaklik_varsayilan": bdm.sicaklik_varsayilan,
        "sistem_istemi": bdm.sistem_istemi,
        "yetenekler": bdm.yetenekler or {},
        "durum": bdm.durum.value,
        "yerel_mi": bdm.yerel_mi,
        "konteyner": bdm.konteyner,
        "olusturulma": bdm.olusturulma.isoformat() if bdm.olusturulma else None,
        "guncellenme": bdm.guncellenme.isoformat() if bdm.guncellenme else None,
    }


def bdm_ozeti(bdm: Bdm) -> dict[str, object]:
    return {
        "id": bdm.id,
        "slug": bdm.slug,
        "gorunen_ad": bdm.gorunen_ad,
        "aciklama": bdm.aciklama,
        "saglayici": bdm.saglayici.value,
        "baglam_penceresi": bdm.baglam_penceresi,
        "yetenekler": bdm.yetenekler or {},
        "durum": bdm.durum.value,
    }


async def slug_bos_mu(oturum: AsyncSession, slug: str) -> bool:
    return (
        await oturum.execute(sa.select(Bdm.id).where(Bdm.slug == slug))
    ).scalar_one_or_none() is None


async def _tekil_slug(oturum: AsyncSession, ad: str, istenen: str | None = None) -> str:
    taban = slug_uret(istenen or ad)
    if await slug_bos_mu(oturum, taban):
        return taban
    if istenen:
        raise Cakisma(f"'{taban}' slug'ı zaten kullanılıyor.", {"alan": "slug"})
    sayac = 2
    while not await slug_bos_mu(oturum, f"{taban}-{sayac}"):
        sayac += 1
        if sayac > 200:
            raise Cakisma("Uygun bir slug üretilemedi.")
    return f"{taban}-{sayac}"


async def bdm_olustur(oturum: AsyncSession, veri: BdmOlustur) -> Bdm:
    bilgi = saglayici_bilgisi(veri.saglayici.value)
    temel_url = veri.temel_url or bilgi.varsayilan_temel_url
    if not temel_url:
        raise GecersizIstek("Bu sağlayıcı için temel adres zorunludur.", {"alan": "temel_url"})

    yerel = bilgi.yerel if veri.yerel_mi is None else veri.yerel_mi
    yetenekler = veri.yetenekler or {
        "akis": bilgi.akis_destegi,
        "gorsel": False,
        "arac": False,
    }
    bdm = Bdm(
        slug=await _tekil_slug(oturum, veri.gorunen_ad, veri.slug),
        gorunen_ad=veri.gorunen_ad,
        aciklama=veri.aciklama,
        saglayici=Saglayici(veri.saglayici.value),
        temel_url=temel_url,
        upstream_model=veri.upstream_model,
        api_anahtari_sifreli=guvenlik.sifrele(veri.api_anahtari) if veri.api_anahtari else None,
        baglam_penceresi=veri.baglam_penceresi,
        maks_cikti=veri.maks_cikti,
        sicaklik_varsayilan=veri.sicaklik_varsayilan,
        sistem_istemi=veri.sistem_istemi,
        yetenekler=yetenekler,
        durum=BdmDurumu.taslak,
        yerel_mi=yerel,
    )
    oturum.add(bdm)
    await oturum.flush()
    await oturum.refresh(bdm)
    return bdm


async def bdm_guncelle(oturum: AsyncSession, bdm: Bdm, veri: BdmGuncelle) -> Bdm:
    ham = veri.model_dump(exclude_unset=True)
    if "saglayici" in ham and ham["saglayici"] is not None:
        bdm.saglayici = Saglayici(ham.pop("saglayici").value)
        bilgi = saglayici_bilgisi(bdm.saglayici.value)
        bdm.yerel_mi = bilgi.yerel
        if not bdm.temel_url:
            bdm.temel_url = bilgi.varsayilan_temel_url
    if "api_anahtari" in ham:
        anahtar = ham.pop("api_anahtari")
        bdm.api_anahtari_sifreli = guvenlik.sifrele(anahtar) if anahtar else None
    for alan, deger in ham.items():
        if deger is not None:
            setattr(bdm, alan, deger)
    await oturum.flush()
    await oturum.refresh(bdm)
    return bdm


async def bdm_getir(oturum: AsyncSession, bdm_id: int) -> Bdm:
    bdm = await oturum.get(Bdm, bdm_id)
    if bdm is None:
        raise Bulunamadi("BDM kaydı bulunamadı.", {"bdm_id": bdm_id})
    return bdm


async def bdm_slug_getir(oturum: AsyncSession, slug: str) -> Bdm:
    bdm = (
        await oturum.execute(sa.select(Bdm).where(Bdm.slug == slug))
    ).scalar_one_or_none()
    if bdm is None:
        raise Bulunamadi("BDM kaydı bulunamadı.", {"slug": slug})
    return bdm


async def bdm_listele(
    oturum: AsyncSession,
    *,
    durumlar: tuple[BdmDurumu, ...] | None = None,
    arama: str | None = None,
) -> list[Bdm]:
    sorgu = sa.select(Bdm).order_by(Bdm.gorunen_ad)
    if durumlar:
        sorgu = sorgu.where(Bdm.durum.in_([d for d in durumlar]))
    if arama:
        desen = f"%{arama.strip()}%"
        sorgu = sorgu.where(sa.or_(Bdm.gorunen_ad.ilike(desen), Bdm.slug.ilike(desen)))
    return list((await oturum.execute(sorgu)).scalars().all())


async def bdm_sil(oturum: AsyncSession, bdm: Bdm) -> None:
    """BDM'i siler; bagli konusma/kullanim kaydi varsa 409 firlatir."""
    from bdm_veritabani.modeller import KullanimKaydi, Konusma

    konusma_sayisi = (
        await oturum.execute(
            sa.select(sa.func.count()).select_from(Konusma).where(Konusma.bdm_id == bdm.id)
        )
    ).scalar_one()
    if konusma_sayisi:
        raise GecersizGecis(
            f"Bu modelin {int(konusma_sayisi)} konuşma kaydı var. Önce kayıtları silin; "
            "modeli kullanımdan kaldırmak için durdurun.",
            {"konusma_sayisi": int(konusma_sayisi)},
        )
    kullanim_sayisi = (
        await oturum.execute(
            sa.select(sa.func.count())
            .select_from(KullanimKaydi)
            .where(KullanimKaydi.bdm_id == bdm.id)
        )
    ).scalar_one()
    if kullanim_sayisi:
        raise GecersizGecis(
            f"Bu modelin {int(kullanim_sayisi)} kullanım kaydı var; silinemez.",
            {"kullanim_kaydi": int(kullanim_sayisi)},
        )
    await oturum.delete(bdm)
    try:
        await oturum.flush()
    except IntegrityError as hata:
        raise GecersizGecis("Bu modele bağlı kayıtlar olduğu için silinemedi.") from hata


async def bdm_kopyala(oturum: AsyncSession, bdm: Bdm, yeni_ad: str, yeni_slug: str | None) -> Bdm:
    yeni = Bdm(
        slug=await _tekil_slug(oturum, yeni_ad, yeni_slug),
        gorunen_ad=yeni_ad,
        aciklama=bdm.aciklama,
        saglayici=bdm.saglayici,
        temel_url=bdm.temel_url,
        upstream_model=bdm.upstream_model,
        api_anahtari_sifreli=bdm.api_anahtari_sifreli,
        baglam_penceresi=bdm.baglam_penceresi,
        maks_cikti=bdm.maks_cikti,
        sicaklik_varsayilan=bdm.sicaklik_varsayilan,
        sistem_istemi=bdm.sistem_istemi,
        yetenekler=dict(bdm.yetenekler or {}),
        durum=BdmDurumu.taslak,
        yerel_mi=bdm.yerel_mi,
    )
    oturum.add(yeni)
    await oturum.flush()
    await oturum.refresh(yeni)
    return yeni


async def kullanilabilir_modeller(
    oturum: AsyncSession, izinli_modeller: list[str] | None = None
) -> list[dict[str, object]]:
    """Sohbet istemcisine acik modeller: hazir veya calisiyor olanlar."""
    modeller = await bdm_listele(
        oturum, durumlar=(BdmDurumu.hazir, BdmDurumu.calisiyor)
    )
    if izinli_modeller:
        izin = {str(x) for x in izinli_modeller}
        modeller = [m for m in modeller if m.slug in izin or str(m.id) in izin]
    return [bdm_ozeti(m) for m in modeller]


def tohum_katalogu_oku() -> list[dict[str, object]]:
    if not TOHUM_DOSYASI.exists():  # pragma: no cover - dosya her zaman var
        return []
    return json.loads(TOHUM_DOSYASI.read_text(encoding="utf-8"))


async def tohum_katalogunu_yukle(oturum: AsyncSession) -> int:
    """Ornek katalog kayitlarini ekler (idempotent)."""
    eklenen = 0
    for kayit in tohum_katalogu_oku():
        slug = str(kayit.get("slug") or "")
        if not slug or not await slug_bos_mu(oturum, slug):
            continue
        try:
            veri = BdmOlustur(**kayit)  # type: ignore[arg-type]
        except Exception:  # pragma: no cover - bozuk tohum kaydı
            continue
        await bdm_olustur(oturum, veri)
        eklenen += 1
    return eklenen


def gpu_gerekir_mi(saglayici: str) -> bool:
    return saglayici in GPU_GEREKEN_SAGLAYICILAR


def yerel_mi(saglayici: str) -> bool:
    return saglayici in YEREL_SAGLAYICILAR
