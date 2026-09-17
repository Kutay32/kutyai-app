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


class UtcZaman(sa.TypeDecorator[datetime]):
    """UTC zaman damgasi: yazarken UTC'ye cevirip naive saklar, okurken UTC'yi geri takar.

    SQLite zaman dilimi bilgisini saklamaz; ham `DateTime(timezone=True)` ile
    okunan deger naive kalir ve API `isoformat()` ciktisi `+00:00` tasimaz —
    istemciler bunu yerel saat sanip kaydirir. Bu tip, damgayi her iki yonde
    de UTC olarak isaretler; kayit bicimi (DDL) degismez.
    """

    impl = sa.DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, deger: datetime | None, lehce: Any) -> datetime | None:
        if deger is None:
            return None
        if deger.tzinfo is None:
            deger = deger.replace(tzinfo=timezone.utc)
        # Aware deger birakilir: SQLite baglayicisi yalnizca alanlari bicimlendirir
        # (damga ayni kalir), Postgres ise ani dogru yorumlar.
        return deger.astimezone(timezone.utc)

    def process_result_value(self, deger: datetime | None, lehce: Any) -> datetime | None:
        if deger is None:
            return None
        if deger.tzinfo is None:
            return deger.replace(tzinfo=timezone.utc)
        return deger.astimezone(timezone.utc)


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
    organizasyon = "organizasyon"


class OrganizasyonDurumu(str, enum.Enum):
    aktif = "aktif"
    askida = "askida"


class UyelikRolu(str, enum.Enum):
    sahip = "sahip"
    yonetici = "yonetici"
    operator = "operator"
    izleyici = "izleyici"
    son_kullanici = "son_kullanici"


class UyelikDurumu(str, enum.Enum):
    aktif = "aktif"
    beklemede = "beklemede"
    pasif = "pasif"


class AracTuru(str, enum.Enum):
    webhook = "webhook"
    yerlesik = "yerlesik"


class AbonelikDurumu(str, enum.Enum):
    deneme = "deneme"
    aktif = "aktif"
    gecikmis = "gecikmis"
    iptal = "iptal"


class FaturaDurumu(str, enum.Enum):
    taslak = "taslak"
    odendi = "odendi"
    basarisiz = "basarisiz"
    iade = "iade"


class SsoTuru(str, enum.Enum):
    oidc = "oidc"
    saml = "saml"


class BelgeKaynagi(str, enum.Enum):
    metin = "metin"
    dosya = "dosya"
    url = "url"


class AracCagrisiDurumu(str, enum.Enum):
    basarili = "basarili"
    hata = "hata"


#: Aktif organizasyon cozulemediginde kullanilan yonlendirme metni.
ORGANIZASYON_GEREKLI_MESAJ = (
    "Aktif bir organizasyon bulunamadı. Bir organizasyona üye olun veya yeni bir tane oluşturun."
)

#: `org_id` zorunlu tablolar. ORM dogrudan ekleme yaptiginda (testler, tohum,
#: yardimci betikler) `oturum.py` icindeki before_flush kancasi bu kolonu
#: varsayilan organizasyonla doldurur.
ORG_ZORUNLU_TABLOLAR: tuple[str, ...] = (
    "bdm",
    "konusma",
    "api_anahtari",
    "dosya",
    "vektor_belgesi",
    "vektor_parcasi",
    "arac",
    "abonelik",
    "fatura",
    "posta_sablonu",
    "sso_saglayici",
)


#: Organizasyon yonetiminde yetkili roller.
ORG_YONETIM_ROLLERI: tuple["UyelikRolu", ...] = (UyelikRolu.sahip, UyelikRolu.yonetici)
#: Personel (panel) sayilan uyelik rolleri.
PERSONEL_UYELIK_ROLLERI: tuple["UyelikRolu", ...] = (
    UyelikRolu.sahip,
    UyelikRolu.yonetici,
    UyelikRolu.operator,
    UyelikRolu.izleyici,
)

