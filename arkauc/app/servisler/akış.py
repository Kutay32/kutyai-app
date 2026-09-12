"""SSE cerceveleme ve sohbet akisi (spec §7.4, §6).

Olay sirasi: `baslangic` → `parca`* → `kullanim` → `bitti`. Hata durumunda
`hata` olayi hata zarfini tasir ve ardindan her zaman `bitti` gonderilir.
Istemci koptugunda upstream istegi iptal edilir ve kismi yanit kaydedilmez;
gunluk istek kotasi akis baslamadan rezerve edildigi icin rezervasyon kalir,
yanit sonunda yalnizca token sayaci artar.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek.hatalar import GecersizIstek, KutyaiHatasi, SunucuHatasi
from arkauc.app.cekirdek.i18n import mesaj
from arkauc.app.servisler.arac import arac_calistir, arac_tanimi
from arkauc.app.servisler.kota import kota_token_ekle
from arkauc.app.servisler.upstream import UstSaglayici
from bdm_konusma_gecmisi import kullanim_yaz, mesaj_ekle
from bdm_veritabani.modeller import (
    Arac,
    Bdm,
    KullanimDurumu,
    Konusma,
    Mesaj,
    MesajRolu,
)

logger = logging.getLogger("kutyai.akis")

TOKEN_BOLEN = 4
ARAC_OZET_SINIRI = 200


def tahmin_token(metin: str) -> int:
    """Upstream `usage` yoksa kaba token tahmini (spec §7.4)."""
    return len(metin or "") // TOKEN_BOLEN


def sse_olay(event: str, veri: object) -> str:
    """SSE cercevesi uretir; sozlukler JSON olarak serilestirilir."""
    govde = veri if isinstance(veri, str) else json.dumps(veri, ensure_ascii=False)
    return f"event: {event}\ndata: {govde}\n\n"


def tur_siniri_asildi(maks_tur: int) -> GecersizIstek:
    """Araç turu sınırı aşıldığında dönen `400 arac_tur_siniri` hatası."""
    return GecersizIstek("arac_tur_siniri", {"maks_tur": maks_tur}, kod="arac_tur_siniri")


def arac_tanimlari(araclar: list[Arac] | None) -> list[dict[str, Any]] | None:
    """Upstream `tools` alanı için araç tanımları; araç yoksa `None`."""
    return [arac_tanimi(arac) for arac in araclar] if araclar else None


def _ozet(veri: object) -> str:
    """Araç sonucundan kısa, tek satırlık özet üretir."""
    if isinstance(veri, str):
        metin = veri
    else:
        metin = json.dumps(veri, ensure_ascii=False, default=str)
    return " ".join(metin.split())[:ARAC_OZET_SINIRI]


async def araclari_yurut(
    oturum: AsyncSession,
    *,
    org_id: int,
    araclar: list[Arac],
    cagrilar: list[dict[str, Any]],
    konusma: Konusma,
    tetikleyen_mesaj_id: int | None,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Modelin araç çağrılarını çalıştırır.

    Dönen ilk liste modele geri verilecek `assistant`/`tool` mesajlarıdır
    (konuşma geçmişine yazılan `rol=arac` kaydı bunları içermez; çünkü geçmiş
    yalnız kullanıcı/asistan mesajlarını taşır). İkincisi kullanıcıya dönen
    `[{ad, durum}]` özetidir.
    """
    adlar = {arac.slug: arac for arac in araclar}
    cagri_mesajlari: list[dict[str, Any]] = []
    sonuc_mesajlari: list[dict[str, Any]] = []
    ozetler: list[dict[str, str]] = []

    for cagri in cagrilar:
        ad = str(cagri.get("ad") or "")
        argumanlar = cagri.get("argumanlar") or {}
        arac = adlar.get(ad)
        baslangic = time.perf_counter()
        if arac is None:
            gerekce = mesaj("arac_bulunamadi")
            sonuc: dict[str, Any] = {
                "durum": "hata",
                "sonuc": {"hata": gerekce},
                "hata": gerekce,
                "gecikme_ms": 0,
            }
        else:
            try:
                sonuc = await arac_calistir(
                    oturum,
                    org_id=org_id,
                    arac=arac,
                    argumanlar=argumanlar,
                    konusma_id=konusma.id,
                    mesaj_id=tetikleyen_mesaj_id,
                )
            except GecersizIstek as hata:
                gerekce = str(hata.govde()["hata"]["mesaj"])
                sonuc = {
                    "durum": "hata",
                    "sonuc": {"hata": gerekce},
                    "hata": gerekce,
                    "gecikme_ms": _gecen_ms(baslangic),
                }
        basarili = sonuc.get("durum") == "basarili"
        durum = "basarili" if basarili else "hata"
        await mesaj_ekle(
            oturum,
            konusma=konusma,
            rol=MesajRolu.arac,
            icerik=json.dumps(
                {"ad": ad, "durum": durum, "sonuc": sonuc.get("sonuc"), "hata": sonuc.get("hata")},
                ensure_ascii=False,
                default=str,
            ),
        )
        cagri_mesajlari.append(
            {
                "id": str(cagri.get("id") or f"cagri_{ad}"),
                "type": "function",
                "function": {"name": ad, "arguments": json.dumps(argumanlar, ensure_ascii=False)},
            }
        )
        sonuc_mesajlari.append(
            {
                "role": "tool",
                "tool_call_id": str(cagri.get("id") or f"cagri_{ad}"),
                "content": json.dumps(
                    {"durum": durum, "sonuc": sonuc.get("sonuc"), "hata": sonuc.get("hata")},
                    ensure_ascii=False,
                    default=str,
                ),
            }
        )
        ozetler.append({"ad": ad, "durum": durum})

    await oturum.commit()
    modele: list[dict[str, Any]] = []
    if cagri_mesajlari:
        modele.append({"role": "assistant", "content": None, "tool_calls": cagri_mesajlari})
        modele.extend(sonuc_mesajlari)
    return modele, ozetler


