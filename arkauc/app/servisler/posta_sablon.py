"""Posta sablon motoru (spec §9).

Sablonlar organizasyon bazinda `posta_sablonu` tablosunda tutulur; kayit yoksa
tohumdaki gomulu varsayilan (TR/EN) kullanilir. Yerine koyma `{{degisken}}`
bicimindedir; kosullu blok yoktur (YAGNI).
"""

from __future__ import annotations

import re
from typing import Any, Mapping

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek.hatalar import Bulunamadi
from bdm_veritabani.modeller import PostaSablonu
from bdm_veritabani.tohum import POSTA_SABLONLARI

DEGISKEN_DESENI = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")

KODLAR: tuple[str, ...] = (
    "dogrulama",
    "sifirlama",
    "davet",
    "kota_uyarisi",
    "fatura",
    "hosgeldin",
)

#: Onizleme icin ornek degisken degerleri.
ORNEK_DEGISKENLER: dict[str, str] = {
    "marka": "KutyAI",
    "ad": "Ayşe Yılmaz",
    "organizasyon": "Acme AI",
    "baglanti": "http://localhost:3000/dogrula?jeton=ornek-jeton",
    "davet_eden": "Mehmet Demir",
    "yuzde": "85",
    "donem": "Eylül 2026",
    "tutar": "TRY 990,00",
    "fatura_no": "1042",
}


def varsayilan_sablon(kod: str, dil: str) -> dict[str, str]:
    """Tohumdaki gomulu varsayilan sablon."""
    for kayit in POSTA_SABLONLARI:
        if kayit["kod"] == kod and kayit["dil"] == dil:
            return dict(kayit)
    for kayit in POSTA_SABLONLARI:
        if kayit["kod"] == kod and kayit["dil"] == "tr":
            return dict(kayit)
    raise Bulunamadi("Posta şablonu bulunamadı.", {"kod": kod, "dil": dil})


def degiskenleri_coz(metin: str, degiskenler: Mapping[str, Any]) -> str:
    """`{{ad}}` yer tutucularini doldurur; bilinmeyen anahtar aynen kalir."""

    def _degistir(eslesme: re.Match[str]) -> str:
        anahtar = eslesme.group(1)
        if anahtar in degiskenler:
            return str(degiskenler[anahtar])
        return eslesme.group(0)

    return DEGISKEN_DESENI.sub(_degistir, metin or "")


async def sablon_getir(
    oturum: AsyncSession, org_id: int, kod: str, dil: str = "tr"
) -> dict[str, str]:
    """Organizasyon sablonu; yoksa varsayilan."""
    satir = (
        await oturum.execute(
            sa.select(PostaSablonu).where(
                PostaSablonu.org_id == org_id,
                PostaSablonu.kod == kod,
                PostaSablonu.dil == dil,
            )
        )
    ).scalar_one_or_none()
    if satir is None:
        return varsayilan_sablon(kod, dil)
    return {
        "kod": satir.kod,
        "dil": satir.dil,
        "konu": satir.konu,
        "govde_metin": satir.govde_metin,
        "govde_html": satir.govde_html,
    }


async def sablonlari_listele(oturum: AsyncSession, org_id: int) -> list[dict[str, Any]]:
    """Tum kodxdil kombinasyonlari: organizasyon degeri varsa o, yoksa varsayilan."""
    satirlar = (
        await oturum.execute(
            sa.select(PostaSablonu).where(PostaSablonu.org_id == org_id)
        )
    ).scalars().all()
    ozel = {(satir.kod, satir.dil): satir for satir in satirlar}

    sonuc: list[dict[str, Any]] = []
    for kod in KODLAR:
        for dil in ("tr", "en"):
            satir = ozel.get((kod, dil))
            if satir is not None:
                sonuc.append(
                    {
                        "kod": kod,
                        "dil": dil,
                        "konu": satir.konu,
                        "govde_metin": satir.govde_metin,
                        "govde_html": satir.govde_html,
                        "ozel": True,
                    }
                )
            else:
                varsayilan = varsayilan_sablon(kod, dil)
                sonuc.append(
                    {
                        "kod": kod,
                        "dil": dil,
                        "konu": varsayilan["konu"],
                        "govde_metin": varsayilan["govde_metin"],
                        "govde_html": varsayilan["govde_html"],
                        "ozel": False,
                    }
                )
    return sonuc


async def sablon_yaz(
    oturum: AsyncSession,
    org_id: int,
    *,
    kod: str,
    dil: str,
    konu: str,
    govde_metin: str,
    govde_html: str,
) -> PostaSablonu:
    if kod not in KODLAR:
        raise Bulunamadi("Posta şablonu bulunamadı.", {"kod": kod})
    satir = (
        await oturum.execute(
            sa.select(PostaSablonu).where(
                PostaSablonu.org_id == org_id,
                PostaSablonu.kod == kod,
                PostaSablonu.dil == dil,
            )
        )
    ).scalar_one_or_none()
    if satir is None:
        satir = PostaSablonu(org_id=org_id, kod=kod, dil=dil)
        oturum.add(satir)
    satir.konu = konu
    satir.govde_metin = govde_metin
    satir.govde_html = govde_html
    await oturum.flush()
    return satir


def onizle(
    sablon: Mapping[str, str], degiskenler: Mapping[str, Any] | None = None
) -> dict[str, str]:
    """Sablonu ornek degiskenlerle doldurur."""
    degerler = {**ORNEK_DEGISKENLER, **(degiskenler or {})}
    return {
        "konu": degiskenleri_coz(sablon.get("konu", ""), degerler),
        "govde_metin": degiskenleri_coz(sablon.get("govde_metin", ""), degerler),
        "govde_html": degiskenleri_coz(sablon.get("govde_html", ""), degerler),
    }
