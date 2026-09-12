"""Konteyner manifesti uretimi (spec §7.5, §10, §4.5).

Uzak saglayicilar (openai, azure, openrouter, ozel) icin manifest uretilmez;
konteynerde calisan yerel saglayicilar (ollama, vllm, tgi) icin imaj, komut,
port, GPU bayragi, kaba bellek tahmini, ortam degiskenleri, birimler ve HTTP
saglik sondasi adresi (`saglik_url`) dondurulur. vllm/tgi agirliklarini
host'taki HuggingFace onbelleginden okur: onbellek dizini konteynere
`birimler` ile baglanir ve `HF_HOME` ayni yola isaret eder.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from arkauc.app.cekirdek import guvenlik
from arkauc.app.cekirdek.ayarlar import ayarlar
from arkauc.app.cekirdek.hatalar import GecersizIstek
from bdm_listesi.saglayicilar import saglayici_bilgisi
from bdm_veritabani.modeller import Bdm, Saglayici

logger = logging.getLogger("kutyai.hazirlama")

VARSAYILAN_PORT = 8000
# HuggingFace onbelleginin konteyner icindeki yolu (bkz. `birimler`, `HF_HOME`).
HF_KONTEYNER_DIZINI = "/root/.cache/huggingface"
# Konteyner HTTP saglik sondasi yollari; Docker surucusu bu adresi
# `kutyai.saglik_url` etiketi olarak yazar (spec §10).
_SAGLIK_YOLLARI: dict[str, str] = {
    "vllm": "/health",
    "tgi": "/health",
    "ollama": "/api/tags",
}
# Model adindaki parametre sayisi: `7B`, `72b`, `1.5B`.
_PARAMETRE_DESENI = re.compile(r"(\d+(?:[.,]\d+)?)\s*[bB](?![A-Za-z0-9])")
# fp16 agirliklar icin parametre basina bellek (GB).
_GB_BASI_PARAMETRE = 2.0


def _port(bdm: Bdm, varsayilan: int | None) -> int:
    ham = (bdm.konteyner or {}).get("port")
    try:
        if ham:
            return int(ham)
    except (TypeError, ValueError):  # pragma: no cover - bozuk konteyner kaydi
        logger.warning("BDM %s icin gecersiz port degeri: %r", bdm.id, ham)
    return int(varsayilan or VARSAYILAN_PORT)


def bellek_tahmini(bdm: Bdm) -> float:
    """Kaba bellek (GB) tahmini.

    Model adindan parametre sayisi (orn. `7B`, `72b`) cikarilabiliyorsa fp16
    agirlik varsayimiyla `parametre_milyar x 2` GB; cikarilamiyorsa baglam
    penceresine dayali kaba deger `baglam_penceresi / 1024 x 0.5` GB doner.
    Alt sinir 0.5 GB'dir; deger gercek olcume degil on kontrol icin kaba bir
    buyukluk mertebesine karsilik gelir.
    """
    eslesme = _PARAMETRE_DESENI.search(bdm.upstream_model or "")
    if eslesme is not None:
        milyar = float(eslesme.group(1).replace(",", "."))
        return max(0.5, round(milyar * _GB_BASI_PARAMETRE, 1))
    return max(0.5, round(bdm.baglam_penceresi / 1024 * 0.5, 1))


def _komut(bdm: Bdm, port: int) -> list[str]:
    if bdm.saglayici is Saglayici.vllm:
        return ["vllm", "serve", bdm.upstream_model, "--port", str(port)]
    if bdm.saglayici is Saglayici.tgi:
        return [
            "text-generation-inference",
            "--model-id",
            bdm.upstream_model,
            "--port",
            str(port),
        ]
    return ["ollama", "serve"]


def _ortam(bdm: Bdm, port: int) -> dict[str, str]:
    """Konteyner ortam degiskenleri.

    Deger gizli anahtar icerebilir (gated modeller icin `HF_TOKEN`); HTTP
    katmani bu degerleri maskeler. HuggingFace kullanan konteynerlerde
    `HF_HOME` onbellek dizinine isaret eder (bkz. `birimler`).
    """
    if bdm.saglayici is Saglayici.ollama:
        return {"OLLAMA_HOST": f"0.0.0.0:{port}"}
    ortam = {"HF_HOME": HF_KONTEYNER_DIZINI}
    if not bdm.api_anahtari_sifreli:
        return ortam
    try:
        anahtar = guvenlik.coz(bdm.api_anahtari_sifreli)
    except Exception:  # pragma: no cover - bozuk sifreli deger
        logger.warning("BDM %s icin upstream anahtari cozulemedi.", bdm.id)
        return ortam
    if anahtar:
        ortam["HF_TOKEN"] = anahtar
    return ortam


def saglik_url(bdm: Bdm, port: int) -> str:
    """Konteyner HTTP saglik sondasi adresi; bilinmeyen saglayicida bos dize.

    Konteyner portu host'a ayni numarayla eslenir (Docker surucusu), bu yuzden
    adres `localhost:{port}` uzerinden kurulur.
    """
    yol = _SAGLIK_YOLLARI.get(bdm.saglayici.value, "")
    return f"http://localhost:{port}{yol}" if yol else ""


def birimler(bdm: Bdm) -> list[dict[str, str]]:
    """Konteynere baglanacak birimler (`[{"kaynak", "hedef", "mod"}]`).

    vllm/tgi agirliklari host'taki HuggingFace onbelleginden okur; onbellek
    dizini konteynerde `HF_HOME` ile ayni yola baglanir. Baska saglayicilarda
    liste bostur; sozlesme geregi alan her zaman liste olarak doner.
    """
    if bdm.saglayici not in (Saglayici.vllm, Saglayici.tgi):
        return []
    return [
        {
            "kaynak": ayarlar.hf_onbellek_yolu(),
            "hedef": HF_KONTEYNER_DIZINI,
            "mod": "rw",
        }
    ]


def manifest_uret(bdm: Bdm) -> dict[str, Any]:
    """Saglayiciya uygun konteyner manifestini uretir."""
    bilgi = saglayici_bilgisi(bdm.saglayici.value)
    if bilgi.konteyner_image is None:
        raise GecersizIstek(
            "Bu sağlayıcı uzak sunucuda çalışır; konteyner manifesti üretilemez.",
            {"saglayici": bdm.saglayici.value},
        )
    port = _port(bdm, bilgi.varsayilan_port)
    return {
        "image": bilgi.konteyner_image,
        "komut": _komut(bdm, port),
        "port": port,
        "gpu": bilgi.gpu_gerekir,
        "bellek_gb": bellek_tahmini(bdm),
        "ortam": _ortam(bdm, port),
        "birimler": birimler(bdm),
        "saglik_url": saglik_url(bdm, port),
    }
