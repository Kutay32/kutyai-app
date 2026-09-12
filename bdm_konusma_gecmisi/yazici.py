"""Konusma ve mesaj yazimi (spec §4.6, §4.7, §4.8).

Maskelenmis icerik yazilir; ham metin hicbir zaman veritabanina girmez.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek.hatalar import Bulunamadi
from bdm_konusma_gecmisi.maskeleme import maskele_metin
from bdm_veritabani.modeller import (
    Bdm,
    KullanimDurumu,
    KullanimKaydi,
    Konusma,
    Mesaj,
    MesajRolu,
)

BASLIK_UZUNLUGU = 60

# Veritabani rol degerlerinin OpenAI uyumlu karsiliklari.
UST_ROL_ADLARI: dict[MesajRolu, str] = {
    MesajRolu.kullanici: "user",
    MesajRolu.asistan: "assistant",
    MesajRolu.sistem: "system",
    MesajRolu.arac: "tool",
}


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
    org_id: int | None = None,
    kullanici_id: int | None = None,
    api_anahtari_id: int | None = None,
    sistem_istemi: str = "",
) -> Konusma:
    if org_id is None:
        org_id = (
            await oturum.execute(sa.select(Bdm.org_id).where(Bdm.id == bdm_id))
        ).scalar_one_or_none()
    if org_id is None:
        raise Bulunamadi("Model kaydı bulunamadı.", {"bdm_id": bdm_id})
    konusma = Konusma(
        org_id=org_id,
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
    org_id: int | None = None,
    kullanici_id: int | None = None,
    api_anahtari_id: int | None = None,
    konusma_id: int | None = None,
    girdi_token: int = 0,
    cikti_token: int = 0,
    gecikme_ms: int = 0,
    durum: KullanimDurumu = KullanimDurumu.basarili,
) -> KullanimKaydi:
    if org_id is None:
        org_id = (
            await oturum.execute(sa.select(Bdm.org_id).where(Bdm.id == bdm_id))
        ).scalar_one_or_none()
    kayit = KullanimKaydi(
        org_id=org_id,
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
    """Upstream'e gonderilecek mesaj listesi (eskiden yeniye).

    Rol adlari OpenAI sozlesmesine cevrilir (`user`/`assistant`); veritabani
    degerleri Turkce oldugu icin ham deger gonderilirse saglayicilar 400 doner.
    """
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
        {"role": UST_ROL_ADLARI[mesaj.rol], "content": mesaj.icerik}
        for mesaj in reversed(mesajlar)
        if mesaj.icerik
    ]
