"""Gorsel ve ses uretimi (spec §8).

Saglayicinin OpenAI uyumlu medya uclarina gider:

* `POST {temel_url}/images/generations` — `data[i].b64_json` ya da indirilen `data[i].url`
* `POST {temel_url}/audio/speech` — ikili ses govdesi
* `POST {temel_url}/audio/transcriptions` — multipart, `{"text": ...}`

`bdm.yetenekler` bayragi kapali olan model icin `MedyaDesteklenmiyor` (400)
firlatilir. Tasima enjekte edilebilir; testler `httpx.MockTransport` baglar.
Saglayici kaynakli her hata tek bicimde `UstSaglayiciHatasi` (502) olur.
"""

from __future__ import annotations

import base64
import logging
from typing import Any

import httpx

from arkauc.app.cekirdek.hatalar import MedyaDesteklenmiyor, UstSaglayiciHatasi
from arkauc.app.servisler.upstream import UstSaglayici
from bdm_veritabani.modeller import Bdm

logger = logging.getLogger("kutyai.medya")

GORSEL_YOLU = "/images/generations"
SES_YOLU = "/audio/speech"
COZUM_YOLU = "/audio/transcriptions"

VARSAYILAN_BOYUT = "1024x1024"
VARSAYILAN_SES = "alloy"
VARSAYILAN_BICIM = "mp3"

#: Gorsel uretimi yanit beklerken okuma zaman asimi (uretim yavastir).
ZAMAN_ASIMI = httpx.Timeout(connect=10.0, read=300.0, write=60.0, pool=10.0)
GOVDE_KIRPMA = 400

#: `bicim` -> (uzanti, MIME); ucta da dogrulama icin kullanilir.
SES_BICIMLERI: dict[str, tuple[str, str]] = {
    "mp3": ("mp3", "audio/mpeg"),
    "opus": ("opus", "audio/ogg"),
    "aac": ("aac", "audio/aac"),
    "flac": ("flac", "audio/flac"),
    "wav": ("wav", "audio/wav"),
    "pcm": ("pcm", "audio/pcm"),
}


def _kirp(metin: str, uzunluk: int = GOVDE_KIRPMA) -> str:
    return " ".join((metin or "").split())[:uzunluk]


def _saglayici_adi(bdm: Bdm) -> str:
    return getattr(bdm.saglayici, "value", str(bdm.saglayici))


def _hata(bdm: Bdm, durum: int, govde: str) -> UstSaglayiciHatasi:
    """Saglayici yaniti hatasi; tam govde yalniz gunluge yazilir."""
    logger.error(
        "Medya upstream yaniti (BDM %s, saglayici %s, durum %s): %s",
        getattr(bdm, "id", None),
        _saglayici_adi(bdm),
        durum,
        _kirp(govde, 2000),
    )
    return UstSaglayiciHatasi(
        "Model sağlayıcısı medya isteğini yanıtlayamadı.",
        {"durum": durum, "saglayici": _saglayici_adi(bdm)},
    )


def _tasima_hatasi(bdm: Bdm, hata: Exception) -> UstSaglayiciHatasi:
    """Tasima istisnasi metni istemciye donmez; sunucu gunlugune yazilir."""
    logger.error(
        "Medya upstream tasima hatasi (BDM %s, saglayici %s): %s: %s",
        getattr(bdm, "id", None),
        _saglayici_adi(bdm),
        type(hata).__name__,
        _kirp(str(hata), GOVDE_KIRPMA),
    )
    return UstSaglayiciHatasi(
        "Model sağlayıcısına bağlanılamadı.",
        {"durum": 0, "saglayici": _saglayici_adi(bdm)},
    )


def yetenek_var(bdm: Bdm, ad: str) -> bool:
    """`bdm.yetenekler` icindeki bayragi okur (eksik alan kapali sayilir)."""
    return bool((bdm.yetenekler or {}).get(ad))


def destek_denetle(bdm: Bdm, ad: str) -> None:
    """Yetenek bayragi kapaliysa 400 `medya_desteklenmiyor` firlatir."""
    if not yetenek_var(bdm, ad):
        raise MedyaDesteklenmiyor(
            ayrinti={"yetenek": ad, "bdm_id": getattr(bdm, "id", None)}
        )


def adres(bdm: Bdm, yol: str) -> str:
    """`temel_url` + medya yolu."""
    return f"{(bdm.temel_url or '').rstrip('/')}{yol}"


def basliklar(bdm: Bdm, *, json_govde: bool = True) -> dict[str, str]:
    """Saglayici kimlik basliklari (Azure `api-key`, digerleri Bearer).

    Multipart istekte `Content-Type` cikarilir; sinir degerini httpx uretir.
    """
    basliklar = UstSaglayici().basliklar(bdm)
    if not json_govde:
        basliklar.pop("Content-Type", None)
    return basliklar


def _istemci(tasima: httpx.AsyncBaseTransport | None) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=tasima, timeout=ZAMAN_ASIMI)


