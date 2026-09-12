"""Kimlik servisleri: kullanici sozlugu, oturum, dogrulama jetonu (spec §4.1-4.3, §7.1-7.2).

Yonlendiriciler ince kalir; parola/oturum/jeton kurallari burada yasar.
Parola ozeti hicbir zaman API yanitina konmaz.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek import guvenlik
from arkauc.app.cekirdek.ayarlar import ayarlar
from arkauc.app.cekirdek.hatalar import (
    Cakisma,
    GecersizIstek,
    JetonGecersiz,
    JetonSuresiDoldu,
    KutyaiHatasi,
    YetkiYok,
)
from bdm_veritabani.modeller import (
    DogrulamaJetonu,
    JetonTuru,
    Kullanici,
    KullaniciDurumu,
    Oturum,
    Rol,
)

EPOSTA_DOGRULAMA_SAAT = 24
SIFRE_SIFIRLAMA_SAAT = 2
EN_KISA_PAROLA = 8

VARSAYILAN_SAYFA_BOYUTU = 25
EN_BUYUK_SAYFA_BOYUTU = 200


class GecersizKimlikBilgisi(KutyaiHatasi):
    """E-posta/parola uyusmazligi; kullanici var mi bilgisini sizdirmaz."""

    durum_kodu = 401
    kod = "gecersiz_kimlik_bilgisi"
    mesaj = "E-posta veya parola hatalı."


# --------------------------------------------------------------------------
# Kullanici yardimcilari
# --------------------------------------------------------------------------


def eposta_normalize(eposta: str) -> str:
    """E-postayi karsilastirma icin sadelestirir (kucuk harf, kirpilmis)."""
    return (eposta or "").strip().lower()


def _iso(deger: datetime | None) -> str | None:
    return deger.isoformat() if deger is not None else None


def _utc(deger: datetime) -> datetime:
    """SQLite'tan saf gelen damgalari UTC farkindalikli hale getirir."""
    if deger.tzinfo is None:
        return deger.replace(tzinfo=timezone.utc)
    return deger


def kullanici_sozlugu(kullanici: Kullanici) -> dict[str, object]:
    """`Kullanici` tipinin API karsiligi; parola ozeti asla donmez."""
    return {
        "id": kullanici.id,
        "eposta": kullanici.eposta,
        "ad_soyad": kullanici.ad_soyad,
        "rol": kullanici.rol.value,
        "durum": kullanici.durum.value,
        "eposta_dogrulandi": bool(kullanici.eposta_dogrulandi),
        "olusturulma": _iso(kullanici.olusturulma),
        "son_giris": _iso(kullanici.son_giris),
    }


def parola_gecerli_mi(kullanici: Kullanici, parola: str) -> bool:
    """Parolayi dogrular; argon2 yeniden hash isterse gunceller."""
    dogru, yeniden_hash = guvenlik.sifre_dogrula(kullanici.sifre_hash, parola)
    if dogru and yeniden_hash:
        kullanici.sifre_hash = guvenlik.sifre_hashle(parola)
    return dogru


def parola_denetle(parola: str) -> None:
    """Parola politikasini uygular (en az 8 karakter)."""
    if len(parola or "") < EN_KISA_PAROLA:
        raise GecersizIstek(f"Parola en az {EN_KISA_PAROLA} karakter olmalıdır.")


async def kullanici_bul(oturum: AsyncSession, eposta: str) -> Kullanici | None:
    return (
        await oturum.execute(
            sa.select(Kullanici).where(Kullanici.eposta == eposta_normalize(eposta))
        )
    ).scalar_one_or_none()


async def kullanici_getir(oturum: AsyncSession, kullanici_id: int) -> Kullanici | None:
    return await oturum.get(Kullanici, kullanici_id)


