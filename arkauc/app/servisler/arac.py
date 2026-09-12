"""Araç çağırma servisi (spec §4).

Sorumluluklar:

* Organizasyon kapsamlı araç seçimi (`araclari_getir`, `arac_bul`).
* Modele sunulacak OpenAI `tools` tanımı (`arac_tanimi`).
* Argümanların JSON Schema denetimi (`argumanlari_dogrula`).
* Yerleşik araçlar (`hesap_makinesi`, `zaman`) ve webhook çağrısı.
* Her çağrının `arac_cagrisi` tablosuna yazılması.

Hata siyaseti: webhook/yerleşik **çalıştırma** hataları istisna olarak
fırlatılmaz; sonuç `{"hata": <mesaj>}` + `durum="hata"` olarak döner ki model
hata metnini görebilsin. Yalnızca argüman şema ihlalleri `GecersizIstek`
(HTTP 400) yükseltir; çağrı ucu bunu `400 gecersiz_istek` olarak yansıtır.
"""

from __future__ import annotations

import ast
import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek import guvenlik
from arkauc.app.cekirdek.ayarlar import ayarlar
from arkauc.app.cekirdek.hatalar import Bulunamadi, GecersizIstek
from arkauc.app.cekirdek.i18n import VARSAYILAN_DIL, mesaj
from bdm_listesi.sema import _adres_dogrula
from bdm_veritabani.modeller import (
    Arac,
    AracCagrisi,
    AracCagrisiDurumu,
    AracTuru,
)

#: Webhook zaman aşımı (saniye). Testler bu sabiti düşürebilir.
ZAMAN_ASIMI_SN = 10.0
#: Yanıt gövdesi üst sınırı (bayt).
YANIT_SINIRI_BAYT = 64 * 1024
#: Webhook gövdesini imzalayan başlık.
IMZA_BASLIGI = "X-Kutyai-Imza"
#: Hesaplanan imza şeması.
IMZA_ONEK = "sha256="

#: Yerleşik araçların varsayılan JSON şemaları.
YERLESIK_SEMALAR: dict[str, dict[str, Any]] = {
    "hesap_makinesi": {
        "type": "object",
        "properties": {
            "ifade": {
                "type": "string",
                "description": "Hesaplanacak aritmetik ifade, örn. (2+3)*4",
            }
        },
        "required": ["ifade"],
        "additionalProperties": False,
    },
    "zaman": {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    },
}
#: Kayıtlı yerleşik araç slug'ları.
YERLESIK_SLUGLAR: tuple[str, ...] = tuple(YERLESIK_SEMALAR)

#: Hesaplama ifadesinde izin verilen ikili işleçler.
_IKILI_ISLECLER = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)
#: İzin verilen tekli işleçler.
_TEKLI_ISLECLER = (ast.UAdd, ast.USub)
#: İfade uzunluğu ve üs sınırları (kaynak tüketimini kısıtlar).
_MAKS_IFADE_UZUNLUK = 200
_MAKS_US = 64
_MAKS_TABAN = 10**9

_TIPLER: dict[str, tuple[type, ...]] = {
    "object": (dict,),
    "array": (list,),
    "string": (str,),
    "boolean": (bool,),
    "integer": (int,),
    "number": (int, float),
    "null": (type(None),),
}


class CalistirmaHatasi(Exception):
    """Çalıştırma sırasında oluşan, modele metin olarak dönen hata."""

    def __init__(self, kod: str, **degiskenler: Any) -> None:
        self.kod = kod
        self.metin = mesaj(kod, VARSAYILAN_DIL, **degiskenler)
        super().__init__(self.metin)


# -- seçim ------------------------------------------------------------------


def yerlesik_mi(arac: Arac) -> bool:
    """Araç yerleşik (kod içi) türde mi?"""
    return arac.tur == AracTuru.yerlesik


