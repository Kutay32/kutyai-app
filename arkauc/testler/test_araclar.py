"""Araç çağırma testleri (spec §4).

Kapsam: CRUD, org izolasyonu, yetki matrisi, webhook çağrısı (imza/başlık/
zaman aşımı/500/64 KB), adres güvenliği, yerleşik araçlar (güvenli hesap
makinesi, zaman), argüman şeması doğrulaması ve çağrı günlüğü.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest
import sqlalchemy as sa

from arkauc.app.cekirdek import guvenlik
from arkauc.app.cekirdek.ayarlar import ayarlar
from arkauc.app.servisler import arac as arac_servisi
from bdm_veritabani.modeller import (
    Arac,
    AracCagrisi,
    AracCagrisiDurumu,
    AracTuru,
    Rol,
)
from bdm_veritabani.oturum import oturum_fabrikasi

UC = "/api/v1/araclar"


# --------------------------------------------------------------------------
# Sahte webhook sunucusu
# --------------------------------------------------------------------------


class SahteWebhook:
    """Gerçek bir yerel HTTP sunucusu; istekleri kaydeder, yanıtı yapılandırır."""

    def __init__(self) -> None:
        self.istekler: list[dict[str, Any]] = []
        self.yanit_kodu = 200
        self.yanit_govdesi: bytes = json.dumps({"tamam": True}).encode("utf-8")
        self.gecikme_sn = 0.0
        kayit = self

        class Isleyici(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args: object) -> None:  # test çıktısını kirletme
                return None

            def do_POST(self) -> None:
                uzunluk = int(self.headers.get("Content-Length") or 0)
                ham = self.rfile.read(uzunluk) if uzunluk else b""
                kayit.istekler.append(
                    {"yol": self.path, "basliklar": dict(self.headers), "govde": ham}
                )
                if kayit.gecikme_sn:
                    time.sleep(kayit.gecikme_sn)
                self.send_response(kayit.yanit_kodu)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(kayit.yanit_govdesi)))
                self.end_headers()
                self.wfile.write(kayit.yanit_govdesi)

        self._sunucu = ThreadingHTTPServer(("127.0.0.1", 0), Isleyici)
        self._durdurucu = threading.Thread(target=self._sunucu.serve_forever, daemon=True)
        self._durdurucu.start()
        self.adres = f"http://127.0.0.1:{self._sunucu.server_address[1]}/arac"

    def kapat(self) -> None:
        self._sunucu.shutdown()
        self._sunucu.server_close()

    @property
    def son_istek(self) -> dict[str, Any]:
        assert self.istekler, "webhook sunucusuna hiç istek gelmedi"
        return self.istekler[-1]


@pytest.fixture
def webhook() -> SahteWebhook:
    sunucu = SahteWebhook()
    yield sunucu
    sunucu.kapat()


@pytest.fixture(autouse=True)
def yerel_izin(monkeypatch: pytest.MonkeyPatch) -> None:
    """Yerel http webhook'larına izin ver (testler gerçek 127.0.0.1 sunucusu kullanır)."""
    monkeypatch.setattr(ayarlar, "arac_yerel_izin", True)
    monkeypatch.setattr(ayarlar, "arac_imza_anahtari", "")


# --------------------------------------------------------------------------
# Yardımcılar
# --------------------------------------------------------------------------


async def _olustur(
    istemci: Any,
    basliklar: dict[str, str],
    *,
    ad: str = "Hava Durumu",
    slug: str | None = None,
    tur: str = "webhook",
    uc_noktasi: str = "",
    json_sema: dict[str, Any] | None = None,
    baslik_verisi: dict[str, str] | None = None,
) -> dict[str, Any]:
    govde: dict[str, Any] = {"ad": ad, "tur": tur, "uc_noktasi": uc_noktasi}
    if slug is not None:
        govde["slug"] = slug
    if json_sema is not None:
        govde["json_sema"] = json_sema
    if baslik_verisi is not None:
        govde["basliklar"] = baslik_verisi
    yanit = await istemci.post(f"{UC}", json=govde, headers=basliklar)
    assert yanit.status_code == 201, yanit.text
    return yanit.json()


