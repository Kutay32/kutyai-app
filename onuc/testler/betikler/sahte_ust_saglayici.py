"""Sahte OpenAI-uyumlu upstream: SSE akan sohbet + model listesi.

Amac: `onuc` sohbet arayuzunun (T1.2.1) akisli yanit yolunu GERCEK bir ag
sunucusuna karsi sinamak. Parcalar arasinda kucuk bir gecikme vardir; boylece
metnin canli aktigi ag kaydinda ve ekranda gorulur.

Uclar:
  GET  /v1/models              -> OpenAI model listesi (BDM `upstream_model` burada)
  POST /v1/chat/completions    -> `stream:true` ise SSE parcalari, degilse tek yanit
  GET  /_vuruslar             -> gelen isteklerin sayaci (kanit)

Yanit metni markdown icerir (baslik, kalin, madde listesi, GFM tablosu ve kod
blogu) ki arayuzun markdown + "Kopyala" yolu da dogrulanabilsin.

Calistirma:
  ./.venv/Scripts/python.exe onuc/testler/betikler/sahte_ust_saglayici.py [PORT]
"""

from __future__ import annotations

import asyncio
import json
import sys
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
MODEL_ADI = "sahte-bdm-1"
PARCA_GECIKMESI_SN = 0.04
PARCA_UZUNLUGU = 14

#: Arayuze akan ornek yanit; markdown + kod blogu + GFM tablosu icerir.
YANIT_METNI = """## Yanıt

Bu yanıt **sahte upstream** tarafından üretildi ve `parça` olaylarıyla akıtıldı.

- Akış çerçeveleri sırayla gelir
- Markdown gövdesi canlı yazılır
- Kod bloğu kopyalanabilir

| Alan | Değer |
|---|---|
| Model | sahte-bdm-1 |
| Akış | açık |

```python
def topla(a: int, b: int) -> int:
    return a + b


print(topla(2, 3))
```
"""

app = FastAPI(title="Sahte Ust Saglayici", docs_url=None, redoc_url=None)

#: Kanit icin istek sayaci: "YONTEM yol" -> adet
VURUSLAR: dict[str, int] = {}


@app.middleware("http")
async def _sayac(istek: Request, cagri):  # type: ignore[no-untyped-def]
    anahtar = f"{istek.method} {istek.url.path}"
    VURUSLAR[anahtar] = VURUSLAR.get(anahtar, 0) + 1
    return await cagri(istek)


@app.get("/_vuruslar")
async def vuruslar() -> dict[str, int]:
    """Bu sunucuya gelen isteklerin ham sayaci."""
    return dict(VURUSLAR)


@app.get("/v1/models")
async def modeller() -> dict[str, object]:
    return {
        "object": "list",
        "data": [{"id": MODEL_ADI, "object": "model", "owned_by": "sahte"}],
    }


def _paket(icerik: str) -> str:
    return "data: " + json.dumps(
        {
            "id": "chatcmpl-sahte-akis",
            "object": "chat.completion.chunk",
            "model": MODEL_ADI,
            "choices": [{"index": 0, "delta": {"content": icerik}, "finish_reason": None}],
        },
        ensure_ascii=False,
    ) + "\n\n"


def _kullanim_paketi(girdi: int, cikti: int) -> str:
    return "data: " + json.dumps(
        {
            "id": "chatcmpl-sahte-akis",
            "object": "chat.completion.chunk",
            "model": MODEL_ADI,
            "choices": [],
            "usage": {"prompt_tokens": girdi, "completion_tokens": cikti, "total_tokens": girdi + cikti},
        },
        ensure_ascii=False,
    ) + "\n\n"


async def _akis(girdi_token: int) -> AsyncIterator[str]:
    """Metni kucuk parcalara bolerek SSE cerceveleri uretir."""
    for baslangic in range(0, len(YANIT_METNI), PARCA_UZUNLUGU):
        yield _paket(YANIT_METNI[baslangic : baslangic + PARCA_UZUNLUGU])
        await asyncio.sleep(PARCA_GECIKMESI_SN)
    yield _kullanim_paketi(girdi_token, len(YANIT_METNI) // 4)
    yield "data: [DONE]\n\n"


@app.post("/v1/chat/completions")
async def sohbet(istek: Request):
    """`stream:true` ise SSE parcalari, degilse tek yanit dondurur."""
    govde = await istek.json()
    mesajlar = govde.get("messages") or []
    girdi_token = sum(len(str(mesaj.get("content") or "")) for mesaj in mesajlar) // 4

    if not govde.get("stream"):
        return JSONResponse(
            {
                "id": "chatcmpl-sahte",
                "object": "chat.completion",
                "model": MODEL_ADI,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": YANIT_METNI},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": girdi_token,
                    "completion_tokens": len(YANIT_METNI) // 4,
                    "total_tokens": girdi_token + len(YANIT_METNI) // 4,
                },
            }
        )

    return StreamingResponse(
        _akis(girdi_token),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