async def araclari_getir(
    oturum: AsyncSession, org_id: int, idler: list[int] | None
) -> list[Arac]:
    """Org'un etkin araçları; `idler` verilirse yalnız o kimlikler.

    Bilinmeyen/başka org'a ait/etkin olmayan kimlikler sessizce elenir; sohbet
    akışı eksik araç yüzünden durmaz.
    """
    kosullar: list[sa.ColumnElement[bool]] = [
        Arac.org_id == org_id,
        Arac.etkin.is_(True),
    ]
    if idler is not None:
        temiz = [int(deger) for deger in idler]
        if not temiz:
            return []
        kosullar.append(Arac.id.in_(temiz))
    satirlar = (
        await oturum.execute(sa.select(Arac).where(*kosullar).order_by(Arac.id))
    ).scalars().all()
    return list(satirlar)


async def arac_bul(oturum: AsyncSession, org_id: int, anahtar: str | int) -> Arac:
    """Slug ya da kimlikle org kapsamlı araç çözer; yoksa `404`."""
    metin = str(anahtar).strip()
    kosullar = [Arac.org_id == org_id]
    if metin.isdigit():
        kosullar.append(sa.or_(Arac.id == int(metin), Arac.slug == metin))
    else:
        kosullar.append(Arac.slug == metin)
    arac = (await oturum.execute(sa.select(Arac).where(*kosullar))).scalars().first()
    if arac is None:
        raise Bulunamadi(
            "arac_bulunamadi", {"arac": metin}, kod="arac_bulunamadi"
        )
    return arac


def arac_tanimi(arac: Arac) -> dict[str, Any]:
    """OpenAI `tools` biçimi."""
    sema = arac.json_sema if isinstance(arac.json_sema, dict) and arac.json_sema else None
    if sema is None:
        sema = YERLESIK_SEMALAR.get(arac.slug) or {
            "type": "object",
            "properties": {},
        }
    return {
        "type": "function",
        "function": {
            "name": arac.slug,
            "description": arac.aciklama or "",
            "parameters": sema,
        },
    }


# -- başlık şifreleme -------------------------------------------------------


def basliklari_sifrele(basliklar: dict[str, str] | None) -> str | None:
    """Başlık sözlüğünü Fernet ile şifreleyip saklanacak metni döndürür."""
    if not basliklar:
        return None
    veri = {str(ad): str(deger) for ad, deger in basliklar.items()}
    return guvenlik.sifrele(json.dumps(veri, ensure_ascii=False))


def _basliklari_coz(arac: Arac) -> dict[str, str]:
    if not arac.basliklar_sifreli:
        return {}
    try:
        veri = json.loads(guvenlik.coz(arac.basliklar_sifreli))
    except Exception as hata:  # bozuk şifreli değer / JSON
        raise GecersizIstek(
            "arac_basliklar_gecersiz", {"arac_id": getattr(arac, "id", None)}
        ) from hata
    if not isinstance(veri, dict):
        raise GecersizIstek("arac_basliklar_gecersiz", {"arac_id": getattr(arac, "id", None)})
    return {str(ad): str(deger) for ad, deger in veri.items()}


def basliklari_maskele(arac: Arac) -> dict[str, str]:
    """Başlıkları değerleri maskelenmiş olarak döndürür (sır sızmaz)."""
    try:
        ham = _basliklari_coz(arac)
    except GecersizIstek:  # pragma: no cover - bozuk kayıt
        return {}
    return {ad: guvenlik.maskele(deger) for ad, deger in ham.items()}


# -- adres güvenliği --------------------------------------------------------


def uc_noktasi_dogrula(uc_noktasi: str) -> str:
    """Webhook uç noktasını SSRF ve şema kurallarına göre denetler.

    v1 `temel_url` kuralları yeniden kullanılır (yalnız http/https, bulut
    metadata konakları yasak); ek olarak https zorunludur ve yalnızca
    `KUTYAI_ARAC_YEREL_IZIN=true` iken http kabul edilir.
    """
    temiz = (uc_noktasi or "").strip()
    if not temiz:
        raise GecersizIstek("arac_uc_noktasi_zorunlu", {}, ceviriler={})
    try:
        # v1 `temel_url` denetimi yeniden kullanılır (tek SSRF kural kaynağı).
        guvenli = _adres_dogrula(temiz)
    except ValueError as hata:
        # Teknik gerekçe yalnızca `ayrinti`ya girer; mesaj katalogdan çevrilir.
        raise GecersizIstek(
            "arac_uc_noktasi_gecersiz", {"neden": str(hata)}
        ) from hata
    ayrisan = urlparse(guvenli)
    if not ayrisan.hostname:
        raise GecersizIstek("arac_uc_noktasi_gecersiz", {"neden": "konak yok"})
    sema = ayrisan.scheme.lower()
    if sema != "https" and not (sema == "http" and ayarlar.arac_yerel_izin):
        raise GecersizIstek("arac_https_zorunlu", {}, ceviriler={})
    return guvenli


