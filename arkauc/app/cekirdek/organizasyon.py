"""Organizasyon (kiraci) yardimcilari (spec §2).

Aktif organizasyon cozumunun tek kaynagi burasidir:
1. `X-Organizasyon: <slug>` basligi
2. erisim jetonundaki `org` claim'i
3. API anahtarinin bagli oldugu organizasyon
4. kullanicinin ilk aktif uyeligi
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek.hatalar import (
    Cakisma,
    OrgErisimYok,
    YetkiYok,
    GecersizIstek,
)
from bdm_veritabani.modeller import (
    ORGANIZASYON_GEREKLI_MESAJ,
    ApiAnahtari,
    Kullanici,
    Organizasyon,
    OrganizasyonDurumu,
    Rol,
    ROL_ESLEME,
    Uyelik,
    UyelikDurumu,
    UyelikRolu,
)

ORG_BASLIGI = "x-organizasyon"


async def uyelik_getir(
    oturum: AsyncSession, organizasyon_id: int, kullanici_id: int
) -> Uyelik | None:
    return (
        await oturum.execute(
            sa.select(Uyelik).where(
                Uyelik.organizasyon_id == organizasyon_id,
                Uyelik.kullanici_id == kullanici_id,
            )
        )
    ).scalar_one_or_none()


async def aktif_uyelikler(oturum: AsyncSession, kullanici_id: int) -> list[Uyelik]:
    return list(
        (
            await oturum.execute(
                sa.select(Uyelik)
                .where(Uyelik.kullanici_id == kullanici_id)
                .order_by(Uyelik.id)
            )
        ).scalars().all()
    )


async def organizasyon_getir_slug(oturum: AsyncSession, slug: str) -> Organizasyon | None:
    return (
        await oturum.execute(
            sa.select(Organizasyon).where(Organizasyon.slug == slug)
        )
    ).scalar_one_or_none()


async def organizasyon_getir(oturum: AsyncSession, organizasyon_id: int) -> Organizasyon:
    organizasyon = await oturum.get(Organizasyon, organizasyon_id)
    if organizasyon is None:
        raise GecersizIstek("Organizasyon bulunamadı.", {"organizasyon_id": organizasyon_id})
    return organizasyon


async def organizasyon_durumu_denetle(organizasyon: Organizasyon) -> None:
    if organizasyon.durum != OrganizasyonDurumu.aktif:
        raise YetkiYok("Bu organizasyon askıya alınmış.")


async def uyelik_ekle(
    oturum: AsyncSession,
    *,
    organizasyon_id: int,
    kullanici_id: int,
    rol: UyelikRolu,
    durum: UyelikDurumu = UyelikDurumu.aktif,
) -> Uyelik:
    mevcut = await uyelik_getir(oturum, organizasyon_id, kullanici_id)
    if mevcut is not None:
        raise Cakisma("Bu kullanıcı zaten organizasyonun üyesi.")
    uyelik = Uyelik(
        organizasyon_id=organizasyon_id,
        kullanici_id=kullanici_id,
        rol=rol,
        durum=durum,
    )
    oturum.add(uyelik)
    await oturum.flush()
    return uyelik


async def varsayilan_uyelik_ekle(
    oturum: AsyncSession, kullanici: Kullanici, *, rol: UyelikRolu | None = None
) -> Uyelik:
    """Kullaniciyi varsayilan organizasyona ekler (JIT, kurulum, testler).

    `rol` verilmezse kullanicinin varsayilan rolunden turetilir. `sahip` rolu
    yalnizca acikca verilir (kurulum sihirbazi ve goc).
    """
    from bdm_veritabani.tohum import varsayilan_organizasyon

    organizasyon = await varsayilan_organizasyon(oturum)
    mevcut = await uyelik_getir(oturum, organizasyon.id, kullanici.id)
    if mevcut is not None:
        return mevcut

    uyelik = Uyelik(
        organizasyon_id=organizasyon.id,
        kullanici_id=kullanici.id,
        rol=rol or ROL_ESLEME[kullanici.rol],
        durum=UyelikDurumu.aktif,
    )
    oturum.add(uyelik)
    await oturum.flush()
    return uyelik


async def denetim_organizasyonu(oturum: AsyncSession, kullanici_id: int) -> int:
    """Denetim izi etiketlemesi icin organizasyon kimligi.

    Kullanicinin ilk aktif uyeligi; hic uyeligi yoksa varsayilan organizasyon
    dondurulur. Boylece kimlik/ayar gibi organizasyon baglami tasimayan
    eylemler de bir kiracinin denetim izinde gorunur, hicbir kayit
    organizasyonsuz (tum kiraclara acik) kalmaz.
    """
    organizasyon_id = (
        await oturum.execute(
            sa.select(Uyelik.organizasyon_id)
            .where(Uyelik.kullanici_id == kullanici_id, Uyelik.durum == UyelikDurumu.aktif)
            .order_by(Uyelik.id)
            .limit(1)
        )
    ).scalar_one_or_none()
    if organizasyon_id is not None:
        return int(organizasyon_id)

    from bdm_veritabani.tohum import varsayilan_organizasyon

    return (await varsayilan_organizasyon(oturum)).id


async def _organizasyon_sec(
    oturum: AsyncSession,
    *,
    baslik: str | None,
    org_claim: int | None,
    kullanici_id: int | None,
    anahtar: ApiAnahtari | None,
    varsayilana_ekle: bool,
) -> Organizasyon:
    """Durum denetimi yapmadan aktif organizasyonu secer (spec §2.2 oncelik sirasi).

    Askida organizasyon denetimi cagirana aittir; boylece hangi dalla
    cozulurse cozulsun ayni kapiya takilir.
    """
    if baslik:
        organizasyon = await organizasyon_getir_slug(oturum, baslik.strip())
        if organizasyon is None:
            raise YetkiYok("Belirtilen organizasyona erişiminiz yok.")
        if anahtar is not None:
            if anahtar.org_id != organizasyon.id:
                raise OrgErisimYok()
            return organizasyon
        if kullanici_id is None:
            raise YetkiYok()
        uyelik = await uyelik_getir(oturum, organizasyon.id, kullanici_id)
        if uyelik is None or uyelik.durum != UyelikDurumu.aktif:
            raise YetkiYok("Belirtilen organizasyona erişiminiz yok.")
        return organizasyon

    if anahtar is not None:
        return await organizasyon_getir(oturum, anahtar.org_id)

    if kullanici_id is None:
        raise GecersizIstek("organizasyon_gerekli", {"neden": ORGANIZASYON_GEREKLI_MESAJ})

    if org_claim is not None:
        uyelik = await uyelik_getir(oturum, org_claim, kullanici_id)
        if uyelik is not None and uyelik.durum == UyelikDurumu.aktif:
            return await organizasyon_getir(oturum, org_claim)

    for uyelik in await aktif_uyelikler(oturum, kullanici_id):
        if uyelik.durum != UyelikDurumu.aktif:
            continue
        organizasyon = await organizasyon_getir(oturum, uyelik.organizasyon_id)
        if organizasyon.durum == OrganizasyonDurumu.aktif:
            return organizasyon

    if varsayilana_ekle:
        kullanici = await oturum.get(Kullanici, kullanici_id)
        if kullanici is not None:
            await varsayilan_uyelik_ekle(oturum, kullanici)
            return await _organizasyon_sec(
                oturum,
                baslik=baslik,
                org_claim=org_claim,
                kullanici_id=kullanici_id,
                anahtar=anahtar,
                varsayilana_ekle=False,
            )

    raise GecersizIstek("organizasyon_gerekli", {"neden": ORGANIZASYON_GEREKLI_MESAJ})


async def organizasyon_coz(
    oturum: AsyncSession,
    *,
    baslik: str | None = None,
    org_claim: int | None = None,
    kullanici_id: int | None = None,
    anahtar: ApiAnahtari | None = None,
    varsayilana_ekle: bool = False,
) -> Organizasyon:
    """Aktif organizasyonu cozer (spec §2.2 oncelik sirasi).

    Cozulen organizasyonun durumu tek cikis noktasinda denetlenir: askida
    organizasyon hangi dalla cozulmus olursa olsun `403 yetki_yok` dondurur.

    `varsayilana_ekle=True` iken hic uyeligi olmayan kullanici varsayilan
    organizasyona eklenir (tek kiracili kurulumlarin ve ilk kullanicinin
    sorunsuz calismasi icin). Panel uclari bunu kullanmaz.
    """
    organizasyon = await _organizasyon_sec(
        oturum,
        baslik=baslik,
        org_claim=org_claim,
        kullanici_id=kullanici_id,
        anahtar=anahtar,
        varsayilana_ekle=varsayilana_ekle,
    )
    await organizasyon_durumu_denetle(organizasyon)
    return organizasyon


def rol_yetkili_mi(uyelik_rolu: UyelikRolu, izinli: tuple[UyelikRolu, ...]) -> bool:
    """`sahip` her zaman yetkilidir."""
    if uyelik_rolu == UyelikRolu.sahip:
        return True
    return uyelik_rolu in izinli


def uyelik_rolleri(roller: tuple[Rol | UyelikRolu, ...]) -> tuple[UyelikRolu, ...]:
    """`Rol` ve `UyelikRolu` karisik verilebilir; ortak tipe cevrilir."""
    sonuc: list[UyelikRolu] = []
    for rol in roller:
        if isinstance(rol, UyelikRolu):
            sonuc.append(rol)
        elif isinstance(rol, Rol):
            sonuc.append(ROL_ESLEME[rol])
        else:  # pragma: no cover - savunma
            raise ValueError(f"Bilinmeyen rol: {rol!r}")
    return tuple(sonuc)
