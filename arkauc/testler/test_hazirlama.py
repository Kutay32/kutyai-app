"""T1.3 — BDM hazirlama ucu testleri: dogrula, cek, manifest, on-kontrol.

Ag erisimi yoktur: upstream cagrilari `httpx.MockTransport` ile sahte tasima
uzerinden enjekte edilir; konteyner surucusu `SahteSurucu` ile degistirilir.
"""

from __future__ import annotations

import json
import pathlib
import types

import httpx
import pytest
import sqlalchemy as sa

from arkauc.app.cekirdek.ayarlar import ayarlar
from arkauc.app.cekirdek.hatalar import GecersizIstek, UstSaglayiciHatasi
from arkauc.app.servisler.konteyner import SahteSurucu, surucu_ata, surucu_temizle
from bdm_hazırlama_ucu import cekim, dogrulama, manifest
from bdm_hazırlama_ucu.on_kontrol import (
    DOCKER_UYARI_MESAJI,
    GPU_UYARI_MESAJI,
    on_kontrol,
)
from bdm_listesi import BdmOlustur, bdm_getir, bdm_olustur, saglayici_bilgisi
from bdm_veritabani.modeller import Bdm, BdmDurumu, IslemKaydi, Rol, Saglayici
from bdm_veritabani.oturum import oturum_fabrikasi

HAZIRLAMA = "/api/v1/bdm/hazirlama"


@pytest.fixture(autouse=True)
def surucu_temizligi():
    """Her testten sonra gecici surucuyu temizler."""
    yield
    surucu_temizle()


@pytest.fixture
def surucu_kur():
    """Sahte konteyner surucusunu kurar."""

    def _kur(**kwargs) -> SahteSurucu:
        surucu = SahteSurucu(**kwargs)
        surucu_ata(surucu)
        return surucu

    return _kur


async def bdm_ekle(
    saglayici: str,
    *,
    upstream_model: str = "llama3",
    api_anahtari: str = "",
    temel_url: str = "",
) -> int:
    """Test icin BDM kaydi olusturur ve kimligini dondurur."""
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_olustur(
            oturum,
            BdmOlustur(
                gorunen_ad=f"{saglayici_bilgisi(saglayici).gorunen_ad} Test",
                saglayici=Saglayici(saglayici),
                upstream_model=upstream_model,
                temel_url=temel_url,
                api_anahtari=api_anahtari,
            ),
        )
        await oturum.commit()
        return bdm.id


async def bdm_durumu(bdm_id: int) -> BdmDurumu:
    async with oturum_fabrikasi()() as oturum:
        return (await bdm_getir(oturum, bdm_id)).durum


def _ndjson(parcalar: list[dict]) -> bytes:
    return ("\n".join(json.dumps(p) for p in parcalar) + "\n").encode("utf-8")


def _sahte_snapshot(cagrilar: list[tuple[str, dict]] | None = None):
    """Ağa çıkmadan `snapshot_download` yerine geçen indirici."""

    def _indir(repo_id: str, **kwargs):
        if cagrilar is not None:
            cagrilar.append((repo_id, kwargs))
        anlik = pathlib.Path(kwargs["cache_dir"]) / "models--sahte" / "snapshots" / "rev1"
        anlik.mkdir(parents=True, exist_ok=True)
        (anlik / "config.json").write_text("{}", encoding="utf-8")
        return anlik.as_posix()

    return _indir


# -- dogrula ----------------------------------------------------------------


async def test_dogrula_basarili_hazir_yazar():
    bdm_id = await bdm_ekle("ollama", upstream_model="llama3")
    istekler: list[str] = []

    def isleyici(istek: httpx.Request) -> httpx.Response:
        istekler.append(istek.url.path)
        return httpx.Response(
            200, json={"data": [{"id": "llama3"}, {"id": "qwen2.5:7b"}]}
        )

    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_getir(oturum, bdm_id)
        sonuc = await dogrulama.dogrula(
            bdm, oturum=oturum, tasima=httpx.MockTransport(isleyici)
        )
        await oturum.commit()

    assert sonuc["basarili"] is True
    assert sonuc["modeller"] == ["llama3", "qwen2.5:7b"]
    assert sonuc["gecikme_ms"] >= 0
    assert "başarılı" in sonuc["mesaj"].lower()
    assert bdm.durum == BdmDurumu.hazir
    assert await bdm_durumu(bdm_id) == BdmDurumu.hazir
    assert istekler == ["/v1/models"]


