"""Güvenlik sıkılaştırma testleri (güvenlik incelemesi bulguları).

Kilitlenen davranışlar:
- SSRF: `temel_url` yalnız http/https; loopback/özel/link-local ve bulut
  metadata adresleri reddedilir (yerel ağ izni yalnız `BdmOlustur` çağrısında
  `yerel_izin=True` ile verilir).
- Argv enjeksiyonu: `upstream_model` bayrak enjeksiyonuna kapalı.
- Oran sınırı, `Authorization` başlığı döndürülerek atlatılamaz.
"""

from __future__ import annotations

import ipaddress

import pytest

from arkauc.app.cekirdek.oran_siniri import Kural, kova_anahtarlari
from bdm_listesi import BdmOlustur, sema
from bdm_listesi.sema import _adres_dogrula


def _kovalar(yol: str, yetki: str | None, jeton_ile_ayir: bool = False) -> list[str]:
    basliklar = []
    if yetki:
        basliklar.append((b"authorization", yetki.encode()))
    kural = Kural("/api/v1/kimlik/", 10, jeton_ile_ayir=jeton_ile_ayir)
    return kova_anahtarlari(
        {"type": "http", "path": yol, "headers": basliklar, "client": ("9.9.9.9", 1)}, kural
    )


def test_kimlik_kovasi_authorization_basligindan_etkilenmez():
    """Saldırgan farklı jeton göndererek yeni kova üretememeli."""
    ilk = _kovalar("/api/v1/kimlik/panel-giris", "Bearer uydurma-1")
    ikinci = _kovalar("/api/v1/kimlik/panel-giris", "Bearer uydurma-2")
    assert ilk == ikinci
    assert ilk[0].startswith("ip:9.9.9.9")


def test_sohbet_kovasi_jeton_ile_ayri_sayilir():
    kovalar = _kovalar("/api/v1/sohbet", "Bearer kuty_abc", jeton_ile_ayir=True)
    assert kovalar[0].startswith("ip:9.9.9.9")
    assert len(kovalar) == 2
    assert kovalar[1].startswith("jeton:")


def test_jeton_ile_ayirmayan_kural_tek_kovali():
    assert len(_kovalar("/api/v1/bdm", "Bearer kuty_abc")) == 1


@pytest.fixture
def cozucu_taklit(monkeypatch: pytest.MonkeyPatch) -> None:
    """DNS'i taklit eder: `localhost` → loopback, diğer adlar → genel IP."""
    sema._cozulemeyen_konaklar.clear()
    monkeypatch.setattr(
        sema,
        "_adres_coz",
        lambda konak: [
            ipaddress.ip_address("127.0.0.1" if konak == "localhost" else "93.184.216.34")
        ],
    )


@pytest.mark.parametrize(
    "adres",
    [
        "http://169.254.169.254/latest/meta-data",
        "http://169.254.169.254./latest/meta-data",
        "http://[::ffff:169.254.169.254]/latest/meta-data",
        "http://2852039166/latest/meta-data",
        "http://100.100.100.200/latest/meta-data",
        "https://metadata.google.internal/x",
        "https://metadata.google.internal./x",
    ],
)
def test_metadata_adresleri_reddedilir(adres):
    """Kara liste değil: normalize edilmiş konak, sayısal IPv4 ve aralıklar denetlenir."""
    with pytest.raises(ValueError):
        _adres_dogrula(adres)


@pytest.mark.parametrize("adres", ["ftp://ornek.local/v1", "file:///C:/Windows/win.ini", "//x/y"])
def test_http_disi_semalar_reddedilir(adres):
    with pytest.raises(ValueError):
        _adres_dogrula(adres)


@pytest.mark.parametrize(
    "adres",
    [
        "http://localhost:11434/v1",
        "http://127.0.0.1:8000/v1",
        "http://[::1]:8000/v1",
        "http://10.0.0.5/v1",
        "http://192.168.1.20/v1",
    ],
)
def test_yerel_adresler_kati_kipte_reddedilir(adres, cozucu_taklit):
    """Loopback/özel ağ adresleri artık kabul edilmez (yerel izin cagirana birakilir)."""
    with pytest.raises(ValueError):
        _adres_dogrula(adres)


def test_genel_https_adresi_kabul_edilir(cozucu_taklit):
    assert _adres_dogrula("https://api.ornek.com/v1") == "https://api.ornek.com/v1"


def test_yerel_izin_loopbacki_acar_metadata_kapatir(cozucu_taklit):
    """`yerel_izin=True` (yerel model sunuculari) loopback'i acar; metadata kapali kalir."""
    assert _adres_dogrula("http://127.0.0.1:11434/v1", yerel_izin=True) == (
        "http://127.0.0.1:11434/v1"
    )
    with pytest.raises(ValueError):
        _adres_dogrula("http://169.254.169.254/latest/meta-data", yerel_izin=True)


def test_bozuk_adres_kayit_asamasinda_reddedilmez():
    """Bozuk adres dogrulama katmaninda Turkce sonuca donusur, kayit engellenmez."""
    assert _adres_dogrula("http://[::1/v1") == "http://[::1/v1"


@pytest.mark.parametrize("model", ["--trust-remote-code", "-x", "model;rm -rf /", "a b"])
def test_model_adinda_bayrak_enjeksiyonu_reddedilir(model):
    with pytest.raises(ValueError):
        BdmOlustur(gorunen_ad="Model", saglayici="vllm", upstream_model=model)


def test_gecerli_model_kimlikleri_kabul_edilir():
    for model in ("meta-llama/Llama-3.1-8B-Instruct", "qwen2.5:7b", "gpt-4o-mini"):
        veri = BdmOlustur(gorunen_ad="Model", saglayici="ollama", upstream_model=model)
        assert veri.upstream_model == model