def _imza_anahtari() -> bytes:
    return (ayarlar.arac_imza_anahtari or ayarlar.gizli_anahtar).encode("utf-8")


def imza_hesapla(govde: bytes) -> str:
    """`X-Kutyai-Imza` değeri (`sha256=<hmac>`)."""
    return IMZA_ONEK + hmac.new(_imza_anahtari(), govde, hashlib.sha256).hexdigest()


# -- argüman denetimi -------------------------------------------------------


def _arguman_hatasi(anahtar: str, alan: str, **degiskenler: Any) -> GecersizIstek:
    """Alan adını ve nedeni katalog anahtarıyla birlikte taşıyan `400`."""
    return GecersizIstek(
        anahtar,
        {"alan": alan, **degiskenler},
        ceviriler={"alan": alan, **degiskenler},
    )


def _tip_uyuyor(deger: Any, tip: str) -> bool:
    beklenen = _TIPLER.get(tip)
    if beklenen is None:
        return True
    if tip in ("integer", "number") and isinstance(deger, bool):
        return False
    return isinstance(deger, beklenen)


def _deger_dogrula(sema: Any, deger: Any, yol: str) -> None:
    if not isinstance(sema, dict):
        return
    tip = sema.get("type")
    if isinstance(tip, str) and not _tip_uyuyor(deger, tip):
        raise _arguman_hatasi("arac_arguman_tur", yol, tur=tip)
    if deger is not None and "enum" in sema:
        izinli = sema.get("enum") or []
        if deger not in izinli:
            raise _arguman_hatasi(
                "arac_arguman_enum", yol, degerler=", ".join(str(x) for x in izinli)
            )
    if isinstance(deger, (int, float)) and not isinstance(deger, bool):
        if "minimum" in sema and deger < sema["minimum"]:
            raise _arguman_hatasi("arac_arguman_minimum", yol, sinir=sema["minimum"])
        if "maximum" in sema and deger > sema["maximum"]:
            raise _arguman_hatasi("arac_arguman_maksimum", yol, sinir=sema["maximum"])
    if isinstance(deger, dict):
        ozellikler = sema.get("properties") or {}
        for ad in sema.get("required") or []:
            if ad not in deger:
                raise _arguman_hatasi(
                    "arac_arguman_zorunlu", f"{yol}.{ad}" if yol else str(ad)
                )
        for ad, alt_sema in ozellikler.items():
            if ad in deger:
                _deger_dogrula(alt_sema, deger[ad], f"{yol}.{ad}" if yol else str(ad))
        if sema.get("additionalProperties") is False:
            fazla = sorted(set(deger) - set(ozellikler))
            if fazla:
                raise _arguman_hatasi(
                    "arac_arguman_fazla", f"{yol}.{fazla[0]}" if yol else str(fazla[0])
                )


def argumanlari_dogrula(arac: Arac, argumanlar: Any) -> dict[str, Any]:
    """Argümanları aracın JSON şemasına göre denetler; sözlüğü döndürür."""
    sema = arac.json_sema if isinstance(arac.json_sema, dict) else {}
    if not sema and yerlesik_mi(arac):
        sema = YERLESIK_SEMALAR.get(arac.slug, {})
    if not sema:
        if argumanlar is None:
            return {}
        if not isinstance(argumanlar, dict):
            raise _arguman_hatasi("arac_arguman_tur", "argumanlar", tur="object")
        return dict(argumanlar)
    if not isinstance(argumanlar, dict):
        raise _arguman_hatasi("arac_arguman_tur", "argumanlar", tur="object")
    _deger_dogrula(sema, argumanlar, "")
    return dict(argumanlar)