def _beklenen_imza(govde: bytes) -> str:
    anahtar = (ayarlar.arac_imza_anahtari or ayarlar.gizli_anahtar).encode("utf-8")
    return "sha256=" + hmac.new(anahtar, govde, hashlib.sha256).hexdigest()


async def _cagri_sayisi() -> int:
    async with oturum_fabrikasi()() as oturum:
        return int(
            (
                await oturum.execute(sa.select(sa.func.count()).select_from(AracCagrisi))
            ).scalar_one()
        )


# --------------------------------------------------------------------------
# CRUD ve org izolasyonu
# --------------------------------------------------------------------------


async def test_crud_akisi(istemci, yardimci) -> None:
    yonetici = await yardimci.yonetici()
    basliklar = yardimci.basliklar(yonetici)

    olusan = await _olustur(
        istemci, basliklar, slug="hava", uc_noktasi="https://ornek.test/hava", ad="Hava"
    )
    assert olusan["slug"] == "hava"
    assert olusan["tur"] == "webhook"
    assert olusan["etkin"] is True

    liste = await istemci.get(UC, headers=basliklar)
    assert liste.status_code == 200
    assert [arac["slug"] for arac in liste.json()] == ["hava"]

    guncel = await istemci.patch(
        f"{UC}/{olusan['id']}",
        json={"aciklama": "Şehir hava durumu", "etkin": False},
        headers=basliklar,
    )
    assert guncel.status_code == 200
    assert guncel.json()["aciklama"] == "Şehir hava durumu"
    assert guncel.json()["etkin"] is False

    yalniz_etkin = await istemci.get(UC, params={"etkin": "true"}, headers=basliklar)
    assert yalniz_etkin.json() == []

    silindi = await istemci.delete(f"{UC}/{olusan['id']}", headers=basliklar)
    assert silindi.status_code == 204
    assert (await istemci.get(UC, headers=basliklar)).json() == []

    yok = await istemci.patch(
        f"{UC}/{olusan['id']}", json={"etkin": True}, headers=basliklar
    )
    assert yok.status_code == 404
    assert yok.json()["hata"]["kod"] == "arac_bulunamadi"


async def test_slug_org_icinde_tekil(istemci, yardimci) -> None:
    yonetici = await yardimci.yonetici()
    basliklar = yardimci.basliklar(yonetici)

    await _olustur(istemci, basliklar, slug="tekil", uc_noktasi="https://ornek.test/a")
    cakisan = await istemci.post(
        UC,
        json={"ad": "Başka", "slug": "tekil", "uc_noktasi": "https://ornek.test/b"},
        headers=basliklar,
    )
    assert cakisan.status_code == 409
    assert cakisan.json()["hata"]["kod"] == "cakisma"

    # slug verilmeyen ikinci kayıt otomatik türetilir ve çakışmaz.
    otomatik = await _olustur(
        istemci, basliklar, ad="Başka Araç", uc_noktasi="https://ornek.test/c"
    )
    assert otomatik["slug"] == "baska-arac"


async def test_org_izolasyonu(istemci, yardimci) -> None:
    a_kullanici = await yardimci.yonetici()
    a_basliklar = yardimci.basliklar(a_kullanici)
    arac = await _olustur(
        istemci, a_basliklar, slug="a-araci", uc_noktasi="https://ornek.test/a"
    )

    b_kullanici = await yardimci.kullanici_ekle(rol=Rol.yonetici)
    b_org = await yardimci.organizasyon("B Org", sahibi=b_kullanici)
    b_basliklar = yardimci.org_basliklari(b_kullanici, b_org)

    assert (await istemci.get(UC, headers=b_basliklar)).json() == []
    assert (
        await istemci.patch(
            f"{UC}/{arac['id']}", json={"etkin": False}, headers=b_basliklar
        )
    ).status_code == 404
    assert (
        await istemci.delete(f"{UC}/{arac['id']}", headers=b_basliklar)
    ).status_code == 404
    assert (
        await istemci.post(
            f"{UC}/{arac['id']}/dene", json={"argumanlar": {}}, headers=b_basliklar
        )
    ).status_code == 404
    # A organizasyonun kaydı hâlâ yerinde.
    assert len((await istemci.get(UC, headers=a_basliklar)).json()) == 1


