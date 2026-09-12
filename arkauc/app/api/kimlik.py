"""Kimlik uclari: kayit, dogrulama, giris, yenileme, cikis, sifre (API.md §5)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek import guvenlik
from arkauc.app.cekirdek.ayarlar_db import ayar_oku, ayar_yaz
from arkauc.app.cekirdek.bagimliliklar import gecerli_kullanici, veritabani_oturumu
from arkauc.app.cekirdek.denetim import islem_kaydet
from arkauc.app.cekirdek.hatalar import (
    Cakisma,
    EpostaDogrulanmadi,
    GecersizIstek,
    YetkiYok,
)
from arkauc.app.servisler import kimlik as kimlik_servisi
from arkauc.app.servisler.posta import (
    dogrulama_baglantisi,
    dogrulama_postasi,
    posta_gonder,
    sifirlama_baglantisi,
    sifirlama_postasi,
    smtp_tanimli_mi,
)
from bdm_veritabani.modeller import (
    PERSONEL_ROLLERI,
    DogrulamaJetonu,
    JetonTuru,
    Kullanici,
    KullaniciDurumu,
    Rol,
)

router = APIRouter(prefix="/kimlik", tags=["kimlik"])

SIFIRLAMA_ISTEK_MESAJI = (
    "E-posta adresiniz kayıtlıysa parola sıfırlama bağlantısı gönderildi."
)


# --------------------------------------------------------------------------
# Istek govdeleri
# --------------------------------------------------------------------------


class KayitIstegi(BaseModel):
    eposta: str
    ad_soyad: str = ""
    parola: str


class DogrulamaIstegi(BaseModel):
    jeton: str


class GirisIstegi(BaseModel):
    eposta: str
    parola: str


class YenilemeIstegi(BaseModel):
    yenileme_jetonu: str


class CikisIstegi(BaseModel):
    yenileme_jetonu: str | None = None


class SifirlamaIstegi(BaseModel):
    eposta: str


class SifreSifirlaIstegi(BaseModel):
    jeton: str
    yeni_parola: str


# --------------------------------------------------------------------------
# Yardimcilar
# --------------------------------------------------------------------------


def _ip(istek: Request) -> str:
    return istek.client.host if istek.client else ""


def _tarayici(istek: Request) -> str:
    return istek.headers.get("user-agent", "")


async def _giris_yap(
    veri: GirisIstegi,
    istek: Request,
    oturum: AsyncSession,
    *,
    panel: bool,
) -> dict[str, object]:
    kullanici = await kimlik_servisi.kullanici_bul(oturum, veri.eposta)
    if kullanici is None or not kimlik_servisi.parola_gecerli_mi(kullanici, veri.parola):
        raise kimlik_servisi.GecersizKimlikBilgisi()
    if kullanici.durum == KullaniciDurumu.pasif:
        raise YetkiYok("Hesabınız devre dışı bırakılmış. Yöneticiye başvurun.")
    if panel:
        if kullanici.rol not in PERSONEL_ROLLERI:
            raise YetkiYok("Panele yalnızca personel hesapları giriş yapabilir.")
    elif kullanici.rol != Rol.son_kullanici:
        raise YetkiYok("Bu giriş kapısı yalnızca son kullanıcılar içindir.")
    if not panel and not kullanici.eposta_dogrulandi:
        raise EpostaDogrulanmadi(
            "Giriş yapmadan önce e-posta adresinizi doğrulamalısınız."
        )

    erisim, yenileme = await kimlik_servisi.oturum_ac(
        oturum, kullanici, ip=_ip(istek), user_agent=_tarayici(istek)
    )
    kullanici.son_giris = datetime.now(timezone.utc)
    await islem_kaydet(
        oturum,
        "kimlik.giris",
        kullanici_id=kullanici.id,
        hedef_tur="kullanici",
        hedef_id=kullanici.id,
        ayrinti={"panel": panel},
        ip=_ip(istek),
    )
    return {
        "erisim_jetonu": erisim,
        "yenileme_jetonu": yenileme,
        "kullanici": kimlik_servisi.kullanici_sozlugu(kullanici),
    }


# --------------------------------------------------------------------------
# Uclar
# --------------------------------------------------------------------------


@router.post("/kayit", status_code=status.HTTP_201_CREATED)
async def kayit(
    veri: KayitIstegi,
    istek: Request,
    oturum: AsyncSession = Depends(veritabani_oturumu),
) -> dict[str, object]:
    """Son kullanici kaydi; hesap `beklemede` acilir ve dogrulama baglantisi gonderilir."""
    if not await ayar_oku(oturum, "kayit_acik", True):
        raise YetkiYok("Kayıt şu anda kapalı. Yöneticiye başvurun.")
    eposta = kimlik_servisi.eposta_normalize(veri.eposta)
    if not eposta:
        raise GecersizIstek("E-posta adresi zorunludur.")
    kimlik_servisi.parola_denetle(veri.parola)
    if await kimlik_servisi.kullanici_bul(oturum, eposta) is not None:
        raise Cakisma("Bu e-posta adresi zaten kayıtlı.")

    kullanici = Kullanici(
        eposta=eposta,
        ad_soyad=(veri.ad_soyad or "").strip(),
        sifre_hash=guvenlik.sifre_hashle(veri.parola),
        rol=Rol.son_kullanici,
        durum=KullaniciDurumu.beklemede,
        eposta_dogrulandi=False,
    )
    oturum.add(kullanici)
    await kimlik_servisi.kaydi_yaz(oturum, eposta)

    jeton = await kimlik_servisi.dogrulama_jetonu_uret(
        oturum, kullanici, JetonTuru.eposta_dogrulama, kimlik_servisi.EPOSTA_DOGRULAMA_SAAT
    )
    baglanti = dogrulama_baglantisi(jeton)
    konu, govde = dogrulama_postasi(
        kullanici.ad_soyad or kullanici.eposta, baglanti, kimlik_servisi.EPOSTA_DOGRULAMA_SAAT
    )
    await posta_gonder(oturum, kullanici.eposta, konu, govde)

    yanit: dict[str, object] = {
        "kullanici": kimlik_servisi.kullanici_sozlugu(kullanici),
        "dogrulama_gerekli": True,
    }
    if not await smtp_tanimli_mi(oturum):
        yanit["gelistirme_baglantisi"] = baglanti
        await ayar_yaz(oturum, "son_dogrulama_baglantisi", baglanti)

    await islem_kaydet(
        oturum,
        "kimlik.kayit",
        kullanici_id=kullanici.id,
        hedef_tur="kullanici",
        hedef_id=kullanici.id,
        ip=_ip(istek),
    )
    return yanit


@router.post("/dogrula")
async def dogrula(
    veri: DogrulamaIstegi,
    oturum: AsyncSession = Depends(veritabani_oturumu),
) -> dict[str, object]:
    """E-posta dogrulama jetonunu tek kullanimlik olarak tuketir."""
    kayit: DogrulamaJetonu = await kimlik_servisi.dogrulama_jetonu_tuket(
        oturum, veri.jeton, JetonTuru.eposta_dogrulama
    )
    kullanici = await oturum.get(Kullanici, kayit.kullanici_id)
    if kullanici is None:
        raise GecersizIstek("Bağlantı geçersiz. Lütfen yeni bir bağlantı isteyin.")

    kullanici.eposta_dogrulandi = True
    # Pasiflestirilmis hesap dogrulama baglantisiyla geri acilmaz.
    if kullanici.durum != KullaniciDurumu.pasif:
        kullanici.durum = KullaniciDurumu.aktif
    await islem_kaydet(
        oturum,
        "kimlik.dogrula",
        kullanici_id=kullanici.id,
        hedef_tur="kullanici",
        hedef_id=kullanici.id,
    )
    return {"dogrulandi": True}


@router.post("/giris")
async def giris(
    veri: GirisIstegi,
    istek: Request,
    oturum: AsyncSession = Depends(veritabani_oturumu),
) -> dict[str, object]:
    """Son kullanici girisi."""
    return await _giris_yap(veri, istek, oturum, panel=False)


@router.post("/panel-giris")
async def panel_giris(
    veri: GirisIstegi,
    istek: Request,
    oturum: AsyncSession = Depends(veritabani_oturumu),
) -> dict[str, object]:
    """Personel girisi; `son_kullanici` rolü reddedilir."""
    return await _giris_yap(veri, istek, oturum, panel=True)


@router.post("/yenile")
async def yenile(
    veri: YenilemeIstegi,
    istek: Request,
    oturum: AsyncSession = Depends(veritabani_oturumu),
) -> dict[str, object]:
    """Yenileme jetonunu dondurur (eski jeton iptal edilir)."""
    kullanici, erisim, yenileme = await kimlik_servisi.oturumu_yenile(
        oturum, veri.yenileme_jetonu, ip=_ip(istek), user_agent=_tarayici(istek)
    )
    await islem_kaydet(
        oturum,
        "kimlik.yenile",
        kullanici_id=kullanici.id,
        hedef_tur="kullanici",
        hedef_id=kullanici.id,
        ip=_ip(istek),
    )
    return {"erisim_jetonu": erisim, "yenileme_jetonu": yenileme}


@router.post("/cikis")
async def cikis(
    istek: Request,
    veri: CikisIstegi | None = None,
    kullanici: Kullanici = Depends(gecerli_kullanici),
    oturum: AsyncSession = Depends(veritabani_oturumu),
) -> dict[str, object]:
    """Verilen yenileme jetonunu iptal eder."""
    if veri is not None and veri.yenileme_jetonu:
        await kimlik_servisi.oturumu_iptal_et(
            oturum, veri.yenileme_jetonu, kullanici_id=kullanici.id
        )
    await islem_kaydet(
        oturum,
        "kimlik.cikis",
        kullanici_id=kullanici.id,
        hedef_tur="kullanici",
        hedef_id=kullanici.id,
        ip=_ip(istek),
    )
    return {"mesaj": "Çıkış yapıldı."}


@router.post("/sifre-sifirlama-iste")
async def sifre_sifirlama_iste(
    veri: SifirlamaIstegi,
    istek: Request,
    oturum: AsyncSession = Depends(veritabani_oturumu),
) -> dict[str, object]:
    """Parola sifirlama baglantisi gonderir; e-posta yoksa da ayni mesaj doner."""
    kullanici = await kimlik_servisi.kullanici_bul(oturum, veri.eposta)
    # Hesap var/yok ayrimi yanit suresinden okunmasin: bulunamayan/pasif hesapta
    # da kayitli hesaptakiyle ayni sabit maliyetli argon2 dogrulamasi odenir.
    kimlik_servisi.zamanlama_dogrulamasi()
    yanit: dict[str, object] = {"mesaj": SIFIRLAMA_ISTEK_MESAJI}
    if kullanici is None or kullanici.durum == KullaniciDurumu.pasif:
        return yanit

    jeton = await kimlik_servisi.dogrulama_jetonu_uret(
        oturum, kullanici, JetonTuru.sifre_sifirlama, kimlik_servisi.SIFRE_SIFIRLAMA_SAAT
    )
    baglanti = sifirlama_baglantisi(jeton)
    konu, govde = sifirlama_postasi(
        kullanici.ad_soyad or kullanici.eposta,
        baglanti,
        kimlik_servisi.SIFRE_SIFIRLAMA_SAAT,
    )
    await posta_gonder(oturum, kullanici.eposta, konu, govde)
    if not await smtp_tanimli_mi(oturum):
        yanit["gelistirme_baglantisi"] = baglanti
        await ayar_yaz(oturum, "son_sifirlama_baglantisi", baglanti)
    await islem_kaydet(
        oturum,
        "kimlik.sifre_sifirlama_iste",
        kullanici_id=kullanici.id,
        hedef_tur="kullanici",
        hedef_id=kullanici.id,
        ip=_ip(istek),
    )
    return yanit


@router.post("/sifre-sifirla")
async def sifre_sifirla(
    veri: SifreSifirlaIstegi,
    oturum: AsyncSession = Depends(veritabani_oturumu),
) -> dict[str, object]:
    """Tek kullanimlik jetonla parolayi gunceller ve tum oturumlari iptal eder."""
    kimlik_servisi.parola_denetle(veri.yeni_parola)
    kayit: DogrulamaJetonu = await kimlik_servisi.dogrulama_jetonu_tuket(
        oturum, veri.jeton, JetonTuru.sifre_sifirlama
    )
    kullanici = await oturum.get(Kullanici, kayit.kullanici_id)
    if kullanici is None:
        raise GecersizIstek("Bağlantı geçersiz. Lütfen yeni bir bağlantı isteyin.")
    if kullanici.durum == KullaniciDurumu.pasif:
        raise YetkiYok("Hesabınız devre dışı bırakılmış. Yöneticiye başvurun.")

    kullanici.sifre_hash = guvenlik.sifre_hashle(veri.yeni_parola)
    iptal = await kimlik_servisi.tum_oturumlari_iptal_et(oturum, kullanici.id)
    await islem_kaydet(
        oturum,
        "kimlik.sifre_sifirla",
        kullanici_id=kullanici.id,
        hedef_tur="kullanici",
        hedef_id=kullanici.id,
        ayrinti={"iptal_edilen_oturum": iptal},
    )
    return {
        "mesaj": "Parolanız güncellendi. Yeni parolanızla giriş yapabilirsiniz."
    }


@router.get("/ben")
async def ben(kullanici: Kullanici = Depends(gecerli_kullanici)) -> dict[str, object]:
    """Oturum sahibinin profili."""
    return kimlik_servisi.kullanici_sozlugu(kullanici)