async def kullanicilari_listele(
    oturum: AsyncSession,
    *,
    rol: Rol | None = None,
    durum: KullaniciDurumu | None = None,
    arama: str | None = None,
    sayfa: int = 1,
    boyut: int = VARSAYILAN_SAYFA_BOYUTU,
) -> dict[str, object]:
    """Filtreli ve sayfali kullanici listesi (`Sayfa<Kullanici>`)."""
    sayfa = max(1, int(sayfa or 1))
    boyut = min(max(1, int(boyut or VARSAYILAN_SAYFA_BOYUTU)), EN_BUYUK_SAYFA_BOYUTU)

    kosullar: list[sa.ColumnElement[bool]] = []
    if rol is not None:
        kosullar.append(Kullanici.rol == rol)
    if durum is not None:
        kosullar.append(Kullanici.durum == durum)
    if arama and arama.strip():
        desen = f"%{arama.strip()}%"
        kosullar.append(
            sa.or_(Kullanici.eposta.ilike(desen), Kullanici.ad_soyad.ilike(desen))
        )

    toplam = int(
        (
            await oturum.execute(
                sa.select(sa.func.count()).select_from(Kullanici).where(*kosullar)
            )
        ).scalar_one()
    )
    kayitlar = (
        await oturum.execute(
            sa.select(Kullanici)
            .where(*kosullar)
            .order_by(Kullanici.id.desc())
            .offset((sayfa - 1) * boyut)
            .limit(boyut)
        )
    ).scalars().all()
    return {
        "toplam": toplam,
        "sayfa": sayfa,
        "boyut": boyut,
        "kayitlar": [kullanici_sozlugu(k) for k in kayitlar],
    }


async def kullanici_olustur(
    oturum: AsyncSession,
    *,
    eposta: str,
    ad_soyad: str,
    parola: str,
    rol: Rol = Rol.son_kullanici,
) -> Kullanici:
    """Yonetici tarafindan olusturulan kullanici: aktif ve dogrulanmis."""
    parola_denetle(parola)
    normal = eposta_normalize(eposta)
    if not normal:
        raise GecersizIstek("E-posta adresi zorunludur.")
    if await kullanici_bul(oturum, normal) is not None:
        raise Cakisma("Bu e-posta adresi zaten kayıtlı.")
    kullanici = Kullanici(
        eposta=normal,
        ad_soyad=(ad_soyad or "").strip(),
        sifre_hash=guvenlik.sifre_hashle(parola),
        rol=rol,
        durum=KullaniciDurumu.aktif,
        eposta_dogrulandi=True,
    )
    oturum.add(kullanici)
    await oturum.flush()
    return kullanici


async def kullanici_guncelle(
    oturum: AsyncSession,
    kullanici: Kullanici,
    *,
    rol: Rol | None = None,
    durum: KullaniciDurumu | None = None,
    ad_soyad: str | None = None,
) -> Kullanici:
    """Verilen alanlari gunceller; pasiflestirilen kullanicinin oturumlari iptal edilir."""
    if rol is not None:
        kullanici.rol = rol
    if durum is not None:
        kullanici.durum = durum
        if durum == KullaniciDurumu.pasif:
            await tum_oturumlari_iptal_et(oturum, kullanici.id)
    if ad_soyad is not None:
        kullanici.ad_soyad = ad_soyad.strip()
    await oturum.flush()
    return kullanici


async def kullanici_pasiflestir(oturum: AsyncSession, kullanici: Kullanici) -> None:
    """Kullaniciyi silmez, pasiflestirir ve acik oturumlarini iptal eder."""
    kullanici.durum = KullaniciDurumu.pasif
    await tum_oturumlari_iptal_et(oturum, kullanici.id)
    await oturum.flush()


# --------------------------------------------------------------------------
# Oturumlar (erisim + yenileme jetonu)
# --------------------------------------------------------------------------


async def oturum_ac(
    oturum: AsyncSession,
    kullanici: Kullanici,
    *,
    ip: str = "",
    user_agent: str = "",
) -> tuple[str, str]:
    """(erisim_jetonu, yenileme_jetonu) uretir ve oturum kaydini yazar."""
    yenileme = guvenlik.rastgele_jeton(48)
    oturum.add(
        Oturum(
            kullanici_id=kullanici.id,
            jeton_hash=guvenlik.ozet(yenileme),
            son_kullanma=datetime.now(timezone.utc)
            + timedelta(days=ayarlar.yenileme_omru_gun),
            ip=ip[:64],
            user_agent=user_agent[:400],
        )
    )
    await oturum.flush()
    erisim, _ = guvenlik.erisim_jetonu_uret(kullanici.id, kullanici.rol.value)
    return erisim, yenileme


async def oturum_bul(oturum: AsyncSession, yenileme_jetonu: str) -> Oturum | None:
    return (
        await oturum.execute(
            sa.select(Oturum).where(Oturum.jeton_hash == guvenlik.ozet(yenileme_jetonu))
        )
    ).scalar_one_or_none()


