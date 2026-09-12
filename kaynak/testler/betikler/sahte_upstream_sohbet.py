"""Sahte OpenAI-uyumlu upstream (port 8199) — bagimsiz gozlem araci.

Calistirma:
    ./.venv/Scripts/python.exe -m uvicorn sahte_upstream_sohbet:app --port 8199
(kaynak/testler/betikler dizininden)

Davranis `model` alanina gore secilir:
  * `hata-500`  -> HTTP 500
  * `yavas`     -> 10 parca, 0.5 sn arayla (istemci kopma testi)
  * diger       -> 3 parca + usage + [DONE]

Her istek gövdesi `SAHTE_KAYIT` yolundaki JSONL dosyasina yazilir; boylece
upstream'e sizan ham veri kanitlanabilir.
"""

from __future__ import annotations

import asyncio
import json
import os
import pathlib
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

KAYIT = pathlib.Path(
    os.environ.get(
        "SAHTE_KAYIT",
        "E:/kutyai-app/kaynak/testler/gecici/sahte_upstream_istekler.jsonl",
    )
)

app = FastAPI(title="sahte upstream")


def _yaz(kayit: dict) -> None:
    KAYIT.parent.mkdir(parents=True, exist_ok=True)
    with KAYIT.open("a", encoding="utf-8") as dosya:
        dosya.write(json.dumps(kayit, ensure_ascii=False) + "\n")


def _sse(paket: dict) -> str:
    return f"data: {json.dumps(paket, ensure_ascii=False)}\n\n"


def _son_kullanici(govde: dict) -> str:
    for mesaj in reversed(govde.get("messages") or []):
        if mesaj.get("role") == "kullanici":
            return str(mesaj.get("content") or "")
    return ""


def _cevap(govde: dict) -> str:
    """Ham e-posta iceren sabit govde: yanit yuzeyinde maskeleme var mi?"""
    return (
        "YANIT: "
        + _son_kullanici(govde)
        + " | iletisim: ayse@acme.com | tel: 0532 123 45 67"
    )


async def _akis(govde: dict, parcalar: list[str], gecikme: float):
    try:
        for parca in parcalar:
            await asyncio.sleep(gecikme)
            yield _sse(
                {
                    "id": "chatcmpl-sahte",
                    "object": "chat.completion.chunk",
                    "model": govde.get("model"),
                    "choices": [
                        {"index": 0, "delta": {"content": parca}, "finish_reason": None}
                    ],
                }
            )
        yield _sse(
            {
                "choices": [],
                "usage": {"prompt_tokens": 12, "completion_tokens": 7},
            }
        )
        yield "data: [DONE]\n\n"
        _yaz({"olay": "akis_tamamlandi", "model": govde.get("model"), "zaman": time.time()})
    except asyncio.CancelledError:
        _yaz({"olay": "akis_iptal_edildi", "model": govde.get("model"), "zaman": time.time()})
        raise


@app.post("/v1/chat/completions")
@app.post("/chat/completions")
async def sohbet(istek: Request):
    govde = await istek.json()
    model = str(govde.get("model") or "")
    basliklar = {
        anahtar: deger
        for anahtar, deger in istek.headers.items()
        if anahtar.lower() in ("authorization", "api-key", "content-type", "accept")
    }
    _yaz(
        {
            "olay": "istek",
            "zaman": time.time(),
            "yol": str(istek.url),
            "model": model,
            "akis": bool(govde.get("stream")),
            "basliklar": basliklar,
            "govde": govde,
        }
    )

    # OpenAI sozlesmesi: role yalniz system|user|assistant|tool olabilir.
    izinli_roller = {"system", "user", "assistant", "tool"}
    gecersiz = [
        mesaj.get("role") for mesaj in (govde.get("messages") or [])
        if mesaj.get("role") not in izinli_roller
    ]
    if gecersiz:
        _yaz({"olay": "gecersiz_roller", "roller": gecersiz, "model": model})
        if model == "kati":
            return JSONResponse(
                {
                    "error": {
                        "message": "Invalid value for 'messages[0].role'",
                        "type": "invalid_request_error",
                        "code": "invalid_role",
                    }
                },
                status_code=400,
            )

    if model == "hata-500":
        return JSONResponse(
            {"error": {"message": "sahte saglayici hatasi", "type": "sahte"}},
            status_code=500,
        )

    if model == "yavas":
        parcalar = [f"parca{i} " for i in range(10)]
        return StreamingResponse(
            _akis(govde, parcalar, 0.5),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )

    if model == "kir":

        async def kirilan():
            for parca in ("ilk ", "ikinci ", "ucuncu "):
                await asyncio.sleep(0.2)
                yield _sse(
                    {"choices": [{"index": 0, "delta": {"content": parca}}]}
                )
            _yaz({"olay": "akis_ortada_kirildi", "model": model})
            raise RuntimeError("sahte upstream baglantiyi kopardi")

        return StreamingResponse(
            kirilan(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )

    if govde.get("stream"):
        cevap = _cevap(govde)
        parcalar = [cevap[i : i + 8] for i in range(0, len(cevap), 8)]
        return StreamingResponse(
            _akis(govde, parcalar, 0.02),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )

    return JSONResponse(
        {
            "id": "chatcmpl-sahte",
            "object": "chat.completion",
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": _cevap(govde)},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 12, "completion_tokens": 7},
        }
    )