async def test_yetki_matrisi(istemci, yardimci) -> None:
    izleyici = await yardimci.kullanici_ekle(rol=Rol.izleyici)
    izleyici_basliklar = yardimci.basliklar(izleyici)
    assert (await istemci.get(UC, headers=izleyici_basliklar)).status_code == 200

    yazma = await istemci.post(
        UC,
        json={"ad": "Yeni", "uc_noktasi": "https://ornek.test/y"},
        headers=izleyici_basliklar,
    )
    assert yazma.status_code == 403
    assert yazma.json()["hata"]["kod"] == "yetki_yok"

    son_kullanici = await yardimci.kullanici_ekle(rol=Rol.son_kullanici)
    son_basliklar = yardimci.basliklar(son_kullanici)
    assert (await istemci.get(UC, headers=son_basliklar)).status_code == 403
    assert (await istemci.get(f"{UC}/cagrilar", headers=son_basliklar)).status_code == 403

    operator = await yardimci.kullanici_ekle(rol=Rol.operator)
    operator_basliklar = yardimci.basliklar(operator)
    assert (
        await istemci.post(
            UC,
            json={"ad": "Operatör Aracı", "uc_noktasi": "https://ornek.test/o"},
            headers=operator_basliklar,
        )
    ).status_code == 201


# --------------------------------------------------------------------------
# Webhook çağrısı
# --------------------------------------------------------------------------


async def test_webhook_cagrisi_imza_ve_basliklar(istemci, yardimci, webhook) -> None:
    yonetici = await yardimci.yonetici()
    basliklar = yardimci.basliklar(yonetici)
    arac = await _olustur(
        istemci,
        basliklar,
        slug="hava",
        ad="Hava",
        uc_noktasi=webhook.adres,
        json_sema={
            "type": "object",
            "properties": {"sehir": {"type": "string"}},
            "required": ["sehir"],
        },
        baslik_verisi={"X-Api-Anahtar": "cok-gizli-deger"},
    )

    # Sır düz metin dönmez, maskelenir.
    assert arac["basliklar"] == {"X-Api-Anahtar": guvenlik.maskele("cok-gizli-deger")}
    assert "cok-gizli-deger" not in json.dumps(arac)

    yanit = await istemci.post(
        f"{UC}/{arac['id']}/dene",
        json={"argumanlar": {"sehir": "Ankara"}},
        headers=basliklar,
    )
    assert yanit.status_code == 200, yanit.text
    govde = yanit.json()
    assert govde["durum"] == "basarili"
    assert govde["sonuc"] == {"tamam": True}

    gelen = webhook.son_istek
    assert gelen["govde"] == json.dumps(
        {"arac": "hava", "argumanlar": {"sehir": "Ankara"}}, ensure_ascii=False
    ).encode("utf-8")
    assert gelen["basliklar"][arac_servisi.IMZA_BASLIGI] == _beklenen_imza(gelen["govde"])
    assert gelen["basliklar"]["X-Api-Anahtar"] == "cok-gizli-deger"
    assert gelen["basliklar"]["Content-Type"] == "application/json"

    # Başlıklar veritabanında şifreli durur.
    async with oturum_fabrikasi()() as oturum:
        kayit = await oturum.get(Arac, arac["id"])
        assert kayit is not None
        assert "cok-gizli-deger" not in (kayit.basliklar_sifreli or "")
        assert json.loads(guvenlik.coz(kayit.basliklar_sifreli or "")) == {
            "X-Api-Anahtar": "cok-gizli-deger"
        }


