"""Saglayici yetenek matrisi (spec §7.3).

Hangi saglayicinin akis destekledigi, GPU gerektirdigi, hangi konteyner
imajini kullandigi burada tek yerde tanimlanir.
"""

from __future__ import annotations

from dataclasses import dataclass

from arkauc.app.cekirdek.hatalar import GecersizIstek


@dataclass(frozen=True, slots=True)
class SaglayiciBilgisi:
    ad: str
    gorunen_ad: str
    yerel: bool
    gpu_gerekir: bool
    akis_destegi: bool
    api_anahtari_gerekir: bool
    varsayilan_temel_url: str
    varsayilan_baglam: int
    varsayilan_maks_cikti: int
    konteyner_image: str | None = None
    varsayilan_port: int | None = None
    aciklama: str = ""


SAGLAYICILAR: dict[str, SaglayiciBilgisi] = {
    "openai": SaglayiciBilgisi(
        ad="openai",
        gorunen_ad="OpenAI",
        yerel=False,
        gpu_gerekir=False,
        akis_destegi=True,
        api_anahtari_gerekir=True,
        varsayilan_temel_url="https://api.openai.com/v1",
        varsayilan_baglam=128000,
        varsayilan_maks_cikti=4096,
        aciklama="OpenAI genel amaçlı modeller.",
    ),
    "azure": SaglayiciBilgisi(
        ad="azure",
        gorunen_ad="Azure OpenAI",
        yerel=False,
        gpu_gerekir=False,
        akis_destegi=True,
        api_anahtari_gerekir=True,
        varsayilan_temel_url="",
        varsayilan_baglam=128000,
        varsayilan_maks_cikti=4096,
        aciklama="Azure uzerinde barindirilan OpenAI modelleri.",
    ),
    "openrouter": SaglayiciBilgisi(
        ad="openrouter",
        gorunen_ad="OpenRouter",
        yerel=False,
        gpu_gerekir=False,
        akis_destegi=True,
        api_anahtari_gerekir=True,
        varsayilan_temel_url="https://openrouter.ai/api/v1",
        varsayilan_baglam=128000,
        varsayilan_maks_cikti=4096,
        aciklama="Tek anahtarla coklu saglayici erisimi.",
    ),
    "ollama": SaglayiciBilgisi(
        ad="ollama",
        gorunen_ad="Ollama (yerel)",
        yerel=True,
        gpu_gerekir=False,
        akis_destegi=True,
        api_anahtari_gerekir=False,
        varsayilan_temel_url="http://localhost:11434/v1",
        varsayilan_baglam=8192,
        varsayilan_maks_cikti=2048,
        konteyner_image="ollama/ollama:latest",
        varsayilan_port=11434,
        aciklama="CPU veya GPU uzerinde yerel model calistirir.",
    ),
    "vllm": SaglayiciBilgisi(
        ad="vllm",
        gorunen_ad="vLLM (yerel)",
        yerel=True,
        gpu_gerekir=True,
        akis_destegi=True,
        api_anahtari_gerekir=False,
        varsayilan_temel_url="http://localhost:8000/v1",
        varsayilan_baglam=32768,
        varsayilan_maks_cikti=4096,
        konteyner_image="vllm/vllm-openai:latest",
        varsayilan_port=8000,
        aciklama="GPU uzerinde yuksek verimli cikarim.",
    ),
    "tgi": SaglayiciBilgisi(
        ad="tgi",
        gorunen_ad="TGI (yerel)",
        yerel=True,
        gpu_gerekir=True,
        akis_destegi=True,
        api_anahtari_gerekir=False,
        varsayilan_temel_url="http://localhost:8080/v1",
        varsayilan_baglam=16384,
        varsayilan_maks_cikti=4096,
        konteyner_image="ghcr.io/huggingface/text-generation-inference:latest",
        varsayilan_port=8080,
        aciklama="HuggingFace Text Generation Inference.",
    ),
    "ozel": SaglayiciBilgisi(
        ad="ozel",
        gorunen_ad="Özel (OpenAI uyumlu)",
        yerel=False,
        gpu_gerekir=False,
        akis_destegi=True,
        api_anahtari_gerekir=False,
        varsayilan_temel_url="",
        varsayilan_baglam=8192,
        varsayilan_maks_cikti=2048,
        aciklama="OpenAI uyumlu herhangi bir adres.",
    ),
}

YEREL_SAGLAYICILAR = frozenset({"ollama", "vllm", "tgi"})
GPU_GEREKEN_SAGLAYICILAR = frozenset({"vllm", "tgi"})


def saglayici_bilgisi(saglayici: str) -> SaglayiciBilgisi:
    deger = str(saglayici).strip().lower()
    bilgi = SAGLAYICILAR.get(deger)
    if bilgi is None:
        raise GecersizIstek(
            f"Bilinmeyen sağlayıcı: {saglayici}",
            {"gecerli_saglayicilar": sorted(SAGLAYICILAR)},
        )
    return bilgi


def saglayici_listesi() -> list[dict[str, object]]:
    return [
        {
            "ad": bilgi.ad,
            "gorunen_ad": bilgi.gorunen_ad,
            "yerel": bilgi.yerel,
            "gpu_gerekir": bilgi.gpu_gerekir,
            "akis_destegi": bilgi.akis_destegi,
            "api_anahtari_gerekir": bilgi.api_anahtari_gerekir,
            "varsayilan_temel_url": bilgi.varsayilan_temel_url,
            "varsayilan_port": bilgi.varsayilan_port,
            "konteyner_image": bilgi.konteyner_image,
            "aciklama": bilgi.aciklama,
        }
        for bilgi in SAGLAYICILAR.values()
    ]
