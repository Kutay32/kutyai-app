"""Upstream erisim dogrulamasi (spec §7.5).

Once `GET {temel_url}/models` yoklanir; bu uc 401/403/404/405 dondururse
1 tokenlik `POST {temel_url}/chat/completions` denemesi yapilir. Gecikme
olculur ve sonuca gore `bdm.durum` `hazir` ya da `hata` yazilir; `calisiyor`
durumundaki BDM'e dokunulmaz (API.md §11 durum makinesi).

Baglanti ve adres hatalari firlatilmaz: sonuc `basarili=False` ve Turkce
mesajla doner, boylece panel kullaniciya nedeni gosterebilir.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek import guvenlik
from bdm_veritabani.modeller import Bdm, BdmDurumu

logger = logging.getLogger("kutyai.hazirlama")

ZAMAN_ASIMI_SN = 10.0
# `/models` ucu kapali olan saglayicilar icin yedek sohbet denemesi kodlari.
YEDEK_DENEME_KODLARI = frozenset({401, 403, 404, 405})
BAGLANTI_MESAJI = "Model sağlayıcısına bağlanılamadı. Adresi ve ağ erişimini kontrol edin."
ADRES_MESAJI = "Model adresi tanımlı değil. Lütfen temel adresi girin."
ADRES_GECERSIZ_MESAJI = "Sağlayıcı adresi geçersiz."
# Cozulemeyen/bozuk adresler: `httpx.InvalidURL` ve `httpx.UnsupportedProtocol`
# `httpx.HTTPError` hiyerarsisinde degildir; IDNA hatalari `UnicodeError`/`ValueError`
# olarak gelir. Adres hatalari baglanti hatasindan ayri mesajla bildirilir.
ADRES_HATALARI: tuple[type[Exception], ...] = (
    httpx.InvalidURL,
    httpx.UnsupportedProtocol,
    UnicodeError,
    ValueError,
)


def varsayilan_tasima() -> httpx.AsyncBaseTransport | None:
    """Varsayilan ag tasimasi; testler sahte tasima enjekte etmek icin ezer."""
    return None


def anahtari_coz(bdm: Bdm) -> str:
    """BDM'nin sifreli upstream anahtarini cozer; yoksa bos dize doner."""
    if not bdm.api_anahtari_sifreli:
        return ""
    try:
        return guvenlik.coz(bdm.api_anahtari_sifreli)
    except Exception:  # pragma: no cover - bozuk sifreli deger
        logger.warning("BDM %s icin upstream anahtari cozulemedi.", bdm.id)
        return ""


def _modelleri_ayikla(govde: Any) -> list[str]:
    kayitlar = govde.get("data") if isinstance(govde, dict) else govde
    if not isinstance(kayitlar, list):
        return []
    return [
        str(kayit["id"])
        for kayit in kayitlar
        if isinstance(kayit, dict) and kayit.get("id")
    ]


def _govdeyi_coz(yanit: httpx.Response) -> Any:
    try:
        return yanit.json()
    except ValueError:
        return {}


def _gecikme_ms(baslangic: float) -> int:
    return max(0, int((time.perf_counter() - baslangic) * 1000))


async def _sonuc(
    bdm: Bdm,
    oturum: AsyncSession | None,
    *,
    basarili: bool,
    gecikme_ms: int,
    modeller: list[str],
    mesaj: str,
) -> dict[str, Any]:
    """Sonucu BDM durumuna yazar ve API govdesini dondurur.

    Calisan bir BDM'in durumu degistirilmez: konteyner ayakta kalir, ancak
    `calisiyor` durumundan `hazir`/`hata` gecisi durum makinesinde yoktur
    (API.md §11) ve BDM'i durdurulamaz hale getirirdi. Sonuc yalnizca yanitta
    bildirilir.
    """
    if bdm.durum != BdmDurumu.calisiyor:
        bdm.durum = BdmDurumu.hazir if basarili else BdmDurumu.hata
        if oturum is not None:
            await oturum.flush()
    return {
        "basarili": basarili,
        "gecikme_ms": gecikme_ms,
        "modeller": modeller,
        "mesaj": mesaj,
    }


async def _baglanti_hatasi(
    bdm: Bdm,
    oturum: AsyncSession | None,
    baslangic: float,
    hata: Exception,
) -> dict[str, Any]:
    logger.warning("BDM %s dogrulanamadi: %s", bdm.id, hata)
    return await _sonuc(
        bdm,
        oturum,
        basarili=False,
        gecikme_ms=_gecikme_ms(baslangic),
        modeller=[],
        mesaj=BAGLANTI_MESAJI,
    )


