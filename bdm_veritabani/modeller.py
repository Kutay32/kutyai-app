"""KutyAI veri modeli — spec §4'teki 12 tablonun tamami.

Kolon ve tablo adlari Turkcedir. Tum zaman damgalari UTC'dir.
Enum'lar `native_enum=False` ile VARCHAR olarak saklanir; boylece ayni sema
hem SQLite hem PostgreSQL uzerinde degismeden calisir.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def simdi() -> datetime:
    """UTC simdiki zaman (Python tarafi varsayilan)."""
    return datetime.now(timezone.utc)


class Taban(DeclarativeBase):
    pass


# --------------------------------------------------------------------------
# Numaralandirmalar
# --------------------------------------------------------------------------


class Rol(str, enum.Enum):
    yonetici = "yonetici"
    operator = "operator"
    izleyici = "izleyici"
    son_kullanici = "son_kullanici"


PERSONEL_ROLLERI: tuple[Rol, ...] = (Rol.yonetici, Rol.operator, Rol.izleyici)


class KullaniciDurumu(str, enum.Enum):
    aktif = "aktif"
    beklemede = "beklemede"
    pasif = "pasif"


class JetonTuru(str, enum.Enum):
    eposta_dogrulama = "eposta_dogrulama"
    sifre_sifirlama = "sifre_sifirlama"


class AnahtarDurumu(str, enum.Enum):
    aktif = "aktif"
    iptal = "iptal"


class Saglayici(str, enum.Enum):
    openai = "openai"
    azure = "azure"
    openrouter = "openrouter"
    ollama = "ollama"
    vllm = "vllm"
    tgi = "tgi"
    ozel = "ozel"


class BdmDurumu(str, enum.Enum):
    taslak = "taslak"
    hazir = "hazir"
    calisiyor = "calisiyor"
    durdu = "durdu"
    hata = "hata"


class MesajRolu(str, enum.Enum):
    kullanici = "kullanici"
    asistan = "asistan"
    sistem = "sistem"
    arac = "arac"


class KullanimDurumu(str, enum.Enum):
    basarili = "basarili"
    hata = "hata"
    kota_asildi = "kota_asildi"


class KotaKapsami(str, enum.Enum):
    kullanici = "kullanici"
    api_anahtari = "api_anahtari"


def _sayisal_enum(sinif: type[enum.Enum], ad: str) -> sa.Enum:
    """Enum'i tasinabilir VARCHAR olarak saklar (degerleri kullanir)."""
    return sa.Enum(
        sinif,
        name=ad,
        native_enum=False,
        length=32,
        values_callable=lambda s: [uye.value for uye in s],
        validate_strings=True,
    )


# --------------------------------------------------------------------------
# 4.1 kullanici
# --------------------------------------------------------------------------


class Kullanici(Taban):
    __tablename__ = "kullanici"

    id: Mapped[int] = mapped_column(primary_key=True)
    eposta: Mapped[str] = mapped_column(sa.String(320), unique=True, index=True)
    ad_soyad: Mapped[str] = mapped_column(sa.String(160), default="")
    sifre_hash: Mapped[str] = mapped_column(sa.String(256))
    rol: Mapped[Rol] = mapped_column(_sayisal_enum(Rol, "rol"), default=Rol.son_kullanici, index=True)
    durum: Mapped[KullaniciDurumu] = mapped_column(
        _sayisal_enum(KullaniciDurumu, "kullanici_durumu"),
        default=KullaniciDurumu.beklemede,
        index=True,
    )
    eposta_dogrulandi: Mapped[bool] = mapped_column(default=False)
    olusturulma: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=simdi)
    guncellenme: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=simdi, onupdate=simdi
    )
    son_giris: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - hata ayiklama kolayligi
        return f"<Kullanici {self.id} {self.eposta} {self.rol.value}>"


# --------------------------------------------------------------------------
# 4.2 oturum
# --------------------------------------------------------------------------


class Oturum(Taban):
    __tablename__ = "oturum"

    id: Mapped[int] = mapped_column(primary_key=True)
    kullanici_id: Mapped[int] = mapped_column(
        sa.ForeignKey("kullanici.id", ondelete="CASCADE"), index=True
    )
    jeton_hash: Mapped[str] = mapped_column(sa.String(128), unique=True, index=True)
    son_kullanma: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    iptal: Mapped[bool] = mapped_column(default=False)
    olusturulma: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=simdi)
    user_agent: Mapped[str] = mapped_column(sa.String(400), default="")
    ip: Mapped[str] = mapped_column(sa.String(64), default="")


# --------------------------------------------------------------------------
# 4.3 dogrulama_jetonu
# --------------------------------------------------------------------------