async def test_webhook_zaman_asimi(istemci, yardimci, webhook, monkeypatch) -> None:
    monkeypatch.setattr(arac_servisi, "ZAMAN_ASIMI_SN", 0.3)
    webhook.gecikme_sn = 1.5
    yonetici = await yardimci.yonetici()
    basliklar = yardimci.basliklar(yonetici)
    arac = await _olustur(istemci, basliklar, slug="yavas", uc_noktasi=webhook.adres)

    yanit = await istemci.post(
        f"{UC}/{arac['id']}/dene", json={"argumanlar": {}}, headers=basliklar
    )
    assert yanit.status_code == 502
    assert yanit.json()["hata"]["kod"] == "arac_hatasi"

    log = await istemci.get(f"{UC}/cagrilar", headers=basliklar)
    kayit = log.json()["kayitlar"][0]
    assert kayit["durum"] == "hata"
    assert kayit["arac_id"] == arac["id"]
    assert "yanıt vermedi" in kayit["hata"]


async def test_webhook_500_hatasi(istemci, yardimci, webhook) -> None:
    webhook.yanit_kodu = 500
    webhook.yanit_govdesi = b'{"hata": "patladim"}'
    yonetici = await yardimci.yonetici()
    basliklar = yardimci.basliklar(yonetici)
    arac = await _olustur(istemci, basliklar, slug="bozuk", uc_noktasi=webhook.adres)

    yanit = await istemci.post(
        f"{UC}/{arac['id']}/dene", json={"argumanlar": {}}, headers=basliklar
    )
    assert yanit.status_code == 502
    assert "500" in yanit.json()["hata"]["ayrinti"]["neden"]

    log = await istemci.get(f"{UC}/cagrilar", headers=basliklar)
    assert log.json()["kayitlar"][0]["durum"] == "hata"


async def test_webhook_yanit_boyutu_sinirli(istemci, yardimci, webhook) -> None:
    webhook.yanit_govdesi = json.dumps({"dolgu": "x" * 70_000}).encode("utf-8")
    yonetici = await yardimci.yonetici()
    basliklar = yardimci.basliklar(yonetici)
    arac = await _olustur(istemci, basliklar, slug="buyuk", uc_noktasi=webhook.adres)

    yanit = await istemci.post(
        f"{UC}/{arac['id']}/dene", json={"argumanlar": {}}, headers=basliklar
    )
    assert yanit.status_code == 502
    assert "64 KB" in yanit.json()["hata"]["ayrinti"]["neden"]


@pytest.mark.parametrize(
    "adres",
    [
        "ftp://ornek.test/arac",
        "https://169.254.169.254/latest/meta-data",
        "https://metadata.google.internal/computeMetadata/v1",
    ],
)
async def test_adres_guvenligi_reddeder(istemci, yardimci, adres) -> None:
    yonetici = await yardimci.yonetici()
    basliklar = yardimci.basliklar(yonetici)
    yanit = await istemci.post(
        UC, json={"ad": "Kötü", "uc_noktasi": adres}, headers=basliklar
    )
    assert yanit.status_code == 400
    assert yanit.json()["hata"]["kod"] == "gecersiz_istek"


async def test_http_yalniz_yerel_izinle(istemci, yardimci, webhook, monkeypatch) -> None:
    monkeypatch.setattr(ayarlar, "arac_yerel_izin", False)
    yonetici = await yardimci.yonetici()
    basliklar = yardimci.basliklar(yonetici)

    reddedilen = await istemci.post(
        UC, json={"ad": "Http", "uc_noktasi": "http://ornek.test/arac"}, headers=basliklar
    )
    assert reddedilen.status_code == 400
    assert "https" in reddedilen.json()["hata"]["mesaj"]

    monkeypatch.setattr(ayarlar, "arac_yerel_izin", True)
    kabul = await istemci.post(
        UC,
        json={"ad": "Http Yerel", "uc_noktasi": "http://127.0.0.1:9/arac"},
        headers=basliklar,
    )
    assert kabul.status_code == 201


