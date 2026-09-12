"""Turdes hata zarfi ve HTTP isleyicileri (spec §6, §10.1).

Tum hatalar su govdeyle doner:

    {"hata": {"kod": "...", "mesaj": "...", "ayrinti": {...}}}

`mesaj` secilen dilde (bkz. `cekirdek/i18n.py`); `kod` her zaman makine-okunur
ve dilden bagimsizdir. Teknik ayrinti yalnizca sunucu loguna ve denetim izine
yazilir.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from arkauc.app.cekirdek.i18n import VARSAYILAN_DIL, dil_coz, mesaj

logger = logging.getLogger("kutyai.hata")


def istek_dili(istek: Request) -> str:
    return dil_coz(istek.headers.get("accept-language"))


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
        ceviriler: dict[str, Any] | None = None,
    ) -> None:
        if mesaj:
            self.mesaj = mesaj
        if kod:
            self.kod = kod
        if durum_kodu:
            self.durum_kodu = durum_kodu
        self.ayrinti: dict[str, Any] = ayrinti or {}
        self.ceviriler: dict[str, Any] = ceviriler or {}
        super().__init__(self.mesaj)

    def govde(self, dil: str = VARSAYILAN_DIL) -> dict[str, Any]:
        """Secilen dilde hata zarfi.

        `mesaj` alani katalogda varsa cevrilir; yoksa Turkce metin aynen doner.
        """
        return {
            "hata": {
                "kod": self.kod,
                "mesaj": mesaj(self.mesaj, dil, **self.ceviriler),
                "ayrinti": self.ayrinti,
            }
        }


class GecersizIstek(KutyaiHatasi):
    durum_kodu = 400
    kod = "gecersiz_istek"
    mesaj = "gecersiz_istek"


class DogrulamaHatasi(KutyaiHatasi):
    durum_kodu = 400
    kod = "dogrulama_hatasi"
    mesaj = "dogrulama_hatasi"


class KimlikGerekli(KutyaiHatasi):
    durum_kodu = 401
    kod = "kimlik_gerekli"
    mesaj = "kimlik_gerekli"


class JetonGecersiz(KutyaiHatasi):
    durum_kodu = 401
    kod = "jeton_gecersiz"
    mesaj = "jeton_gecersiz"


class JetonSuresiDoldu(KutyaiHatasi):
    durum_kodu = 401
    kod = "jeton_suresi_doldu"
    mesaj = "jeton_suresi_doldu"


class AnahtarGecersiz(KutyaiHatasi):
    durum_kodu = 401
    kod = "anahtar_gecersiz"
    mesaj = "anahtar_gecersiz"


class GecersizKimlikBilgisi(KutyaiHatasi):
    durum_kodu = 401
    kod = "gecersiz_kimlik_bilgisi"
    mesaj = "gecersiz_kimlik_bilgisi"


class YetkiYok(KutyaiHatasi):
    durum_kodu = 403
    kod = "yetki_yok"
    mesaj = "yetki_yok"


class OrgErisimYok(KutyaiHatasi):
    durum_kodu = 403
    kod = "org_erisim_yok"
    mesaj = "org_erisim_yok"


class EpostaDogrulanmadi(KutyaiHatasi):
    durum_kodu = 403
    kod = "eposta_dogrulanmadi"
    mesaj = "eposta_dogrulanmadi"


class Bulunamadi(KutyaiHatasi):
    durum_kodu = 404
    kod = "bulunamadi"
    mesaj = "bulunamadi"


class Cakisma(KutyaiHatasi):
    durum_kodu = 409
    kod = "cakisma"
    mesaj = "cakisma"


class GecersizGecis(KutyaiHatasi):
    durum_kodu = 409
    kod = "gecersiz_gecis"
    mesaj = "gecersiz_gecis"


class AbonelikGecikmis(KutyaiHatasi):
    durum_kodu = 402
    kod = "abonelik_gecikmis"
    mesaj = "abonelik_gecikmis"


class KotaAsildi(KutyaiHatasi):
    durum_kodu = 429
    kod = "kota_asildi"
    mesaj = "kota_asildi"


class OranSiniri(KutyaiHatasi):
    durum_kodu = 429
    kod = "oran_siniri"
    mesaj = "oran_siniri"


class MedyaDesteklenmiyor(KutyaiHatasi):
    durum_kodu = 400
    kod = "medya_desteklenmiyor"
    mesaj = "medya_desteklenmiyor"


class DosyaCokBuyuk(KutyaiHatasi):
    durum_kodu = 413
    kod = "dosya_cok_buyuk"
    mesaj = "dosya_cok_buyuk"


class UstSaglayiciHatasi(KutyaiHatasi):
    durum_kodu = 502
    kod = "ust_saglayici_hatasi"
    mesaj = "ust_saglayici_hatasi"


class AracHatasi(KutyaiHatasi):
    durum_kodu = 502
    kod = "arac_hatasi"
    mesaj = "arac_hatasi"


class RagGommeHatasi(KutyaiHatasi):
    durum_kodu = 502
    kod = "rag_gomme_hatasi"
    mesaj = "rag_gomme_hatasi"


class BdmHazirDegil(KutyaiHatasi):
    durum_kodu = 503
    kod = "bdm_hazir_degil"
    mesaj = "bdm_hazir_degil"


class SurucuYok(KutyaiHatasi):
    durum_kodu = 503
    kod = "surucu_yok"
    mesaj = "surucu_yok"


class SunucuHatasi(KutyaiHatasi):
    durum_kodu = 500
    kod = "sunucu_hatasi"
    mesaj = "sunucu_hatasi"


_HTTP_KODLARI: dict[int, str] = {
    400: "gecersiz_istek",
    401: "kimlik_gerekli",
    402: "abonelik_gecikmis",
    403: "yetki_yok",
    404: "bulunamadi",
    405: "yontem_izinli_degil",
    409: "cakisma",
    413: "dosya_cok_buyuk",
    429: "oran_siniri",
    500: "sunucu_hatasi",
    502: "ust_saglayici_hatasi",
    503: "surucu_yok",
}


def isleyicileri_kur(uygulama: FastAPI) -> None:
    """Hata isleyicilerini uygulamaya baglar (dil duyarli)."""

    @uygulama.exception_handler(KutyaiHatasi)
    async def _kutyai(istek: Request, hata: KutyaiHatasi) -> JSONResponse:
        return JSONResponse(status_code=hata.durum_kodu, content=hata.govde(istek_dili(istek)))

    @uygulama.exception_handler(RequestValidationError)
    async def _dogrulama(istek: Request, hata: RequestValidationError) -> JSONResponse:
        ayrinti = {"alanlar": [hata_ozeti(h) for h in hata.errors()]}
        return JSONResponse(
            status_code=400,
            content=DogrulamaHatasi(ayrinti=ayrinti).govde(istek_dili(istek)),
        )

    @uygulama.exception_handler(StarletteHTTPException)
    async def _http(istek: Request, hata: StarletteHTTPException) -> JSONResponse:
        dil = istek_dili(istek)
        kod = _HTTP_KODLARI.get(hata.status_code)
        if kod is None:
            return JSONResponse(
                status_code=hata.status_code,
                content={
                    "hata": {
                        "kod": "http_hatasi",
                        "mesaj": mesaj("http_hatasi", dil),
                        "ayrinti": {},
                    }
                },
            )
        return JSONResponse(status_code=hata.status_code, content=KutyaiHatasi(kod=kod).govde(dil))

    @uygulama.exception_handler(Exception)
    async def _beklenmeyen(istek: Request, hata: Exception) -> JSONResponse:
        logger.exception("Beklenmeyen hata: %s %s", istek.method, istek.url.path)
        return JSONResponse(
            status_code=500, content=SunucuHatasi().govde(istek_dili(istek))
        )


def hata_ozeti(hata: dict[str, Any]) -> dict[str, Any]:
    """Pydantic dogrulama hatasini sade bir sozluge cevirir."""
    yer = [str(parca) for parca in hata.get("loc", ()) if parca != "body"]
    return {
        "alan": ".".join(yer) or "gövde",
        "mesaj": hata.get("msg", "Geçersiz değer."),
    }
