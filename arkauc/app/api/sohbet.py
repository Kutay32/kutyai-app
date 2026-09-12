"""Sohbet uclari: tek yanit, SSE akisi ve konusma gecmisi (spec §7.4)."""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek.ayarlar_db import ayar_oku
from arkauc.app.cekirdek.bagimliliklar import (
    IstemciKimligi,
    gecerli_istemci,
    veritabani_oturumu,
)
from arkauc.app.cekirdek.hatalar import (
    BdmHazirDegil,
    Bulunamadi,
    GecersizIstek,
    KotaAsildi,
    YetkiYok,
)
from arkauc.app.servisler.akış import sohbet_akisi, tahmin_token
from arkauc.app.servisler.kota import kota_kullan, kota_token_ekle
from arkauc.app.servisler.upstream import UstSaglayici
from bdm_konusma_gecmisi import (
    konusma_detayi,
    konusma_olustur,
    konusma_sahibi_mi,
    konusmalari_listele,
    kullanim_yaz,
    maskele_metin,
    mesaj_ekle,
    ust_saglayici_mesajlari,
)
from bdm_listesi import bdm_getir, bdm_slug_getir
from bdm_veritabani.modeller import (
    Bdm,
    BdmDurumu,
    KullanimDurumu,
    Konusma,
    Mesaj,
    MesajRolu,
)

logger = logging.getLogger("kutyai.sohbet")

router = APIRouter(tags=["sohbet"])

KULLANILABILIR_DURUMLAR = (BdmDurumu.hazir, BdmDurumu.calisiyor)
AKIS_BASLIKLARI = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
LISTE_ALANLARI = (
    "id",
    "baslik",
    "bdm_id",
    "bdm_ad",
    "guncellenme",
    "mesaj_sayisi",
    "token_girdi",
    "token_cikti",
)


class SohbetIstegi(BaseModel):
    """Sohbet istegi; `bdm_id` yerine `bdm_slug` kullanilabilir."""

    bdm_id: int | None = None
    bdm_slug: str | None = None
    konusma_id: int | None = None
    mesaj: str = Field(min_length=1)
    sistem_istemi: str | None = None
    sicaklik: float | None = None
    maks_token: int | None = None


class BaslikIstegi(BaseModel):
    baslik: str = Field(min_length=1, max_length=200)


def ust_saglayici() -> UstSaglayici:
    """Varsayilan upstream istemcisi; testler bagimlilik gecersiz kilma ile baglar."""
    return UstSaglayici()


async def _bakim_denetimi(oturum: AsyncSession) -> None:
    """Bakım modu açıkken sohbet uçlarını kapatır (API §9)."""
    if await ayar_oku(oturum, "bakim_modu", False):
        raise BdmHazirDegil("Sistem bakımda.", {"bakim_modu": True})


async def _sistem_istemini_maskele(
    oturum: AsyncSession, sistem_istemi: str | None
) -> str | None:
    """Sistem istemini kayıt ve upstream aynı maskeli metni görecek şekilde maskeler."""
    if not sistem_istemi:
        return sistem_istemi
    return await maskele_metin(oturum, sistem_istemi)


async def _bdm_coz(oturum: AsyncSession, istek: SohbetIstegi, kimlik: IstemciKimligi) -> Bdm:
    if istek.bdm_id is None and not istek.bdm_slug:
        raise GecersizIstek("bdm_id veya bdm_slug zorunludur.", {"alan": "bdm_id"})
    if istek.bdm_id is not None:
        bdm = await bdm_getir(oturum, istek.bdm_id)
    else:
        bdm = await bdm_slug_getir(oturum, istek.bdm_slug or "")
    if bdm.durum not in KULLANILABILIR_DURUMLAR:
        raise BdmHazirDegil(
            "Seçilen model şu anda kullanıma hazır değil.",
            {"bdm_id": bdm.id, "durum": bdm.durum.value},
        )
    izinli = list((kimlik.anahtar.izinli_modeller if kimlik.anahtar else None) or [])
    if izinli and bdm.slug not in izinli and str(bdm.id) not in izinli:
        raise YetkiYok("Bu API anahtarı seçilen model için yetkili değil.")
    return bdm