async def sohbet_akisi(
    oturum: AsyncSession,
    *,
    ust: UstSaglayici,
    bdm: Bdm,
    konusma: Konusma,
    kullanici_mesaji: Mesaj,
    mesajlar: list[dict[str, Any]],
    kullanici_id: int | None,
    api_anahtari_id: int | None,
    sicaklik: float,
    maks_token: int,
    org_id: int | None = None,
    araclar: list[Arac] | None = None,
    maks_tur: int = 4,
    kaynaklar: list[dict[str, Any]] | None = None,
    dil: str | None = None,
) -> AsyncIterator[str]:
    """Kullanici mesaji yazilmis bir konusma icin SSE akisini uretir.

    Arac tanimliyken olay sirasi `baslangic` → (`arac_cagrisi` → `arac_sonucu`)*
    → `parca`* → `kullanim` → `bitti` olur; icerik parcalari araç turlari
    tamamlandiktan sonra yayinlanir.
    """
    baslangic = time.perf_counter()
    tahmini_girdi = kullanici_mesaji.token_sayisi or tahmin_token(kullanici_mesaji.icerik)
    parcalar: list[str] = []
    girdi_token = 0
    cikti_token = 0
    ozetler: list[dict[str, str]] = []
    tanimlar = arac_tanimlari(araclar)
    calisan_mesajlar = list(mesajlar)
    tur = 0

    yield sse_olay(
        "baslangic", {"konusma_id": konusma.id, "mesaj_id": kullanici_mesaji.id}
    )

    try:
        while True:
            tur_cagrilari: list[dict[str, Any]] = []
            akis = ust.akis_uret(
                bdm,
                calisan_mesajlar,
                sicaklik=sicaklik,
                maks_token=maks_token,
                araclar=tanimlar,
            )
            try:
                async for olay in akis:
                    if "parca" in olay:
                        parca = str(olay["parca"])
                        parcalar.append(parca)
                        # Araç turunda içerik sonradan yayınlanır: sıra korunur.
                        if tanimlar is None:
                            yield sse_olay("parca", {"icerik": parca})
                    elif "kullanim" in olay:
                        girdi_token += int(olay["kullanim"].get("girdi") or 0)
                        cikti_token += int(olay["kullanim"].get("cikti") or 0)
                    elif "arac_cagrilari" in olay:
                        tur_cagrilari.extend(olay["arac_cagrilari"])
            finally:
                await akis.aclose()

            if not tur_cagrilari:
                break
            if tur >= maks_tur:
                raise tur_siniri_asildi(maks_tur)
            tur += 1
            for cagri in tur_cagrilari:
                yield sse_olay(
                    "arac_cagrisi",
                    {"ad": cagri.get("ad"), "argumanlar": cagri.get("argumanlar") or {}},
                )
            eklenecek, tur_ozetleri = await araclari_yurut(
                oturum,
                org_id=org_id if org_id is not None else bdm.org_id,
                araclar=araclar or [],
                cagrilar=tur_cagrilari,
                konusma=konusma,
                tetikleyen_mesaj_id=kullanici_mesaji.id,
            )
            for ozet in tur_ozetleri:
                yield sse_olay("arac_sonucu", ozet)
            ozetler.extend(tur_ozetleri)
            calisan_mesajlar.extend(eklenecek)

        if tanimlar is not None:
            for parca in parcalar:
                yield sse_olay("parca", {"icerik": parca})
    except asyncio.CancelledError:
        logger.info("İstemci koptu; kısmi yanıt kaydedilmedi (konuşma %s).", konusma.id)
        raise
    except KutyaiHatasi as hata:
        await _hatali_kaydet(
            oturum,
            bdm=bdm,
            konusma=konusma,
            kullanici_id=kullanici_id,
            api_anahtari_id=api_anahtari_id,
            gecikme_ms=_gecen_ms(baslangic),
        )
        yield sse_olay("hata", hata.govde(dil) if dil else hata.govde())
        yield sse_olay("bitti", {})
        return
    except Exception as hata:  # pragma: no cover - beklenmeyen altyapi hatasi
        logger.exception("Sohbet akışı beklenmedik hata verdi: %s", hata)
        await _hatali_kaydet(
            oturum,
            bdm=bdm,
            konusma=konusma,
            kullanici_id=kullanici_id,
            api_anahtari_id=api_anahtari_id,
            gecikme_ms=_gecen_ms(baslangic),
        )
        yield sse_olay("hata", SunucuHatasi().govde())
        yield sse_olay("bitti", {})
        return

    icerik = "".join(parcalar)
    girdi = girdi_token or tahmini_girdi
    cikti = cikti_token or tahmin_token(icerik)
    gecikme_ms = _gecen_ms(baslangic)
    yield sse_olay(
        "kullanim",
        {"token_girdi": girdi, "token_cikti": cikti, "gecikme_ms": gecikme_ms},
    )

    try:
        await _tamamla(
            oturum,
            bdm=bdm,
            konusma=konusma,
            kullanici_mesaji=kullanici_mesaji,
            icerik=icerik,
            girdi=girdi,
            cikti=cikti,
            tahmini_girdi=tahmini_girdi,
            gecikme_ms=gecikme_ms,
            kullanici_id=kullanici_id,
            api_anahtari_id=api_anahtari_id,
        )
    except Exception as hata:  # pragma: no cover - kalici kayit arizasi
        logger.exception("Sohbet kaydı yazılamadı: %s", hata)
        yield sse_olay("hata", SunucuHatasi().govde())
        yield sse_olay("bitti", {})
        return

    son: dict[str, Any] = {}
    if kaynaklar:
        son["kaynaklar"] = kaynaklar
    if ozetler:
        son["arac_cagrilari"] = ozetler
    yield sse_olay("bitti", son)