#: Kullanici varsayilan rolu -> organizasyon uyelik rolu.
#: (`sahip` yalnizca organizasyonu olusturan ya da devredilen kisiye verilir.)
ROL_ESLEME: dict["Rol", "UyelikRolu"] = {
    Rol.yonetici: UyelikRolu.yonetici,
    Rol.operator: UyelikRolu.operator,
    Rol.izleyici: UyelikRolu.izleyici,
    Rol.son_kullanici: UyelikRolu.son_kullanici,
}


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
    olusturulma: Mapped[datetime] = mapped_column(UtcZaman, default=simdi)
    guncellenme: Mapped[datetime] = mapped_column(
        UtcZaman, default=simdi, onupdate=simdi
    )
    son_giris: Mapped[datetime | None] = mapped_column(UtcZaman, nullable=True)

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
    son_kullanma: Mapped[datetime] = mapped_column(UtcZaman)
    iptal: Mapped[bool] = mapped_column(default=False)
    olusturulma: Mapped[datetime] = mapped_column(UtcZaman, default=simdi)
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
    son_kullanma: Mapped[datetime] = mapped_column(UtcZaman)
    kullanildi: Mapped[bool] = mapped_column(default=False)
    olusturulma: Mapped[datetime] = mapped_column(UtcZaman, default=simdi)


# --------------------------------------------------------------------------
# 4.4 api_anahtari
# --------------------------------------------------------------------------


class ApiAnahtari(Taban):
    __tablename__ = "api_anahtari"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        sa.ForeignKey("organizasyon.id", ondelete="RESTRICT"), index=True
    )
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
    olusturulma: Mapped[datetime] = mapped_column(UtcZaman, default=simdi)
    son_kullanim: Mapped[datetime | None] = mapped_column(UtcZaman, nullable=True)


# --------------------------------------------------------------------------
# 4.5 bdm
# --------------------------------------------------------------------------


class Bdm(Taban):
    __tablename__ = "bdm"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        sa.ForeignKey("organizasyon.id", ondelete="RESTRICT"), index=True
    )
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
    gomme_modeli: Mapped[str] = mapped_column(
        sa.String(200), default="text-embedding-3-small"
    )
    yetenekler: Mapped[dict[str, Any]] = mapped_column(
        sa.JSON, default=lambda: {"akis": True, "gorsel": False, "arac": False, "ses": False}
    )
    durum: Mapped[BdmDurumu] = mapped_column(
        _sayisal_enum(BdmDurumu, "bdm_durumu"), default=BdmDurumu.taslak, index=True
    )
    yerel_mi: Mapped[bool] = mapped_column(default=False)
    konteyner: Mapped[dict[str, Any] | None] = mapped_column(sa.JSON, nullable=True)
    olusturulma: Mapped[datetime] = mapped_column(UtcZaman, default=simdi)
    guncellenme: Mapped[datetime] = mapped_column(
        UtcZaman, default=simdi, onupdate=simdi
    )


# --------------------------------------------------------------------------
# 4.6 konusma  /  4.7 mesaj
# --------------------------------------------------------------------------


class Konusma(Taban):
    __tablename__ = "konusma"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        sa.ForeignKey("organizasyon.id", ondelete="RESTRICT"), index=True
    )
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
    olusturulma: Mapped[datetime] = mapped_column(UtcZaman, default=simdi)
    guncellenme: Mapped[datetime] = mapped_column(
        UtcZaman, default=simdi, onupdate=simdi
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
    olusturulma: Mapped[datetime] = mapped_column(UtcZaman, default=simdi)

    konusma: Mapped[Konusma] = relationship(back_populates="mesajlar")


# --------------------------------------------------------------------------
# 4.8 kullanim_kaydi
# --------------------------------------------------------------------------


class KullanimKaydi(Taban):
    __tablename__ = "kullanim_kaydi"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("organizasyon.id", ondelete="SET NULL"), nullable=True, index=True
    )
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
        UtcZaman, default=simdi, index=True
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
    gun_sifirlanma: Mapped[datetime] = mapped_column(UtcZaman, default=simdi)
    ay_sifirlanma: Mapped[datetime] = mapped_column(UtcZaman, default=simdi)


# --------------------------------------------------------------------------
# 4.10 islem_kaydi
# --------------------------------------------------------------------------