async def _konusma_coz(
    oturum: AsyncSession, istek: SohbetIstegi, bdm: Bdm, kimlik: IstemciKimligi
) -> Konusma:
    if istek.konusma_id is None:
        return await konusma_olustur(
            oturum,
            bdm_id=bdm.id,
            kullanici_id=kimlik.kullanici_id,
            api_anahtari_id=kimlik.anahtar_id,
            sistem_istemi=await _sistem_istemini_maskele(
                oturum, istek.sistem_istemi or bdm.sistem_istemi
            ),
        )
    konusma = await oturum.get(Konusma, istek.konusma_id)
    if konusma is None or not await konusma_sahibi_mi(
        oturum,
        konusma,
        kullanici_id=kimlik.kullanici_id,
        api_anahtari_id=kimlik.anahtar_id,
    ):
        raise Bulunamadi("Konuşma bulunamadı.", {"konusma_id": istek.konusma_id})
    if konusma.bdm_id != bdm.id:
        raise GecersizIstek(
            "Konuşma farklı bir modele ait.", {"konusma_id": konusma.id, "bdm_id": bdm.id}
        )
    return konusma


async def _konusma_getir(
    oturum: AsyncSession, konusma_id: int, kimlik: IstemciKimligi
) -> Konusma:
    konusma = await oturum.get(Konusma, konusma_id)
    if konusma is None or not await konusma_sahibi_mi(
        oturum,
        konusma,
        kullanici_id=kimlik.kullanici_id,
        api_anahtari_id=kimlik.anahtar_id,
    ):
        raise Bulunamadi("Konuşma bulunamadı.", {"konusma_id": konusma_id})
    return konusma


async def _kota_denetle(oturum: AsyncSession, bdm: Bdm, kimlik: IstemciKimligi) -> None:
    """Kotadan istek rezerve eder; limit doluysa 429 firlatir ve kaydeder."""
    try:
        await kota_kullan(
            oturum,
            kullanici_id=kimlik.kullanici_id,
            api_anahtari_id=kimlik.anahtar_id,
            bdm_id=bdm.id,
        )
    except KotaAsildi:
        await kullanim_yaz(
            oturum,
            bdm_id=bdm.id,
            kullanici_id=kimlik.kullanici_id,
            api_anahtari_id=kimlik.anahtar_id,
            durum=KullanimDurumu.kota_asildi,
        )
        await oturum.commit()
        raise


async def _hatayi_kaydet(
    oturum: AsyncSession, bdm: Bdm, konusma: Konusma, kimlik: IstemciKimligi
) -> None:
    try:
        await kullanim_yaz(
            oturum,
            bdm_id=bdm.id,
            kullanici_id=kimlik.kullanici_id,
            api_anahtari_id=kimlik.anahtar_id,
            konusma_id=konusma.id,
            durum=KullanimDurumu.hata,
        )
        await oturum.commit()
    except Exception as hata:  # pragma: no cover - kayit arizasi
        logger.warning("Hatalı istek kaydedilemedi: %s", hata)


async def _mesajlari_hazirla(
    oturum: AsyncSession, konusma: Konusma, sistem_istemi: str | None
) -> list[dict[str, str]]:
    sistem = sistem_istemi if sistem_istemi is not None else konusma.sistem_istemi
    sistem = await _sistem_istemini_maskele(oturum, sistem)
    mesajlar = await ust_saglayici_mesajlari(oturum, konusma)
    return ([{"role": "system", "content": sistem}] if sistem else []) + mesajlar


def _sicaklik(bdm: Bdm, istenen: float | None) -> float:
    return bdm.sicaklik_varsayilan if istenen is None else float(istenen)


