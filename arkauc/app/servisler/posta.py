"""Posta gonderimi: konsol ve SMTP suruculeri (spec §11).

SMTP yapilandirmasi once `ayar` tablosundan okunur (panelden girilen degerler);
tablodaki deger bos ise `KUTYAI_SMTP_*` ortam degerine dusulur. `smtp_sifre`
tabloda Fernet ile sifreli saklanir; cozulemezse ham deger kullanilir (henuz
sifrelenmemis eski kayitlar icin).

Etkin host bos ise `konsol` surucusu kullanilir: iletiyi loglar, gonderimi
basarili sayar ve baglanti test/kurulum icin `gelistirme_baglantisi` alanina
yazilir (yalnizca uretim disi ortamda; bkz. GUVENLIK.md).
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Any, Protocol, runtime_checkable
from urllib.parse import quote

from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek import guvenlik
from arkauc.app.cekirdek.ayarlar import ayarlar
from arkauc.app.cekirdek.ayarlar_db import ayar_oku

logger = logging.getLogger("kutyai.posta")

SMTP_ZAMAN_ASIMI = 10


@dataclass(slots=True)
class PostaAyarlari:
    """Etkin SMTP yapilandirmasi (ayar tablosu + ortam birlestirilmis)."""

    host: str = ""
    port: int = 587
    kullanici: str = ""
    sifre: str = ""
    gonderen: str = ""
    tls: bool = True

    @property
    def tanimli_mi(self) -> bool:
        return bool(self.host.strip())


@runtime_checkable
class PostaSürücüsü(Protocol):
    """Tum posta suruculerinin uymasi gereken sozlesme."""

    ad: str

    def gonder(self, kime: str, konu: str, govde: str) -> bool:
        """Iletiyi gonderir; basariliysa True doner."""
        ...


class KonsolPosta:
    """Gelistirme surucusu: iletiyi loglar, gonderimi basarili sayar."""

    ad = "konsol"

    def gonder(self, kime: str, konu: str, govde: str) -> bool:
        logger.info("Konsol posta | kime=%s | konu=%s\n%s", kime, konu, govde)
        return True


class SmtpPosta:
    """`smtplib` tabanli surucu; `tls` acikken STARTTLS kullanir."""

    ad = "smtp"

    def __init__(self, yapilandirma: PostaAyarlari) -> None:
        self.yapilandirma = yapilandirma

    def gonder(self, kime: str, konu: str, govde: str) -> bool:
        y = self.yapilandirma
        ileti = EmailMessage()
        ileti["From"] = y.gonderen or ayarlar.smtp_gonderen
        ileti["To"] = kime
        ileti["Subject"] = konu
        ileti.set_content(govde)
        try:
            with smtplib.SMTP(y.host, y.port, timeout=SMTP_ZAMAN_ASIMI) as sunucu:
                sunucu.ehlo()
                if y.tls:
                    sunucu.starttls()
                    sunucu.ehlo()
                if y.kullanici:
                    sunucu.login(y.kullanici, y.sifre)
                sunucu.send_message(ileti)
        except (smtplib.SMTPException, OSError) as hata:
            logger.warning("SMTP gonderimi basarisiz | kime=%s | %s", kime, hata)
            return False
        return True


def _metin(deger: Any, varsayilan: str) -> str:
    """Bos/None tablo degerini ortam varsayilanina dusurur."""
    metin = "" if deger is None else str(deger).strip()
    return metin or varsayilan


def _mantiksal(deger: Any, varsayilan: bool) -> bool:
    if deger is None:
        return varsayilan
    if isinstance(deger, bool):
        return deger
    return str(deger).strip().lower() in {"1", "true", "evet", "acik", "açık", "yes"}


def _port(deger: Any, varsayilan: int) -> int:
    """Gecersiz/eksik port degerinde ortam varsayilanina duser."""
    try:
        return int(_metin(deger, str(varsayilan)))
    except (TypeError, ValueError):
        return varsayilan


def _sifre_coz(deger: Any, varsayilan: str) -> str:
    """Fernet ile sifreli degeri cozer; cozulemezse ham degeri kullanir."""
    ham = "" if deger is None else str(deger)
    if not ham:
        return varsayilan
    try:
        return guvenlik.coz(ham)
    except Exception:  # sifrelenmemis eski kayit ya da gecersiz anahtar
        return ham


async def posta_ayarlarini_oku(oturum: AsyncSession) -> PostaAyarlari:
    """`ayar` tablosundaki SMTP degerlerini okur; bos alanlarda ortama duser."""
    return PostaAyarlari(
        host=_metin(await ayar_oku(oturum, "smtp_host"), ayarlar.smtp_host),
        port=_port(await ayar_oku(oturum, "smtp_port"), ayarlar.smtp_port),
        kullanici=_metin(
            await ayar_oku(oturum, "smtp_kullanici"), ayarlar.smtp_kullanici
        ),
        sifre=_sifre_coz(
            await ayar_oku(oturum, "smtp_sifre"), ayarlar.smtp_sifre
        ),
        gonderen=_metin(
            await ayar_oku(oturum, "smtp_gonderen"), ayarlar.smtp_gonderen
        ),
        tls=_mantiksal(await ayar_oku(oturum, "smtp_tls"), ayarlar.smtp_tls),
    )


async def smtp_tanimli_mi(oturum: AsyncSession) -> bool:
    """Etkin SMTP host'u tanimli mi (panel ya da ortam)."""
    return (await posta_ayarlarini_oku(oturum)).tanimli_mi


