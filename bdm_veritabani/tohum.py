"""Tohum verisi: varsayilan ayarlar ve KVKK maskeleme kurallari.

Kullanim: `await tohumla()` uygulama acilirken ya da test kurulumunda cagrilir.
Idempotenttir; var olan kayitlari degistirmez.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from bdm_veritabani.modeller import Ayar, MaskelemeKurali
from bdm_veritabani.oturum import oturum_fabrikasi

VARSAYILAN_AYARLAR: dict[str, object] = {
    "kurulum_tamam": False,
    "marka_adi": "KutyAI",
    "varsayilan_bdm_slug": None,
    "saklama_gun": 90,
    "maskeleme_aktif": True,
    "kayit_acik": True,
    "bakim_modu": False,
    "smtp_gonderen": "",
    "son_dogrulama_baglantisi": None,
    "son_sifirlama_baglantisi": None,
}

MASKELEME_KURALLARI: tuple[tuple[str, str, int], ...] = (
    ("tckn", r"\b[1-9][0-9]{10}\b", 10),
    ("eposta", r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", 20),
    ("telefon", r"(?:\+90|0)?[\s.\-]?\(?5[0-9]{2}\)?[\s.\-]?[0-9]{3}[\s.\-]?[0-9]{2}[\s.\-]?[0-9]{2}", 30),
    ("iban", r"\bTR[0-9]{2}[\s]?(?:[0-9]{4}[\s]?){5}[0-9]{2}\b", 40),
    ("kredi_karti", r"\b(?:[0-9][ \-]?){13,16}\b", 50),
)


async def tohumla(oturum: AsyncSession | None = None) -> None:
    """Varsayilan ayar ve maskeleme kurallarini ekler (idempotent)."""
    if oturum is not None:
        await _uygula(oturum)
        return
    async with oturum_fabrikasi()() as kendi_oturum:
        await _uygula(kendi_oturum)
        await kendi_oturum.commit()


async def _uygula(oturum: AsyncSession) -> None:
    mevcut_ayarlar = set(
        (await oturum.execute(sa.select(Ayar.anahtar))).scalars().all()
    )
    for anahtar, deger in VARSAYILAN_AYARLAR.items():
        if anahtar not in mevcut_ayarlar:
            oturum.add(Ayar(anahtar=anahtar, deger=deger))

    mevcut_kurallar = set(
        (await oturum.execute(sa.select(MaskelemeKurali.ad))).scalars().all()
    )
    for ad, desen, sira in MASKELEME_KURALLARI:
        if ad not in mevcut_kurallar:
            oturum.add(MaskelemeKurali(ad=ad, desen=desen, sira=sira, etkin=True))

    await oturum.flush()