def _maks_token(bdm: Bdm, istenen: int | None) -> int:
    return int(istenen) if istenen else int(bdm.maks_cikti)


def _sohbet_satiri(kayit: dict[str, object]) -> dict[str, object]:
    return {alan: kayit.get(alan) for alan in LISTE_ALANLARI}


@router.post("/sohbet")
async def sohbet(
    istek: SohbetIstegi,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    kimlik: IstemciKimligi = Depends(gecerli_istemci),
    ust: UstSaglayici = Depends(ust_saglayici),
) -> dict[str, object]:
    """Tek yanitli sohbet; upstream hatasi 502 `ust_saglayici_hatasi` dondurur."""
    await _bakim_denetimi(oturum)
    bdm = await _bdm_coz(oturum, istek, kimlik)
    await _kota_denetle(oturum, bdm, kimlik)
    konusma = await _konusma_coz(oturum, istek, bdm, kimlik)

    tahmini_girdi = tahmin_token(istek.mesaj)
    kullanici_mesaji = await mesaj_ekle(
        oturum,
        konusma=konusma,
        rol=MesajRolu.kullanici,
        icerik=istek.mesaj,
        token_sayisi=tahmini_girdi,
    )
    await oturum.commit()

    baslangic = time.perf_counter()
    mesajlar = await _mesajlari_hazirla(oturum, konusma, istek.sistem_istemi)
    try:
        sonuc = await ust.tek_yanit(
            bdm,
            mesajlar,
            sicaklik=_sicaklik(bdm, istek.sicaklik),
            maks_token=_maks_token(bdm, istek.maks_token),
        )
    except Exception:
        await _hatayi_kaydet(oturum, bdm, konusma, kimlik)
        raise

    gecikme_ms = max(0, int((time.perf_counter() - baslangic) * 1000))
    upstream_kullanim = sonuc.get("kullanim") or {}
    icerik = str(sonuc.get("icerik") or "")
    girdi = int(upstream_kullanim.get("girdi") or 0) or tahmini_girdi
    cikti = int(upstream_kullanim.get("cikti") or 0) or tahmin_token(icerik)
    if girdi != tahmini_girdi:
        konusma.token_girdi = max(0, (konusma.token_girdi or 0) + (girdi - tahmini_girdi))
        kullanici_mesaji.token_sayisi = girdi
    asistan_mesaji = await mesaj_ekle(
        oturum,
        konusma=konusma,
        rol=MesajRolu.asistan,
        icerik=icerik,
        token_sayisi=cikti,
        gecikme_ms=gecikme_ms,
        model=bdm.upstream_model,
    )
    await kullanim_yaz(
        oturum,
        bdm_id=bdm.id,
        kullanici_id=kimlik.kullanici_id,
        api_anahtari_id=kimlik.anahtar_id,
        konusma_id=konusma.id,
        girdi_token=girdi,
        cikti_token=cikti,
        gecikme_ms=gecikme_ms,
        durum=KullanimDurumu.basarili,
    )
    await kota_token_ekle(
        oturum,
        kullanici_id=kimlik.kullanici_id,
        api_anahtari_id=kimlik.anahtar_id,
        token=girdi + cikti,
    )
    await oturum.commit()

    return {
        "konusma_id": konusma.id,
        "mesaj_id": asistan_mesaji.id,
        "icerik": icerik,
        "token_girdi": girdi,
        "token_cikti": cikti,
        "gecikme_ms": gecikme_ms,
    }


