"""BDM hazirlama uclari (spec §7.5): dogrula, cek, manifest, on-kontrol.

Tum uclar personel rollerine (`gecerli_personel()`) kapalidir. GPU gerektiren
saglayicida (vllm, tgi) GPU yoksa `cek` ve `manifest` uclari `503 surucu_yok`
firlatir.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek import guvenlik
from arkauc.app.cekirdek.bagimliliklar import gecerli_personel, veritabani_oturumu
from arkauc.app.cekirdek.denetim import islem_kaydet
from arkauc.app.cekirdek.hatalar import KutyaiHatasi, SurucuYok
from arkauc.app.servisler.konteyner import surucu_al
from bdm_hazırlama_ucu import cekim, dogrulama, manifest
from bdm_hazırlama_ucu.on_kontrol import GPU_UYARI_MESAJI, on_kontrol
from bdm_listesi.katalog import bdm_getir
from bdm_listesi.saglayicilar import saglayici_bilgisi
from bdm_veritabani.modeller import Bdm, Kullanici

router = APIRouter()

_SSE_BASLIKLARI = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
_GIZLI_ORTAM_IPUCLARI = ("TOKEN", "KEY", "SECRET", "SIFRE", "PAROLA")


async def _gpu_denetle(bdm: Bdm) -> None:
    """GPU gerektiren saglayicida GPU yoksa `503 surucu_yok` firlatir."""
    if not saglayici_bilgisi(bdm.saglayici.value).gpu_gerekir:
        return
    try:
        durum = await surucu_al(bdm.saglayici.value, bdm.yerel_mi).durum()
    except KutyaiHatasi:
        raise
    except Exception as hata:  # pragma: no cover - surucu/altyapi arizasi
        raise SurucuYok(
            "Konteyner çalışma zamanı sorgulanamadı. Docker çalışıyor mu?",
            {"saglayici": bdm.saglayici.value},
        ) from hata
    if not durum.gpu_var:
        raise SurucuYok(
            GPU_UYARI_MESAJI,
            {"saglayici": bdm.saglayici.value, "gpu_gerekli": True},
        )


def _cerceve(olay: str, veri: dict[str, Any]) -> str:
    return f"event: {olay}\ndata: {json.dumps(veri, ensure_ascii=False)}\n\n"


async def _sse(olaylar: AsyncIterator[dict[str, Any]]) -> AsyncIterator[str]:
    """Akisi SSE cercevelerine cevirir; hatalar `event: hata` olarak akitilir.

    Uretici ne firlatirsa firlatsin baglanti govdesiz kapanmaz: istisna Turkce
    hata zarfina cevrilir ve ardindan her zaman `event: bitti` gonderilir
    (API.md §9). Istemci kopmasi (`asyncio.CancelledError`) yakalanmaz.
    """
    try:
        async for olay in olaylar:
            yield _cerceve("ilerleme", olay)
    except KutyaiHatasi as hata:
        yield _cerceve("hata", hata.govde())
    except Exception as hata:  # noqa: BLE001 - SSE govdesi yarim kapanmamali
        yield _cerceve("hata", cekim.akis_hatasi(hata).govde())
    yield _cerceve("bitti", {})


def _ortami_maskele(ortam: dict[str, str]) -> dict[str, str]:
    """Gizli anahtar tasiyan ortam degerlerini maskeler (spec §11)."""
    return {
        anahtar: (
            guvenlik.maskele(deger)
            if any(ipucu in anahtar.upper() for ipucu in _GIZLI_ORTAM_IPUCLARI)
            else deger
        )
        for anahtar, deger in ortam.items()
    }


@router.post("/{bdm_id}/dogrula")
async def bdm_dogrula(
    bdm_id: int,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    kullanici: Kullanici = Depends(gecerli_personel()),
) -> dict[str, Any]:
    """Upstream baglantisini ve model listesini dogrular; sonucu denetim izine yazar."""
    bdm = await bdm_getir(oturum, bdm_id)
    sonuc = await dogrulama.dogrula(bdm, oturum=oturum)
    await islem_kaydet(
        oturum,
        "bdm.dogrulandi",
        kullanici_id=kullanici.id,
        hedef_tur="bdm",
        hedef_id=bdm.id,
        ayrinti={
            "basarili": sonuc["basarili"],
            "gecikme_ms": sonuc["gecikme_ms"],
            "model_sayisi": len(sonuc["modeller"]),
        },
    )
    return sonuc


@router.post("/{bdm_id}/cek")
async def bdm_cek(
    bdm_id: int,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    kullanici: Kullanici = Depends(gecerli_personel()),
) -> StreamingResponse:
    """Ollama model indirmesini SSE (`event: ilerleme`, sonunda `event: bitti`) akitir."""
    bdm = await bdm_getir(oturum, bdm_id)
    await _gpu_denetle(bdm)
    cekim.cek_destegi_denetle(bdm)
    return StreamingResponse(
        _sse(cekim.cek_akisi(bdm)),
        media_type="text/event-stream",
        headers=_SSE_BASLIKLARI,
    )


@router.post("/{bdm_id}/manifest")
async def bdm_manifest(
    bdm_id: int,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    kullanici: Kullanici = Depends(gecerli_personel()),
) -> dict[str, Any]:
    """Konteyner manifestini onizler; gizli ortam degerleri maskelenir."""
    bdm = await bdm_getir(oturum, bdm_id)
    await _gpu_denetle(bdm)
    govde = manifest.manifest_uret(bdm)
    govde["ortam"] = _ortami_maskele(govde["ortam"])
    return govde


@router.get("/{bdm_id}/on-kontrol")
async def bdm_on_kontrol(
    bdm_id: int,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    kullanici: Kullanici = Depends(gecerli_personel()),
) -> dict[str, Any]:
    """Docker, GPU, disk ve imaj hazirligini raporlar."""
    bdm = await bdm_getir(oturum, bdm_id)
    return await on_kontrol(bdm)
