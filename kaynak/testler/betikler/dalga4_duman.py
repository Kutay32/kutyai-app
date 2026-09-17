"""Dalga 4 uçtan uca duman betiği — tek komut, kendi kendine yeten.

Ayağa kaldırdıkları (hepsi geçici kaynak, betik bitince kapanır):
  * arka uç       : `uvicorn arkauc.app.main:app` alt süreç (127.0.0.1:8099)
  * sahte upstream: bu dosyanın içinde, iş parçacığı (127.0.0.1:8098)
  * sahte webhook : bu dosyanın içinde, iş parçacığı (127.0.0.1:8097)
  * SQLite        : geçici dizinde (`KUTYAI_VERITABANI_URL`), depo dosyasına dokunulmaz

Kullanım:
  ./.venv/Scripts/python.exe kaynak/testler/betikler/dalga4_duman.py

Kanıt: `kaynak/testler/kanit/dalga4-duman.json` — her adım
`{ad, komut, beklenen, gozlenen, sonuc}` biçiminde yazılır. Çıkış kodu:
kalan adım varsa 1, yoksa 0.

Senaryolar: kiracılık (iki organizasyon), API anahtarı, denetim izi/konuşma
logları, kullanım özeti, dosya→RAG, araç çağrısı (HMAC imzalı webhook),
plan/kota, i18n ve medya üretimi.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import math
import os
import pathlib
import re
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import zlib
from datetime import datetime, timezone
from typing import Any, AsyncIterator

import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

KOK = pathlib.Path(__file__).resolve().parents[3]
KANIT_YOLU = KOK / "kaynak" / "testler" / "kanit" / "dalga4-duman.json"

ARKA_UC_PORT = 8099
UPSTREAM_PORT = 8098
WEBHOOK_PORT = 8097

API = f"http://127.0.0.1:{ARKA_UC_PORT}/api/v1"
UPSTREAM_TEMEL = f"http://127.0.0.1:{UPSTREAM_PORT}/v1"
WEBHOOK_UCU = f"http://127.0.0.1:{WEBHOOK_PORT}/kanca"

IMZA_ANAHTARI = "duman-arac-imza-anahtari-2026"
YONETICI_EPOSTA = "duman@kutyai.example.com"
YONETICI_PAROLA = "duman-parola-2026"

MODEL_SOHBET = "sahte-sohbet-1"
MODEL_GORUNTU = "sahte-gorsel-1"
MODEL_SES = "sahte-ses-1"
MARKA = "DUMAN-KELIMESI-9147"
METIN_DOSYASI = (
    "KutyAI duman belgesi.\n"
    f"Bu paragraf {MARKA} anahtarını taşır ve bilgi tabanı aramasında "
    "benzer parça olarak dönmelidir.\n"
    "İkinci satır yalnızca parçalama için dolgu metnidir.\n"
)
AZAMI_KOTA_DENEMESI = 260

#: Sahte 1x1 PNG (imza baytları `gorsel_mime` sniffi için geçerli).
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg=="
)

# ---------------------------------------------------------------------------
# Kanıt defteri
# ---------------------------------------------------------------------------

ADIMLAR: list[dict[str, str]] = []
GECTI: list[str] = []
KALDI: list[str] = []

#: Sahte sunucuların gördüğü istekler (kanıt ve çapraz doğrulama için).
KAYITLAR: dict[str, list[dict[str, Any]]] = {"upstream": [], "webhook": []}


def adim(ad: str, komut: str, beklenen: str, gozlenen: str, gecti: bool) -> bool:
    """Tek bir adımı kaydeder ve konsola yazar."""
    ADIMLAR.append(
        {
            "ad": ad,
            "komut": komut,
            "beklenen": beklenen,
            "gozlenen": gozlenen,
            "sonuc": "gecti" if gecti else "kaldi",
        }
    )
    (GECTI if gecti else KALDI).append(ad)
    print(f"[{'GEÇTİ' if gecti else 'KALDI'}] {ad} — {gozlenen}")
    return gecti


def _kod(yanit: httpx.Response) -> str | None:
    """Hata zarfından `kod` alanını çeker."""
    try:
        return ((yanit.json() or {}).get("hata") or {}).get("kod")
    except ValueError:
        return None


def _ozet(yanit: httpx.Response, sinir: int = 260) -> str:
    """`<durum> :: <gövde>` biçiminde kısa yanıt özeti."""
    try:
        govde = json.dumps(yanit.json(), ensure_ascii=False)
    except ValueError:
        govde = yanit.text
    return f"{yanit.status_code} :: {govde[:sinir]}"


def _hata_ozeti(yanit: httpx.Response) -> str:
    return f"{yanit.status_code} kod={_kod(yanit)} :: {yanit.text[:200]}"


def _sse_ayristir(govde: str) -> list[tuple[str, Any]]:
    """SSE gövdesini `(olay, veri)` listesine çevirir."""
    olaylar: list[tuple[str, Any]] = []
    ad: str | None = None
    for satir in govde.splitlines():
        if satir.startswith("event: "):
            ad = satir[len("event: ") :].strip()
        elif satir.startswith("data: "):
            ham = satir[len("data: ") :]
            try:
                veri: Any = json.loads(ham)
            except ValueError:
                veri = ham
            olaylar.append((ad or "mesaj", veri))
    return olaylar


# ---------------------------------------------------------------------------
# Sahte upstream (8098): OpenAI uyumlu sohbet, gömme, görsel ve ses
# ---------------------------------------------------------------------------

upstream = FastAPI(title="dalga4 sahte upstream")
BOYUT = 96


def _vektor(metin: str) -> list[float]:
    """Sözcük torbası gömlemi: aynı sözcükleri paylaşan metinler benzemeli."""
    vektor = [0.0] * BOYUT
    for parca in re.findall(r"[0-9A-Za-zÇĞİÖŞÜçğıöşü_]+", metin.lower()):
        vektor[zlib.crc32(parca.encode("utf-8")) % BOYUT] += 1.0
    vektor = [deger + 0.01 for deger in vektor]
    norm = math.sqrt(sum(deger * deger for deger in vektor)) or 1.0
    return [deger / norm for deger in vektor]


def _sse_paket(icerik: dict[str, Any]) -> str:
    return f"data: {json.dumps(icerik, ensure_ascii=False)}\n\n"


def _son_kullanici(mesajlar: list[dict[str, Any]]) -> str:
    for mesaj in reversed(mesajlar):
        if mesaj.get("role") == "user":
            return str(mesaj.get("content") or "")
    return ""


def _sema_argumanlari(arac: dict[str, Any]) -> dict[str, Any]:
    """Araç şemasından geçerli bir örnek argüman sözlüğü üretir."""
    sema = (arac.get("function") or {}).get("parameters") or {}
    argumanlar: dict[str, Any] = {}
    for alan, tanim in (sema.get("properties") or {}).items():
        tur = (tanim or {}).get("type")
        argumanlar[alan] = {
            "string": "duman",
            "integer": 1,
            "number": 1.0,
            "boolean": True,
            "array": [],
            "object": {},
        }.get(tur, "duman")
    return argumanlar


@upstream.get("/v1/models")
@upstream.get("/models")
async def upstream_modeller() -> dict[str, Any]:
    return {
        "object": "list",
        "data": [
            {"id": MODEL_SOHBET, "object": "model", "owned_by": "duman"},
            {"id": MODEL_GORUNTU, "object": "model", "owned_by": "duman"},
            {"id": MODEL_SES, "object": "model", "owned_by": "duman"},
            {"id": "sahte-gomme-1", "object": "model", "owned_by": "duman"},
        ],
    }


async def _upstream_sohbet(istek: Request) -> Response:
    govde = await istek.json()
    KAYITLAR["upstream"].append({"yol": "chat/completions", "govde": govde})
    mesajlar = govde.get("messages") or []
    araclar = govde.get("tools") or []
    arac_sonucu_var = any(mesaj.get("role") == "tool" for mesaj in mesajlar)
    akis = bool(govde.get("stream"))
    kullanim = {"prompt_tokens": 12, "completion_tokens": 7, "total_tokens": 19}
    ortak = {"id": "duman-1", "object": "chat.completion", "model": govde.get("model")}

    if araclar and not arac_sonucu_var:
        arac = araclar[0]
        ad = (arac.get("function") or {}).get("name") or "bilinmeyen"
        argumanlar = json.dumps(_sema_argumanlari(arac), ensure_ascii=False)
        cagri = {
            "index": 0,
            "id": "cagri_duman_1",
            "type": "function",
            "function": {"name": ad, "arguments": argumanlar},
        }
        if not akis:
            return JSONResponse(
                {
                    **ortak,
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": None, "tool_calls": [cagri]},
                            "finish_reason": "tool_calls",
                        }
                    ],
                    "usage": kullanim,
                }
            )

        async def arac_akisi() -> AsyncIterator[str]:
            yield _sse_paket(
                {"choices": [{"index": 0, "delta": {"tool_calls": [cagri]}, "finish_reason": None}]}
            )
            yield _sse_paket(
                {
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}],
                    "usage": kullanim,
                }
            )
            yield "data: [DONE]\n\n"

        return StreamingResponse(arac_akisi(), media_type="text/event-stream")

    icerik = f"Duman yanıtı: {_son_kullanici(mesajlar)[:60]}"
    if not akis:
        return JSONResponse(
            {
                **ortak,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": icerik},
                        "finish_reason": "stop",
                    }
                ],
                "usage": kullanim,
            }
        )

    parcalar = [icerik[indis : indis + 12] for indis in range(0, len(icerik), 12)] or [""]

    async def icerik_akisi() -> AsyncIterator[str]:
        for parca in parcalar:
            yield _sse_paket(
                {"choices": [{"index": 0, "delta": {"content": parca}, "finish_reason": None}]}
            )
        yield _sse_paket(
            {
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                "usage": kullanim,
            }
        )
        yield "data: [DONE]\n\n"

    return StreamingResponse(icerik_akisi(), media_type="text/event-stream")


upstream.add_api_route("/v1/chat/completions", _upstream_sohbet, methods=["POST"])
upstream.add_api_route("/chat/completions", _upstream_sohbet, methods=["POST"])


async def _upstream_gomme(istek: Request) -> dict[str, Any]:
    govde = await istek.json()
    KAYITLAR["upstream"].append({"yol": "embeddings", "govde": govde})
    girdiler = govde.get("input") or []
    if isinstance(girdiler, str):
        girdiler = [girdiler]
    return {
        "object": "list",
        "model": govde.get("model"),
        "data": [
            {"object": "embedding", "index": sira, "embedding": _vektor(str(metin))}
            for sira, metin in enumerate(girdiler)
        ],
        "usage": {"prompt_tokens": 4, "total_tokens": 4},
    }


upstream.add_api_route("/v1/embeddings", _upstream_gomme, methods=["POST"])
upstream.add_api_route("/embeddings", _upstream_gomme, methods=["POST"])


async def _upstream_gorsel(istek: Request) -> dict[str, Any]:
    govde = await istek.json()
    KAYITLAR["upstream"].append({"yol": "images/generations", "govde": govde})
    adet = max(1, min(int(govde.get("n") or 1), 4))
    kodlu = base64.b64encode(PNG_1X1).decode("ascii")
    return {
        "created": int(time.time()),
        "data": [{"b64_json": kodlu, "revised_prompt": govde.get("prompt")} for _ in range(adet)],
    }


upstream.add_api_route("/v1/images/generations", _upstream_gorsel, methods=["POST"])
upstream.add_api_route("/images/generations", _upstream_gorsel, methods=["POST"])


async def _upstream_ses(istek: Request) -> Response:
    govde = await istek.json()
    KAYITLAR["upstream"].append({"yol": "audio/speech", "govde": govde})
    bicim = str(govde.get("response_format") or "mp3")
    return Response(content=b"ID3" + b"\x00" * 64 + bicim.encode("ascii"), media_type="audio/mpeg")


upstream.add_api_route("/v1/audio/speech", _upstream_ses, methods=["POST"])
upstream.add_api_route("/audio/speech", _upstream_ses, methods=["POST"])


# ---------------------------------------------------------------------------
# Sahte webhook alıcısı (8097): HMAC-SHA256 imzasını doğrular
# ---------------------------------------------------------------------------

webhook = FastAPI(title="dalga4 sahte webhook")


@webhook.post("/kanca")
async def webhook_kanca(istek: Request) -> Response:
    govde = await istek.body()
    gelen = istek.headers.get("x-kutyai-imza", "")
    beklenen = "sha256=" + hmac.new(
        IMZA_ANAHTARI.encode("utf-8"), govde, hashlib.sha256
    ).hexdigest()
    dogrulandi = hmac.compare_digest(gelen, beklenen)
    KAYITLAR["webhook"].append(
        {
            "imza": gelen,
            "beklenen": beklenen,
            "dogrulandi": dogrulandi,
            "govde": govde.decode("utf-8", "replace"),
        }
    )
    if not dogrulandi:
        return JSONResponse({"ok": False, "neden": "imza"}, status_code=401)
    return JSONResponse({"ok": True, "yankı": govde.decode("utf-8", "replace")})


# ---------------------------------------------------------------------------
# Sunucu yardımcıları
# ---------------------------------------------------------------------------


class IplikSunucusu:
    """Uvicorn'u iş parçacığında koşar (sahte sunucular için)."""

    def __init__(self, ad: str, uygulama: FastAPI, port: int) -> None:
        self.ad = ad
        self.port = port
        yapilandirma = uvicorn.Config(
            uygulama, host="127.0.0.1", port=port, log_level="warning", access_log=False
        )
        self.sunucu = uvicorn.Server(yapilandirma)
        self.iplik = threading.Thread(target=self.sunucu.run, name=f"sahte-{ad}", daemon=True)

    def basla(self, sn: float = 20.0) -> None:
        self.iplik.start()
        bitis = time.monotonic() + sn
        while time.monotonic() < bitis:
            if self.sunucu.started:
                return
            if not self.iplik.is_alive():
                raise RuntimeError(f"Sahte {self.ad} sunucusu başlatılamadı (port {self.port}).")
            time.sleep(0.05)
        raise RuntimeError(f"Sahte {self.ad} sunucusu {sn:.0f} sn içinde açılmadı.")

    def dur(self) -> None:
        self.sunucu.should_exit = True
        self.iplik.join(timeout=5.0)


