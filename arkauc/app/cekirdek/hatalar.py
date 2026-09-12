"""Turdes hata zarfi ve HTTP isleyicileri (spec §6).

Tum hatalar su govdeyle doner:

    {"hata": {"kod": "...", "mesaj": "...", "ayrinti": {...}}}

`mesaj` her zaman Turkce ve kullaniciya gosterilebilir; teknik ayrinti
yalnizca sunucu loguna ve denetim izine yazilir.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("kutyai.hata")


class KutyaiHatasi(Exception):
    """Uygulama hatalarinin tabani."""

    durum_kodu: int = 400
    kod: str = "gecersiz_istek"
    mesaj: str = "İstek işlenemedi."

    def __init__(
        self,
        mesaj: str | None = None,
        ayrinti: dict[str, Any] | None = None,
        *,
        kod: str | None = None,
        durum_kodu: int | None = None,
    ) -> None:
        if mesaj:
            self.mesaj = mesaj
        if kod:
            self.kod = kod
        if durum_kodu:
            self.durum_kodu = durum_kodu
        self.ayrinti: dict[str, Any] = ayrinti or {}
        super().__init__(self.mesaj)

    def govde(self) -> dict[str, Any]:
        return {"hata": {"kod": self.kod, "mesaj": self.mesaj, "ayrinti": self.ayrinti}}


class GecersizIstek(KutyaiHatasi):
    durum_kodu = 400
    kod = "gecersiz_istek"
    mesaj = "İstek geçersiz."


class DogrulamaHatasi(KutyaiHatasi):
    durum_kodu = 400
    kod = "dogrulama_hatasi"
    mesaj = "Gönderilen alanlar doğrulanamadı."


class KimlikGerekli(KutyaiHatasi):
    durum_kodu = 401
    kod = "kimlik_gerekli"
    mesaj = "Bu işlem için giriş yapmalısınız."


class JetonGecersiz(KutyaiHatasi):
    durum_kodu = 401
    kod = "jeton_gecersiz"
    mesaj = "Oturum bilgisi geçersiz. Lütfen tekrar giriş yapın."


class JetonSuresiDoldu(KutyaiHatasi):
    durum_kodu = 401
    kod = "jeton_suresi_doldu"
    mesaj = "Oturum süresi doldu. Lütfen tekrar giriş yapın."


class AnahtarGecersiz(KutyaiHatasi):
    durum_kodu = 401
    kod = "anahtar_gecersiz"
    mesaj = "API anahtarı geçersiz veya iptal edilmiş."


class YetkiYok(KutyaiHatasi):
    durum_kodu = 403
    kod = "yetki_yok"
    mesaj = "Bu işlem için yetkiniz yok."


class EpostaDogrulanmadi(KutyaiHatasi):
    durum_kodu = 403
    kod = "eposta_dogrulanmadi"
    mesaj = "Sohbete başlamadan önce e-posta adresinizi doğrulamalısınız."


class Bulunamadi(KutyaiHatasi):
    durum_kodu = 404
    kod = "bulunamadi"
    mesaj = "Kayıt bulunamadı."


class Cakisma(KutyaiHatasi):
    durum_kodu = 409
    kod = "cakisma"
    mesaj = "Bu kayıt zaten mevcut."


class GecersizGecis(KutyaiHatasi):
    durum_kodu = 409
    kod = "gecersiz_gecis"
    mesaj = "Bu durum geçişine izin verilmiyor."


class KotaAsildi(KutyaiHatasi):
    durum_kodu = 429
    kod = "kota_asildi"
    mesaj = "Kotanız doldu."


class OranSiniri(KutyaiHatasi):
    durum_kodu = 429
    kod = "oran_siniri"
    mesaj = "Çok fazla istek gönderdiniz. Lütfen biraz bekleyin."


class UstSaglayiciHatasi(KutyaiHatasi):
    durum_kodu = 502
    kod = "ust_saglayici_hatasi"
    mesaj = "Model sağlayıcısına ulaşılamadı."


class BdmHazirDegil(KutyaiHatasi):
    durum_kodu = 503
    kod = "bdm_hazir_degil"
    mesaj = "Seçilen model şu anda kullanıma hazır değil."


class SurucuYok(KutyaiHatasi):
    durum_kodu = 503
    kod = "surucu_yok"
    mesaj = "Konteyner çalışma zamanı bulunamadı."


class SunucuHatasi(KutyaiHatasi):
    durum_kodu = 500
    kod = "sunucu_hatasi"
    mesaj = "Beklenmeyen bir sunucu hatası oluştu."


_HTTP_KODLARI: dict[int, tuple[str, str]] = {
    400: ("gecersiz_istek", "İstek geçersiz."),
    401: ("kimlik_gerekli", "Bu işlem için giriş yapmalısınız."),
    403: ("yetki_yok", "Bu işlem için yetkiniz yok."),
    404: ("bulunamadi", "Kayıt bulunamadı."),
    405: ("yontem_izinli_degil", "Bu adres için bu yöntem kullanılamaz."),
    409: ("cakisma", "Bu kayıt zaten mevcut."),
    429: ("oran_siniri", "Çok fazla istek gönderdiniz."),
}


def isleyicileri_kur(uygulama: FastAPI) -> None:
    """Hata isleyicilerini uygulamaya baglar."""

    @uygulama.exception_handler(KutyaiHatasi)
    async def _kutyai(_istek: Request, hata: KutyaiHatasi) -> JSONResponse:
        return JSONResponse(status_code=hata.durum_kodu, content=hata.govde())

    @uygulama.exception_handler(RequestValidationError)
    async def _dogrulama(_istek: Request, hata: RequestValidationError) -> JSONResponse:
        ayrinti = {"alanlar": [hata_ozeti(h) for h in hata.errors()]}
        return JSONResponse(
            status_code=400,
            content=DogrulamaHatasi(ayrinti=ayrinti).govde(),
        )

    @uygulama.exception_handler(StarletteHTTPException)
    async def _http(_istek: Request, hata: StarletteHTTPException) -> JSONResponse:
        kod, mesaj = _HTTP_KODLARI.get(
            hata.status_code, ("http_hatasi", str(hata.detail or "İstek işlenemedi."))
        )
        return JSONResponse(
            status_code=hata.status_code,
            content={"hata": {"kod": kod, "mesaj": mesaj, "ayrinti": {}}},
        )

    @uygulama.exception_handler(Exception)
    async def _beklenmeyen(istek: Request, hata: Exception) -> JSONResponse:
        logger.exception("Beklenmeyen hata: %s %s", istek.method, istek.url.path)
        return JSONResponse(status_code=500, content=SunucuHatasi().govde())


def hata_ozeti(hata: dict[str, Any]) -> dict[str, Any]:
    """Pydantic dogrulama hatasini sade bir sozluge cevirir."""
    yer = [str(parca) for parca in hata.get("loc", ()) if parca != "body"]
    return {
        "alan": ".".join(yer) or "gövde",
        "mesaj": hata.get("msg", "Geçersiz değer."),
    }