class IslemKaydi(Taban):
    __tablename__ = "islem_kaydi"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("organizasyon.id", ondelete="SET NULL"), nullable=True, index=True
    )
    kullanici_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("kullanici.id", ondelete="SET NULL"), nullable=True, index=True
    )
    eylem: Mapped[str] = mapped_column(sa.String(120), index=True)
    hedef_tur: Mapped[str] = mapped_column(sa.String(80), default="")
    hedef_id: Mapped[str] = mapped_column(sa.String(80), default="")
    ayrinti: Mapped[dict[str, Any]] = mapped_column(sa.JSON, default=dict)
    ip: Mapped[str] = mapped_column(sa.String(64), default="")
    olusturulma: Mapped[datetime] = mapped_column(
        UtcZaman, default=simdi, index=True
    )


# --------------------------------------------------------------------------
# 4.11 ayar
# --------------------------------------------------------------------------


class Ayar(Taban):
    __tablename__ = "ayar"

    anahtar: Mapped[str] = mapped_column(sa.String(80), primary_key=True)
    deger: Mapped[Any] = mapped_column(sa.JSON, nullable=True)
    guncellenme: Mapped[datetime] = mapped_column(
        UtcZaman, default=simdi, onupdate=simdi
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


# ==========================================================================
# v2 — Cok kiracili yapi
# ==========================================================================


class Organizasyon(Taban):
    __tablename__ = "organizasyon"

    id: Mapped[int] = mapped_column(primary_key=True)
    ad: Mapped[str] = mapped_column(sa.String(160))
    slug: Mapped[str] = mapped_column(sa.String(80), unique=True, index=True)
    durum: Mapped[OrganizasyonDurumu] = mapped_column(
        _sayisal_enum(OrganizasyonDurumu, "organizasyon_durumu"),
        default=OrganizasyonDurumu.aktif,
    )
    olusturulma: Mapped[datetime] = mapped_column(UtcZaman, default=simdi)
    guncellenme: Mapped[datetime] = mapped_column(
        UtcZaman, default=simdi, onupdate=simdi
    )


class Uyelik(Taban):
    __tablename__ = "uyelik"
    __table_args__ = (
        sa.UniqueConstraint("organizasyon_id", "kullanici_id", name="uq_uyelik"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organizasyon_id: Mapped[int] = mapped_column(
        sa.ForeignKey("organizasyon.id", ondelete="CASCADE"), index=True
    )
    kullanici_id: Mapped[int] = mapped_column(
        sa.ForeignKey("kullanici.id", ondelete="CASCADE"), index=True
    )
    rol: Mapped[UyelikRolu] = mapped_column(_sayisal_enum(UyelikRolu, "uyelik_rolu"))
    durum: Mapped[UyelikDurumu] = mapped_column(
        _sayisal_enum(UyelikDurumu, "uyelik_durumu"), default=UyelikDurumu.aktif
    )
    olusturulma: Mapped[datetime] = mapped_column(UtcZaman, default=simdi)


class Plan(Taban):
    __tablename__ = "plan"

    id: Mapped[int] = mapped_column(primary_key=True)
    ad: Mapped[str] = mapped_column(sa.String(120))
    slug: Mapped[str] = mapped_column(sa.String(60), unique=True, index=True)
    aylik_fiyat_kurus: Mapped[int] = mapped_column(default=0)
    para: Mapped[str] = mapped_column(sa.String(3), default="TRY")
    dahil_istek: Mapped[int | None] = mapped_column(nullable=True)
    dahil_token: Mapped[int | None] = mapped_column(nullable=True)
    ozellikler: Mapped[dict[str, Any]] = mapped_column(sa.JSON, default=dict)
    etkin: Mapped[bool] = mapped_column(default=True)
    olusturulma: Mapped[datetime] = mapped_column(UtcZaman, default=simdi)


class Abonelik(Taban):
    __tablename__ = "abonelik"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        sa.ForeignKey("organizasyon.id", ondelete="CASCADE"), index=True
    )
    plan_id: Mapped[int] = mapped_column(
        sa.ForeignKey("plan.id", ondelete="RESTRICT"), index=True
    )
    durum: Mapped[AbonelikDurumu] = mapped_column(
        _sayisal_enum(AbonelikDurumu, "abonelik_durumu"), default=AbonelikDurumu.deneme
    )
    donem_basi: Mapped[datetime] = mapped_column(UtcZaman, default=simdi)
    donem_sonu: Mapped[datetime] = mapped_column(UtcZaman, default=simdi)
    saglayici: Mapped[str] = mapped_column(sa.String(40), default="yerel")
    dis_id: Mapped[str] = mapped_column(sa.String(200), default="")
    olusturulma: Mapped[datetime] = mapped_column(UtcZaman, default=simdi)
    guncellenme: Mapped[datetime] = mapped_column(
        UtcZaman, default=simdi, onupdate=simdi
    )


class Fatura(Taban):
    __tablename__ = "fatura"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        sa.ForeignKey("organizasyon.id", ondelete="CASCADE"), index=True
    )
    abonelik_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("abonelik.id", ondelete="SET NULL"), nullable=True, index=True
    )
    tutar_kurus: Mapped[int] = mapped_column(default=0)
    para: Mapped[str] = mapped_column(sa.String(3), default="TRY")
    durum: Mapped[FaturaDurumu] = mapped_column(
        _sayisal_enum(FaturaDurumu, "fatura_durumu"), default=FaturaDurumu.taslak
    )
    kalemler: Mapped[list[dict[str, Any]]] = mapped_column(sa.JSON, default=list)
    dis_id: Mapped[str] = mapped_column(sa.String(200), default="")
    olusturulma: Mapped[datetime] = mapped_column(UtcZaman, default=simdi)
    odeme_tarihi: Mapped[datetime | None] = mapped_column(
        UtcZaman, nullable=True
    )