@router.post("/sohbet/akis")
async def sohbet_akis(
    istek: SohbetIstegi,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    kimlik: IstemciKimligi = Depends(gecerli_istemci),
    ust: UstSaglayici = Depends(ust_saglayici),
) -> Response:
    """SSE akisi: `baslangic`, `parca`*, `kullanim`, `hata`?, `bitti`."""
    await _bakim_denetimi(oturum)
    bdm = await _bdm_coz(oturum, istek, kimlik)
    await _kota_denetle(oturum, bdm, kimlik)
    konusma = await _konusma_coz(oturum, istek, bdm, kimlik)

    kullanici_mesaji: Mesaj = await mesaj_ekle(
        oturum,
        konusma=konusma,
        rol=MesajRolu.kullanici,
        icerik=istek.mesaj,
        token_sayisi=tahmin_token(istek.mesaj),
    )
    await oturum.commit()
    mesajlar = await _mesajlari_hazirla(oturum, konusma, istek.sistem_istemi)

    akis = sohbet_akisi(
        oturum,
        ust=ust,
        bdm=bdm,
        konusma=konusma,
        kullanici_mesaji=kullanici_mesaji,
        mesajlar=mesajlar,
        kullanici_id=kimlik.kullanici_id,
        api_anahtari_id=kimlik.anahtar_id,
        sicaklik=_sicaklik(bdm, istek.sicaklik),
        maks_token=_maks_token(bdm, istek.maks_token),
    )
    return StreamingResponse(
        akis, media_type="text/event-stream", headers=dict(AKIS_BASLIKLARI)
    )


@router.get("/sohbet/konusmalar")
async def konusmalar(
    oturum: AsyncSession = Depends(veritabani_oturumu),
    kimlik: IstemciKimligi = Depends(gecerli_istemci),
) -> dict[str, object]:
    """Istek sahibinin kendi konusmalari."""
    sahiplik: dict[str, int | None] = (
        {"api_anahtari_id": kimlik.anahtar_id}
        if kimlik.anahtar_id is not None
        else {"kullanici_id": kimlik.kullanici_id}
    )
    sonuc = await konusmalari_listele(oturum, **sahiplik)  # type: ignore[arg-type]
    return {
        "toplam": sonuc["toplam"],
        "sayfa": sonuc["sayfa"],
        "boyut": sonuc["boyut"],
        "kayitlar": [_sohbet_satiri(k) for k in sonuc["kayitlar"]],  # type: ignore[union-attr]
    }


@router.get("/sohbet/konusmalar/{konusma_id}")
async def konusma_detay(
    konusma_id: int,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    kimlik: IstemciKimligi = Depends(gecerli_istemci),
) -> dict[str, object]:
    konusma = await _konusma_getir(oturum, konusma_id, kimlik)
    detay = await konusma_detayi(oturum, konusma)
    mesajlar = [
        {
            "id": mesaj["id"],
            "rol": mesaj["rol"],
            "icerik": mesaj["icerik"],
            "token_sayisi": mesaj["token_sayisi"],
            "gecikme_ms": mesaj["gecikme_ms"],
            "olusturulma": mesaj["olusturulma"],
        }
        for mesaj in detay["mesajlar"]  # type: ignore[union-attr]
    ]
    return {
        "id": detay["id"],
        "baslik": detay["baslik"],
        "bdm_id": detay["bdm_id"],
        "olusturulma": detay["olusturulma"],
        "mesajlar": mesajlar,
    }


@router.patch("/sohbet/konusmalar/{konusma_id}")
async def konusma_basligi(
    konusma_id: int,
    govde: BaslikIstegi,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    kimlik: IstemciKimligi = Depends(gecerli_istemci),
) -> dict[str, object]:
    konusma = await _konusma_getir(oturum, konusma_id, kimlik)
    konusma.baslik = govde.baslik
    await oturum.commit()
    return {"id": konusma.id, "baslik": konusma.baslik}


@router.delete("/sohbet/konusmalar/{konusma_id}", status_code=204)
async def konusma_sil(
    konusma_id: int,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    kimlik: IstemciKimligi = Depends(gecerli_istemci),
) -> Response:
    konusma = await _konusma_getir(oturum, konusma_id, kimlik)
    await oturum.delete(konusma)
    await oturum.commit()
    return Response(status_code=204)