# -- yerleşik araçlar -------------------------------------------------------


def _sayi_dugumu(dugum: ast.AST) -> float:
    if (
        isinstance(dugum, ast.Constant)
        and isinstance(dugum.value, (int, float))
        and not isinstance(dugum.value, bool)
    ):
        return dugum.value
    if isinstance(dugum, ast.UnaryOp) and isinstance(dugum.op, _TEKLI_ISLECLER):
        deger = _sayi_dugumu(dugum.operand)
        return +deger if isinstance(dugum.op, ast.UAdd) else -deger
    if isinstance(dugum, ast.BinOp) and isinstance(dugum.op, _IKILI_ISLECLER):
        sol = _sayi_dugumu(dugum.left)
        sag = _sayi_dugumu(dugum.right)
        islec = dugum.op
        if isinstance(islec, ast.Pow) and (abs(sag) > _MAKS_US or abs(sol) > _MAKS_TABAN):
            raise GecersizIstek("gecersiz_ifade", {}, ceviriler={})
        try:
            if isinstance(islec, ast.Add):
                return sol + sag
            if isinstance(islec, ast.Sub):
                return sol - sag
            if isinstance(islec, ast.Mult):
                return sol * sag
            if isinstance(islec, ast.Div):
                return sol / sag
            if isinstance(islec, ast.FloorDiv):
                return sol // sag
            if isinstance(islec, ast.Mod):
                return sol % sag
            sonuc = sol**sag
        except (ZeroDivisionError, OverflowError, ValueError) as hata:
            raise GecersizIstek("gecersiz_ifade", {}, ceviriler={}) from hata
        if isinstance(sonuc, complex):  # negatif taban + kesirli üs
            raise GecersizIstek("gecersiz_ifade", {}, ceviriler={})
        return sonuc
    raise GecersizIstek("gecersiz_ifade", {}, ceviriler={})


def _hesap_makinesi(argumanlar: dict[str, Any]) -> dict[str, Any]:
    ifade = argumanlar.get("ifade")
    if not isinstance(ifade, str) or not ifade.strip():
        raise _arguman_hatasi("arac_arguman_zorunlu", "ifade")
    if len(ifade) > _MAKS_IFADE_UZUNLUK:
        raise _arguman_hatasi("arac_arguman_uzunluk", "ifade", sinir=_MAKS_IFADE_UZUNLUK)
    try:
        agac = ast.parse(ifade, mode="eval")
    except SyntaxError as hata:
        raise GecersizIstek("gecersiz_ifade", {}, ceviriler={}) from hata
    return {"sonuc": _sayi_dugumu(agac.body)}


def _yerlesik_calistir(slug: str, argumanlar: dict[str, Any]) -> dict[str, Any]:
    if slug == "hesap_makinesi":
        return _hesap_makinesi(argumanlar)
    if slug == "zaman":
        return {"zaman": datetime.now(timezone.utc).isoformat()}
    raise GecersizIstek("arac_yerlesik_bilinmiyor", {"slug": slug}, ceviriler={"slug": slug})


# -- webhook ----------------------------------------------------------------


async def _sinirli_oku(yanit: httpx.Response) -> bytes:
    parcalar: list[bytes] = []
    toplam = 0
    async for parca in yanit.aiter_bytes():
        toplam += len(parca)
        if toplam > YANIT_SINIRI_BAYT:
            raise CalistirmaHatasi("arac_yanit_cok_buyuk")
        parcalar.append(parca)
    return b"".join(parcalar)


def _yanit_coz(ham: bytes) -> dict[str, Any]:
    metin = ham.decode("utf-8", "replace").strip()
    if not metin:
        return {}
    try:
        veri = json.loads(metin)
    except ValueError:
        return {"metin": metin}
    return veri if isinstance(veri, dict) else {"yanit": veri}


