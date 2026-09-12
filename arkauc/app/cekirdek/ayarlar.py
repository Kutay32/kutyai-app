"""Uygulama ayarlari (spec §5).

Tum ayarlar `KUTYAI_` oneki ile ortam degiskenlerinden ya da kok dizindeki
`.env` dosyasindan okunur. GELISTIRME ortaminda eksik sirlar gecici olarak
uretilir; URETIM ortaminda eksik sir ile uygulama baslamaz (`dogrula`).
"""

from __future__ import annotations

import logging
import secrets
from pathlib import Path

from pydantic import PrivateAttr
from pydantic_settings import BaseSettings, SettingsConfigDict

KOK = Path(__file__).resolve().parents[3]
logger = logging.getLogger("kutyai.ayarlar")

_URETIM_ADLARI = {"uretim", "production", "prod"}


class Ayarlar(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="KUTYAI_",
        env_file=str(KOK / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    ortam: str = "gelistirme"

    veritabani_url: str = ""

    gizli_anahtar: str = ""
    sifreleme_anahtari: str = ""
    erisim_omru_dk: int = 15
    yenileme_omru_gun: int = 30

    onuc_url: str = "http://localhost:3000"
    panel_url: str = "http://localhost:3001"
    cors_kaynaklar: str = "http://localhost:3000,http://localhost:3001"

    saklama_gun: int = 90
    maskeleme_aktif: bool = True
    oran_siniri_istek_dk: int = 60

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_kullanici: str = ""
    smtp_sifre: str = ""
    smtp_gonderen: str = "KutyAI <bildirim@kutyai.local>"
    smtp_tls: bool = True

    docker_soketi: str = ""
    image_onbellek: str = "vllm/vllm-openai:latest,ollama/ollama:latest"

    _uretilen: list[str] = PrivateAttr(default_factory=list)

    def model_post_init(self, __context: object) -> None:
        if not self.gizli_anahtar:
            self.gizli_anahtar = secrets.token_urlsafe(48)
            self._uretilen.append("KUTYAI_GIZLI_ANAHTAR")
        if not self.sifreleme_anahtari:
            from cryptography.fernet import Fernet

            self.sifreleme_anahtari = Fernet.generate_key().decode()
            self._uretilen.append("KUTYAI_SIFRELEME_ANAHTARI")
        if self._uretilen:
            logger.warning(
                "Gelistirme icin gecici sirlar uretildi: %s. Uretimde bunlari .env icinde tanimlayin.",
                ", ".join(self._uretilen),
            )

    # -- turetilmis degerler -------------------------------------------------

    @property
    def uretim_mi(self) -> bool:
        return self.ortam.strip().lower() in _URETIM_ADLARI

    def veritabani_url_cozum(self) -> str:
        """Etkin veritabani URL'i; bos ise kok dizinde SQLite kullanilir."""
        ham = (self.veritabani_url or "").strip()
        if not ham:
            yol = (KOK / "bdm_veritabani" / "kutyai.db").as_posix()
            return f"sqlite+aiosqlite:///{yol}"
        if ham.startswith("sqlite:///"):
            return ham.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
        if ham.startswith("postgresql://"):
            return ham.replace("postgresql://", "postgresql+asyncpg://", 1)
        return ham

    @property
    def sqlite_mi(self) -> bool:
        return self.veritabani_url_cozum().startswith("sqlite")

    @property
    def cors_listesi(self) -> list[str]:
        return [parca.strip() for parca in self.cors_kaynaklar.split(",") if parca.strip()]

    @property
    def image_listesi(self) -> list[str]:
        return [parca.strip() for parca in self.image_onbellek.split(",") if parca.strip()]

    @property
    def smtp_var_mi(self) -> bool:
        return bool(self.smtp_host.strip())

    def dogrula(self) -> None:
        """Uretim ortaminda zorunlu sirlari denetler."""
        if self.uretim_mi and self._uretilen:
            raise RuntimeError(
                "Uretim ortaminda su ortam degiskenleri zorunludur: "
                + ", ".join(self._uretilen)
            )


ayarlar = Ayarlar()