# --------------------------------------------------------------------------
# Yerleşik araçlar
# --------------------------------------------------------------------------


async def test_hesap_makinesi_guvenli(istemci, yardimci) -> None:
    yonetici = await yardimci.yonetici()
    basliklar = yardimci.basliklar(yonetici)
    arac = await istemci.post(
        UC,
        json={"ad": "Hesap Makinesi", "tur": "yerlesik", "slug": "hesap_makinesi"},
        headers=basliklar,
    )
    assert arac.status_code == 201, arac.text
    assert arac.json()["uc_noktasi"] == ""
    assert arac.json()["json_sema"]["required"] == ["ifade"]

    iyi = await istemci.post(
        f"{UC}/{arac.json()['id']}/dene",
        json={"argumanlar": {"ifade": "(2 + 3) * 4"}},
        headers=basliklar,
    )
    assert iyi.status_code == 200
    assert iyi.json()["sonuc"] == {"sonuc": 20}

    for kotu in (
        "__import__('os').system('echo pwn')",
        "open('/etc/passwd').read()",
        "eval('1+1')",
        "().__class__.__bases__",
        "[1, 2, 3]",
        "1/0",
        "2**(10**9)",
    ):
        yanit = await istemci.post(
            f"{UC}/{arac.json()['id']}/dene",
            json={"argumanlar": {"ifade": kotu}},
            headers=basliklar,
        )
        assert yanit.status_code == 400, kotu
        assert yanit.json()["hata"]["kod"] == "gecersiz_istek"


async def test_hesap_makinesi_eksik_arguman(istemci, yardimci) -> None:
    yonetici = await yardimci.yonetici()
    basliklar = yardimci.basliklar(yonetici)
    arac = await istemci.post(
        UC,
        json={"ad": "Hesap Makinesi", "tur": "yerlesik", "slug": "hesap_makinesi"},
        headers=basliklar,
    )
    yanit = await istemci.post(
        f"{UC}/{arac.json()['id']}/dene", json={"argumanlar": {}}, headers=basliklar
    )
    assert yanit.status_code == 400
    assert yanit.json()["hata"]["ayrinti"]["alan"] == "ifade"


async def test_zaman_yerlesik(istemci, yardimci) -> None:
    yonetici = await yardimci.yonetici()
    basliklar = yardimci.basliklar(yonetici)
    arac = await istemci.post(
        UC, json={"ad": "Zaman", "tur": "yerlesik", "slug": "zaman"}, headers=basliklar
    )
    assert arac.status_code == 201, arac.text

    yanit = await istemci.post(
        f"{UC}/{arac.json()['id']}/dene", json={"argumanlar": {}}, headers=basliklar
    )
    assert yanit.status_code == 200
    assert isinstance(datetime.fromisoformat(yanit.json()["sonuc"]["zaman"]), datetime)


async def test_bilinmeyen_yerlesik_reddedilir(istemci, yardimci) -> None:
    yonetici = await yardimci.yonetici()
    basliklar = yardimci.basliklar(yonetici)
    yanit = await istemci.post(
        UC, json={"ad": "Web Ara", "tur": "yerlesik", "slug": "web_ara"}, headers=basliklar
    )
    assert yanit.status_code == 400
    assert "web_ara" in yanit.json()["hata"]["mesaj"]


# --------------------------------------------------------------------------
# Argüman şeması ve çağrı günlüğü
# --------------------------------------------------------------------------