class DogrulamaJetonu(Taban):
    __tablename__ = "dogrulama_jetonu"

    id: Mapped[int] = mapped_column(primary_key=True)
    kullanici_id: Mapped[int] = mapped_column(
        sa.ForeignKey("kullanici.id", ondelete="CASCADE"), index=True
    )
    tur: Mapped[JetonTuru] = mapped_column(_sayisal_enum(JetonTuru, "jeton_turu"))
    jeton_hash: Mapped[str] = mapped_column(sa.String(128), unique=True, index=True)
    son_kullanma: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    kullanildi: Mapped[bool] = mapped_column(default=False)
    olusturulma: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=simdi)


# --------------------------------------------------------------------------
# 4.4 api_anahtari
# --------------------------------------------------------------------------


class ApiAnahtari(Taban):
    __tablename__ = "api_anahtari"

    id: Mapped[int] = mapped_column(primary_key=True)
    ad: Mapped[str] = mapped_column(sa.String(160))
    onek: Mapped[str] = mapped_column(sa.String(24), index=True)
    anahtar_hash: Mapped[str] = mapped_column(sa.String(128), unique=True, index=True)
    son_dort: Mapped[str] = mapped_column(sa.String(8))
    kullanici_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("kullanici.id", ondelete="SET NULL"), nullable=True, index=True
    )
    durum: Mapped[AnahtarDurumu] = mapped_column(
        _sayisal_enum(AnahtarDurumu, "anahtar_durumu"), default=AnahtarDurumu.aktif
    )
    izinli_modeller: Mapped[list[str]] = mapped_column(sa.JSON, default=list)
    gunluk_istek_siniri: Mapped[int | None] = mapped_column(nullable=True)
    olusturulma: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=simdi)
    son_kullanim: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)


# --------------------------------------------------------------------------
# 4.5 bdm
# --------------------------------------------------------------------------


class Bdm(Taban):
    __tablename__ = "bdm"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(sa.String(80), unique=True, index=True)
    gorunen_ad: Mapped[str] = mapped_column(sa.String(160))
    aciklama: Mapped[str] = mapped_column(sa.Text, default="")
    saglayici: Mapped[Saglayici] = mapped_column(_sayisal_enum(Saglayici, "saglayici"), index=True)
    temel_url: Mapped[str] = mapped_column(sa.String(400), default="")
    upstream_model: Mapped[str] = mapped_column(sa.String(200), default="")
    api_anahtari_sifreli: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    baglam_penceresi: Mapped[int] = mapped_column(default=8192)
    maks_cikti: Mapped[int] = mapped_column(default=2048)
    sicaklik_varsayilan: Mapped[float] = mapped_column(default=0.7)
    sistem_istemi: Mapped[str] = mapped_column(sa.Text, default="")
    yetenekler: Mapped[dict[str, Any]] = mapped_column(
        sa.JSON, default=lambda: {"akis": True, "gorsel": False, "arac": False}
    )
    durum: Mapped[BdmDurumu] = mapped_column(
        _sayisal_enum(BdmDurumu, "bdm_durumu"), default=BdmDurumu.taslak, index=True
    )
    yerel_mi: Mapped[bool] = mapped_column(default=False)
    konteyner: Mapped[dict[str, Any] | None] = mapped_column(sa.JSON, nullable=True)
    olusturulma: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=simdi)
    guncellenme: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=simdi, onupdate=simdi
    )


# --------------------------------------------------------------------------
# 4.6 konusma  /  4.7 mesaj
# --------------------------------------------------------------------------


class Konusma(Taban):
    __tablename__ = "konusma"

    id: Mapped[int] = mapped_column(primary_key=True)
    kullanici_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("kullanici.id", ondelete="SET NULL"), nullable=True, index=True
    )
    api_anahtari_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("api_anahtari.id", ondelete="SET NULL"), nullable=True, index=True
    )
    bdm_id: Mapped[int] = mapped_column(sa.ForeignKey("bdm.id", ondelete="RESTRICT"), index=True)
    baslik: Mapped[str] = mapped_column(sa.String(200), default="Yeni sohbet")
    sistem_istemi: Mapped[str] = mapped_column(sa.Text, default="")
    token_girdi: Mapped[int] = mapped_column(default=0)
    token_cikti: Mapped[int] = mapped_column(default=0)
    arsivlendi: Mapped[bool] = mapped_column(default=False)
    olusturulma: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=simdi)
    guncellenme: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=simdi, onupdate=simdi
    )

    mesajlar: Mapped[list["Mesaj"]] = relationship(
        back_populates="konusma",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Mesaj.id",
    )