async def oturumu_yenile(
    oturum: AsyncSession,
    yenileme_jetonu: str,
    *,
    ip: str = "",
    user_agent: str = "",
) -> tuple[Kullanici, str, str]:
    """Refresh rotasyonu: eski kayit iptal edilir, yeni jeton cifti uretilir."""
    kayit = await oturum_bul(oturum, yenileme_jetonu)
    if kayit is None or kayit.iptal:
        raise JetonGecersiz("Oturum bilgisi geçersiz. Lütfen tekrar giriş yapın.")
    if _utc(kayit.son_kullanma) <= datetime.now(timezone.utc):
        raise JetonSuresiDoldu()
    kullanici = await oturum.get(Kullanici, kayit.kullanici_id)
    if kullanici is None:
        raise JetonGecersiz("Oturum bilgisi geçersiz. Lütfen tekrar giriş yapın.")
    if kullanici.durum == KullaniciDurumu.pasif:
        raise YetkiYok("Hesabınız devre dışı bırakılmış.")
    kayit.iptal = True
    erisim, yeni_yenileme = await oturum_ac(
        oturum, kullanici, ip=ip, user_agent=user_agent
    )
    return kullanici, erisim, yeni_yenileme


async def oturumu_iptal_et(
    oturum: AsyncSession, yenileme_jetonu: str, *, kullanici_id: int | None = None
) -> bool:
    """Yenileme jetonunun oturumunu iptal eder. Sahibi uyusmuyorsa dokunmaz."""
    kayit = await oturum_bul(oturum, yenileme_jetonu)
    if kayit is None:
        return False
    if kullanici_id is not None and kayit.kullanici_id != kullanici_id:
        return False
    kayit.iptal = True
    await oturum.flush()
    return True


async def tum_oturumlari_iptal_et(oturum: AsyncSession, kullanici_id: int) -> int:
    """Kullanicinin acik oturumlarini iptal eder; iptal edilen sayisini doner."""
    sonuc = await oturum.execute(
        sa.update(Oturum)
        .where(Oturum.kullanici_id == kullanici_id, Oturum.iptal.is_(False))
        .values(iptal=True)
    )
    return int(sonuc.rowcount or 0)


# --------------------------------------------------------------------------
# Dogrulama / sifirlama jetonlari
# --------------------------------------------------------------------------


async def dogrulama_jetonu_uret(
    oturum: AsyncSession,
    kullanici: Kullanici,
    tur: JetonTuru,
    saat: int,
) -> str:
    """Ayni turdeki eski jetonlari gecersiz kilar ve yeni tek kullanimlik jeton uretir."""
    await oturum.execute(
        sa.update(DogrulamaJetonu)
        .where(
            DogrulamaJetonu.kullanici_id == kullanici.id,
            DogrulamaJetonu.tur == tur,
            DogrulamaJetonu.kullanildi.is_(False),
        )
        .values(kullanildi=True)
    )
    jeton = guvenlik.rastgele_jeton(32)
    oturum.add(
        DogrulamaJetonu(
            kullanici_id=kullanici.id,
            tur=tur,
            jeton_hash=guvenlik.ozet(jeton),
            son_kullanma=datetime.now(timezone.utc) + timedelta(hours=saat),
        )
    )
    await oturum.flush()
    return jeton


async def dogrulama_jetonu_tuket(
    oturum: AsyncSession, jeton: str, tur: JetonTuru
) -> DogrulamaJetonu:
    """Jetonu hash'i ile bulur ve tek kullanimlik/sureli kurallarini denetler."""
    kayit = (
        await oturum.execute(
            sa.select(DogrulamaJetonu).where(
                DogrulamaJetonu.jeton_hash == guvenlik.ozet(jeton),
                DogrulamaJetonu.tur == tur,
            )
        )
    ).scalar_one_or_none()
    if kayit is None:
        raise GecersizIstek("Bağlantı geçersiz. Lütfen yeni bir bağlantı isteyin.")
    if kayit.kullanildi:
        raise GecersizIstek("Bu bağlantı daha önce kullanılmış.")
    if _utc(kayit.son_kullanma) <= datetime.now(timezone.utc):
        raise GecersizIstek("Bağlantının süresi doldu. Lütfen yeni bir bağlantı isteyin.")
    return kayit
