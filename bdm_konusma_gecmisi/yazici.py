"""Konusma ve mesaj yazimi (spec §4.6, §4.7, §4.8).

Maskelenmis icerik yazilir; ham metin hicbir zaman veritabanina girmez.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from bdm_konusma_gecmisi.maskeleme import maskele_metin
from bdm_veritabani.modeller import (
    KullanimDurumu,
    KullanimKaydi,
    Konusma,
    Mesaj,
    MesajRolu,
)

BASLIK_UZUNLUGU = 60


def baslik_uret(metin: str) -> str:
    """Ilk mesajdan konusma basligi turetir."""
    temiz = " ".join((metin or "").split())
    if not temiz:
        return "Yeni sohbet"
    if len(temiz) <= BASLIK_UZUNLUGU:
        return temiz
    return temiz[:BASLIK_UZUNLUGU].rstrip() + "…"


async def konusma_olustur(
    oturum: AsyncSession,
    *,
    bdm_id: int,
    kullanici_id: int | None = None,
    api_anahtari_id: int | None = None,
    sistem_istemi: str = "",
) -> Konusma:
    konusma = Konusma(
        bdm_id=bdm_id,
        kullanici_id=kullanici_id,
        api_anahtari_id=api_anahtari_id,
        sistem_istemi=sistem_istemi or "",
    )
    oturum.add(konusma)
    await oturum.flush()
    await oturum.refresh(konusma)
    return konusma


async def mesaj_ekle(
    oturum: AsyncSession,
    *,
    konusma: Konusma,
    rol: MesajRolu,
    icerik: str,
    token_sayisi: int = 0,
    gecikme_ms: int = 0,
    model: str = "",
    hata: str | None = None,
    maskele_uygula: bool = True,
) -> Mesaj:
    """Mesaji maskelenmis olarak kaydeder ve konusma basligini gunceller."""
    kayit_icerigi = await maskele_metin(oturum, icerik) if maskele_uygula else icerik
    mesaj = Mesaj(
        konusma_id=konusma.id,
        rol=rol,
        icerik=kayit_icerigi,
        token_sayisi=token_sayisi,
        gecikme_ms=gecikme_ms,
        model=model,
        hata=hata,
    )
    oturum.add(mesaj)

    if rol == MesajRolu.kullanici:
        if konusma.token_girdi is None:
            konusma.token_girdi = 0
        konusma.token_girdi = (konusma.token_girdi or 0) + token_sayisi
        if not konusma.baslik or konusma.baslik == "Yeni sohbet":
            konusma.baslik = baslik_uret(kayit_icerigi)
    elif rol == MesajRolu.asistan:
        konusma.token_cikti = (konusma.token_cikti or 0) + token_sayisi

    await oturum.flush()
    await oturum.refresh(mesaj)
    return mesaj


async def kullanim_yaz(
    oturum: AsyncSession,
    *,
    bdm_id: int,
    kullanici_id: int | None = None,
    api_anahtari_id: int | None = None,
    konusma_id: int | None = None,
    girdi_token: int = 0,
    cikti_token: int = 0,
    gecikme_ms: int = 0,
    durum: KullanimDurumu = KullanimDurumu.basarili,
) -> KullanimKaydi:
    kayit = KullanimKaydi(
        bdm_id=bdm_id,
        kullanici_id=kullanici_id,
        api_anahtari_id=api_anahtari_id,
        konusma_id=konusma_id,
        girdi_token=girdi_token,
        cikti_token=cikti_token,
        gecikme_ms=gecikme_ms,
        durum=durum,
    )
    oturum.add(kayit)
    await oturum.flush()
    return kayit


async def ust_saglayici_mesajlari(
    oturum: AsyncSession, konusma: Konusma, *, limit: int = 40
) -> list[dict[str, str]]:
    """Upstream'e gonderilecek mesaj listesi (eskiden yeniye)."""
    from bdm_veritabani.modeller import Mesaj

    mesajlar = (
        await oturum.execute(
            sa.select(Mesaj)
            .where(
                Mesaj.konusma_id == konusma.id,
                Mesaj.rol.in_([MesajRolu.kullanici, MesajRolu.asistan]),
            )
            .order_by(Mesaj.id.desc())
            .limit(limit)
        )
    ).scalars().all()
    return [
        {"role": mesaj.rol.value, "content": mesaj.icerik}
        for mesaj in reversed(mesajlar)
        if mesaj.icerik
    ]