class Mesaj(Taban):
    __tablename__ = "mesaj"

    id: Mapped[int] = mapped_column(primary_key=True)
    konusma_id: Mapped[int] = mapped_column(
        sa.ForeignKey("konusma.id", ondelete="CASCADE"), index=True
    )
    rol: Mapped[MesajRolu] = mapped_column(_sayisal_enum(MesajRolu, "mesaj_rolu"))
    icerik: Mapped[str] = mapped_column(sa.Text, default="")
    token_sayisi: Mapped[int] = mapped_column(default=0)
    gecikme_ms: Mapped[int] = mapped_column(default=0)
    model: Mapped[str] = mapped_column(sa.String(200), default="")
    hata: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    olusturulma: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=simdi)

    konusma: Mapped[Konusma] = relationship(back_populates="mesajlar")


# --------------------------------------------------------------------------
# 4.8 kullanim_kaydi
# --------------------------------------------------------------------------


class KullanimKaydi(Taban):
    __tablename__ = "kullanim_kaydi"

    id: Mapped[int] = mapped_column(primary_key=True)
    kullanici_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("kullanici.id", ondelete="SET NULL"), nullable=True, index=True
    )
    api_anahtari_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("api_anahtari.id", ondelete="SET NULL"), nullable=True, index=True
    )
    bdm_id: Mapped[int] = mapped_column(sa.ForeignKey("bdm.id", ondelete="RESTRICT"), index=True)
    konusma_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("konusma.id", ondelete="SET NULL"), nullable=True, index=True
    )
    girdi_token: Mapped[int] = mapped_column(default=0)
    cikti_token: Mapped[int] = mapped_column(default=0)
    gecikme_ms: Mapped[int] = mapped_column(default=0)
    durum: Mapped[KullanimDurumu] = mapped_column(
        _sayisal_enum(KullanimDurumu, "kullanim_durumu"), default=KullanimDurumu.basarili
    )
    olusturulma: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=simdi, index=True
    )


# --------------------------------------------------------------------------
# 4.9 kota
# --------------------------------------------------------------------------


class Kota(Taban):
    __tablename__ = "kota"
    __table_args__ = (sa.UniqueConstraint("kapsam", "kapsam_id", name="uq_kota_kapsam"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    kapsam: Mapped[KotaKapsami] = mapped_column(_sayisal_enum(KotaKapsami, "kota_kapsami"))
    kapsam_id: Mapped[int] = mapped_column(index=True)
    gunluk_istek: Mapped[int | None] = mapped_column(nullable=True)
    aylik_token: Mapped[int | None] = mapped_column(nullable=True)
    kullanilan_gunluk: Mapped[int] = mapped_column(default=0)
    kullanilan_aylik: Mapped[int] = mapped_column(default=0)
    gun_sifirlanma: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=simdi)
    ay_sifirlanma: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=simdi)


# --------------------------------------------------------------------------
# 4.10 islem_kaydi
# --------------------------------------------------------------------------


class IslemKaydi(Taban):
    __tablename__ = "islem_kaydi"

    id: Mapped[int] = mapped_column(primary_key=True)
    kullanici_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("kullanici.id", ondelete="SET NULL"), nullable=True, index=True
    )
    eylem: Mapped[str] = mapped_column(sa.String(120), index=True)
    hedef_tur: Mapped[str] = mapped_column(sa.String(80), default="")
    hedef_id: Mapped[str] = mapped_column(sa.String(80), default="")
    ayrinti: Mapped[dict[str, Any]] = mapped_column(sa.JSON, default=dict)
    ip: Mapped[str] = mapped_column(sa.String(64), default="")
    olusturulma: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=simdi, index=True
    )


# --------------------------------------------------------------------------
# 4.11 ayar
# --------------------------------------------------------------------------


class Ayar(Taban):
    __tablename__ = "ayar"

    anahtar: Mapped[str] = mapped_column(sa.String(80), primary_key=True)
    deger: Mapped[Any] = mapped_column(sa.JSON, nullable=True)
    guncellenme: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=simdi, onupdate=simdi
    )


# --------------------------------------------------------------------------
# 4.12 maskeleme_kurali
# --------------------------------------------------------------------------


class MaskelemeKurali(Taban):
    __tablename__ = "maskeleme_kurali"

    id: Mapped[int] = mapped_column(primary_key=True)
    ad: Mapped[str] = mapped_column(sa.String(80), unique=True)
    desen: Mapped[str] = mapped_column(sa.String(400))
    etkin: Mapped[bool] = mapped_column(default=True)
    sira: Mapped[int] = mapped_column(default=0)