async def surucu_sec(oturum: AsyncSession) -> PostaSürücüsü:
    """Etkin host doluysa SMTP, aksi hâlde konsol surucusunu secer."""
    yapilandirma = await posta_ayarlarini_oku(oturum)
    if yapilandirma.tanimli_mi:
        return SmtpPosta(yapilandirma)
    return KonsolPosta()


async def posta_gonder(
    oturum: AsyncSession, kime: str, konu: str, govde: str
) -> bool:
    """Iletiyi etkin surucuyle gonderir; gonderim basarisizsa False doner.

    Bloklayan SMTP cagrisi is parcacigina tasinir; basarisizlik istegi bozmaz.
    """
    surucu = await surucu_sec(oturum)
    return await asyncio.to_thread(surucu.gonder, kime, konu, govde)


def dogrulama_baglantisi(jeton: str) -> str:
    """Son kullanici uygulamasindaki e-posta dogrulama adresi."""
    return f"{ayarlar.onuc_url.rstrip('/')}/dogrula?jeton={quote(jeton)}"


def sifirlama_baglantisi(jeton: str) -> str:
    """Son kullanici uygulamasindaki parola sifirlama adresi."""
    return f"{ayarlar.onuc_url.rstrip('/')}/sifre-sifirla?jeton={quote(jeton)}"


def dogrulama_postasi(kullanici_ad: str, baglanti: str, saat: int) -> tuple[str, str]:
    """(konu, govde) dondurur."""
    konu = "KutyAI hesabınızı doğrulayın"
    govde = (
        f"Merhaba {kullanici_ad},\n\n"
        "KutyAI hesabınızı doğrulamak için aşağıdaki bağlantıyı açın:\n"
        f"{baglanti}\n\n"
        f"Bu bağlantı {saat} saat geçerlidir. Bağlantı tek kullanımlıktır.\n\n"
        "KutyAI"
    )
    return konu, govde


def sifirlama_postasi(kullanici_ad: str, baglanti: str, saat: int) -> tuple[str, str]:
    """(konu, govde) dondurur."""
    konu = "KutyAI parola sıfırlama"
    govde = (
        f"Merhaba {kullanici_ad},\n\n"
        "Parolanızı sıfırlamak için aşağıdaki bağlantıyı açın:\n"
        f"{baglanti}\n\n"
        f"Bu bağlantı {saat} saat geçerlidir. Bağlantı tek kullanımlıktır.\n\n"
        "KutyAI"
    )
    return konu, govde
