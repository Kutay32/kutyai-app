"""Model indirme akisi (spec §7.5).

Ollama yerel API'sinin `POST {temel}/api/pull` NDJSON akisi `{yuzde, mesaj}`
olaylarina cevrilir; `temel_url` icindeki `/v1` eki kirpilir. vllm/tgi (ve
`upstream_model` HuggingFace depo kimligi olan `ozel`) icin agirliklar
`huggingface_hub.snapshot_download` ile `ayarlar.hf_onbellek_yolu()` dizinine
indirilir; bu dizin manifest uzerinden konteynere baglanir. Diger
saglayicilarda indirme desteklenmez: `GecersizIstek` firlatilir.

Indirme asamalari sabit yuzdelerle bildirilir (arac `total=0` ile acildigi icin
gercek bir dosya yuzdesi yoktur): hazirlik 5, indirme 60, dogrulama 90, bitti 100.
Akis sirasinda olusan hatalar `akis_hatasi`/`_hf_hatasina_cevir` ile Turkce hata
zarfina cevrilir; HTTP katmani (`uc._sse`) bunu `event: hata` olarak akitir.
"""

from __future__ import annotations

import asyncio
import json
import logging
import pathlib
import re
from collections.abc import AsyncIterator
from typing import Any

import httpx
from huggingface_hub import snapshot_download
from tqdm.auto import tqdm

from arkauc.app.cekirdek.ayarlar import ayarlar
from arkauc.app.cekirdek.hatalar import (
    GecersizIstek,
    KutyaiHatasi,
    SunucuHatasi,
    UstSaglayiciHatasi,
)
from bdm_hazırlama_ucu.dogrulama import BAGLANTI_MESAJI, anahtari_coz
from bdm_veritabani.modeller import Bdm, Saglayici

logger = logging.getLogger("kutyai.hazirlama")

ZAMAN_ASIMI_SN = 30.0
DESTEKLENMEYEN_MESAJ = "Bu sağlayıcı için model indirme desteklenmiyor."
MODEL_YOK_MESAJI = "İndirilecek model adı tanımlı değil."

# Adres/tasima kaynakli istisnalar: `httpx.InvalidURL`, `httpx.UnsupportedProtocol`
# disinda IDNA hatalari (`UnicodeError`) ve bozuk adres degerleri (`ValueError`)
# da `httpx.HTTPError` hiyerarsisinde degildir; ayrica yakalanmalari gerekir.
AG_HATALARI: tuple[type[Exception], ...] = (
    httpx.InvalidURL,
    httpx.UnsupportedProtocol,
    httpx.HTTPError,
    UnicodeError,
    ValueError,
)

# HuggingFace snapshot indirmesi destekleyen saglayicilar (spec §7.5).
HF_SAGLAYICILARI = (Saglayici.vllm, Saglayici.tgi)
# `ozel` saglayicida model adi "sahip/depo" bicimindeyse HF deposu sayilir.
HF_DEPO_DESENI = re.compile(r"^[\w.-]+/[\w.-]+$")
# Snapshot asamalari; `total=0` acilan araclar gercek yuzde vermedigi icin
# uydurma dosya yuzdesi yerine asama yuzdesi bildirilir.
ASAMA_HAZIRLIK = 5
ASAMA_INDIRME = 60
ASAMA_DOGRULAMA = 90
ASAMA_BITTI = 100

HF_ERISIM_MESAJI = (
    "Model deposuna erişim reddedildi. HF_TOKEN değerini ve depo lisansını kontrol edin."
)
HF_BULUNAMADI_MESAJI = "Model deposu bulunamadı. Depo kimliğini kontrol edin."
HF_BAGLANTI_MESAJI = (
    "Model deposuna erişilemedi; ağ bağlantısını ve HF_TOKEN ayarını kontrol edin."
)
HF_ONBELLEK_MESAJI = "Model indirilemedi; önbellek dizinine yazılamadı."
HF_BOS_MESAJI = "Snapshot indirildi ancak önbellek dizini boş görünüyor."