def _gecen_ms(baslangic: float) -> int:
    return max(0, int((time.perf_counter() - baslangic) * 1000))


async def _tamamla(
    oturum: AsyncSession,
    *,
    bdm: Bdm,
    konusma: Konusma,
    kullanici_mesaji: Mesaj,
    icerik: str,
    girdi: int,
    cikti: int,
    tahmini_girdi: int,
    gecikme_ms: int,
    kullanici_id: int | None,
    api_anahtari_id: int | None,
) -> None:
    """Asistan mesajini, kullanim kaydini ve kota sayaclarini yazar."""
    if girdi != tahmini_girdi:
        konusma.token_girdi = max(0, (konusma.token_girdi or 0) + (girdi - tahmini_girdi))
        kullanici_mesaji.token_sayisi = girdi
    await mesaj_ekle(
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
        kullanici_id=kullanici_id,
        api_anahtari_id=api_anahtari_id,
        konusma_id=konusma.id,
        girdi_token=girdi,
        cikti_token=cikti,
        gecikme_ms=gecikme_ms,
        durum=KullanimDurumu.basarili,
    )
    await kota_token_ekle(
        oturum,
        kullanici_id=kullanici_id,
        api_anahtari_id=api_anahtari_id,
        token=girdi + cikti,
    )
    await oturum.commit()


async def _hatali_kaydet(
    oturum: AsyncSession,
    *,
    bdm: Bdm,
    konusma: Konusma,
    kullanici_id: int | None,
    api_anahtari_id: int | None,
    gecikme_ms: int,
) -> None:
    """Basarisiz istegi kullanim kaydina isler (kismi yanit yazilmaz)."""
    try:
        await kullanim_yaz(
            oturum,
            bdm_id=bdm.id,
            kullanici_id=kullanici_id,
            api_anahtari_id=api_anahtari_id,
            konusma_id=konusma.id,
            gecikme_ms=gecikme_ms,
            durum=KullanimDurumu.hata,
        )
        await oturum.commit()
    except Exception as hata:  # pragma: no cover - kayit arizasi
        logger.warning("Hatalı istek kaydedilemedi: %s", hata)