async def _webhook_calistir(arac: Arac, argumanlar: dict[str, Any]) -> dict[str, Any]:
    adres = uc_noktasi_dogrula(arac.uc_noktasi)
    basliklar = _basliklari_coz(arac)
    govde = json.dumps(
        {"arac": arac.slug, "argumanlar": argumanlar}, ensure_ascii=False
    ).encode("utf-8")
    basliklar["Content-Type"] = "application/json"
    basliklar["Accept"] = "application/json"
    basliklar[IMZA_BASLIGI] = imza_hesapla(govde)

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(ZAMAN_ASIMI_SN), follow_redirects=False
        ) as istemci:
            async with istemci.stream(
                "POST", adres, content=govde, headers=basliklar
            ) as yanit:
                durum = yanit.status_code
                ham = await _sinirli_oku(yanit)
    except httpx.TimeoutException as hata:
        raise CalistirmaHatasi("arac_zaman_asimi", sinir=ZAMAN_ASIMI_SN) from hata
    except httpx.HTTPError as hata:
        raise CalistirmaHatasi("arac_baglanti_hatasi") from hata

    if durum >= 300:
        # Yönlendirmeler izlenmez (SSRF kaçışı olmasın); 2xx dışı her yanıt hatadır.
        raise CalistirmaHatasi("arac_http_hatasi", durum=durum)
    return _yanit_coz(ham)


# -- çalıştırma -------------------------------------------------------------


async def _cagri_yaz(
    oturum: AsyncSession,
    *,
    org_id: int,
    arac: Arac,
    argumanlar: dict[str, Any],
    sonuc: dict[str, Any],
    durum: AracCagrisiDurumu,
    gecikme_ms: int,
    hata: str | None,
    konusma_id: int | None,
    mesaj_id: int | None,
) -> None:
    oturum.add(
        AracCagrisi(
            org_id=org_id,
            konusma_id=konusma_id,
            mesaj_id=mesaj_id,
            arac_id=arac.id,
            ad=arac.slug,
            argumanlar=argumanlar,
            sonuc=sonuc,
            durum=durum,
            gecikme_ms=gecikme_ms,
            hata=hata,
        )
    )
    await oturum.flush()


async def arac_calistir(
    oturum: AsyncSession,
    *,
    org_id: int,
    arac: Arac,
    argumanlar: dict[str, Any],
    konusma_id: int | None = None,
    mesaj_id: int | None = None,
) -> dict[str, Any]:
    """Aracı çalıştırır ve çağrıyı `arac_cagrisi` tablosuna yazar.

    Dönen sözlük::

        {"durum": "basarili"|"hata", "sonuc": {...}, "hata": str|None,
         "kod": str|None, "gecikme_ms": int}

    Yalnızca argüman şema ihlali `GecersizIstek` yükseltir (HTTP 400).
    """
    if arac.org_id != org_id or not arac.etkin:
        raise Bulunamadi(
            "arac_bulunamadi", {"arac_id": arac.id}, kod="arac_bulunamadi"
        )

    ham = argumanlari_dogrula(arac, argumanlar)

    baslangic = time.perf_counter()
    durum = AracCagrisiDurumu.basarili
    kod: str | None = None
    hata_metni: str | None = None
    try:
        sonuc = (
            _yerlesik_calistir(arac.slug, ham)
            if yerlesik_mi(arac)
            else await _webhook_calistir(arac, ham)
        )
    except CalistirmaHatasi as hata:
        sonuc = {"hata": hata.metin}
        durum = AracCagrisiDurumu.hata
        kod = hata.kod
        hata_metni = hata.metin
    except GecersizIstek as hata:
        metin = mesaj(hata.mesaj, VARSAYILAN_DIL, **hata.ceviriler)
        sonuc = {"hata": metin}
        durum = AracCagrisiDurumu.hata
        kod = hata.kod
        hata_metni = metin

    gecikme_ms = int((time.perf_counter() - baslangic) * 1000)
    await _cagri_yaz(
        oturum,
        org_id=org_id,
        arac=arac,
        argumanlar=ham,
        sonuc=sonuc,
        durum=durum,
        gecikme_ms=gecikme_ms,
        hata=hata_metni,
        konusma_id=konusma_id,
        mesaj_id=mesaj_id,
    )
    return {
        "durum": durum.value,
        "sonuc": sonuc,
        "hata": hata_metni,
        "kod": kod,
        "gecikme_ms": gecikme_ms,
    }