async def test_arguman_semasi_dogrulanir(istemci, yardimci, webhook) -> None:
    yonetici = await yardimci.yonetici()
    basliklar = yardimci.basliklar(yonetici)
    arac = await _olustur(
        istemci,
        basliklar,
        slug="sehir",
        uc_noktasi=webhook.adres,
        json_sema={
            "type": "object",
            "properties": {
                "sehir": {"type": "string"},
                "gun": {"type": "integer", "minimum": 1, "maximum": 7},
            },
            "required": ["sehir"],
            "additionalProperties": False,
        },
    )

    eksik = await istemci.post(
        f"{UC}/{arac['id']}/dene", json={"argumanlar": {"gun": 3}}, headers=basliklar
    )
    assert eksik.status_code == 400
    assert eksik.json()["hata"]["kod"] == "gecersiz_istek"
    assert eksik.json()["hata"]["ayrinti"]["alan"] == "sehir"

    yanlis_tur = await istemci.post(
        f"{UC}/{arac['id']}/dene",
        json={"argumanlar": {"sehir": "Ankara", "gun": "üç"}},
        headers=basliklar,
    )
    assert yanlis_tur.status_code == 400
    assert yanlis_tur.json()["hata"]["ayrinti"]["alan"] == "gun"

    sinir = await istemci.post(
        f"{UC}/{arac['id']}/dene",
        json={"argumanlar": {"sehir": "Ankara", "gun": 99}},
        headers=basliklar,
    )
    assert sinir.status_code == 400
    assert sinir.json()["hata"]["ayrinti"]["alan"] == "gun"

    fazla = await istemci.post(
        f"{UC}/{arac['id']}/dene",
        json={"argumanlar": {"sehir": "Ankara", "renk": "mavi"}},
        headers=basliklar,
    )
    assert fazla.status_code == 400
    assert fazla.json()["hata"]["ayrinti"]["alan"] == "renk"

    # Başarısız denemeler çağrı günlüğüne yazılmaz (istek hiç çalıştırılmadı).
    assert await _cagri_sayisi() == 0
    assert webhook.istekler == []


async def test_cagri_gunlugu_sayfalama_ve_filtre(istemci, yardimci, webhook) -> None:
    yonetici = await yardimci.yonetici()
    basliklar = yardimci.basliklar(yonetici)
    arac = await _olustur(istemci, basliklar, slug="loglu", uc_noktasi=webhook.adres)
    digeri = await _olustur(
        istemci, basliklar, slug="digeri", ad="Diğeri", uc_noktasi=webhook.adres
    )

    assert (
        await istemci.post(
            f"{UC}/{arac['id']}/dene", json={"argumanlar": {"x": 1}}, headers=basliklar
        )
    ).status_code == 200
    webhook.yanit_kodu = 500
    assert (
        await istemci.post(
            f"{UC}/{digeri['id']}/dene", json={"argumanlar": {}}, headers=basliklar
        )
    ).status_code == 502

    hepsi = await istemci.get(f"{UC}/cagrilar", headers=basliklar)
    assert hepsi.status_code == 200
    govde = hepsi.json()
    assert govde["toplam"] == 2
    assert [kayit["ad"] for kayit in govde["kayitlar"]] == ["digeri", "loglu"]
    assert govde["kayitlar"][1]["argumanlar"] == {"x": 1}
    assert govde["kayitlar"][1]["sonuc"] == {"tamam": True}
    assert govde["kayitlar"][1]["gecikme_ms"] >= 0

    hatali = await istemci.get(
        f"{UC}/cagrilar", params={"durum": "hata"}, headers=basliklar
    )
    assert hatali.json()["toplam"] == 1
    assert hatali.json()["kayitlar"][0]["ad"] == "digeri"

    suzulmus = await istemci.get(
        f"{UC}/cagrilar", params={"arac_id": arac["id"]}, headers=basliklar
    )
    assert suzulmus.json()["toplam"] == 1
    assert suzulmus.json()["kayitlar"][0]["ad"] == "loglu"

    sayfa = await istemci.get(
        f"{UC}/cagrilar", params={"sayfa": 2, "boyut": 1}, headers=basliklar
    )
    assert sayfa.json()["toplam"] == 2
    assert [k["ad"] for k in sayfa.json()["kayitlar"]] == ["loglu"]