def gorsel_mime(icerik: bytes) -> tuple[str, str]:
    """Imza baytlarindan `(uzanti, MIME)` secer; bilinmezse PNG kabul edilir."""
    if icerik.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png", "image/png"
    if icerik.startswith(b"\xff\xd8\xff"):
        return "jpg", "image/jpeg"
    if icerik[:4] == b"RIFF" and icerik[8:12] == b"WEBP":
        return "webp", "image/webp"
    return "png", "image/png"


def _gorsel_kayitlari(bdm: Bdm, yanit: httpx.Response) -> list[dict[str, Any]]:
    """`data` dizisini dogrular; bos/bozuk yanit saglayici hatasina cevrilir."""
    try:
        paket = yanit.json()
    except ValueError as hata:
        raise _hata(bdm, yanit.status_code, yanit.text) from hata
    kayitlar = paket.get("data") if isinstance(paket, dict) else None
    if not isinstance(kayitlar, list) or not kayitlar:
        raise _hata(bdm, yanit.status_code, yanit.text)
    return [kayit for kayit in kayitlar if isinstance(kayit, dict)]


async def _gorsel_icerigi(
    istemci: httpx.AsyncClient, bdm: Bdm, kayit: dict[str, Any]
) -> bytes:
    """Tek gorsel kaydini bayta cevirir: once `b64_json`, sonra `url` indirilir."""
    kodlu = kayit.get("b64_json")
    if isinstance(kodlu, str) and kodlu:
        try:
            return base64.b64decode(kodlu)
        except (ValueError, TypeError) as hata:
            raise _hata(bdm, 200, f"data[].b64_json cozulemedi: {type(hata).__name__}") from hata
    url = kayit.get("url")
    if isinstance(url, str) and url:
        indirme = await istemci.get(url)
        if indirme.status_code >= 400:
            raise _hata(bdm, indirme.status_code, indirme.text)
        return indirme.content
    raise _hata(bdm, 200, "data[] icinde b64_json veya url yok")


async def gorsel_uret(
    bdm: Bdm,
    istem: str,
    *,
    boyut: str = VARSAYILAN_BOYUT,
    adet: int = 1,
    tasima: httpx.AsyncBaseTransport | None = None,
) -> list[bytes]:
    """`POST {temel_url}/images/generations` ile gorsel uretir."""
    destek_denetle(bdm, "gorsel")
    govde: dict[str, Any] = {
        "model": bdm.upstream_model,
        "prompt": istem,
        "size": boyut,
        "n": int(adet),
    }
    try:
        async with _istemci(tasima) as istemci:
            yanit = await istemci.post(
                adres(bdm, GORSEL_YOLU), json=govde, headers=basliklar(bdm)
            )
            if yanit.status_code >= 400:
                raise _hata(bdm, yanit.status_code, yanit.text)
            return [
                await _gorsel_icerigi(istemci, bdm, kayit)
                for kayit in _gorsel_kayitlari(bdm, yanit)
            ]
    except UstSaglayiciHatasi:
        raise
    except httpx.HTTPError as hata:
        raise _tasima_hatasi(bdm, hata) from hata


async def ses_uret(
    bdm: Bdm,
    metin: str,
    *,
    ses: str = VARSAYILAN_SES,
    bicim: str = VARSAYILAN_BICIM,
    tasima: httpx.AsyncBaseTransport | None = None,
) -> bytes:
    """`POST {temel_url}/audio/speech` ile ses uretir (ikili govde)."""
    destek_denetle(bdm, "ses")
    govde: dict[str, Any] = {
        "model": bdm.upstream_model,
        "input": metin,
        "voice": ses,
        "response_format": bicim,
    }
    try:
        async with _istemci(tasima) as istemci:
            yanit = await istemci.post(
                adres(bdm, SES_YOLU), json=govde, headers=basliklar(bdm)
            )
    except httpx.HTTPError as hata:
        raise _tasima_hatasi(bdm, hata) from hata
    if yanit.status_code >= 400:
        raise _hata(bdm, yanit.status_code, yanit.text)
    if not yanit.content:
        raise _hata(bdm, yanit.status_code, "bos ses govdesi")
    return yanit.content


async def ses_coz(
    bdm: Bdm,
    dosya_adi: str,
    icerik: bytes,
    *,
    tasima: httpx.AsyncBaseTransport | None = None,
) -> str:
    """`POST {temel_url}/audio/transcriptions` (multipart) ile metne cevirir."""
    destek_denetle(bdm, "ses")
    try:
        async with _istemci(tasima) as istemci:
            yanit = await istemci.post(
                adres(bdm, COZUM_YOLU),
                files={"file": (dosya_adi, icerik)},
                data={"model": bdm.upstream_model},
                headers=basliklar(bdm, json_govde=False),
            )
    except httpx.HTTPError as hata:
        raise _tasima_hatasi(bdm, hata) from hata
    if yanit.status_code >= 400:
        raise _hata(bdm, yanit.status_code, yanit.text)
    try:
        paket = yanit.json()
    except ValueError as hata:
        raise _hata(bdm, yanit.status_code, yanit.text) from hata
    metin = paket.get("text") if isinstance(paket, dict) else None
    if not isinstance(metin, str):
        raise _hata(bdm, yanit.status_code, yanit.text)
    return metin
