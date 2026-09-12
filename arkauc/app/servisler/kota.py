"""Kota denetimi ve sayaclari (spec §4.9, §9).

Iki kapsam desteklenir: `kullanici` ve `api_anahtari`. Gunluk istek sayaci
`gun_sifirlanma`, aylik token sayaci `ay_sifirlanma` gectiginde sifirlanir.
Sinir tanimli degilse (`gunluk_istek` ve `aylik_token` bos) kapsam serbesttir.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek.hatalar import KotaAsildi
from bdm_veritabani.modeller import ApiAnahtari, Kota, KotaKapsami


def _utc(an: datetime) -> datetime:
    """SQLite naive dondurur; karsilastirma icin UTC kabul edilir."""
    return an if an.tzinfo else an.replace(tzinfo=timezone.utc)


def gun_sonu(an: datetime | None = None) -> datetime:
    """Icinde bulunulan gunun bitisi (ertesi gun 00:00 UTC)."""
    an = _utc(an or datetime.now(timezone.utc))
    return an.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)


def ay_sonu(an: datetime | None = None) -> datetime:
    """Icinde bulunulan ayin bitisi (gelecek ayin 1'i 00:00 UTC)."""
    an = _utc(an or datetime.now(timezone.utc))
    baslangic = an.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return (baslangic + timedelta(days=32)).replace(day=1)


def iso(an: datetime) -> str:
    return _utc(an).isoformat().replace("+00:00", "Z")


def _sifirla(kayit: Kota, an: datetime) -> None:
    """Suresi gecmis sayaclari sifirlar."""
    if _utc(kayit.gun_sifirlanma) <= an:
        kayit.kullanilan_gunluk = 0
        kayit.gun_sifirlanma = gun_sonu(an)
    if _utc(kayit.ay_sifirlanma) <= an:
        kayit.kullanilan_aylik = 0
        kayit.ay_sifirlanma = ay_sonu(an)


async def _kayit_getir(
    oturum: AsyncSession, kapsam: KotaKapsami, kapsam_id: int
) -> Kota | None:
    return (
        await oturum.execute(
            sa.select(Kota).where(Kota.kapsam == kapsam, Kota.kapsam_id == kapsam_id)
        )
    ).scalar_one_or_none()


async def _kayit_olustur(
    oturum: AsyncSession, kapsam: KotaKapsami, kapsam_id: int
) -> Kota:
    an = datetime.now(timezone.utc)
    kayit = Kota(
        kapsam=kapsam,
        kapsam_id=kapsam_id,
        gun_sifirlanma=gun_sonu(an),
        ay_sifirlanma=ay_sonu(an),
    )
    oturum.add(kayit)
    await oturum.flush()
    return kayit


async def _anahtar(oturum: AsyncSession, api_anahtari_id: int | None) -> ApiAnahtari | None:
    if api_anahtari_id is None:
        return None
    return await oturum.get(ApiAnahtari, api_anahtari_id)


async def _kapsamlar(
    oturum: AsyncSession,
    *,
    kullanici_id: int | None,
    api_anahtari_id: int | None,
    olustur: bool,
) -> list[tuple[Kota | None, int | None, int | None]]:
    """Etkin kapsamlari `(kayit, gunluk_limit, aylik_limit)` olarak dondurur."""
    kapsamlar: list[tuple[Kota | None, int | None, int | None]] = []

    if kullanici_id is not None:
        kayit = await _kayit_getir(oturum, KotaKapsami.kullanici, kullanici_id)
        if kayit is not None:
            kapsamlar.append((kayit, kayit.gunluk_istek, kayit.aylik_token))

    if api_anahtari_id is not None:
        anahtar = await _anahtar(oturum, api_anahtari_id)
        if anahtar is not None:
            kayit = await _kayit_getir(oturum, KotaKapsami.api_anahtari, api_anahtari_id)
            if kayit is None and olustur and anahtar.gunluk_istek_siniri is not None:
                kayit = await _kayit_olustur(
                    oturum, KotaKapsami.api_anahtari, api_anahtari_id
                )
            # Anahtarin kendi gunluk siniri kapsam limitini gecersiz kilar.
            gunluk = (
                anahtar.gunluk_istek_siniri
                if anahtar.gunluk_istek_siniri is not None
                else (kayit.gunluk_istek if kayit is not None else None)
            )
            aylik = kayit.aylik_token if kayit is not None else None
            if kayit is not None or gunluk is not None:
                kapsamlar.append((kayit, gunluk, aylik))

    return kapsamlar


def _ayrinti(kayit: Kota, sifirlanma: datetime, bdm_id: int | None) -> dict[str, object]:
    ayrinti: dict[str, object] = {
        "kapsam": kayit.kapsam.value,
        "sifirlanma": iso(sifirlanma),
    }
    if bdm_id is not None:
        ayrinti["bdm_id"] = bdm_id
    return ayrinti


async def kota_kullan(
    oturum: AsyncSession,
    *,
    kullanici_id: int | None,
    api_anahtari_id: int | None,
    bdm_id: int | None = None,
    token: int = 0,
) -> None:
    """Istegi kotadan duser: sayaci tek kosullu UPDATE ile atomik artirir.

    Gunluk/aylik limit dolduysa hicbir sayac artmaz ve `429 kota_asildi`
    firlatilir. Kosul ve artirim ayni SQL ifadesinde oldugu icin paralel
    isteklerden yalnizca biri sayaci ilerletir (kayip guncelleme yok).
    """
    an = datetime.now(timezone.utc)
    for kayit, gunluk, aylik in await _kapsamlar(
        oturum,
        kullanici_id=kullanici_id,
        api_anahtari_id=api_anahtari_id,
        olustur=True,
    ):
        if kayit is None:
            continue
        _sifirla(kayit, an)
        await oturum.flush()
        kosullar: list[sa.ColumnElement[bool]] = [Kota.id == kayit.id]
        if gunluk is not None:
            kosullar.append(Kota.kullanilan_gunluk < gunluk)
        if aylik is not None:
            kosullar.append(Kota.kullanilan_aylik < aylik)
        sonuc = await oturum.execute(
            sa.update(Kota)
            .where(*kosullar)
            .values(
                kullanilan_gunluk=Kota.kullanilan_gunluk + 1,
                kullanilan_aylik=Kota.kullanilan_aylik + max(0, int(token)),
            )
            .execution_options(synchronize_session="fetch")
        )
        if int(sonuc.rowcount or 0) == 1:
            continue
        await oturum.refresh(kayit)
        if gunluk is not None and kayit.kullanilan_gunluk >= gunluk:
            raise KotaAsildi(
                "Günlük istek kotanız doldu.",
                _ayrinti(kayit, kayit.gun_sifirlanma, bdm_id),
            )
        if aylik is not None and kayit.kullanilan_aylik >= aylik:
            raise KotaAsildi(
                "Aylık token kotanız doldu.",
                _ayrinti(kayit, kayit.ay_sifirlanma, bdm_id),
            )
        raise KotaAsildi("Kotanız doldu.", _ayrinti(kayit, kayit.gun_sifirlanma, bdm_id))


async def kota_token_ekle(
    oturum: AsyncSession,
    *,
    kullanici_id: int | None,
    api_anahtari_id: int | None,
    token: int,
) -> None:
    """Aylik token sayacini tek SQL ifadesiyle atomik artirir (limit denetlemez)."""
    token = max(0, int(token))
    if token == 0:
        return
    an = datetime.now(timezone.utc)
    for kayit, _, _ in await _kapsamlar(
        oturum,
        kullanici_id=kullanici_id,
        api_anahtari_id=api_anahtari_id,
        olustur=False,
    ):
        if kayit is None:
            continue
        _sifirla(kayit, an)
        await oturum.flush()
        await oturum.execute(
            sa.update(Kota)
            .where(Kota.id == kayit.id)
            .values(kullanilan_aylik=Kota.kullanilan_aylik + token)
            .execution_options(synchronize_session="fetch")
        )


async def kota_durumu(
    oturum: AsyncSession,
    *,
    kullanici_id: int | None,
    api_anahtari_id: int | None,
) -> dict[str, object]:
    """Her iki kapsamin limit ve sayaclarini raporlar."""
    an = datetime.now(timezone.utc)
    kayitlar = {
        kayit.kapsam: (kayit, gunluk, aylik)
        for kayit, gunluk, aylik in await _kapsamlar(
            oturum,
            kullanici_id=kullanici_id,
            api_anahtari_id=api_anahtari_id,
            olustur=False,
        )
    }

    def _sozluk(kapsam: KotaKapsami) -> dict[str, object]:
        kayit, gunluk, aylik = kayitlar.get(kapsam, (None, None, None))
        if kayit is None:
            return {
                "gunluk_istek": gunluk,
                "aylik_token": aylik,
                "kullanilan_gunluk": 0,
                "kullanilan_aylik": 0,
                "gun_sifirlanma": iso(gun_sonu(an)),
                "ay_sifirlanma": iso(ay_sonu(an)),
            }
        return {
            "gunluk_istek": gunluk,
            "aylik_token": aylik,
            "kullanilan_gunluk": kayit.kullanilan_gunluk,
            "kullanilan_aylik": kayit.kullanilan_aylik,
            "gun_sifirlanma": iso(kayit.gun_sifirlanma),
            "ay_sifirlanma": iso(kayit.ay_sifirlanma),
        }

    await oturum.flush()
    return {
        "kullanici": _sozluk(KotaKapsami.kullanici),
        "api_anahtari": _sozluk(KotaKapsami.api_anahtari),
    }


def kapsam_sec(
    *, kullanici_id: int | None, api_anahtari_id: int | None
) -> tuple[KotaKapsami, int] | None:
    """Etkin kapsami secer: anahtar varsa `api_anahtari`, yoksa `kullanici`."""
    if api_anahtari_id is not None:
        return KotaKapsami.api_anahtari, api_anahtari_id
    if kullanici_id is not None:
        return KotaKapsami.kullanici, kullanici_id
    return None


async def kapsam_kota_durumu(
    oturum: AsyncSession,
    *,
    kullanici_id: int | None,
    api_anahtari_id: int | None,
) -> dict[str, object] | None:
    """Secilen kapsamin kota durumu; tanimli kota yoksa `None` doner."""
    secim = kapsam_sec(kullanici_id=kullanici_id, api_anahtari_id=api_anahtari_id)
    if secim is None:
        return None
    kapsam, kapsam_id = secim
    kayit = await _kayit_getir(oturum, kapsam, kapsam_id)
    gunluk = kayit.gunluk_istek if kayit is not None else None
    aylik = kayit.aylik_token if kayit is not None else None
    if kapsam is KotaKapsami.api_anahtari:
        anahtar = await _anahtar(oturum, kapsam_id)
        if anahtar is not None and anahtar.gunluk_istek_siniri is not None:
            gunluk = anahtar.gunluk_istek_siniri
    if kayit is None and gunluk is None and aylik is None:
        return None
    an = datetime.now(timezone.utc)
    kayit_gun = kayit.gun_sifirlanma if kayit is not None else gun_sonu(an)
    kayit_ay = kayit.ay_sifirlanma if kayit is not None else ay_sonu(an)
    return {
        "gunluk_istek": gunluk,
        "kullanilan_gunluk": kayit.kullanilan_gunluk if kayit is not None else 0,
        "aylik_token": aylik,
        "kullanilan_aylik": kayit.kullanilan_aylik if kayit is not None else 0,
        "gun_sifirlanma": iso(kayit_gun),
        "ay_sifirlanma": iso(kayit_ay),
    }
