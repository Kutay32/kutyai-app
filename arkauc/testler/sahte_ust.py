"""Sahte upstream saglayici: `httpx.MockTransport` ile SSE uretir.

Testler `SahteUst().saglayici()` sonucunu `ust_saglayici` bagimliligina
gecirir; boylece gercek ag trafigi olmadan akis dogrulanir.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from arkauc.app.servisler.upstream import UstSaglayici

VARSAYILAN_PARCALAR: tuple[str, ...] = ("Mer", "haba", " dünya")
VARSAYILAN_KULLANIM: dict[str, int] = {"prompt_tokens": 12, "completion_tokens": 7}
MODEL = "sahte-model"


def kullanim(prompt_tokens: int = 12, completion_tokens: int = 7) -> dict[str, int]:
    return {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens}


def sse_govdesi(
    parcalar: tuple[str, ...] | list[str],
    *,
    kullanim: dict[str, int] | None = VARSAYILAN_KULLANIM,
    kuyruk: str = "",
) -> bytes:
    """OpenAI uyumlu SSE akisi uretir; `data: [DONE]` ile biter."""
    satirlar: list[str] = []
    for parca in parcalar:
        paket = {
            "id": "chatcmpl-sahte",
            "object": "chat.completion.chunk",
            "model": MODEL,
            "choices": [{"index": 0, "delta": {"content": parca}, "finish_reason": None}],
        }
        satirlar.append(f"data: {json.dumps(paket, ensure_ascii=False)}")
    if kullanim is not None:
        satirlar.append(f"data: {json.dumps({'choices': [], 'usage': kullanim})}")
    satirlar.append("data: [DONE]")
    return ("\n\n".join(satirlar) + "\n\n" + kuyruk).encode("utf-8")


def yanit_govdesi(icerik: str, *, kullanim: dict[str, int] | None = VARSAYILAN_KULLANIM) -> dict:
    return {
        "id": "chatcmpl-sahte",
        "object": "chat.completion",
        "model": MODEL,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": icerik},
                "finish_reason": "stop",
            }
        ],
        "usage": kullanim or {},
    }


class YavasAkis(httpx.AsyncByteStream):
    """Parcalari araliklarla veren akis; istemci kopmasini test etmek icin."""

    def __init__(self, parcalar: tuple[str, ...] | list[str], gecikme: float = 0.05) -> None:
        self.parcalar = tuple(parcalar)
        self.gecikme = gecikme
        self.kapandi = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for parca in self.parcalar:
            await asyncio.sleep(self.gecikme)
            paket = {"choices": [{"index": 0, "delta": {"content": parca}}]}
            yield f"data: {json.dumps(paket, ensure_ascii=False)}\n\n".encode("utf-8")
        yield b"data: [DONE]\n\n"

    async def aclose(self) -> None:
        self.kapandi = True


class SahteUst:
    """MockTransport tabanli sahte saglayici; gonderilen istekleri kaydeder."""

    def __init__(
        self,
        *,
        parcalar: tuple[str, ...] | list[str] = VARSAYILAN_PARCALAR,
        icerik: str | None = None,
        kullanim: dict[str, int] | None = VARSAYILAN_KULLANIM,
        durum: int = 200,
        yavas: YavasAkis | None = None,
        kuyruk: str = "",
        hata: Exception | None = None,
    ) -> None:
        self.parcalar = tuple(parcalar)
        self.icerik = icerik if icerik is not None else "".join(self.parcalar)
        self.kullanim = kullanim
        self.durum = durum
        self.yavas = yavas
        self.kuyruk = kuyruk
        self.hata = hata
        self.istekler: list[dict[str, Any]] = []
        self.tasima = httpx.MockTransport(self._isle)

    # -- baglanti ------------------------------------------------------------

    def saglayici(self) -> UstSaglayici:
        """`ust_saglayici` bagimliligi yerine gecirilecek istemci."""
        return UstSaglayici(tasima=self.tasima)

    @property
    def son_istek(self) -> dict[str, Any]:
        return self.istekler[-1]

    @property
    def son_govde(self) -> dict[str, Any]:
        return self.istekler[-1]["govde"]

    # -- tasima isleyicisi ---------------------------------------------------

    def _isle(self, istek: httpx.Request) -> httpx.Response:
        if self.hata is not None:
            raise self.hata
        govde: dict[str, Any] = {}
        if istek.content:
            govde = json.loads(istek.content.decode("utf-8"))
        self.istekler.append(
            {
                "url": str(istek.url),
                "yontem": istek.method,
                "basliklar": dict(istek.headers),
                "govde": govde,
            }
        )
        if self.durum >= 400:
            return httpx.Response(
                self.durum, json={"error": {"message": "sahte sağlayıcı hatası", "type": "sahte"}}
            )
        if govde.get("stream"):
            if self.yavas is not None:
                return httpx.Response(
                    200,
                    headers={"content-type": "text/event-stream"},
                    stream=self.yavas,
                )
            return httpx.Response(
                200,
                headers={"content-type": "text/event-stream"},
                content=sse_govdesi(self.parcalar, kullanim=self.kullanim, kuyruk=self.kuyruk),
            )
        return httpx.Response(200, json=yanit_govdesi(self.icerik, kullanim=self.kullanim))