class Dosya(Taban):
    __tablename__ = "dosya"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        sa.ForeignKey("organizasyon.id", ondelete="CASCADE"), index=True
    )
    kullanici_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("kullanici.id", ondelete="SET NULL"), nullable=True, index=True
    )
    ad: Mapped[str] = mapped_column(sa.String(300))
    mime: Mapped[str] = mapped_column(sa.String(160), default="application/octet-stream")
    boyut: Mapped[int] = mapped_column(default=0)
    sha256: Mapped[str] = mapped_column(sa.String(64), default="", index=True)
    yol: Mapped[str] = mapped_column(sa.Text, default="")
    metin: Mapped[str] = mapped_column(sa.Text, default="")
    olusturulma: Mapped[datetime] = mapped_column(UtcZaman, default=simdi)


class VektorBelgesi(Taban):
    __tablename__ = "vektor_belgesi"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        sa.ForeignKey("organizasyon.id", ondelete="CASCADE"), index=True
    )
    ad: Mapped[str] = mapped_column(sa.String(300))
    kaynak: Mapped[BelgeKaynagi] = mapped_column(
        _sayisal_enum(BelgeKaynagi, "belge_kaynagi"), default=BelgeKaynagi.metin
    )
    dosya_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("dosya.id", ondelete="SET NULL"), nullable=True
    )
    belge_meta: Mapped[dict[str, Any]] = mapped_column(sa.JSON, default=dict)
    parca_sayisi: Mapped[int] = mapped_column(default=0)
    olusturulma: Mapped[datetime] = mapped_column(UtcZaman, default=simdi)


class VektorParcasi(Taban):
    __tablename__ = "vektor_parcasi"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        sa.ForeignKey("organizasyon.id", ondelete="CASCADE"), index=True
    )
    belge_id: Mapped[int] = mapped_column(
        sa.ForeignKey("vektor_belgesi.id", ondelete="CASCADE"), index=True
    )
    sira: Mapped[int] = mapped_column(default=0)
    icerik: Mapped[str] = mapped_column(sa.Text, default="")
    vektor: Mapped[list[float]] = mapped_column(sa.JSON, default=list)
    token_sayisi: Mapped[int] = mapped_column(default=0)
    olusturulma: Mapped[datetime] = mapped_column(UtcZaman, default=simdi)