async def _adres_hatasi(
    bdm: Bdm,
    oturum: AsyncSession | None,
    baslangic: float,
    hata: Exception,
) -> dict[str, Any]:
    """Bozuk/cozulemeyen adresi 500 yerine Turkce sonucla bildirir."""
    logger.warning("BDM %s icin saglayici adresi gecersiz: %s", bdm.id, hata)
    return await _sonuc(
        bdm,
        oturum,
        basarili=False,
        gecikme_ms=_gecikme_ms(baslangic),
        modeller=[],
        mesaj=ADRES_GECERSIZ_MESAJI,
    )


async def dogrula(
    bdm: Bdm,
    *,
    oturum: AsyncSession | None = None,
    istemci: httpx.AsyncClient | None = None,
    tasima: httpx.AsyncBaseTransport | None = None,
) -> dict[str, Any]:
    """BDM'nin upstream baglantisini dogrular; `{basarili, gecikme_ms, modeller, mesaj}` doner.

    `istemci` verilirse kullanilir ve kapatilmaz; `tasima` verilirse gecici
    bir istemci acilip is bitiminde kapatilir (testler icin sahte tasima).
    """
    temel = (bdm.temel_url or "").rstrip("/")
    if not temel:
        return await _sonuc(
            bdm, oturum, basarili=False, gecikme_ms=0, modeller=[], mesaj=ADRES_MESAJI
        )

    anahtar = anahtari_coz(bdm)
    basliklar = {"Authorization": f"Bearer {anahtar}"} if anahtar else {}
    kendi_istemcisi = istemci is None
    if istemci is None:
        istemci = httpx.AsyncClient(
            transport=tasima if tasima is not None else varsayilan_tasima(),
            timeout=ZAMAN_ASIMI_SN,
        )
    baslangic = time.perf_counter()
    try:
        return await _denemeleri_yap(istemci, bdm, oturum, temel, basliklar, baslangic)
    finally:
        if kendi_istemcisi:
            await istemci.aclose()


async def _denemeleri_yap(
    istemci: httpx.AsyncClient,
    bdm: Bdm,
    oturum: AsyncSession | None,
    temel: str,
    basliklar: dict[str, str],
    baslangic: float,
) -> dict[str, Any]:
    try:
        yanit = await istemci.get(f"{temel}/models", headers=basliklar)
    except ADRES_HATALARI as hata:
        return await _adres_hatasi(bdm, oturum, baslangic, hata)
    except httpx.HTTPError as hata:
        return await _baglanti_hatasi(bdm, oturum, baslangic, hata)

    if yanit.status_code == 200:
        modeller = _modelleri_ayikla(_govdeyi_coz(yanit))
        mesaj = (
            f"Bağlantı başarılı; {len(modeller)} model listelendi."
            if modeller
            else "Bağlantı başarılı ancak sağlayıcı model listesi boş döndü."
        )
        return await _sonuc(
            bdm,
            oturum,
            basarili=True,
            gecikme_ms=_gecikme_ms(baslangic),
            modeller=modeller,
            mesaj=mesaj,
        )

    if yanit.status_code not in YEDEK_DENEME_KODLARI:
        return await _sonuc(
            bdm,
            oturum,
            basarili=False,
            gecikme_ms=_gecikme_ms(baslangic),
            modeller=[],
            mesaj=(
                f"Sağlayıcı model listesi {yanit.status_code} koduyla yanıt verdi. "
                "Temel adresi ve anahtarı kontrol edin."
            ),
        )

    # Model listesi kapali olabilir: 1 tokenlik sohbet denemesi.
    try:
        yanit = await istemci.post(
            f"{temel}/chat/completions",
            headers=basliklar,
            json={
                "model": bdm.upstream_model,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 1,
                "stream": False,
            },
        )
    except ADRES_HATALARI as hata:
        return await _adres_hatasi(bdm, oturum, baslangic, hata)
    except httpx.HTTPError as hata:
        return await _baglanti_hatasi(bdm, oturum, baslangic, hata)

    if yanit.status_code == 200:
        return await _sonuc(
            bdm,
            oturum,
            basarili=True,
            gecikme_ms=_gecikme_ms(baslangic),
            modeller=[],
            mesaj="Model listesi alınamadı ancak sohbet ucu yanıt verdi.",
        )
    return await _sonuc(
        bdm,
        oturum,
        basarili=False,
        gecikme_ms=_gecikme_ms(baslangic),
        modeller=[],
        mesaj=(
            f"Sohbet denemesi {yanit.status_code} koduyla başarısız oldu. "
            "Model adını ve anahtarı kontrol edin."
        ),
    )