# Ollama durum metinlerinin Turkce karsiliklari.
DURUM_CEVIRILERI: dict[str, str] = {
    "pulling manifest": "Manifest indiriliyor",
    "downloading": "Model indiriliyor",
    "verifying sha256 digest": "Bütünlük imzası doğrulanıyor",
    "writing manifest": "Manifest yazılıyor",
    "removing any unused layers": "Kullanılmayan katmanlar temizleniyor",
    "success": "Model hazır",
}


def varsayilan_tasima() -> httpx.AsyncBaseTransport | None:
    """Varsayilan ag tasimasi; testler sahte tasima enjekte etmek icin ezer."""
    return None


def akis_hatasi(hata: BaseException) -> KutyaiHatasi:
    """Indirme akisini kesen istisnayi Turkce hata zarfina cevirir.

    Tasima/adres kaynakli hatalar saglayici hatasi olarak bildirilir; beklenmeyen
    hatalar sunucu hatasina duser. Cagiran taraf sonucu `event: hata` olarak akitir.
    """
    if isinstance(hata, AG_HATALARI):
        logger.warning("Model indirme akisi kesildi: %s", hata)
        return UstSaglayiciHatasi(
            BAGLANTI_MESAJI, {"neden": type(hata).__name__}
        )
    logger.exception("Model indirme akisinda beklenmeyen hata.", exc_info=hata)
    return SunucuHatasi()


class _SessizTqdm(tqdm):
    """HF'nin kendi ilerleme cubugunu susturur; ilerleme `event: ilerleme` ile akar."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["disable"] = True
        super().__init__(*args, **kwargs)


def hf_indirmesi_mi(bdm: Bdm) -> bool:
    """Model agirliklari HuggingFace snapshot'i olarak mi indirilecek?"""
    if bdm.saglayici in HF_SAGLAYICILARI:
        return True
    return bdm.saglayici is Saglayici.ozel and bool(
        HF_DEPO_DESENI.match((bdm.upstream_model or "").strip())
    )


def cek_destegi_denetle(bdm: Bdm) -> None:
    """Saglayicinin model indirmeyi destekleyip desteklemedigini denetler."""
    if bdm.saglayici is not Saglayici.ollama and not hf_indirmesi_mi(bdm):
        raise GecersizIstek(
            DESTEKLENMEYEN_MESAJ, {"saglayici": bdm.saglayici.value}
        )
    if not (bdm.upstream_model or "").strip():
        raise GecersizIstek(MODEL_YOK_MESAJI)


def _snapshot_indir(repo_id: str, hedef: str, anahtar: str) -> str:
    """`snapshot_download` sarmalayicisi; testler bunu ezerek aga cikmaz."""
    return str(
        snapshot_download(
            repo_id,
            cache_dir=hedef,
            token=anahtar or None,
            tqdm_class=_SessizTqdm,
        )
    )


def _hf_hatasina_cevir(hata: BaseException) -> UstSaglayiciHatasi:
    """HuggingFace indirme hatasini Turkce saglayici hatasina cevirir."""
    durum = getattr(getattr(hata, "response", None), "status_code", None)
    if durum in (401, 403):
        mesaj = HF_ERISIM_MESAJI
    elif durum == 404:
        mesaj = HF_BULUNAMADI_MESAJI
    elif durum:
        mesaj = (
            f"Model deposuna erişilemedi ({durum}). "
            "Depo adresini ve anahtarı kontrol edin."
        )
    elif isinstance(hata, (ConnectionError, TimeoutError, httpx.HTTPError)):
        mesaj = HF_BAGLANTI_MESAJI
    elif isinstance(hata, OSError):
        mesaj = HF_ONBELLEK_MESAJI
    else:
        mesaj = HF_BAGLANTI_MESAJI
    logger.warning("HuggingFace snapshot indirilemedi: %s", hata)
    return UstSaglayiciHatasi(mesaj, {"neden": type(hata).__name__})


