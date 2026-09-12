"""Sahte OpenAI-uyumlu + Ollama upstream.

Amac: `bdm_hazirlama_ucu` dogrulama/indirme uclarini GERCEK bir ag sunucusuna
karsi sinamak.

Uclar:
  GET  /v1/models              -> OpenAI model listesi (2 model)
  POST /v1/chat/completions    -> 1 tokenlik sahte tamamlama
  GET  /api/tags               -> Ollama yerel model listesi
  POST /api/pull               -> Ollama NDJSON indirme akisi
  GET  /_vuruslar              -> bu sunucuya gelen isteklerin sayaci (kanit)

Calistirma:
  ./.venv/Scripts/python.exe kaynak/testler/betikler/sahte_upstream.py [PORT]
"""

from __future__ import annotations

import json
import sys
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8199

app = FastAPI(title="Sahte Upstream", docs_url=None, redoc_url=None)

#: Kanit icin istek sayaci: yol -> adet
VURUSLAR: dict[str, int] = {}


@app.middleware("http")
async def _sayac(istek: Request, cagri):  # type: ignore[no-untyped-def]
    anahtar = f"{istek.method} {istek.url.path}"
    VURUSLAR[anahtar] = VURUSLAR.get(anahtar, 0) + 1
    return await cagri(istek)


@app.get("/_vuruslar")
async def vuruslar() -> dict[str, int]:
    """Gelen isteklerin ham sayaci."""
    return dict(VURUSLAR)


@app.get("/v1/models")
async def modeller() -> dict[str, object]:
    return {
        "object": "list",
        "data": [
            {"id": "sahte-model-kucuk", "object": "model", "owned_by": "sahte"},
            {"id": "sahte-model-buyuk", "object": "model", "owned_by": "sahte"},
        ],
    }


#: `/models` ucu 401 donen saglayici taklidi: dogrulama yedek yolunu tetikler.
@app.get("/modeller401/v1/models")
async def modeller_401() -> JSONResponse:
    return JSONResponse({"error": {"message": "invalid api key"}}, status_code=401)


@app.post("/modeller401/v1/chat/completions")
async def sohbet_401(istek: Request) -> JSONResponse:
    return await sohbet(istek)


@app.post("/v1/chat/completions")
async def sohbet(istek: Request) -> JSONResponse:
    govde = await istek.json()
    return JSONResponse(
        {
            "id": "chatcmpl-sahte",
            "object": "chat.completion",
            "model": govde.get("model", "bilinmeyen"),
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "pong"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }
    )


@app.get("/api/tags")
async def etiketler() -> dict[str, object]:
    return {"models": [{"name": "sahte-model-kucuk:latest", "model": "sahte-model-kucuk:latest"}]}


@app.post("/api/pull")
async def indir(istek: Request) -> StreamingResponse:
    govde = await istek.json()
    model = str(govde.get("model") or "sahte")

    async def akis() -> AsyncIterator[str]:
        olaylar = [
            {"status": "pulling manifest"},
            {"status": "downloading", "total": 1000, "completed": 250},
            {"status": "downloading", "total": 1000, "completed": 900},
            {"status": "verifying sha256 digest"},
            {"status": "writing manifest"},
            {"status": "removing any unused layers"},
            {"status": "success"},
        ]
        for olay in olaylar:
            yield json.dumps({**olay, "model": model}, ensure_ascii=False) + "\n"

    return StreamingResponse(akis(), media_type="application/x-ndjson")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
