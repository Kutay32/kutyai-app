"""BDM katalog semalari (girdi modelleri) — spec §4.5, §8."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from bdm_veritabani.modeller import Saglayici


class BdmOlustur(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    gorunen_ad: str = Field(min_length=2, max_length=160)
    slug: str | None = Field(default=None, max_length=80)
    aciklama: str = Field(default="", max_length=2000)
    saglayici: Saglayici
    temel_url: str = Field(default="", max_length=400)
    upstream_model: str = Field(default="", max_length=200)
    api_anahtari: str = Field(default="", max_length=400)
    baglam_penceresi: int = Field(default=8192, ge=128, le=2_000_000)
    maks_cikti: int = Field(default=2048, ge=16, le=200_000)
    sicaklik_varsayilan: float = Field(default=0.7, ge=0.0, le=2.0)
    sistem_istemi: str = Field(default="", max_length=8000)
    yerel_mi: bool | None = None
    yetenekler: dict[str, bool] | None = None

    @field_validator("temel_url")
    @classmethod
    def _url_temizle(cls, deger: str) -> str:
        return deger.rstrip("/")


class BdmGuncelle(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    gorunen_ad: str | None = Field(default=None, min_length=2, max_length=160)
    aciklama: str | None = Field(default=None, max_length=2000)
    saglayici: Saglayici | None = None
    temel_url: str | None = Field(default=None, max_length=400)
    upstream_model: str | None = Field(default=None, max_length=200)
    api_anahtari: str | None = Field(default=None, max_length=400)
    baglam_penceresi: int | None = Field(default=None, ge=128, le=2_000_000)
    maks_cikti: int | None = Field(default=None, ge=16, le=200_000)
    sicaklik_varsayilan: float | None = Field(default=None, ge=0.0, le=2.0)
    sistem_istemi: str | None = Field(default=None, max_length=8000)
    yerel_mi: bool | None = None
    yetenekler: dict[str, bool] | None = None

    @field_validator("temel_url")
    @classmethod
    def _url_temizle(cls, deger: str | None) -> str | None:
        return deger.rstrip("/") if deger is not None else None


class BdmKopyala(BaseModel):
    yeni_ad: str = Field(min_length=2, max_length=160)
    yeni_slug: str | None = Field(default=None, max_length=80)
