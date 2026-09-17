"""Bellek ici kayan pencere oran sinirlayici (spec §11).

Kimlik uclarinda kaba kuvvet denemelerini, sohbet ucunda istemci basina
istek patlamasini sinirlar. Saf ASGI ara katmani olarak yazilmistir: SSE
yanitlarinin govdesine dokunmaz, akis bozulmaz.

Anahtar, istek kimligidir: `Authorization` basligi varsa jeton ozeti,
yoksa istemci IP adresi. Boylece ayni IP'deki farkli oturumlar birbirini
etkilemez, ayni jetonun paralel kullanimi ise paylasilan pencereye sayilir.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from threading import Lock
from typing import Any

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from arkauc.app.cekirdek.ayarlar import ayarlar
from arkauc.app.cekirdek.guvenlik import ozet

ORAN_SINIRI_MESAJI = "Çok fazla istek gönderdiniz. Lütfen biraz bekleyin."
KIMLIK_LIMITI = 10
VARSAYILAN_LIMIT = 240
PENCERE_SN = 60


@dataclass(frozen=True, slots=True)
class Kural:
    onek: str
    limit: int
    pencere_sn: int = PENCERE_SN
    jeton_ile_ayir: bool = False


def kurallar() -> tuple[Kural, ...]:
    """Etkin kurallar; limitler ayarlardan gelir."""
    sohbet = max(1, int(ayarlar.oran_siniri_istek_dk))
    kimlik = max(1, int(ayarlar.oran_siniri_kimlik_dk))
    return (
        # Kimlik uclarinda ayrim YALNIZ IP ile yapilir: istemci `Authorization`
        # basligini degistirerek yeni kova uretememeli.
        Kural("/api/v1/kimlik/", kimlik),
        Kural("/api/v1/sohbet", sohbet, jeton_ile_ayir=True),
        Kural("/api/v1/", VARSAYILAN_LIMIT),
    )


class KayanPencere:
    """Anahtar basina zaman damgasi kuyrugu."""

    def __init__(self) -> None:
        self._kayitlar: dict[str, deque[float]] = {}
        self._kilit = Lock()

    def izin(self, anahtar: str, limit: int, pencere_sn: int) -> tuple[bool, int]:
        """(izin_var_mi, yeniden_dene_sn) dondurur."""
        simdi = time.monotonic()
        with self._kilit:
            kuyruk = self._kayitlar.get(anahtar)
            if kuyruk is None:
                kuyruk = deque()
                self._kayitlar[anahtar] = kuyruk
            while kuyruk and simdi - kuyruk[0] > pencere_sn:
                kuyruk.popleft()
            if len(kuyruk) >= limit:
                return False, int(pencere_sn - (simdi - kuyruk[0])) + 1
            kuyruk.append(simdi)
            if len(self._kayitlar) > 20_000:  # pragma: no cover - bellek korumasi
                self._temizle(simdi, pencere_sn)
            return True, 0

    def temizle(self) -> None:
        with self._kilit:
            self._kayitlar.clear()

    def _temizle(self, simdi: float, pencere_sn: int) -> None:
        bos: list[str] = []
        for anahtar, kuyruk in self._kayitlar.items():
            while kuyruk and simdi - kuyruk[0] > pencere_sn:
                kuyruk.popleft()
            if not kuyruk:
                bos.append(anahtar)
        for anahtar in bos:
            del self._kayitlar[anahtar]


PENCERE = KayanPencere()


def kural_sec(yol: str) -> Kural | None:
    if not yol.startswith("/api/v1"):
        return None
    for kural in kurallar():
        if yol.startswith(kural.onek):
            return kural
    return None


def istemci_ip(scope: Scope) -> str:
    """Istemci IP'si; guvenilir vekil arkasinda X-Forwarded-For'un ilk degeri."""
    if ayarlar.guvenilir_vekil:
        basliklar = {anahtar: deger for anahtar, deger in scope.get("headers", [])}
        iletilen = basliklar.get(b"x-forwarded-for")
        if iletilen:
            ilk = iletilen.decode("latin-1").split(",")[0].strip()
            if ilk:
                return ilk
    istemci = scope.get("client")
    return istemci[0] if istemci else "bilinmeyen"


def kova_anahtarlari(scope: Scope, kural: Kural) -> list[str]:
    """Bir istegin sayilacagi tum kovalar.

    Her istek her zaman IP kovasina sayilir. Yalnizca `jeton_ile_ayir` acik
    olan kurallarda jeton ozeti ikinci kova olarak eklenir; boylece istemci
    rastgele `Authorization` basligi ureterek siniri atlayamaz.
    """
    anahtarlar = [f"ip:{istemci_ip(scope)}|{kural.onek}"]
    if kural.jeton_ile_ayir:
        basliklar = {anahtar: deger for anahtar, deger in scope.get("headers", [])}
        yetki = basliklar.get(b"authorization")
        if yetki:
            anahtarlar.append(f"jeton:{ozet(yetki.decode('latin-1'))}|{kural.onek}")
    return anahtarlar


class OranSiniriMiddleware:
    """Saf ASGI ara katmani; yanit govdesine dokunmaz.

    Ilk parametre adi `app`'dir: Starlette ara katmanlari `cls(app, ...)` ile
    kurar ve `app` adi kurulum biciminden bagimsiz olarak gecerlidir.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("method") == "OPTIONS":
            await self.app(scope, receive, send)
            return

        kural = kural_sec(str(scope.get("path", "")))
        if kural is None:
            await self.app(scope, receive, send)
            return

        anahtarlar = kova_anahtarlari(scope, kural)
        izin = True
        yeniden_dene = 0
        for anahtar in anahtarlar:
            gecti, kalan = PENCERE.izin(anahtar, kural.limit, kural.pencere_sn)
            if not gecti:
                izin = False
                yeniden_dene = max(yeniden_dene, kalan)
                break
        if izin:
            await self.app(scope, receive, send)
            return

        yanit = JSONResponse(
            status_code=429,
            content={
                "hata": {
                    "kod": "oran_siniri",
                    "mesaj": ORAN_SINIRI_MESAJI,
                    "ayrinti": {"yeniden_dene_sn": yeniden_dene},
                }
            },
            headers={"Retry-After": str(yeniden_dene)},
        )
        await yanit(scope, receive, send)


def sinirlayiciyi_sifirla() -> None:
    """Testler arasi izolasyon icin pencereyi bosaltir."""
    PENCERE.temizle()


__all__: list[str] = [
    "Message",
    "OranSiniriMiddleware",
    "PENCERE",
    "Kural",
    "kova_anahtarlari",
    "istemci_ip",
    "kural_sec",
    "sinirlayiciyi_sifirla",
]