async def test_dogrula_model_listesi_yoksa_sohbet_denemesi_yapar():
    bdm_id = await bdm_ekle("openai", upstream_model="gpt-4o-mini")
    istekler: list[str] = []

    def isleyici(istek: httpx.Request) -> httpx.Response:
        istekler.append(istek.url.path)
        if istek.url.path.endswith("/models"):
            return httpx.Response(404, json={"error": "yok"})
        govde = json.loads(istek.content)
        assert govde["model"] == "gpt-4o-mini"
        assert govde["max_tokens"] == 1
        return httpx.Response(200, json={"choices": [{"message": {"content": "p"}}]})

    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_getir(oturum, bdm_id)
        sonuc = await dogrulama.dogrula(
            bdm, oturum=oturum, tasima=httpx.MockTransport(isleyici)
        )

    assert sonuc["basarili"] is True
    assert sonuc["modeller"] == []
    assert istekler == ["/v1/models", "/v1/chat/completions"]
    assert bdm.durum == BdmDurumu.hazir


async def test_dogrula_baglanti_hatasi_hata_yazar():
    bdm_id = await bdm_ekle("ollama", upstream_model="llama3")

    def isleyici(istek: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("bağlantı kurulamadı")

    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_getir(oturum, bdm_id)
        sonuc = await dogrulama.dogrula(
            bdm, oturum=oturum, tasima=httpx.MockTransport(isleyici)
        )
        await oturum.commit()

    assert sonuc["basarili"] is False
    assert sonuc["modeller"] == []
    assert "bağlanılamadı" in sonuc["mesaj"].lower()
    assert bdm.durum == BdmDurumu.hata
    assert await bdm_durumu(bdm_id) == BdmDurumu.hata


async def test_dogrula_calisiyor_durumunu_korur():
    """Regresyon (BULGU-2): çalışan BDM'in durumu doğrulama sonucuyla değişmez.

    `calisiyor` durumundan `hazir`/`hata` geçişi durum makinesinde yoktur; yazılırsa
    konteyner ayakta kalırken BDM durdurulamaz hale gelir.
    """
    bdm_id = await bdm_ekle("ollama", upstream_model="llama3")
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_getir(oturum, bdm_id)
        bdm.durum = BdmDurumu.calisiyor
        await oturum.commit()

    def kopuk(istek: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("bağlantı kurulamadı")

    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_getir(oturum, bdm_id)
        basarisiz = await dogrulama.dogrula(
            bdm, oturum=oturum, tasima=httpx.MockTransport(kopuk)
        )
        await oturum.commit()

    assert basarisiz["basarili"] is False
    assert "bağlanılamadı" in basarisiz["mesaj"].lower()
    assert await bdm_durumu(bdm_id) == BdmDurumu.calisiyor

    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_getir(oturum, bdm_id)
        basarili = await dogrulama.dogrula(
            bdm,
            oturum=oturum,
            tasima=httpx.MockTransport(
                lambda istek: httpx.Response(200, json={"data": [{"id": "llama3"}]})
            ),
        )
        await oturum.commit()

    assert basarili["basarili"] is True
    assert await bdm_durumu(bdm_id) == BdmDurumu.calisiyor


async def test_dogrula_gecersiz_adres_500_yerine_turkce_sonuc(istemci, yardimci):
    """Regresyon (BULGU-3): çözülemeyen/bozuk adres 500 değil, Türkçe sonuç döner."""
    yonetici = await yardimci.yonetici()
    basliklar = yardimci.basliklar(yonetici)

    # Sema denetiminden geçip httpx'in reddettiği adresler: IDNA-geçersiz konak
    # (`httpx.InvalidURL`) ve geçersiz IDNA kod noktası (`UnicodeError`).
    for temel_url in ("http://\u2603.com/v1", "http://xn--a/v1"):
        bdm_id = await bdm_ekle(
            "ozel", upstream_model="gpt-4o-mini", temel_url=temel_url
        )
        yanit = await istemci.post(
            f"{HAZIRLAMA}/{bdm_id}/dogrula", headers=basliklar
        )

        assert yanit.status_code == 200, temel_url
        govde = yanit.json()
        assert govde["basarili"] is False
        assert govde["mesaj"] == dogrulama.ADRES_GECERSIZ_MESAJI
        assert await bdm_durumu(bdm_id) == BdmDurumu.hata


async def test_dogrula_basarisiz_kod_turkce_mesaj_dondurur():
    bdm_id = await bdm_ekle("openrouter", upstream_model="anthropic/claude-3.5-sonnet")

    def isleyici(istek: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_getir(oturum, bdm_id)
        sonuc = await dogrulama.dogrula(
            bdm, oturum=oturum, tasima=httpx.MockTransport(isleyici)
        )

    assert sonuc["basarili"] is False
    assert "500" in sonuc["mesaj"]
    assert bdm.durum == BdmDurumu.hata


async def test_dogrula_ucu_denetim_izi_yazar(istemci, yardimci, monkeypatch):
    operator = await yardimci.kullanici_ekle(rol=Rol.operator)
    bdm_id = await bdm_ekle("ollama", upstream_model="llama3")
    monkeypatch.setattr(
        dogrulama,
        "varsayilan_tasima",
        lambda: httpx.MockTransport(
            lambda istek: httpx.Response(200, json={"data": [{"id": "llama3"}]})
        ),
    )

    yanit = await istemci.post(
        f"{HAZIRLAMA}/{bdm_id}/dogrula", headers=yardimci.basliklar(operator)
    )

    assert yanit.status_code == 200
    govde = yanit.json()
    assert set(govde) == {"basarili", "gecikme_ms", "modeller", "mesaj"}
    assert govde["basarili"] is True
    assert govde["modeller"] == ["llama3"]
    async with oturum_fabrikasi()() as oturum:
        eylemler = (
            await oturum.execute(
                sa.select(IslemKaydi.eylem, IslemKaydi.hedef_id).where(
                    IslemKaydi.eylem == "bdm.dogrulandi"
                )
            )
        ).all()
    assert eylemler == [("bdm.dogrulandi", str(bdm_id))]


async def test_dogrula_ucu_kimlik_gerekli(istemci):
    bdm_id = await bdm_ekle("ollama")
    yanit = await istemci.post(f"{HAZIRLAMA}/{bdm_id}/dogrula")
    assert yanit.status_code == 401
    assert yanit.json()["hata"]["kod"] == "kimlik_gerekli"


async def test_dogrula_ucu_son_kullaniciya_kapali(istemci, yardimci):
    kullanici = await yardimci.kullanici_ekle()
    bdm_id = await bdm_ekle("ollama")
    yanit = await istemci.post(
        f"{HAZIRLAMA}/{bdm_id}/dogrula", headers=yardimci.basliklar(kullanici)
    )
    assert yanit.status_code == 403
    assert yanit.json()["hata"]["kod"] == "yetki_yok"


async def test_dogrula_ucu_bilinmeyen_bdm_404(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    yanit = await istemci.post(
        f"{HAZIRLAMA}/9999/dogrula", headers=yardimci.basliklar(yonetici)
    )
    assert yanit.status_code == 404
    assert yanit.json()["hata"]["kod"] == "bulunamadi"


# -- cek --------------------------------------------------------------------


async def test_cek_ollama_ilerleme_olaylari():
    bdm_id = await bdm_ekle("ollama", upstream_model="llama3")
    cagrilar: list[dict] = []

    def isleyici(istek: httpx.Request) -> httpx.Response:
        assert istek.url.path == "/api/pull"  # /v1 kirpildi
        cagrilar.append(json.loads(istek.content))
        return httpx.Response(
            200,
            content=_ndjson(
                [
                    {"status": "pulling manifest"},
                    {"status": "downloading", "total": 100, "completed": 40},
                    {"status": "downloading", "total": 100, "completed": 100},
                    {"status": "success"},
                ]
            ),
        )

    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_getir(oturum, bdm_id)
        olaylar = [
            olay
            async for olay in cekim.cek_akisi(bdm, tasima=httpx.MockTransport(isleyici))
        ]

    assert cagrilar == [{"model": "llama3", "stream": True}]
    assert [o["yuzde"] for o in olaylar] == [0, 40, 100, 100]
    assert olaylar[0]["mesaj"] == "Manifest indiriliyor"
    assert olaylar[-1] == {"yuzde": 100, "mesaj": "Model hazır"}
    assert all(o["mesaj"] for o in olaylar)


async def test_cek_desteklenmeyen_saglayici_hata_verir():
    bdm_id = await bdm_ekle("openai", upstream_model="gpt-4o-mini")
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_getir(oturum, bdm_id)
        with pytest.raises(GecersizIstek) as hata:
            async for _ in cekim.cek_akisi(bdm):
                pass
    assert "indirme desteklenmiyor" in hata.value.mesaj


async def test_cek_ucu_desteklenmeyen_saglayici_400(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    bdm_id = await bdm_ekle("openai", upstream_model="gpt-4o-mini")
    yanit = await istemci.post(
        f"{HAZIRLAMA}/{bdm_id}/cek", headers=yardimci.basliklar(yonetici)
    )
    assert yanit.status_code == 400
    assert yanit.json()["hata"]["kod"] == "gecersiz_istek"


async def test_cek_ucu_sse_cerceveleri(istemci, yardimci, monkeypatch):
    yonetici = await yardimci.yonetici()
    bdm_id = await bdm_ekle("ollama", upstream_model="llama3")
    monkeypatch.setattr(
        cekim,
        "varsayilan_tasima",
        lambda: httpx.MockTransport(
            lambda istek: httpx.Response(
                200,
                content=_ndjson(
                    [{"status": "downloading", "total": 10, "completed": 10}]
                ),
            )
        ),
    )

    yanit = await istemci.post(
        f"{HAZIRLAMA}/{bdm_id}/cek", headers=yardimci.basliklar(yonetici)
    )

    assert yanit.status_code == 200
    assert yanit.headers["content-type"].startswith("text/event-stream")
    metin = yanit.text
    assert 'event: ilerleme\ndata: {"yuzde": 100, "mesaj": "Model indiriliyor"}' in metin
    assert metin.rstrip().endswith("event: bitti\ndata: {}")


async def test_cek_ucu_hata_olayini_akittir(istemci, yardimci, monkeypatch):
    yonetici = await yardimci.yonetici()
    bdm_id = await bdm_ekle("ollama", upstream_model="llama3")
    monkeypatch.setattr(
        cekim,
        "varsayilan_tasima",
        lambda: httpx.MockTransport(
            lambda istek: httpx.Response(500, json={"error": "pull reddedildi"})
        ),
    )

    yanit = await istemci.post(
        f"{HAZIRLAMA}/{bdm_id}/cek", headers=yardimci.basliklar(yonetici)
    )

    assert yanit.status_code == 200
    metin = yanit.text
    assert "event: hata" in metin
    assert "ust_saglayici_hatasi" in metin
    assert metin.rstrip().endswith("event: bitti\ndata: {}")


async def test_cek_ucu_upstream_kapali_sse_cercevesi_akitir(istemci, yardimci, monkeypatch):
    """Regresyon (BULGU-1): kapalı upstream'de akış gövdesiz kapanmaz.

    Taşıma hatası yakalanmazsa yanıt `200 text/event-stream` olarak başladığı için
    hata işleyicisi 500 gönderemez ve istemci `RemoteProtocolError` alır.
    """
    yonetici = await yardimci.yonetici()
    bdm_id = await bdm_ekle("ollama", upstream_model="llama3")

    def kopuk(istek: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("bağlantı kurulamadı")

    monkeypatch.setattr(cekim, "varsayilan_tasima", lambda: httpx.MockTransport(kopuk))

    yanit = await istemci.post(
        f"{HAZIRLAMA}/{bdm_id}/cek", headers=yardimci.basliklar(yonetici)
    )

    assert yanit.status_code == 200
    assert yanit.headers["content-type"].startswith("text/event-stream")
    metin = yanit.text
    assert "event: hata" in metin
    assert "ust_saglayici_hatasi" in metin
    assert "bağlanılamadı" in metin
    assert metin.rstrip().endswith("event: bitti\ndata: {}")


async def test_cek_ucu_akis_ortasinda_kopan_baglanti(istemci, yardimci, monkeypatch):
    """Regresyon (BULGU-1): akış ortasında kopan bağlantı da çerçeveye çevrilir."""
    yonetici = await yardimci.yonetici()
    bdm_id = await bdm_ekle("ollama", upstream_model="llama3")

    class _KopanAkis(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield (
                json.dumps({"status": "downloading", "total": 100, "completed": 40})
                + "\n"
            ).encode("utf-8")
            raise httpx.ReadError("akış koptu")

    monkeypatch.setattr(
        cekim,
        "varsayilan_tasima",
        lambda: httpx.MockTransport(lambda istek: httpx.Response(200, stream=_KopanAkis())),
    )

    yanit = await istemci.post(
        f"{HAZIRLAMA}/{bdm_id}/cek", headers=yardimci.basliklar(yonetici)
    )

    assert yanit.status_code == 200
    metin = yanit.text
    assert 'event: ilerleme\ndata: {"yuzde": 40' in metin
    assert "event: hata" in metin
    assert "ust_saglayici_hatasi" in metin
    assert metin.rstrip().endswith("event: bitti\ndata: {}")


async def test_cek_ucu_kapali_porta_karsi_gercek_tasima(istemci, yardimci):
    """Regresyon (BULGU-1): gözlemcinin canlı senaryosu — kapalı porta gerçek httpx taşıması."""
    yonetici = await yardimci.yonetici()
    bdm_id = await bdm_ekle(
        "ollama",
        upstream_model="llama3",
        temel_url="http://127.0.0.1:8198/v1",
    )

    yanit = await istemci.post(
        f"{HAZIRLAMA}/{bdm_id}/cek", headers=yardimci.basliklar(yonetici)
    )

    assert yanit.status_code == 200
    assert yanit.headers["content-type"].startswith("text/event-stream")
    metin = yanit.text
    assert "event: hata" in metin
    assert "ust_saglayici_hatasi" in metin
    assert metin.rstrip().endswith("event: bitti\ndata: {}")


async def test_cek_ucu_kimlik_gerekli(istemci):
    bdm_id = await bdm_ekle("ollama")
    yanit = await istemci.post(f"{HAZIRLAMA}/{bdm_id}/cek")
    assert yanit.status_code == 401


# -- cek: HuggingFace snapshot (vllm/tgi) -----------------------------------


@pytest.mark.parametrize(
    ("saglayici", "model"),
    [
        ("vllm", "mistralai/Mistral-7B-Instruct-v0.3"),
        ("tgi", "meta-llama/Llama-3.1-8B-Instruct"),
    ],
)
async def test_cek_hf_snapshot_indirir(saglayici, model, monkeypatch, tmp_path):
    """Regresyon (spec §7.5): vllm/tgi için ağırlıklar HF snapshot'ı olarak iner."""
    onbellek = tmp_path / "hf-onbellek"
    monkeypatch.setattr(ayarlar, "hf_onbellek", str(onbellek))
    cagrilar: list[tuple[str, dict]] = []
    monkeypatch.setattr(cekim, "snapshot_download", _sahte_snapshot(cagrilar))

    bdm_id = await bdm_ekle(saglayici, upstream_model=model)
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_getir(oturum, bdm_id)
        olaylar = [olay async for olay in cekim.cek_akisi(bdm)]

    assert onbellek.is_dir()
    assert [olay["yuzde"] for olay in olaylar] == [5, 60, 90, 100]
    assert all(olay["mesaj"] for olay in olaylar)
    assert olaylar[-1]["mesaj"] == "Model hazır"
    assert len(cagrilar) == 1
    repo_id, kwargs = cagrilar[0]
    assert repo_id == model
    assert pathlib.Path(kwargs["cache_dir"]) == onbellek
    assert kwargs["token"] is None  # anahtar tanımlı değil


async def test_cek_hf_ozel_saglayici_depo_kimligini_kabul_eder(monkeypatch, tmp_path):
    monkeypatch.setattr(ayarlar, "hf_onbellek", str(tmp_path / "hf"))
    monkeypatch.setattr(cekim, "snapshot_download", _sahte_snapshot())
    bdm_id = await bdm_ekle(
        "ozel",
        upstream_model="Qwen/Qwen2.5-7B-Instruct",
        temel_url="http://127.0.0.1:1234/v1",
    )
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_getir(oturum, bdm_id)
        olaylar = [olay async for olay in cekim.cek_akisi(bdm)]

    assert olaylar[-1] == {"yuzde": 100, "mesaj": "Model hazır"}


async def test_cek_hf_anahtari_snapshot_indirmeye_gecirir(monkeypatch, tmp_path):
    monkeypatch.setattr(ayarlar, "hf_onbellek", str(tmp_path / "hf"))
    cagrilar: list[tuple[str, dict]] = []
    monkeypatch.setattr(cekim, "snapshot_download", _sahte_snapshot(cagrilar))
    bdm_id = await bdm_ekle(
        "vllm",
        upstream_model="meta-llama/Llama-3.1-8B-Instruct",
        api_anahtari="hf-jeton-1234567890",
    )
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_getir(oturum, bdm_id)
        async for _ in cekim.cek_akisi(bdm):
            pass

    assert cagrilar[0][1]["token"] == "hf-jeton-1234567890"


async def test_cek_hf_bos_snapshot_hata_verir(monkeypatch, tmp_path):
    monkeypatch.setattr(ayarlar, "hf_onbellek", str(tmp_path / "hf"))
    monkeypatch.setattr(
        cekim,
        "snapshot_download",
        lambda repo_id, **kwargs: str(tmp_path / "bos"),
    )
    (tmp_path / "bos").mkdir()
    bdm_id = await bdm_ekle("vllm", upstream_model="mistralai/Mistral-7B-Instruct-v0.3")
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_getir(oturum, bdm_id)
        with pytest.raises(UstSaglayiciHatasi) as hata:
            async for _ in cekim.cek_akisi(bdm):
                pass

    assert "boş" in hata.value.mesaj.lower()


@pytest.mark.parametrize("durum", [401, 403, 404])
async def test_cek_hf_hata_mesaji_turkce(durum, monkeypatch, tmp_path):
    monkeypatch.setattr(ayarlar, "hf_onbellek", str(tmp_path / "hf"))

    class _SahteHata(Exception):
        response = types.SimpleNamespace(status_code=durum)

    def _patlat(repo_id: str, **kwargs):
        raise _SahteHata("depo hatası")

    monkeypatch.setattr(cekim, "snapshot_download", _patlat)
    bdm_id = await bdm_ekle("tgi", upstream_model="meta-llama/Llama-3.1-8B-Instruct")
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_getir(oturum, bdm_id)
        with pytest.raises(UstSaglayiciHatasi) as hata:
            async for _ in cekim.cek_akisi(bdm):
                pass

    assert hata.value.kod == "ust_saglayici_hatasi"
    if durum in (401, 403):
        assert "erişim reddedildi" in hata.value.mesaj.lower()
    else:
        assert "bulunamadı" in hata.value.mesaj.lower()


async def test_cek_ucu_hf_sse_cerceveleri(istemci, yardimci, surucu_kur, monkeypatch, tmp_path):
    surucu_kur(gpu_var=True)
    monkeypatch.setattr(ayarlar, "hf_onbellek", str(tmp_path / "hf"))
    monkeypatch.setattr(cekim, "snapshot_download", _sahte_snapshot())
    yonetici = await yardimci.yonetici()
    bdm_id = await bdm_ekle("vllm", upstream_model="mistralai/Mistral-7B-Instruct-v0.3")

    yanit = await istemci.post(
        f"{HAZIRLAMA}/{bdm_id}/cek", headers=yardimci.basliklar(yonetici)
    )

    assert yanit.status_code == 200
    assert yanit.headers["content-type"].startswith("text/event-stream")
    metin = yanit.text
    assert 'event: ilerleme\ndata: {"yuzde": 5' in metin
    assert 'event: ilerleme\ndata: {"yuzde": 100, "mesaj": "Model hazır"}' in metin
    assert "event: hata" not in metin
    assert metin.rstrip().endswith("event: bitti\ndata: {}")


async def test_cek_ucu_hf_hatasi_sse_cercevesi_akitir(
    istemci, yardimci, surucu_kur, monkeypatch, tmp_path
):
    surucu_kur(gpu_var=True)
    monkeypatch.setattr(ayarlar, "hf_onbellek", str(tmp_path / "hf"))

    def _patlat(repo_id: str, **kwargs):
        raise httpx.ConnectError("bağlantı kurulamadı")

    monkeypatch.setattr(cekim, "snapshot_download", _patlat)
    yonetici = await yardimci.yonetici()
    bdm_id = await bdm_ekle("vllm", upstream_model="mistralai/Mistral-7B-Instruct-v0.3")

    yanit = await istemci.post(
        f"{HAZIRLAMA}/{bdm_id}/cek", headers=yardimci.basliklar(yonetici)
    )

    assert yanit.status_code == 200
    metin = yanit.text
    assert "event: hata" in metin
    assert "ust_saglayici_hatasi" in metin
    assert metin.rstrip().endswith("event: bitti\ndata: {}")


@pytest.mark.parametrize(
    ("saglayici", "model", "temel_url"),
    [
        ("vllm", "mistralai/Mistral-7B-Instruct-v0.3", ""),
        ("tgi", "meta-llama/Llama-3.1-8B-Instruct", ""),
        ("ozel", "Qwen/Qwen2.5-7B-Instruct", "http://127.0.0.1:1234/v1"),
    ],
)
async def test_cek_destegi_denetle_hf_dalini_kabul_eder(saglayici, model, temel_url):
    bdm_id = await bdm_ekle(saglayici, upstream_model=model, temel_url=temel_url)
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_getir(oturum, bdm_id)
        cekim.cek_destegi_denetle(bdm)  # fırlatmamalı


@pytest.mark.parametrize(
    ("saglayici", "model", "temel_url"),
    [
        ("openai", "gpt-4o-mini", "https://api.openai.com/v1"),
        ("azure", "gpt-4o-mini", "https://ornek.openai.azure.com/v1"),
        ("openrouter", "anthropic/claude-3.5-sonnet", "https://openrouter.ai/api/v1"),
        ("ozel", "gpt-4o-mini", "http://127.0.0.1:1234/v1"),
    ],
)
async def test_cek_destegi_denetle_hf_olmayanlari_reddeder(saglayici, model, temel_url):
    bdm_id = await bdm_ekle(saglayici, upstream_model=model, temel_url=temel_url)
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_getir(oturum, bdm_id)
        with pytest.raises(GecersizIstek) as hata:
            cekim.cek_destegi_denetle(bdm)

    assert "indirme desteklenmiyor" in hata.value.mesaj


# -- GPU denetimi -----------------------------------------------------------


async def test_gpu_yok_vllm_uclari_surucu_yok_dondurur(istemci, yardimci, surucu_kur):
    surucu_kur(gpu_var=False)
    yonetici = await yardimci.yonetici()
    bdm_id = await bdm_ekle("vllm", upstream_model="mistralai/Mistral-7B-Instruct-v0.3")
    basliklar = yardimci.basliklar(yonetici)

    for yol in ("cek", "manifest"):
        yanit = await istemci.post(f"{HAZIRLAMA}/{bdm_id}/{yol}", headers=basliklar)
        assert yanit.status_code == 503, yol
        hata = yanit.json()["hata"]
        assert hata["kod"] == "surucu_yok"
        assert "GPU" in hata["mesaj"]


async def test_gpu_var_vllm_manifest_uretir(istemci, yardimci, surucu_kur):
    surucu_kur(gpu_var=True, image_onbellek=["vllm/vllm-openai:latest"])
    yonetici = await yardimci.yonetici()
    bdm_id = await bdm_ekle("vllm", upstream_model="mistralai/Mistral-7B-Instruct-v0.3")

    yanit = await istemci.post(
        f"{HAZIRLAMA}/{bdm_id}/manifest", headers=yardimci.basliklar(yonetici)
    )

    assert yanit.status_code == 200
    assert yanit.json()["komut"][:2] == ["vllm", "serve"]


# -- manifest ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("saglayici", "model", "beklenen_komut", "port", "gpu", "bellek_gb", "saglik"),
    [
        (
            "vllm",
            "mistralai/Mistral-7B-Instruct-v0.3",
            [
                "vllm",
                "serve",
                "mistralai/Mistral-7B-Instruct-v0.3",
                "--port",
                "8000",
            ],
            8000,
            True,
            14.0,
            "http://localhost:8000/health",
        ),
        (
            "tgi",
            "meta-llama/Llama-3.1-8B-Instruct",
            [
                "text-generation-inference",
                "--model-id",
                "meta-llama/Llama-3.1-8B-Instruct",
                "--port",
                "8080",
            ],
            8080,
            True,
            16.0,
            "http://localhost:8080/health",
        ),
        (
            "ollama",
            "llama3",
            ["ollama", "serve"],
            11434,
            False,
            4.0,
            "http://localhost:11434/api/tags",
        ),
    ],
)
async def test_manifest_saglayiciya_gore_komut_uretir(
    saglayici, model, beklenen_komut, port, gpu, bellek_gb, saglik
):
    bdm_id = await bdm_ekle(saglayici, upstream_model=model)
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_getir(oturum, bdm_id)
        uretilen = manifest.manifest_uret(bdm)

    assert uretilen["komut"] == beklenen_komut
    assert uretilen["port"] == port
    assert uretilen["gpu"] is gpu
    assert uretilen["image"] == saglayici_bilgisi(saglayici).konteyner_image
    assert uretilen["bellek_gb"] == pytest.approx(bellek_gb)
    assert isinstance(uretilen["ortam"], dict)
    # Regresyon (BULGU-4): Docker sürücüsünün HTTP sağlık sondası bu adresi kullanır.
    assert uretilen["saglik_url"] == saglik


async def test_manifest_uzak_saglayici_icin_uretilmez():
    bdm_id = await bdm_ekle("openai", upstream_model="gpt-4o-mini")
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_getir(oturum, bdm_id)
        with pytest.raises(GecersizIstek) as hata:
            manifest.manifest_uret(bdm)
    assert "manifesti üretilemez" in hata.value.mesaj


async def test_manifest_gizli_ortami_maskeler(istemci, yardimci, surucu_kur):
    surucu_kur(gpu_var=True)
    yonetici = await yardimci.yonetici()
    bdm_id = await bdm_ekle(
        "vllm",
        upstream_model="meta-llama/Llama-3.1-8B-Instruct",
        api_anahtari="hf-gizli-jeton-1234567890",
    )

    yanit = await istemci.post(
        f"{HAZIRLAMA}/{bdm_id}/manifest", headers=yardimci.basliklar(yonetici)
    )

    assert yanit.status_code == 200
    govde = yanit.json()
    ortam = govde["ortam"]
    assert set(ortam) == {"HF_TOKEN", "HF_HOME"}
    assert ortam["HF_TOKEN"] == "hf-g***7890"
    assert ortam["HF_HOME"] == manifest.HF_KONTEYNER_DIZINI
    assert "hf-gizli-jeton-1234567890" not in yanit.text
    assert govde["birimler"] == [
        {
            "kaynak": ayarlar.hf_onbellek_yolu(),
            "hedef": manifest.HF_KONTEYNER_DIZINI,
            "mod": "rw",
        }
    ]
    # Surucuye giden manifest cozulmus jetonu tasir.
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_getir(oturum, bdm_id)
        assert manifest.manifest_uret(bdm)["ortam"]["HF_TOKEN"] == (
            "hf-gizli-jeton-1234567890"
        )


async def test_manifest_hf_onbellegini_konteynere_baglar(monkeypatch, tmp_path):
    """Regresyon (spec §7.5): indirilen snapshot dizini konteynere bağlanır."""
    onbellek = tmp_path / "hf-onbellek"
    monkeypatch.setattr(ayarlar, "hf_onbellek", str(onbellek))
    bdm_id = await bdm_ekle("vllm", upstream_model="mistralai/Mistral-7B-Instruct-v0.3")
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_getir(oturum, bdm_id)
        uretilen = manifest.manifest_uret(bdm)

    assert uretilen["birimler"] == [
        {
            "kaynak": str(onbellek),
            "hedef": manifest.HF_KONTEYNER_DIZINI,
            "mod": "rw",
        }
    ]
    assert pathlib.Path(uretilen["birimler"][0]["kaynak"]) == onbellek
    assert uretilen["ortam"]["HF_HOME"] == manifest.HF_KONTEYNER_DIZINI

    ollama_id = await bdm_ekle("ollama", upstream_model="llama3")
    async with oturum_fabrikasi()() as oturum:
        ollama = await bdm_getir(oturum, ollama_id)
        uretilen_ollama = manifest.manifest_uret(ollama)

    assert uretilen_ollama["birimler"] == []
    assert "HF_HOME" not in uretilen_ollama["ortam"]


# -- on kontrol -------------------------------------------------------------


async def test_on_kontrol_gpu_eksikligini_bildirir(surucu_kur):
    surucu_kur(gpu_var=False, docker_var=True)
    bdm_id = await bdm_ekle("vllm", upstream_model="mistralai/Mistral-7B-Instruct-v0.3")
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_getir(oturum, bdm_id)
        sonuc = await on_kontrol(bdm)

    assert set(sonuc) == {"docker", "gpu", "disk_gb", "image_var", "uygun", "uyarilar"}
    assert sonuc["uygun"] is False
    assert sonuc["gpu"] is False
    assert sonuc["docker"] is True
    assert GPU_UYARI_MESAJI in sonuc["uyarilar"]
    assert sonuc["disk_gb"] > 0


async def test_on_kontrol_gpu_varsa_uygun(surucu_kur):
    surucu_kur(
        gpu_var=True, docker_var=True, image_onbellek=["vllm/vllm-openai:latest"]
    )
    bdm_id = await bdm_ekle("vllm", upstream_model="mistralai/Mistral-7B-Instruct-v0.3")
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_getir(oturum, bdm_id)
        sonuc = await on_kontrol(bdm)

    assert sonuc["uygun"] is True
    assert sonuc["gpu"] is True
    assert sonuc["image_var"] is True
    assert sonuc["uyarilar"] == []


async def test_on_kontrol_ucu_uyari_dondurur(istemci, yardimci, surucu_kur):
    surucu_kur(gpu_var=False)
    operator = await yardimci.kullanici_ekle(rol=Rol.operator)
    bdm_id = await bdm_ekle("tgi", upstream_model="meta-llama/Llama-3.1-8B-Instruct")

    yanit = await istemci.get(
        f"{HAZIRLAMA}/{bdm_id}/on-kontrol", headers=yardimci.basliklar(operator)
    )

    assert yanit.status_code == 200
    govde = yanit.json()
    assert govde["uygun"] is False
    assert GPU_UYARI_MESAJI in govde["uyarilar"]


@pytest.mark.parametrize(
    ("saglayici", "temel_url"),
    [
        ("openai", "https://api.openai.com/v1"),
        ("azure", "https://ornek.openai.azure.com/v1"),
        ("openrouter", "https://openrouter.ai/api/v1"),
        ("ozel", "http://127.0.0.1:1234/v1"),
    ],
)
async def test_on_kontrol_uzak_saglayicida_konteyner_uyarisi_uretmez(
    saglayici, temel_url, surucu_kur
):
    """Regresyon (BULGU-5): uzak sağlayıcıda Docker/imaj uyarısı yanıltıcıdır."""
    surucu_kur(docker_var=False, gpu_var=False, image_onbellek=[])
    bdm_id = await bdm_ekle(
        saglayici, upstream_model="gpt-4o-mini", temel_url=temel_url
    )
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_getir(oturum, bdm_id)
        sonuc = await on_kontrol(bdm)

    assert sonuc["uygun"] is True
    assert sonuc["uyarilar"] == []


async def test_on_kontrol_ollama_sunucusunda_konteyner_uyarisi_uretmez(surucu_kur):
    """Regresyon (BULGU-5): Ollama host üzerinde çalışan sunucudur, imaj gerektirmez."""
    surucu_kur(docker_var=False, gpu_var=False, image_onbellek=[])
    bdm_id = await bdm_ekle("ollama", upstream_model="llama3")
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_getir(oturum, bdm_id)
        sonuc = await on_kontrol(bdm)

    assert sonuc["uygun"] is True
    assert sonuc["uyarilar"] == []


async def test_on_kontrol_konteyner_saglayicisinda_docker_uyarisi_kalir(surucu_kur):
    """Konteyner sağlayıcılarında (vllm/tgi) Docker/imaj uyarıları korunur."""
    surucu_kur(docker_var=False, gpu_var=True, image_onbellek=[])
    bdm_id = await bdm_ekle("vllm", upstream_model="mistralai/Mistral-7B-Instruct-v0.3")
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_getir(oturum, bdm_id)
        sonuc = await on_kontrol(bdm)

    assert sonuc["uygun"] is False
    assert DOCKER_UYARI_MESAJI in sonuc["uyarilar"]
    assert any("vllm/vllm-openai:latest" in uyari for uyari in sonuc["uyarilar"])