async def _hf_akisi(bdm: Bdm) -> AsyncIterator[dict[str, Any]]:
    """HuggingFace snapshot'ini onbellek dizinine indirir ve asamalari akitir."""
    depo = (bdm.upstream_model or "").strip()
    hedef = pathlib.Path(ayarlar.hf_onbellek_yolu())
    yield {"yuzde": ASAMA_HAZIRLIK, "mesaj": "HuggingFace önbelleği hazırlanıyor"}
    try:
        await asyncio.to_thread(hedef.mkdir, parents=True, exist_ok=True)
    except OSError as hata:
        raise _hf_hatasina_cevir(hata) from hata

    yield {"yuzde": ASAMA_INDIRME, "mesaj": "Snapshot indiriliyor"}
    try:
        yol = await asyncio.to_thread(_snapshot_indir, depo, str(hedef), anahtari_coz(bdm))
    except Exception as hata:
        raise _hf_hatasina_cevir(hata) from hata

    yield {"yuzde": ASAMA_DOGRULAMA, "mesaj": "Snapshot doğrulanıyor"}
    inen = pathlib.Path(yol)
    if not inen.is_dir() or not any(inen.iterdir()):
        logger.warning("BDM %s icin snapshot dizini bos: %s", bdm.id, yol)
        raise UstSaglayiciHatasi(HF_BOS_MESAJI, {"depo": depo})

    yield {"yuzde": ASAMA_BITTI, "mesaj": "Model hazır"}


def ollama_temeli(temel_url: str) -> str:
    """`/v1` ile biten OpenAI uyumlu adresten Ollama kokunu uretir."""
    temel = (temel_url or "").rstrip("/")
    if temel.endswith("/v1"):
        temel = temel[:-3].rstrip("/")
    return temel


def _olaya_cevir(satir: str, onceki_yuzde: int) -> dict[str, Any] | None:
    satir = satir.strip()
    if not satir:
        return None
    try:
        kayit = json.loads(satir)
    except ValueError:
        logger.debug("Ollama akisinda cozulemeyen satir: %s", satir[:200])
        return None
    if not isinstance(kayit, dict):
        return None

    ham_durum = str(kayit.get("status") or "").strip()
    toplam = kayit.get("total")
    tamamlanan = kayit.get("completed")
    if isinstance(toplam, int) and toplam > 0 and isinstance(tamamlanan, int):
        yuzde = max(0, min(100, int(tamamlanan / toplam * 100)))
    elif ham_durum == "success":
        yuzde = 100
    else:
        yuzde = onceki_yuzde

    mesaj = DURUM_CEVIRILERI.get(ham_durum, ham_durum or "Model indiriliyor")
    return {"yuzde": yuzde, "mesaj": mesaj}


async def cek_akisi(
    bdm: Bdm, *, tasima: httpx.AsyncBaseTransport | None = None
) -> AsyncIterator[dict[str, Any]]:
    """Model indirmesini `{yuzde, mesaj}` olaylari olarak akitir.

    Ollama'da `/api/pull` NDJSON akisi, vllm/tgi (`ozel` dahil) icin HuggingFace
    snapshot indirmesi kullanilir.
    """
    cek_destegi_denetle(bdm)
    if hf_indirmesi_mi(bdm):
        async for olay in _hf_akisi(bdm):
            yield olay
        return

    temel = ollama_temeli(bdm.temel_url)
    if not temel:
        raise GecersizIstek("Model adresi tanımlı değil. Lütfen temel adresi girin.")

    etkin_tasima = tasima if tasima is not None else varsayilan_tasima()
    async with httpx.AsyncClient(transport=etkin_tasima, timeout=ZAMAN_ASIMI_SN) as istemci:
        async with istemci.stream(
            "POST",
            f"{temel}/api/pull",
            json={"model": bdm.upstream_model, "stream": True},
        ) as yanit:
            if yanit.status_code != 200:
                raise UstSaglayiciHatasi(
                    f"Model indirme isteği {yanit.status_code} koduyla reddedildi.",
                    {"saglayici": bdm.saglayici.value, "model": bdm.upstream_model},
                )
            yuzde = 0
            async for satir in yanit.aiter_lines():
                olay = _olaya_cevir(satir, yuzde)
                if olay is None:
                    continue
                yuzde = olay["yuzde"]
                yield olay
