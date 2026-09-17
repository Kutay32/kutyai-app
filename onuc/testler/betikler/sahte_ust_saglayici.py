"""Sahte OpenAI-uyumlu upstream: SSE akan sohbet + model listesi.

Amac: `onuc` sohbet arayuzunun (T1.2.1) akisli yanit yolunu GERCEK bir ag
sunucusuna karsi sinamak. Parcalar arasinda kucuk bir gecikme vardir; boylece
metnin canli aktigi ag kaydinda ve ekranda gorulur.

Uclar:
  GET  /v1/models              -> OpenAI model listesi (BDM `upstream_model` burada)
  POST /v1/chat/completions    -> `stream:true` ise SSE parcalari, degilse tek yanit
  POST /v1/embeddings          -> deterministik (sabit) vektorler; RAG yolu icin
  POST /v1/images/generations  -> 1x1 PNG (`b64_json`); medya gorsel uretimi icin
  POST /v1/audio/speech        -> gecerli WAV baytlari; medya ses uretimi icin
  GET  /_vuruslar             -> gelen isteklerin sayaci (kanit)

Yanit metni markdown icerir (baslik, kalin, madde listesi, GFM tablosu ve kod
blogu) ki arayuzun markdown + "Kopyala" yolu da dogrulanabilsin.

Arac turlari: istek `tools` tasiyorsa ve henuz `rol=tool` mesaji yoksa sunucu
arac cagrisi akan bir tur uretir; ikinci turda normal metin akar. Boylece
`arac_cagrisi`/`arac_sonucu` olaylari ve arayuz kartlari gercek akisla sinanir.

Calistirma:
  ./.venv/Scripts/python.exe onuc/testler/betikler/sahte_ust_saglayici.py [PORT]
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import json
import math
import sys
import wave
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
MODEL_ADI = "sahte-bdm-1"
PARCA_GECIKMESI_SN = 0.04
PARCA_UZUNLUGU = 14

#: Gomme vektoru boyutu; `vektor_parcasi.vektor` ile ayni olmali.
GOMME_BOYUTU = 8

#: 1x1 PNG (kirmizi); imza baytlari asagida dogrulanir.
PNG_1X1_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
    "z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg=="
)

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


def _arac_paketi(ad: str, cagri_id: str = "cagri_sahte_1") -> str:
    """Tek parcalik `tool_calls` deltasi (argumanlar JSON dizesi olarak)."""
    argumanlar = json.dumps({"ifade": "2+2"} if ad == "hesap_makinesi" else {})
    return "data: " + json.dumps(
        {
            "id": "chatcmpl-sahte-akis",
            "object": "chat.completion.chunk",
            "model": MODEL_ADI,
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "tool_calls": [
                            {
                                "index": 0,
                                "id": cagri_id,
                                "type": "function",
                                "function": {"name": ad, "arguments": argumanlar},
                            }
                        ]
                    },
                    "finish_reason": None,
                }
            ],
        },
        ensure_ascii=False,
    ) + "\n\n"


def _bitis_paketi() -> str:
    return "data: " + json.dumps(
        {
            "id": "chatcmpl-sahte-akis",
            "object": "chat.completion.chunk",
            "model": MODEL_ADI,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}],
        },
        ensure_ascii=False,
    ) + "\n\n"


async def _arac_akisi(ad: str) -> AsyncIterator[str]:
    """Arac cagrisi isteyen tur: tek delta + bitis."""
    yield _arac_paketi(ad)
    await asyncio.sleep(PARCA_GECIKMESI_SN)
    yield _bitis_paketi()
    yield "data: [DONE]\n\n"


def _gomme_vektoru(metin: str) -> list[float]:
    """Deterministik vektor: ilk boyut sabit, kalanlar metin ozetinden.

    Sabit buyuk boyut sayesinde sorgu ile belge parcasi arasindaki kosinus
    benzerligi yuksek cikar; RAG yolu (parcalama -> gomme -> kosinus arama)
    gercek ag uzerinden sinanabilir.
    """
    ozet = hashlib.sha256(metin.encode("utf-8")).digest()
    ham = [1.0] + [((ozet[sira] / 255.0) - 0.5) * 0.2 for sira in range(GOMME_BOYUTU - 1)]
    uzunluk = math.sqrt(sum(deger * deger for deger in ham)) or 1.0
    return [round(deger / uzunluk, 6) for deger in ham]


def _sessiz_wav() -> bytes:
    """0,2 sn sessiz WAV; oynatici gecerli bir kayit yukleyebilsin."""
    tampon = io.BytesIO()
    with wave.open(tampon, "wb") as dosya:
        dosya.setnchannels(1)
        dosya.setsampwidth(1)
        dosya.setframerate(8000)
        dosya.writeframes(b"\x80" * 1600)
    return tampon.getvalue()


SES_BAYTLARI = _sessiz_wav()
if not base64.b64decode(PNG_1X1_B64).startswith(b"\x89PNG\r\n\x1a\n"):  # pragma: no cover
    raise SystemExit("PNG_1X1_B64 gecerli bir PNG degil")


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


@app.post("/v1/embeddings")
async def gommeler(istek: Request) -> dict[str, object]:
    """`input` tek metin ya da liste olabilir; her girdi icin vektor doner."""
    govde = await istek.json()
    girdiler = govde.get("input")
    metinler = [girdiler] if isinstance(girdiler, str) else list(girdiler or [])
    return {
        "object": "list",
        "model": govde.get("model") or MODEL_ADI,
        "data": [
            {"object": "embedding", "index": sira, "embedding": _gomme_vektoru(str(metin))}
            for sira, metin in enumerate(metinler)
        ],
        "usage": {"prompt_tokens": 0, "total_tokens": 0},
    }


@app.post("/v1/images/generations")
async def gorsel_uret(istek: Request) -> dict[str, object]:
    """1x1 PNG doner; `n` kadar kayit uretir."""
    govde = await istek.json()
    adet = max(1, int(govde.get("n") or 1))
    return {"created": 0, "data": [{"b64_json": PNG_1X1_B64} for _ in range(adet)]}


@app.post("/v1/audio/speech")
async def ses_uret(istek: Request) -> Response:
    """Gecerli WAV baytlari doner (istenen bicimden bagimsiz, test kolayligi)."""
    await istek.body()
    return Response(content=SES_BAYTLARI, media_type="audio/wav")


@app.post("/v1/chat/completions")
async def sohbet(istek: Request):
    """`stream:true` ise SSE parcalari, degilse tek yanit dondurur."""
    govde = await istek.json()
    mesajlar = govde.get("messages") or []
    girdi_token = sum(len(str(mesaj.get("content") or "")) for mesaj in mesajlar) // 4

    araclar = govde.get("tools") or []
    arac_sonucu_geldi = any(mesaj.get("role") == "tool" for mesaj in mesajlar)
    if govde.get("stream") and araclar and not arac_sonucu_geldi:
        ad = str(((araclar[0] or {}).get("function") or {}).get("name") or "")
        return StreamingResponse(
            _arac_akisi(ad),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

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