class Arac(Taban):
    __tablename__ = "arac"
    __table_args__ = (sa.UniqueConstraint("org_id", "slug", name="uq_arac_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        sa.ForeignKey("organizasyon.id", ondelete="CASCADE"), index=True
    )
    ad: Mapped[str] = mapped_column(sa.String(120))
    slug: Mapped[str] = mapped_column(sa.String(60), index=True)
    aciklama: Mapped[str] = mapped_column(sa.Text, default="")
    json_sema: Mapped[dict[str, Any]] = mapped_column(sa.JSON, default=dict)
    tur: Mapped[AracTuru] = mapped_column(
        _sayisal_enum(AracTuru, "arac_turu"), default=AracTuru.webhook
    )
    uc_noktasi: Mapped[str] = mapped_column(sa.String(400), default="")
    basliklar_sifreli: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    etkin: Mapped[bool] = mapped_column(default=True)
    olusturulma: Mapped[datetime] = mapped_column(UtcZaman, default=simdi)
    guncellenme: Mapped[datetime] = mapped_column(
        UtcZaman, default=simdi, onupdate=simdi
    )


class AracCagrisi(Taban):
    __tablename__ = "arac_cagrisi"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        sa.ForeignKey("organizasyon.id", ondelete="CASCADE"), index=True
    )
    konusma_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("konusma.id", ondelete="SET NULL"), nullable=True, index=True
    )
    mesaj_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("mesaj.id", ondelete="SET NULL"), nullable=True
    )
    arac_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("arac.id", ondelete="SET NULL"), nullable=True, index=True
    )
    ad: Mapped[str] = mapped_column(sa.String(120), default="")
    argumanlar: Mapped[dict[str, Any]] = mapped_column(sa.JSON, default=dict)
    sonuc: Mapped[dict[str, Any]] = mapped_column(sa.JSON, default=dict)
    durum: Mapped[AracCagrisiDurumu] = mapped_column(
        _sayisal_enum(AracCagrisiDurumu, "arac_cagrisi_durumu"),
        default=AracCagrisiDurumu.basarili,
    )
    gecikme_ms: Mapped[int] = mapped_column(default=0)
    hata: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    olusturulma: Mapped[datetime] = mapped_column(UtcZaman, default=simdi)


class SsoSaglayici(Taban):
    __tablename__ = "sso_saglayici"
    __table_args__ = (
        sa.UniqueConstraint("org_id", "slug", name="uq_sso_saglayici_slug"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        sa.ForeignKey("organizasyon.id", ondelete="CASCADE"), index=True
    )
    tur: Mapped[SsoTuru] = mapped_column(_sayisal_enum(SsoTuru, "sso_turu"))
    ad: Mapped[str] = mapped_column(sa.String(120))
    slug: Mapped[str] = mapped_column(sa.String(60), index=True)
    etkin: Mapped[bool] = mapped_column(default=True)
    ayarlar: Mapped[dict[str, Any]] = mapped_column(sa.JSON, default=dict)
    sir_sifreli: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    olusturulma: Mapped[datetime] = mapped_column(UtcZaman, default=simdi)
    guncellenme: Mapped[datetime] = mapped_column(
        UtcZaman, default=simdi, onupdate=simdi
    )


class SsoKimlik(Taban):
    __tablename__ = "sso_kimlik"
    __table_args__ = (
        sa.UniqueConstraint("saglayici_id", "dis_id", name="uq_sso_kimlik"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    kullanici_id: Mapped[int] = mapped_column(
        sa.ForeignKey("kullanici.id", ondelete="CASCADE"), index=True
    )
    saglayici_id: Mapped[int] = mapped_column(
        sa.ForeignKey("sso_saglayici.id", ondelete="CASCADE"), index=True
    )
    dis_id: Mapped[str] = mapped_column(sa.String(300), index=True)
    eposta: Mapped[str] = mapped_column(sa.String(320), default="")
    olusturulma: Mapped[datetime] = mapped_column(UtcZaman, default=simdi)


class PostaSablonu(Taban):
    __tablename__ = "posta_sablonu"
    __table_args__ = (
        sa.UniqueConstraint("org_id", "kod", "dil", name="uq_posta_sablonu"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        sa.ForeignKey("organizasyon.id", ondelete="CASCADE"), index=True
    )
    kod: Mapped[str] = mapped_column(sa.String(60), index=True)
    dil: Mapped[str] = mapped_column(sa.String(5), default="tr")
    konu: Mapped[str] = mapped_column(sa.String(300), default="")
    govde_metin: Mapped[str] = mapped_column(sa.Text, default="")
    govde_html: Mapped[str] = mapped_column(sa.Text, default="")
    guncellenme: Mapped[datetime] = mapped_column(
        UtcZaman, default=simdi, onupdate=simdi
    )
