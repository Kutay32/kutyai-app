"""Gomme (embedding) uretimi — OpenAI uyumlu `/embeddings` (spec §5).

Saglayici sozlesmesi sohbet istemcisiyle aynidir (`servisler/upstream.py`):
Azure `api-key`, diger saglayicilar `Authorization: Bearer` kullanir. Istekler
`TOPLU_BOYUT`luk gruplara bolunur; tasima enjekte edilebilir, boylece testler
`httpx.MockTransport` ile gercek ag trafigi olmadan calisir.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from arkauc.app.cekirdek import guvenlik
from arkauc.app.cekirdek.hatalar import RagGommeHatasi
from bdm_veritabani.modeller import Bdm

logger = logging.getLogger("kutyai.gomme")

GOMME_YOLU = "/embeddings"
#: OpenAI `/embeddings` tek istekte sinirli sayida girdi kabul eder.
TOPLU_BOYUT = 32
ZAMAN_ASIMI = httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=10.0)


def _saglayici_adi(bdm: Bdm) -> str:
    return getattr(bdm.saglayici, "value", str(bdm.saglayici))


def basliklar(bdm: Bdm) -> dict[str, str]:
    """Azure `api-key`, diger saglayicilar `Authorization: Bearer` kullanir."""
    sonuc = {"Content-Type": "application/json", "Accept": "application/json"}
    anahtar = ""
    if bdm.api_anahtari_sifreli:
        try:
            anahtar = guvenlik.coz(bdm.api_anahtari_sifreli)
        except Exception:  # pragma: no cover - bozuk sifreli deger
            logger.warning("BDM %s için gömme anahtarı çözülemedi.", bdm.id)
    if anahtar:
        if _saglayici_adi(bdm) == "azure":
            sonuc["api-key"] = anahtar
        else:
            sonuc["Authorization"] = f"Bearer {anahtar}"
    return sonuc


def _hata(bdm: Bdm, durum: int, govde: str, *, neden: str = "") -> RagGommeHatasi:
    """Ayrintiya yalniz durum ve saglayici adi girer; tam govde gunluge yazilir."""
    logger.error(
        "Gömme yanıtı hatası (BDM %s, sağlayıcı %s, durum %s): %s",
        getattr(bdm, "id", None),
        _saglayici_adi(bdm),
        durum,
        (govde or "")[:500],
    )
    ayrinti: dict[str, Any] = {"durum": durum, "saglayici": _saglayici_adi(bdm)}
    if neden:
        ayrinti["neden"] = neden
    return RagGommeHatasi("rag_gomme_hatasi", ayrinti)


def _tasima_hatasi(bdm: Bdm, hata: Exception) -> RagGommeHatasi:
    """Tasima istisnasi metni istemciye donmez; sunucu gunlugune yazilir."""
    logger.error(
        "Gömme taşıma hatası (BDM %s, sağlayıcı %s): %s",
        getattr(bdm, "id", None),
        _saglayici_adi(bdm),
        hata,
    )
    return RagGommeHatasi("rag_gomme_hatasi", {"saglayici": _saglayici_adi(bdm)})


def _vektorleri_ayikla(paket: Any, beklenen: int) -> list[list[float]]:
    """`data[i].embedding` alanlarini `index` sirasina gore cikarir."""
    kayitlar = paket.get("data") if isinstance(paket, dict) else None
    if not isinstance(kayitlar, list) or len(kayitlar) != beklenen:
        return []
    sirali = sorted(
        kayitlar,
        key=lambda kayit: int(kayit.get("index", 0)) if isinstance(kayit, dict) else 0,
    )
    vektorler: list[list[float]] = []
    for kayit in sirali:
        vektor = kayit.get("embedding") if isinstance(kayit, dict) else None
        if not isinstance(vektor, list) or not vektor:
            return []
        try:
            vektorler.append([float(deger) for deger in vektor])
        except (TypeError, ValueError):
            return []
    return vektorler


async def gomme_uret(
    bdm: Bdm,
    metinler: list[str],
    *,
    tasima: httpx.AsyncBaseTransport | None = None,
) -> list[list[float]]:
    """Metinleri `bdm.gomme_modeli` ile vektore cevirir (sira korunur).

    Istekler `TOPLU_BOYUT`luk gruplara bolunur. Ag, HTTP durum ve yanit
    bicimi hatalari `RagGommeHatasi` (502) olarak yukselir.
    """
    girdiler = [metin if isinstance(metin, str) else str(metin) for metin in metinler]
    if not girdiler:
        return []
    model = (bdm.gomme_modeli or "").strip()
    if not model:
        raise RagGommeHatasi(
            "gomme_modeli_yok",
            {"bdm_id": getattr(bdm, "id", None)},
            kod="gomme_modeli_yok",
            durum_kodu=400,
        )

    adres = f"{(bdm.temel_url or '').rstrip('/')}{GOMME_YOLU}"
    basliklar_ = basliklar(bdm)
    vektorler: list[list[float]] = []
    async with httpx.AsyncClient(transport=tasima, timeout=ZAMAN_ASIMI) as istemci:
        for baslangic in range(0, len(girdiler), TOPLU_BOYUT):
            yigin = girdiler[baslangic : baslangic + TOPLU_BOYUT]
            try:
                yanit = await istemci.post(
                    adres, headers=basliklar_, json={"model": model, "input": yigin}
                )
            except httpx.HTTPError as hata:
                raise _tasima_hatasi(bdm, hata) from hata
            if yanit.status_code >= 400:
                raise _hata(bdm, yanit.status_code, yanit.text)
            try:
                paket = yanit.json()
            except ValueError:
                raise _hata(bdm, yanit.status_code, yanit.text, neden="gecersiz_json") from None
            cikan = _vektorleri_ayikla(paket, len(yigin))
            if not cikan:
                raise _hata(bdm, yanit.status_code, yanit.text, neden="eksik_vektor")
            vektorler.extend(cikan)
    return vektorler