def _port_bos(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as soket:
        soket.settimeout(0.5)
        return soket.connect_ex(("127.0.0.1", port)) != 0


def _bosluk_bekle(port: int, sn: float = 10.0) -> None:
    bitis = time.monotonic() + sn
    while time.monotonic() < bitis:
        if _port_bos(port):
            return
        time.sleep(0.1)


class ArkaUc:
    """`uvicorn arkauc.app.main:app` alt sürecini yönetir."""

    def __init__(self, gecici: pathlib.Path) -> None:
        self.gecici = gecici
        self.gunluk = gecici / "arka-uc.log"
        self.komut = [
            sys.executable,
            "-m",
            "uvicorn",
            "arkauc.app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(ARKA_UC_PORT),
            "--log-level",
            "warning",
        ]
        self.surec: subprocess.Popen[bytes] | None = None
        self._dosya: Any = None

    def basla(self, sn: float = 90.0) -> None:
        ortam = {**os.environ, **_ortam_degiskenleri(self.gecici)}
        self._dosya = self.gunluk.open("wb")
        self.surec = subprocess.Popen(
            self.komut, cwd=str(KOK), env=ortam, stdout=self._dosya, stderr=subprocess.STDOUT
        )
        bitis = time.monotonic() + sn
        with httpx.Client(timeout=5.0) as istemci:
            while time.monotonic() < bitis:
                if self.surec.poll() is not None:
                    raise RuntimeError(
                        "Arka uç erken kapandı:\n" + self.gunluk_tail()
                    )
                try:
                    yanit = istemci.get(f"{API}/saglik")
                    if yanit.status_code == 200:
                        return
                except httpx.HTTPError:
                    pass
                time.sleep(0.25)
        raise RuntimeError(f"Arka uç {sn:.0f} sn içinde hazır olmadı:\n" + self.gunluk_tail())

    def gunluk_tail(self, satir: int = 25) -> str:
        try:
            icerik = self.gunluk.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return "(günlük okunamadı)"
        return "\n".join(icerik[-satir:])

    def dur(self) -> None:
        if self.surec is not None and self.surec.poll() is None:
            self.surec.terminate()
            try:
                self.surec.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.surec.kill()
                self.surec.wait(timeout=5)
        if self._dosya is not None:
            self._dosya.close()


def _ortam_degiskenleri(gecici: pathlib.Path) -> dict[str, str]:
    """Arka uç alt sürecinin geçici ortamı (depo `.env` değerlerini ezer)."""
    veritabani = (gecici / "kutyai.db").as_posix()
    return {
        "KUTYAI_ORTAM": "test",
        "KUTYAI_VERITABANI_URL": f"sqlite:///{veritabani}",
        "KUTYAI_GIZLI_ANAHTAR": base64.urlsafe_b64encode(os.urandom(48)).decode("ascii"),
        "KUTYAI_SIFRELEME_ANAHTARI": base64.urlsafe_b64encode(os.urandom(32)).decode("ascii"),
        "KUTYAI_DOSYA_DIZINI": (gecici / "dosyalar").as_posix(),
        "KUTYAI_ARAC_IMZA_ANAHTARI": IMZA_ANAHTARI,
        "KUTYAI_ARAC_YEREL_IZIN": "true",
        "KUTYAI_ORAN_SINIRI_ISTEK_DK": "100000",
        "KUTYAI_ORAN_SINIRI_KIMLIK_DK": "100000",
        "KUTYAI_ODEME_SAGLAYICI": "yerel",
    }


# ---------------------------------------------------------------------------
# HTTP / SQLite yardımcıları
# ---------------------------------------------------------------------------

ISTEMCI = httpx.Client(timeout=90.0)
VERITABANI: pathlib.Path = pathlib.Path()


def cagir(
    yontem: str,
    yol: str,
    *,
    jeton: str | None = None,
    org: str | None = None,
    anahtar: str | None = None,
    basliklar: dict[str, str] | None = None,
    **kw: Any,
) -> httpx.Response:
    """API'ye kimlik/kiracı başlıklarıyla istek atar."""
    tumu = dict(basliklar or {})
    if jeton:
        tumu["Authorization"] = f"Bearer {jeton}"
    if anahtar:
        tumu["Authorization"] = f"Bearer {anahtar}"
    if org:
        tumu["X-Organizasyon"] = org
    return ISTEMCI.request(yontem, f"{API}{yol}", headers=tumu, **kw)


def sql(ifade: str, parametreler: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
    """Geçici SQLite'ta doğrudan sorgu (test fikstürü)."""
    baglanti = sqlite3.connect(VERITABANI, timeout=15)
    try:
        return baglanti.execute(ifade, parametreler).fetchall()
    finally:
        baglanti.close()


def sql_yaz(ifade: str, parametreler: tuple[Any, ...] = ()) -> None:
    """Geçici SQLite'ta doğrudan yazma (yalnız kurulum fikstürleri için)."""
    baglanti = sqlite3.connect(VERITABANI, timeout=15)
    try:
        baglanti.execute(ifade, parametreler)
        baglanti.commit()
    finally:
        baglanti.close()


def _bekle(sn: float) -> None:
    time.sleep(max(0.0, sn))


# ---------------------------------------------------------------------------
# Duman senaryosu
# ---------------------------------------------------------------------------


def senaryoyu_kos() -> None:
    """Tüm adımları koşar; sonuçları `ADIMLAR`a yazar."""
    # -- S0: kurulum, panel girişi, varsayılan organizasyon ---------------
    saglik = cagir("GET", "/saglik")
    adim(
        "S0.1 Sağlık ucu",
        "GET /api/v1/saglik",
        "200 durum=ayakta",
        _ozet(saglik),
        saglik.status_code == 200 and saglik.json().get("durum") == "ayakta",
    )

    kurulum = cagir(
        "POST",
        "/kurulum",
        json={
            "marka_adi": "Duman A.Ş.",
            "yonetici": {
                "eposta": YONETICI_EPOSTA,
                "ad_soyad": "Duman Yönetici",
                "parola": YONETICI_PAROLA,
            },
            "bdm": {
                "gorunen_ad": "Duman Varsayılan",
                "slug": "duman-varsayilan",
                "saglayici": "ozel",
                "temel_url": UPSTREAM_TEMEL,
                "upstream_model": MODEL_SOHBET,
                "yetenekler": {"akis": True, "gorsel": False, "ses": False, "arac": False},
            },
            "dogrula": True,
        },
    )
    kurulum_govde = kurulum.json() if kurulum.status_code == 201 else {}
    yeteneksiz_bdm = (kurulum_govde.get("bdm") or {}).get("id")
    adim(
        "S0.2 Kurulum sihirbazı",
        "POST /api/v1/kurulum (dogrula=true)",
        "201 kurulum_tamam=true + upstream doğrulaması başarılı",
        _ozet(kurulum),
        kurulum.status_code == 201
        and kurulum_govde.get("kurulum_tamam") is True
        and (kurulum_govde.get("dogrulama") or {}).get("basarili") is True,
    )

    giris = cagir(
        "POST", "/kimlik/panel-giris", json={"eposta": YONETICI_EPOSTA, "parola": YONETICI_PAROLA}
    )
    jeton = (giris.json() or {}).get("erisim_jetonu") if giris.status_code == 200 else None
    adim(
        "S0.3 Panel girişi (personel kapısı)",
        "POST /api/v1/kimlik/panel-giris",
        "200 erisim_jetonu",
        _ozet(giris),
        bool(jeton),
    )
    if not jeton:
        return

    varsayilan_bdm = cagir("GET", "/bdm", jeton=jeton)
    organizasyonlar = cagir("GET", "/organizasyonlar", jeton=jeton)
    slugs = [k.get("slug") for k in (organizasyonlar.json() or [])]
    adim(
        "S0.4 Varsayılan organizasyon çözümü",
        "GET /api/v1/bdm (başlıksız) + GET /api/v1/organizasyonlar",
        "200 ve üyelik listesinde slug=varsayilan",
        f"bdm={varsayilan_bdm.status_code} organizasyonlar={slugs}",
        varsayilan_bdm.status_code == 200 and "varsayilan" in slugs,
    )

    # -- S1: iki organizasyon ve kiracılık -------------------------------
    a_yanit = cagir(
        "POST", "/organizasyonlar", jeton=jeton, json={"ad": "Duman A", "slug": "duman-a"}
    )
    b_yanit = cagir(
        "POST", "/organizasyonlar", jeton=jeton, json={"ad": "Duman B", "slug": "duman-b"}
    )
    a_org = (a_yanit.json() or {}).get("id") if a_yanit.status_code == 201 else None
    b_org = (b_yanit.json() or {}).get("id") if b_yanit.status_code == 201 else None
    adim(
        "S1.1 İki organizasyon oluşturma (A, B)",
        "POST /api/v1/organizasyonlar ×2",
        "201 + 201 (A id≠B id)",
        f"A={_ozet(a_yanit, 90)} | B={_ozet(b_yanit, 90)}",
        a_yanit.status_code == 201 and b_yanit.status_code == 201 and a_org != b_org,
    )
    if not a_org or not b_org:
        return

    bdm_govde = {
        "gorunen_ad": "Duman A Modeli",
        "slug": "duman-a-modeli",
        "saglayici": "ozel",
        "temel_url": UPSTREAM_TEMEL,
        "upstream_model": MODEL_SOHBET,
        "yetenekler": {"akis": True, "gorsel": True, "ses": True, "arac": True},
    }
    bdm_a_yanit = cagir("POST", "/bdm", jeton=jeton, org="duman-a", json=bdm_govde)
    bdm_a = (bdm_a_yanit.json() or {}).get("id") if bdm_a_yanit.status_code == 201 else None
    adim(
        "S1.2 A organizasyonunda BDM oluştur",
        "POST /api/v1/bdm (X-Organizasyon: duman-a)",
        "201",
        _ozet(bdm_a_yanit),
        bdm_a_yanit.status_code == 201,
    )

    bdm_b_yanit = cagir(
        "POST",
        "/bdm",
        jeton=jeton,
        org="duman-b",
        json={**bdm_govde, "gorunen_ad": "Duman B Modeli", "slug": "duman-b-modeli"},
    )
    bdm_b = (bdm_b_yanit.json() or {}).get("id") if bdm_b_yanit.status_code == 201 else None
    adim(
        "S1.3 B organizasyonunda kendi BDM'i",
        "POST /api/v1/bdm (X-Organizasyon: duman-b)",
        "201",
        _ozet(bdm_b_yanit),
        bdm_b_yanit.status_code == 201,
    )
    if not bdm_a or not bdm_b:
        return

    satirlar = sql("SELECT id, org_id, slug FROM bdm WHERE id = ?", (bdm_a,))
    adim(
        "S1.4 BDM kaydı gerçekten A organizasyonuna mı yazıldı? (DB)",
        f"sqlite: SELECT id, org_id, slug FROM bdm WHERE id={bdm_a}",
        f"org_id = A ({a_org})",
        f"bdm satırı={satirlar} A org_id={a_org}",
        bool(satirlar) and satirlar[0][1] == a_org,
    )

    hazir = cagir("POST", f"/bdm/hazirlama/{bdm_a}/dogrula", jeton=jeton, org="duman-a")
    satirlar = sql("SELECT durum FROM bdm WHERE id = ?", (bdm_a,))
    adim(
        "S1.5 A BDM'i upstream doğrulamasıyla hazır duruma geçer",
        f"POST /api/v1/bdm/hazirlama/{bdm_a}/dogrula (A) + DB durum",
        "200 basarili=true ve DB durum=hazir",
        f"{_ozet(hazir)} DB={satirlar}",
        hazir.status_code == 200
        and (hazir.json() or {}).get("basarili") is True
        and bool(satirlar)
        and satirlar[0][0] == "hazir",
    )
    cagir("POST", f"/bdm/hazirlama/{bdm_b}/dogrula", jeton=jeton, org="duman-b")

    liste_b = cagir("GET", "/bdm", jeton=jeton, org="duman-b")
    b_idler = [kayit.get("id") for kayit in (liste_b.json() or [])]
    adim(
        "S1.6 B listesinde A'nın BDM'i görünmez",
        "GET /api/v1/bdm (X-Organizasyon: duman-b)",
        f"{bdm_a} numaralı BDM B listesinde yok",
        f"200 B listesi={b_idler} (A bdm={bdm_a})",
        liste_b.status_code == 200 and bdm_a not in b_idler,
    )

    yamala_b = cagir(
        "PATCH", f"/bdm/{bdm_a}", jeton=jeton, org="duman-b", json={"aciklama": "B denedi"}
    )
    adim(
        "S1.7 Başka organizasyonun BDM'i değiştirilemez",
        f"PATCH /api/v1/bdm/{bdm_a} (X-Organizasyon: duman-b)",
        "404 bulunamadi",
        _hata_ozeti(yamala_b),
        yamala_b.status_code == 404 and _kod(yamala_b) == "bulunamadi",
    )

    sil_b = cagir("DELETE", f"/bdm/{bdm_a}", jeton=jeton, org="duman-b")
    adim(
        "S1.8 Başka organizasyonun BDM'i silinemez",
        f"DELETE /api/v1/bdm/{bdm_a} (X-Organizasyon: duman-b)",
        "404 bulunamadi",
        _hata_ozeti(sil_b),
        sil_b.status_code == 404 and _kod(sil_b) == "bulunamadi",
    )

    hazirlama_b = cagir("POST", f"/bdm/hazirlama/{bdm_a}/dogrula", jeton=jeton, org="duman-b")
    adim(
        "S1.9 Başka organizasyonun BDM'i hazırlanamaz",
        f"POST /api/v1/bdm/hazirlama/{bdm_a}/dogrula (X-Organizasyon: duman-b)",
        "404 bulunamadi",
        _hata_ozeti(hazirlama_b),
        hazirlama_b.status_code == 404 and _kod(hazirlama_b) == "bulunamadi",
    )

    yonetim_b = cagir("POST", f"/bdm/yonetim/{bdm_a}/durdur", jeton=jeton, org="duman-b")
    adim(
        "S1.10 Başka organizasyonun BDM yönetimi kullanılamaz",
        f"POST /api/v1/bdm/yonetim/{bdm_a}/durdur (X-Organizasyon: duman-b)",
        "404 bulunamadi",
        _hata_ozeti(yonetim_b),
        yonetim_b.status_code == 404 and _kod(yonetim_b) == "bulunamadi",
    )

    liste_a = cagir("GET", "/bdm", jeton=jeton, org="duman-a")
    a_idler = [kayit.get("id") for kayit in (liste_a.json() or [])]
    adim(
        "S1.11 A kendi BDM'ine erişmeye devam eder",
        "GET /api/v1/bdm (X-Organizasyon: duman-a)",
        f"200 ve liste {bdm_a} içerir",
        f"200 A listesi={a_idler}",
        liste_a.status_code == 200 and bdm_a in a_idler,
    )

    # -- S2: API anahtarı -------------------------------------------------
    anahtar_yanit = cagir(
        "POST",
        "/api-anahtarlari",
        jeton=jeton,
        org="duman-a",
        json={"ad": "Duman Anahtarı", "izinli_modeller": ["duman-a-modeli"]},
    )
    anahtar_govde = anahtar_yanit.json() if anahtar_yanit.status_code == 201 else {}
    anahtar_id = anahtar_govde.get("id")
    tam_anahtar = anahtar_govde.get("tam_anahtar")
    adim(
        "S2.1 A organizasyonunda API anahtarı üret",
        "POST /api/v1/api-anahtarlari (X-Organizasyon: duman-a)",
        "201 + tam_anahtar bir kez döner",
        _ozet(anahtar_yanit),
        anahtar_yanit.status_code == 201 and bool(tam_anahtar),
    )
    if not anahtar_id or not tam_anahtar:
        return

    satirlar = sql("SELECT id, org_id FROM api_anahtari WHERE id = ?", (anahtar_id,))
    adim(
        "S2.2 Anahtar kaydı A organizasyonuna yazıldı (DB)",
        f"sqlite: SELECT id, org_id FROM api_anahtari WHERE id={anahtar_id}",
        f"org_id = A ({a_org})",
        f"satır={satirlar} A org_id={a_org}",
        bool(satirlar) and satirlar[0][1] == a_org,
    )

    anahtarlar_b = cagir("GET", "/api-anahtarlari", jeton=jeton, org="duman-b")
    b_anahtar_idler = [kayit.get("id") for kayit in (anahtarlar_b.json() or [])]
    adim(
        "S2.3 A'nın anahtarı B listesinde görünmez",
        "GET /api/v1/api-anahtarlari (X-Organizasyon: duman-b)",
        f"{anahtar_id} B listesinde yok",
        f"200 B listesi={b_anahtar_idler} (A anahtarı={anahtar_id})",
        anahtarlar_b.status_code == 200 and anahtar_id not in b_anahtar_idler,
    )

    iptal_b = cagir("POST", f"/api-anahtarlari/{anahtar_id}/iptal", jeton=jeton, org="duman-b")
    adim(
        "S2.4 B, A'nın anahtarını iptal edemez",
        f"POST /api/v1/api-anahtarlari/{anahtar_id}/iptal (X-Organizasyon: duman-b)",
        "404 bulunamadi",
        _hata_ozeti(iptal_b),
        iptal_b.status_code == 404 and _kod(iptal_b) == "bulunamadi",
    )

    anahtar_sohbet = cagir(
        "POST",
        "/sohbet",
        anahtar=tam_anahtar,
        json={"bdm_id": bdm_a, "mesaj": "Anahtar kimliğiyle ilk mesaj."},
    )
    sohbet_a_id = (anahtar_sohbet.json() or {}).get("konusma_id") if anahtar_sohbet.status_code == 200 else None
    adim(
        "S2.5 API anahtarı sohbet erişimi (jeton yerine anahtar)",
        "POST /api/v1/sohbet (Authorization: Bearer <tam_anahtar>)",
        "200 ve konusma_id",
        _ozet(anahtar_sohbet),
        anahtar_sohbet.status_code == 200 and bool(sohbet_a_id),
    )

    # -- S3: denetim izi ve konuşma logları -------------------------------
    denetim_a = cagir(
        "GET", "/islem-kayitlari", jeton=jeton, org="duman-a", params={"eylem": "bdm.olusturuldu"}
    )
    kayitlar_a = (denetim_a.json() or {}).get("kayitlar") or []
    adim(
        "S3.1 A'nın denetim izi kendi kayıtlarını taşır",
        "GET /api/v1/islem-kayitlari?eylem=bdm.olusturuldu (A)",
        f"200 ve hedef_id={bdm_a}",
        f"200 toplam={(denetim_a.json() or {}).get('toplam')} hedefler="
        f"{[k.get('hedef_id') for k in kayitlar_a][:5]}",
        denetim_a.status_code == 200
        and any(str(k.get("hedef_id")) == str(bdm_a) for k in kayitlar_a),
    )

    denetim_b = cagir(
        "GET", "/islem-kayitlari", jeton=jeton, org="duman-b", params={"eylem": "bdm.olusturuldu"}
    )
    kayitlar_b = (denetim_b.json() or {}).get("kayitlar") or []
    adim(
        "S3.2 A'nın denetim kayıtları B'de görünmez",
        "GET /api/v1/islem-kayitlari?eylem=bdm.olusturuldu (B)",
        f"kayıtlar {bdm_a} hedefini içermez",
        f"200 B hedefler={[k.get('hedef_id') for k in kayitlar_b][:5]}",
        denetim_b.status_code == 200 and all(k.get("hedef_id") != bdm_a for k in kayitlar_b),
    )

    loglar_a = cagir("GET", "/loglar/konusmalar", jeton=jeton, org="duman-a")
    loglar_b = cagir("GET", "/loglar/konusmalar", jeton=jeton, org="duman-b")
    b_konusmalar = (loglar_b.json() or {}).get("kayitlar") or []
    adim(
        "S3.3 Konuşma logları organizasyona göre süzülür",
        "GET /api/v1/loglar/konusmalar (A) vs (B)",
        f"A'da {sohbet_a_id} var, B'de yok",
        f"A toplam={(loglar_a.json() or {}).get('toplam')} "
        f"B toplam={(loglar_b.json() or {}).get('toplam')} "
        f"B id'ler={[k.get('id') for k in b_konusmalar][:5]}",
        loglar_a.status_code == 200
        and int((loglar_a.json() or {}).get("toplam") or 0) >= 1
        and sohbet_a_id not in [k.get("id") for k in b_konusmalar],
    )

    # -- S4: kullanım özeti / zaman serisi --------------------------------
    ozet_a = cagir("GET", "/kullanim/ozet", jeton=jeton, org="duman-a")
    ozet_a_govde = ozet_a.json() if ozet_a.status_code == 200 else {}
    adim(
        "S4.1 A'nın kullanım özeti isteği sayar",
        "GET /api/v1/kullanim/ozet (A)",
        "200 toplam_istek≥1, toplam_token>0",
        _ozet(ozet_a),
        ozet_a.status_code == 200
        and int(ozet_a_govde.get("toplam_istek") or 0) >= 1
        and int(ozet_a_govde.get("toplam_token") or 0) > 0,
    )

    seri_a = cagir("GET", "/kullanim/zaman-serisi", jeton=jeton, org="duman-a", params={"gun": 30})
    seri_a_govde = seri_a.json() if seri_a.status_code == 200 else {}
    adim(
        "S4.2 A'nın zaman serisi dolu döner",
        "GET /api/v1/kullanim/zaman-serisi?gun=30 (A)",
        "200 seri boş değil",
        _ozet(seri_a),
        seri_a.status_code == 200 and bool(seri_a_govde.get("seri")),
    )

    ozet_b = cagir("GET", "/kullanim/ozet", jeton=jeton, org="duman-b")
    adim(
        "S4.3 A'nın kullanımı B özetine sızmaz",
        "GET /api/v1/kullanim/ozet (B)",
        "200 toplam_istek=0",
        _ozet(ozet_b),
        ozet_b.status_code == 200 and int((ozet_b.json() or {}).get("toplam_istek") or 0) == 0,
    )

    # -- S5: dosya → RAG --------------------------------------------------
    dosya_yanit = cagir(
        "POST",
        "/dosyalar",
        jeton=jeton,
        org="duman-a",
        files={"dosya": ("duman-belgesi.txt", METIN_DOSYASI.encode("utf-8"), "text/plain")},
    )
    dosya_govde = dosya_yanit.json() if dosya_yanit.status_code == 201 else {}
    dosya_id = dosya_govde.get("id")
    adim(
        "S5.1 A organizasyonuna metin dosyası yükle",
        "POST /api/v1/dosyalar (multipart dosya, text/plain)",
        "201 ve dosya kaydı",
        _ozet(dosya_yanit),
        dosya_yanit.status_code == 201 and bool(dosya_id),
    )
    if not dosya_id:
        return

    satirlar = sql("SELECT id, org_id FROM dosya WHERE id = ?", (dosya_id,))
    adim(
        "S5.2 Dosya kaydı A organizasyonuna yazıldı (DB)",
        f"sqlite: SELECT id, org_id FROM dosya WHERE id={dosya_id}",
        f"org_id = A ({a_org})",
        f"satır={satirlar}",
        bool(satirlar) and satirlar[0][1] == a_org,
    )

    belge_yanit = cagir(
        "POST",
        "/rag/belgeler",
        jeton=jeton,
        org="duman-a",
        json={"ad": "Duman Belgesi", "bdm_id": bdm_a, "dosya_id": dosya_id},
    )
    belge_govde = belge_yanit.json() if belge_yanit.status_code == 201 else {}
    belge_id = belge_govde.get("id")
    adim(
        "S5.3 Dosyadan RAG belgesi üret (parçala + göm)",
        "POST /api/v1/rag/belgeler {ad, bdm_id, dosya_id}",
        "201 parca_sayisi>0",
        _ozet(belge_yanit),
        belge_yanit.status_code == 201 and int(belge_govde.get("parca_sayisi") or 0) > 0,
    )
    if not belge_id:
        return

    arama_yanit = cagir(
        "POST",
        "/rag/ara",
        jeton=jeton,
        org="duman-a",
        json={"sorgu": MARKA, "bdm_id": bdm_a},
    )
    arama_govde = arama_yanit.json() if arama_yanit.status_code == 200 else {}
    sonuclar = arama_govde.get("sonuclar") or []
    adim(
        "S5.4 RAG araması benzer parçayı döndürür",
        f"POST /api/v1/rag/ara {{sorgu: {MARKA}}}",
        "200 sonuclar dolu ve ilk parça anahtarı taşır",
        _ozet(arama_yanit),
        arama_yanit.status_code == 200
        and bool(sonuclar)
        and MARKA in str(sonuclar[0].get("icerik") or ""),
    )

    kaynak_sohbet = cagir(
        "POST",
        "/sohbet",
        jeton=jeton,
        org="duman-a",
        json={"bdm_id": bdm_a, "mesaj": MARKA, "rag": True},
    )
    kaynak_sohbet_govde = kaynak_sohbet.json() if kaynak_sohbet.status_code == 200 else {}
    adim(
        "S5.5 RAG'li sohbet kaynak döndürür",
        "POST /api/v1/sohbet {rag: true}",
        "200 kaynaklar dolu",
        _ozet(kaynak_sohbet),
        kaynak_sohbet.status_code == 200 and bool(kaynak_sohbet_govde.get("kaynaklar")),
    )

    ekli_sohbet = cagir(
        "POST",
        "/sohbet",
        jeton=jeton,
        org="duman-a",
        json={"bdm_id": bdm_a, "mesaj": "Ekli dosyayı özetle.", "dosya_idleri": [dosya_id]},
    )
    ek_gonderildi = any(
        MARKA in json.dumps(kayit.get("govde") or {}, ensure_ascii=False)
        for kayit in KAYITLAR["upstream"]
    )
    adim(
        "S5.6 Sohbete dosya eki sistem istemine eklenir",
        "POST /api/v1/sohbet {dosya_idleri: [id]} + upstream gövdesi",
        "200 ve upstream isteğinde dosya metni",
        f"{_ozet(ekli_sohbet)} upstream'de_metin={ek_gonderildi}",
        ekli_sohbet.status_code == 200 and ek_gonderildi,
    )

    belge_b = cagir("GET", f"/rag/belgeler/{belge_id}", jeton=jeton, org="duman-b")
    arama_b = cagir(
        "POST", "/rag/ara", jeton=jeton, org="duman-b", json={"sorgu": MARKA, "bdm_id": bdm_b}
    )
    adim(
        "S5.7 A'nın belgesi B'ye görünmez (detay 404, arama boş)",
        f"GET /api/v1/rag/belgeler/{belge_id} (B) + POST /rag/ara (B)",
        "404 belge_bulunamadi (ya da bulunamadi) ve B araması boş",
        f"detay={_hata_ozeti(belge_b)} arama={_ozet(arama_b, 120)}",
        belge_b.status_code == 404
        and _kod(belge_b) in ("belge_bulunamadi", "bulunamadi")
        and not ((arama_b.json() or {}).get("sonuclar") or []),
    )

    dosya_b = cagir(
        "POST",
        "/sohbet",
        jeton=jeton,
        org="duman-b",
        json={"bdm_id": bdm_b, "mesaj": "A'nın dosyası", "dosya_idleri": [dosya_id]},
    )
    adim(
        "S5.8 B, A'nın dosyasını sohbete ekleyemez",
        "POST /api/v1/sohbet {dosya_idleri: [A dosyası]} (B)",
        "404 bulunamadi",
        _hata_ozeti(dosya_b),
        dosya_b.status_code == 404 and _kod(dosya_b) == "bulunamadi",
    )

    # -- S6: araç çağrısı -------------------------------------------------
    arac_yanit = cagir(
        "POST",
        "/araclar",
        jeton=jeton,
        org="duman-a",
        json={
            "ad": "Duman Webhook Aracı",
            "slug": "duman-webhook",
            "aciklama": "Duman betiği için HMAC imzalı webhook",
            "tur": "webhook",
            "uc_noktasi": WEBHOOK_UCU,
            "basliklar": {"X-Duman": "1"},
            "json_sema": {
                "type": "object",
                "properties": {"sorgu": {"type": "string"}},
                "required": ["sorgu"],
                "additionalProperties": False,
            },
        },
    )
    arac_govde = arac_yanit.json() if arac_yanit.status_code == 201 else {}
    arac_id = arac_govde.get("id")
    adim(
        "S6.1 Webhook aracı oluştur",
        "POST /api/v1/araclar {tur: webhook, uc_noktasi: 127.0.0.1:8097}",
        "201 ve araç kaydı",
        _ozet(arac_yanit),
        arac_yanit.status_code == 201 and bool(arac_id),
    )
    if not arac_id:
        return

    deneme_oncesi = len(KAYITLAR["webhook"])
    dene_yanit = cagir(
        "POST",
        f"/araclar/{arac_id}/dene",
        jeton=jeton,
        org="duman-a",
        json={"argumanlar": {"sorgu": "duman"}},
    )
    dene_govde = dene_yanit.json() if dene_yanit.status_code == 200 else {}
    imza_kaydi = KAYITLAR["webhook"][deneme_oncesi:]
    adim(
        "S6.2 Araç çalıştırma + HMAC imza doğrulaması",
        f"POST /api/v1/araclar/{arac_id}/dene (sahte webhook imzayı doğrular)",
        "200 durum=basarili ve imza sha256=<hmac> geçerli",
        f"{_ozet(dene_yanit)} imza_doğrulandı="
        f"{[k['dogrulandi'] for k in imza_kaydi]}",
        dene_yanit.status_code == 200
        and dene_govde.get("durum") == "basarili"
        and bool(imza_kaydi)
        and all(k["dogrulandi"] for k in imza_kaydi),
    )

    arac_sohbet = cagir(
        "POST",
        "/sohbet",
        jeton=jeton,
        org="duman-a",
        json={"bdm_id": bdm_a, "mesaj": "Aracı kullan.", "arac_sluglari": ["duman-webhook"]},
    )
    arac_sohbet_govde = arac_sohbet.json() if arac_sohbet.status_code == 200 else {}
    cagrilar = arac_sohbet_govde.get("arac_cagrilari") or []
    adim(
        "S6.3 Sohbette araç turu (çağrı → sonuç → yanıt)",
        "POST /api/v1/sohbet {arac_sluglari: [duman-webhook]}",
        "200 arac_cagrilari dolu, içerik araç sonrası üretilir",
        _ozet(arac_sohbet),
        arac_sohbet.status_code == 200
        and bool(cagrilar)
        and cagrilar[0].get("durum") == "basarili"
        and bool(arac_sohbet_govde.get("icerik")),
    )

    akis_yanit = ISTEMCI.stream(
        "POST",
        f"{API}/sohbet/akis",
        headers={"Authorization": f"Bearer {jeton}", "X-Organizasyon": "duman-a"},
        json={"bdm_id": bdm_a, "mesaj": "Aracı akışta kullan.", "arac_sluglari": ["duman-webhook"]},
    )
    with akis_yanit as yanit:
        akis_govdesi = "".join(yanit.iter_text())
    olaylar = [ad for ad, _ in _sse_ayristir(akis_govdesi)]
    adim(
        "S6.4 SSE akışında araç olayları",
        "POST /api/v1/sohbet/akis {arac_sluglari}",
        "olaylar: baslangic, arac_cagrisi, arac_sonucu, parca, bitti",
        f"olaylar={olaylar}",
        {"baslangic", "arac_cagrisi", "arac_sonucu", "parca", "bitti"}.issubset(set(olaylar)),
    )

    cagri_kayitlari = sql("SELECT org_id, durum FROM arac_cagrisi WHERE arac_id = ?", (arac_id,))
    adim(
        "S6.5 Araç çağrı günlüğü organizasyona etiketlenir (DB)",
        f"sqlite: SELECT org_id, durum FROM arac_cagrisi WHERE arac_id={arac_id}",
        f"tüm satırlarda org_id = A ({a_org})",
        f"satırlar={cagri_kayitlari}",
        bool(cagri_kayitlari) and all(satir[0] == a_org for satir in cagri_kayitlari),
    )

    araclar_b = cagir("GET", "/araclar", jeton=jeton, org="duman-b")
    b_araclar = [kayit.get("id") for kayit in (araclar_b.json() or [])]
    adim(
        "S6.6 A'nın aracı B listesinde görünmez",
        "GET /api/v1/araclar (X-Organizasyon: duman-b)",
        f"{arac_id} B listesinde yok",
        f"200 B listesi={b_araclar}",
        araclar_b.status_code == 200 and arac_id not in b_araclar,
    )

    # -- S7: plan / kota --------------------------------------------------
    planlar = cagir("GET", "/faturalama/planlar", jeton=jeton, org="duman-a")
    plan_listesi = planlar.json() if planlar.status_code == 200 else []
    plan_deneme = next((p for p in plan_listesi if p.get("slug") == "deneme"), None)
    adim(
        "S7.1 Plan listesi",
        "GET /api/v1/faturalama/planlar",
        "200 ve deneme planı listede",
        _ozet(planlar),
        planlar.status_code == 200 and plan_deneme is not None,
    )
    if plan_deneme is None:
        return

    abonelik = cagir(
        "POST",
        "/faturalama/abonelik",
        jeton=jeton,
        org="duman-a",
        json={"plan_id": plan_deneme["id"], "donem_gun": 30},
    )
    abonelik_govde = abonelik.json() if abonelik.status_code == 201 else {}
    abonelik_durum = (abonelik_govde.get("abonelik") or {}).get("durum")
    adim(
        "S7.2 Plan seç + abonelik ve fatura üretimi",
        "POST /api/v1/faturalama/abonelik {plan_id: deneme}",
        "201 abonelik.durum=aktif + fatura",
        _ozet(abonelik),
        abonelik.status_code == 201
        and abonelik_durum == "aktif"
        and bool((abonelik_govde.get("fatura") or {}).get("id")),
    )

    kota_satirlari = sql(
        "SELECT gunluk_istek, aylik_token FROM kota WHERE kapsam = ? AND kapsam_id = ?",
        ("organizasyon", a_org),
    )
    adim(
        "S7.3 Plan limitleri organizasyon kotasına yazıldı (DB)",
        f"sqlite: SELECT gunluk_istek, aylik_token FROM kota WHERE kapsam_id={a_org}",
        f"gunluk_istek={plan_deneme.get('dahil_istek')}",
        f"satırlar={kota_satirlari}",
        bool(kota_satirlari) and kota_satirlari[0][0] == plan_deneme.get("dahil_istek"),
    )

    kota_yaniti: httpx.Response | None = None
    deneme_sayisi = 0
    beklemeler = 0
    while deneme_sayisi < AZAMI_KOTA_DENEMESI and beklemeler <= 3:
        deneme_sayisi += 1
        deneme = cagir(
            "POST",
            "/sohbet",
            jeton=jeton,
            org="duman-a",
            json={"bdm_id": bdm_a, "mesaj": f"kota denemesi {deneme_sayisi}"},
        )
        kod = _kod(deneme)
        if deneme.status_code == 429 and kod == "oran_siniri":
            beklemeler += 1
            _bekle(float(deneme.headers.get("retry-after") or 5) + 0.5)
            continue
        if deneme.status_code != 200:
            kota_yaniti = deneme
            break
    adim(
        "S7.4 Kota aşımı → 429 kota_asildi",
        f"POST /api/v1/sohbet ×{deneme_sayisi} (deneme planı kotası dolana kadar)",
        "429 kota_asildi",
        f"deneme={deneme_sayisi} beklemeler={beklemeler} "
        + (_hata_ozeti(kota_yaniti) if kota_yaniti is not None else "kota dolmadı"),
        kota_yaniti is not None
        and kota_yaniti.status_code == 429
        and _kod(kota_yaniti) == "kota_asildi",
    )

    gecikmis_abonelik = cagir(
        "POST",
        "/faturalama/abonelik",
        jeton=jeton,
        org="duman-b",
        json={"plan_id": plan_deneme["id"], "donem_gun": 30},
    )
    if gecikmis_abonelik.status_code == 201:
        sql_yaz(
            "UPDATE abonelik SET durum = ? WHERE org_id = ?",
            ("gecikmis", b_org),
        )
    gecikmis_sohbet = cagir(
        "POST",
        "/sohbet",
        jeton=jeton,
        org="duman-b",
        json={"bdm_id": bdm_b, "mesaj": "Gecikmiş abonelikte sohbet denemesi."},
    )
    adim(
        "S7.5 Gecikmiş abonelikte sohbet 402 abonelik_gecikmis (spec §6)",
        "POST /api/v1/faturalama/abonelik (B) → DB durum=gecikmis → POST /api/v1/sohbet (B)",
        "402 abonelik_gecikmis",
        f"abonelik={_ozet(gecikmis_abonelik, 100)} sohbet={_hata_ozeti(gecikmis_sohbet)}",
        gecikmis_sohbet.status_code == 402 and _kod(gecikmis_sohbet) == "abonelik_gecikmis",
    )

    # -- S8: i18n ---------------------------------------------------------
    tr_yanit = cagir(
        "GET", "/boyle-bir-uc-yok", basliklar={"Accept-Language": "tr"}
    )
    en_yanit = cagir(
        "GET", "/boyle-bir-uc-yok", basliklar={"Accept-Language": "en"}
    )
    tr_mesaj = ((tr_yanit.json() or {}).get("hata") or {}).get("mesaj")
    en_mesaj = ((en_yanit.json() or {}).get("hata") or {}).get("mesaj")
    adim(
        "S8.1 Aynı hata TR ve EN farklı mesaj döner",
        "GET /api/v1/boyle-bir-uc-yok (Accept-Language: tr | en)",
        "iki mesaj farklı ve kod aynı",
        f"TR={tr_mesaj!r} EN={en_mesaj!r}",
        bool(tr_mesaj) and bool(en_mesaj) and tr_mesaj != en_mesaj,
    )

    adim(
        "S8.2 Content-Language başlığı (API.md §16)",
        "GET /api/v1/boyle-bir-uc-yok yanıt başlıkları",
        "Content-Language: tr | en",
        f"TR={tr_yanit.headers.get('content-language')} "
        f"EN={en_yanit.headers.get('content-language')}",
        (tr_yanit.headers.get("content-language") or "").startswith("tr")
        and (en_yanit.headers.get("content-language") or "").startswith("en"),
    )

    yetkisiz = cagir("GET", "/bdm", basliklar={"Accept-Language": "en"})
    adim(
        "S8.3 401 zarfı da dilden bağımsız kod + çevrilmiş mesaj taşır",
        "GET /api/v1/bdm (jetonsuz, Accept-Language: en)",
        "401 kimlik_gerekli + İngilizce mesaj",
        _ozet(yetkisiz),
        yetkisiz.status_code == 401
        and _kod(yetkisiz) == "kimlik_gerekli"
        and "must sign in" in str(((yetkisiz.json() or {}).get("hata") or {}).get("mesaj")),
    )

    # -- S9: medya --------------------------------------------------------
    gorsel_yanit = cagir(
        "POST",
        "/medya/gorsel",
        jeton=jeton,
        org="duman-a",
        json={"bdm_id": bdm_a, "istem": "duman görseli", "adet": 1},
    )
    gorsel_govde = gorsel_yanit.json() if gorsel_yanit.status_code == 200 else []
    gorsel_id = (gorsel_govde or [{}])[0].get("dosya_id") if gorsel_govde else None
    gorsel_satir = sql("SELECT org_id, mime FROM dosya WHERE id = ?", (gorsel_id,)) if gorsel_id else []
    adim(
        "S9.1 Görsel üretimi dosya kaydı oluşturur",
        "POST /api/v1/medya/gorsel {bdm_id: A, istem}",
        "200 dosya_id + DB kaydı (image/png, A org)",
        f"{_ozet(gorsel_yanit)} DB={gorsel_satir}",
        gorsel_yanit.status_code == 200
        and bool(gorsel_id)
        and bool(gorsel_satir)
        and gorsel_satir[0][0] == a_org
        and str(gorsel_satir[0][1]).startswith("image/"),
    )

    ses_yanit = cagir(
        "POST",
        "/medya/ses",
        jeton=jeton,
        org="duman-a",
        json={"bdm_id": bdm_a, "metin": "Duman ses denemesi.", "bicim": "mp3"},
    )
    ses_govde = ses_yanit.json() if ses_yanit.status_code == 200 else {}
    ses_id = ses_govde.get("dosya_id")
    ses_satir = sql("SELECT org_id, mime FROM dosya WHERE id = ?", (ses_id,)) if ses_id else []
    adim(
        "S9.2 Ses üretimi dosya kaydı oluşturur",
        "POST /api/v1/medya/ses {bdm_id: A, metin, bicim: mp3}",
        "200 dosya_id + DB kaydı (audio/mpeg, A org)",
        f"{_ozet(ses_yanit)} DB={ses_satir}",
        ses_yanit.status_code == 200
        and bool(ses_id)
        and bool(ses_satir)
        and ses_satir[0][0] == a_org
        and str(ses_satir[0][1]).startswith("audio/"),
    )

    kapali_istem = cagir(
        "POST",
        "/medya/gorsel",
        jeton=jeton,
        org="varsayilan",
        json={"bdm_id": yeteneksiz_bdm, "istem": "yetenek kapalı denemesi"},
    )
    kapali_kod = _kod(kapali_istem)
    adim(
        "S9.3 Yetenek kapalıyken medya reddedilir",
        "POST /api/v1/medya/gorsel (gorsel yeteneği kapalı BDM)",
        "400 medya_desteklenmiyor",
        _hata_ozeti(kapali_istem),
        kapali_istem.status_code == 400 and kapali_kod == "medya_desteklenmiyor",
    )


# ---------------------------------------------------------------------------
# Giriş noktası
# ---------------------------------------------------------------------------


def kaniti_yaz(sure_sn: float, ortam: dict[str, Any], hata: str | None = None) -> None:
    KANIT_YOLU.parent.mkdir(parents=True, exist_ok=True)
    govde: dict[str, Any] = {
        "senaryo": "Dalga 4 uçtan uca duman: kiracılık, RAG, araç, kota, i18n, medya",
        "zaman": datetime.now(timezone.utc).isoformat(),
        "sure_sn": round(sure_sn, 1),
        "ortam": ortam,
        "ozet": {
            "gecti": len(GECTI),
            "kaldi": len(KALDI),
            "yapilamadi": 1 if hata else 0,
        },
        "adimlar": ADIMLAR,
    }
    if hata:
        govde["kurulum_hatasi"] = hata
    KANIT_YOLU.write_text(json.dumps(govde, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    baslangic = time.monotonic()
    gecici = pathlib.Path(tempfile.mkdtemp(prefix="d4-e2e-"))
    global VERITABANI
    VERITABANI = gecici / "kutyai.db"

    ortam: dict[str, Any] = {
        "arka_uc": f"http://127.0.0.1:{ARKA_UC_PORT}",
        "arka_uc_komutu": (
            f"{pathlib.Path(sys.executable).name} -m uvicorn arkauc.app.main:app "
            f"--host 127.0.0.1 --port {ARKA_UC_PORT}"
        ),
        "sahte_upstream": UPSTREAM_TEMEL,
        "sahte_webhook": WEBHOOK_UCU,
        "veritabani": str(VERITABANI),
        "python": sys.version.split()[0],
        "calistirilan": " ".join(
            [
                pathlib.Path(sys.executable).as_posix(),
                pathlib.Path(__file__).resolve().relative_to(KOK).as_posix(),
            ]
        ),
        "degiskenler": {
            anahtar: ("<rastgele>" if "ANAHTAR" in anahtar else deger)
            for anahtar, deger in _ortam_degiskenleri(gecici).items()
        },
    }

    dolu_portlar = [p for p in (ARKA_UC_PORT, UPSTREAM_PORT, WEBHOOK_PORT) if not _port_bos(p)]
    if dolu_portlar:
        hata = f"Şu portlar dolu: {dolu_portlar}. Betik geçici sunucular için bu portları ister."
        adim("S0.0 Portların boş olması", "socket connect_ex", "8099/8098/8097 boş", hata, False)
        kaniti_yaz(time.monotonic() - baslangic, ortam, hata)
        return 1

    sahte_upstream = IplikSunucusu("upstream", upstream, UPSTREAM_PORT)
    sahte_webhook = IplikSunucusu("webhook", webhook, WEBHOOK_PORT)
    arka_uc = ArkaUc(gecici)
    hata: str | None = None

    try:
        sahte_upstream.basla()
        sahte_webhook.basla()
        arka_uc.basla()

        ortam["tohumlanan_bdmler"] = sql("SELECT id, slug FROM bdm ORDER BY id")

        senaryoyu_kos()
    except Exception as istisna:  # pragma: no cover - beklenmeyen kurulum hatası
        hata = f"{type(istisna).__name__}: {istisna}"
        adim("S0.0 Senaryo koşumu", "senaryoyu_kos()", "istisnasız tamamlanma", hata, False)
        print(arka_uc.gunluk_tail())
    finally:
        arka_uc.dur()
        sahte_upstream.dur()
        sahte_webhook.dur()
        _bosluk_bekle(ARKA_UC_PORT)
        ortam["sahte_upstream_istekleri"] = len(KAYITLAR["upstream"])
        ortam["sahte_webhook_istekleri"] = len(KAYITLAR["webhook"])
        ortam["gecici_dizin"] = str(gecici)
        kaniti_yaz(time.monotonic() - baslangic, ortam, hata)

    print()
    print(f"SONUÇ: {len(GECTI)} geçti, {len(KALDI)} kaldı")
    for ad in KALDI:
        print(f"  KALAN: {ad}")
    print(f"Kanıt: {KANIT_YOLU.as_posix()}")
    return 1 if KALDI else 0


if __name__ == "__main__":
    sys.exit(main())
