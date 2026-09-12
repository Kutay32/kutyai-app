"""Mesaj kataloglari ve dil cozumleme (spec §10.1).

Mesajlar `arkauc/ceviriler/<dil>.json` dosyalarindan okunur. Anahtar, hata
`kod`u ya da serbest bir mesaj kimligidir; bulunamazsa Turkce katalog, o da
yoksa anahtarin kendisi dondurulur (boylece kademeli gecis guvenli olur).
"""

from __future__ import annotations

import json
import string
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

KOK = Path(__file__).resolve().parents[3]
CEVIRI_DIZINI = KOK / "arkauc" / "ceviriler"

VARSAYILAN_DIL = "tr"
DESTEKLENEN_DILLER: tuple[str, ...] = ("tr", "en")
DIL_ADLARI: dict[str, str] = {"tr": "Türkçe", "en": "English"}


@lru_cache(maxsize=8)
def katalog(dil: str) -> Mapping[str, str]:
    """Dil katalogu; dosya yoksa bos sozluk."""
    if dil not in DESTEKLENEN_DILLER:
        dil = VARSAYILAN_DIL
    yol = CEVIRI_DIZINI / f"{dil}.json"
    if not yol.exists():  # pragma: no cover - dosyalar depoda
        return {}
    return json.loads(yol.read_text(encoding="utf-8"))


def dil_coz(accept_language: str | None) -> str:
    """`Accept-Language` basligindan desteklenen dili secer."""
    if not accept_language:
        return VARSAYILAN_DIL
    for parca in accept_language.split(","):
        etiket = parca.split(";")[0].strip().lower()
        if not etiket:
            continue
        kok = etiket.split("-")[0]
        if kok in DESTEKLENEN_DILLER:
            return kok
    return VARSAYILAN_DIL


def _bicimle(sablon: str, degiskenler: Mapping[str, Any]) -> str:
    """Eksik/susli parantezlerde cokmeyen guvenli bicimlendirme."""
    if not degiskenler:
        return sablon
    try:
        return string.Formatter().vformat(sablon, (), _GuvenliSozluk(degiskenler))
    except (ValueError, KeyError, IndexError):
        return sablon


class _GuvenliSozluk(dict):
    def __missing__(self, anahtar: str) -> str:  # pragma: no cover - basit yol
        return "{" + anahtar + "}"


def mesaj(anahtar: str, dil: str = VARSAYILAN_DIL, **degiskenler: Any) -> str:
    """Anahtari verilen dilde cozer; yoksa Turkceye, o da yoksa anahtara duser."""
    sablon = katalog(dil).get(anahtar)
    if sablon is None:
        sablon = katalog(VARSAYILAN_DIL).get(anahtar, anahtar)
    return _bicimle(sablon, degiskenler)


def dil_listesi() -> list[dict[str, str]]:
    return [
        {"kod": kod, "ad": DIL_ADLARI.get(kod, kod), "varsayilan": kod == VARSAYILAN_DIL}
        for kod in DESTEKLENEN_DILLER
    ]


def katalogu_temizle() -> None:
    """Testlerde katalog onbellegini bosaltir."""
    katalog.cache_clear()