async def test_silinen_arac_cagrilari_korunur(istemci, yardimci, webhook) -> None:
    yonetici = await yardimci.yonetici()
    basliklar = yardimci.basliklar(yonetici)
    arac = await _olustur(istemci, basliklar, slug="silinecek", uc_noktasi=webhook.adres)
    await istemci.post(
        f"{UC}/{arac['id']}/dene", json={"argumanlar": {}}, headers=basliklar
    )

    assert (await istemci.delete(f"{UC}/{arac['id']}", headers=basliklar)).status_code == 204
    log = await istemci.get(f"{UC}/cagrilar", headers=basliklar)
    kayitlar = log.json()["kayitlar"]
    assert len(kayitlar) == 1
    assert kayitlar[0]["arac_id"] is None
    assert kayitlar[0]["ad"] == "silinecek"


async def test_org_izolasyonu_cagri_gunlugu(istemci, yardimci, webhook) -> None:
    a_kullanici = await yardimci.yonetici()
    a_basliklar = yardimci.basliklar(a_kullanici)
    arac = await _olustur(istemci, a_basliklar, slug="a-log", uc_noktasi=webhook.adres)
    await istemci.post(
        f"{UC}/{arac['id']}/dene", json={"argumanlar": {}}, headers=a_basliklar
    )

    b_kullanici = await yardimci.kullanici_ekle(rol=Rol.yonetici)
    b_org = await yardimci.organizasyon("B Log Org", sahibi=b_kullanici)
    b_basliklar = yardimci.org_basliklari(b_kullanici, b_org)

    log = await istemci.get(f"{UC}/cagrilar", headers=b_basliklar)
    assert log.json()["toplam"] == 0


# --------------------------------------------------------------------------
# Servis düzeyi
# --------------------------------------------------------------------------


def test_arac_tanimi_openai_bicimi() -> None:
    arac = Arac(
        org_id=1,
        ad="Hava Durumu",
        slug="hava",
        aciklama="Şehir hava durumu",
        json_sema={"type": "object", "properties": {"sehir": {"type": "string"}}},
        tur=AracTuru.webhook,
        uc_noktasi="https://ornek.test/hava",
    )
    tanim = arac_servisi.arac_tanimi(arac)
    assert tanim == {
        "type": "function",
        "function": {
            "name": "hava",
            "description": "Şehir hava durumu",
            "parameters": {"type": "object", "properties": {"sehir": {"type": "string"}}},
        },
    }
    assert arac_servisi.yerlesik_mi(arac) is False
    arac.tur = AracTuru.yerlesik
    assert arac_servisi.yerlesik_mi(arac) is True


async def test_bilinmeyen_arac_bulunamadi(yardimci) -> None:
    from arkauc.app.cekirdek.hatalar import Bulunamadi

    async with oturum_fabrikasi()() as oturum:
        with pytest.raises(Bulunamadi):
            await arac_servisi.arac_bul(oturum, 99_999, "yok")


async def test_durum_enum_logda(istemci, yardimci, webhook) -> None:
    """Çağrı kaydı `durum` alanını taşır ve org_id ile yazılır."""
    yonetici = await yardimci.yonetici()
    basliklar = yardimci.basliklar(yonetici)
    arac = await _olustur(istemci, basliklar, slug="enum", uc_noktasi=webhook.adres)
    await istemci.post(
        f"{UC}/{arac['id']}/dene", json={"argumanlar": {}}, headers=basliklar
    )
    async with oturum_fabrikasi()() as oturum:
        kayit = (await oturum.execute(sa.select(AracCagrisi))).scalars().one()
        assert kayit.durum == AracCagrisiDurumu.basarili
        assert kayit.org_id is not None
        assert kayit.arac_id == arac["id"]
