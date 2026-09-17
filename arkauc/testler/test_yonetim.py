"""Yönetim ucu ve konteyner sürücüleri testleri (spec §7.6, §10)."""

from __future__ import annotations

import asyncio
import importlib
import json
import os
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import pytest
import sqlalchemy as sa

from arkauc.app.cekirdek.hatalar import SurucuYok, UstSaglayiciHatasi
from arkauc.app.servisler.konteyner import SahteSurucu, surucu_ata, surucu_temizle
from bdm_veritabani.modeller import Bdm, BdmDurumu, IslemKaydi, Saglayici
from bdm_veritabani.oturum import oturum_fabrikasi

gunlukler = importlib.import_module("bdm_yönetim_ucu.gunlukler")
yasam_dongusu = importlib.import_module("bdm_yönetim_ucu.yasam_dongusu")

UC = "/api/v1/bdm/yonetim"
SAHTE_MANIFEST: dict[str, object] = {
    "image": "vllm/vllm-openai:latest",
    "komut": ["--model", "mistralai/Mistral-7B-Instruct-v0.2"],
    "port": 8000,
    "gpu": True,
    "bellek_gb": 12,
    "ortam": {"HF_HOME": "/models"},
    "saglik_url": "http://localhost:8000/health",
}


async def _manifest(bdm: Bdm) -> dict[str, object]:
    """Hazırlama modülü paralel geliştirildiği için testlerde sabit manifest kullanılır."""
    return dict(SAHTE_MANIFEST)


async def _bdm_ekle(
    saglayici: str = "vllm",
    durum: BdmDurumu = BdmDurumu.taslak,
    *,
    slug: str | None = None,
    temel_url: str = "http://localhost:8000/v1",
    upstream_model: str = "mistralai/Mistral-7B-Instruct-v0.2",
    konteyner: dict[str, object] | None = None,
) -> int:
    async with oturum_fabrikasi()() as oturum:
        bdm = Bdm(
            slug=slug or f"{saglayici}-test",
            gorunen_ad=f"{saglayici} test modeli",
            saglayici=Saglayici(saglayici),
            temel_url=temel_url,
            upstream_model=upstream_model,
            durum=durum,
            yerel_mi=True,
            yetenekler={"akis": True, "gorsel": False, "arac": False},
            konteyner=konteyner,
        )
        oturum.add(bdm)
        await oturum.commit()
        await oturum.refresh(bdm)
        return bdm.id


async def _durum_yaz(bdm_id: int, durum: BdmDurumu) -> None:
    async with oturum_fabrikasi()() as oturum:
        bdm = await oturum.get(Bdm, bdm_id)
        assert bdm is not None
        await yasam_dongusu.gecisi_kilitle(oturum, bdm, durum)
        await oturum.commit()


async def _bdm_oku(bdm_id: int) -> Bdm:
    async with oturum_fabrikasi()() as oturum:
        bdm = await oturum.get(Bdm, bdm_id)
        assert bdm is not None
        return bdm


async def _eylemler(bdm_id: int) -> set[str]:
    async with oturum_fabrikasi()() as oturum:
        satirlar = (
            await oturum.execute(
                sa.select(IslemKaydi.eylem).where(
                    IslemKaydi.hedef_tur == "bdm", IslemKaydi.hedef_id == str(bdm_id)
                )
            )
        ).scalars()
        return set(satirlar.all())


@pytest.fixture
def surucu():
    sahte = SahteSurucu(docker_var=True, gpu_var=True)
    surucu_ata(sahte)
    yield sahte
    surucu_temizle()


@pytest.fixture
def surucu_gpusuz():
    sahte = SahteSurucu(docker_var=True, gpu_var=False)
    surucu_ata(sahte)
    yield sahte
    surucu_temizle()


@pytest.fixture
def manifest(monkeypatch):
    monkeypatch.setattr(yasam_dongusu, "manifest_al", _manifest)
    return SAHTE_MANIFEST


class _SahteSunucu:
    """Testler için sahte HTTP sunucusu (127.0.0.1, rastgele port).

    - `GET /api/tags` → `{"models": [{"name": "llama3"}]}` (Ollama yoklaması)
    - `POST /api/generate` → gövdesi `istekler` listesine yazılır, `yanit_kodu` döner
    - `GET /saglik` → `saglik_kodu` ile yanıtlanır (Docker sağlık sondası)
    """

    def __init__(self) -> None:
        self.istekler: list[tuple[str, dict[str, object]]] = []
        self.yanit_kodu = 200
        self.saglik_kodu = 200
        kayit = self

        class Isleyici(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args: object) -> None:  # test çıktısını kirletme
                return None

            def _gonder(self, kod: int, govde: dict[str, object]) -> None:
                ham = json.dumps(govde).encode("utf-8")
                self.send_response(kod)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(ham)))
                self.end_headers()
                self.wfile.write(ham)

            def do_GET(self) -> None:
                if self.path.startswith("/api/tags"):
                    kayit.istekler.append(("GET /api/tags", {}))
                    self._gonder(200, {"models": [{"name": "llama3"}]})
                elif self.path.startswith("/saglik"):
                    kayit.istekler.append(("GET /saglik", {}))
                    self._gonder(kayit.saglik_kodu, {})
                else:
                    self._gonder(404, {})

            def do_POST(self) -> None:
                uzunluk = int(self.headers.get("Content-Length") or 0)
                ham = self.rfile.read(uzunluk).decode("utf-8") if uzunluk else ""
                try:
                    govde: dict[str, object] = json.loads(ham) if ham else {}
                except json.JSONDecodeError:
                    govde = {"ham": ham}
                kayit.istekler.append((f"POST {self.path}", govde))
                self._gonder(kayit.yanit_kodu, {"done": True})

        self._sunucu = ThreadingHTTPServer(("127.0.0.1", 0), Isleyici)
        self._durdurucu = threading.Thread(target=self._sunucu.serve_forever, daemon=True)
        self._durdurucu.start()
        self.temel_url = f"http://127.0.0.1:{self._sunucu.server_address[1]}"

    def kapat(self) -> None:
        self._sunucu.shutdown()
        self._sunucu.server_close()

    def uretim_govdeleri(self) -> list[dict[str, object]]:
        return [govde for ad, govde in self.istekler if ad == "POST /api/generate"]


@pytest.fixture
def sahte_sunucu() -> _SahteSunucu:
    sunucu = _SahteSunucu()
    yield sunucu
    sunucu.kapat()


class _KopanSurucu(SahteSurucu):
    """Akış ortasında sürücü hatası veren sürücü."""

    async def gunlukler(self, konteyner_id: str, satir: int = 200):  # type: ignore[override]
        yield "ilk satır"
        raise SurucuYok("Konteyner akışı koptu.")


class _AsiliSurucu(SahteSurucu):
    """Satır üretmeyen, test serbest bırakana kadar askıda kalan sürücü (nabız ölçümü)."""

    def __init__(self) -> None:
        super().__init__()
        self.devam = asyncio.Event()

    async def gunlukler(self, konteyner_id: str, satir: int = 200):  # type: ignore[override]
        await self.devam.wait()
        yield "geç kalan satır"


class _DurdurmaHatasiSurucusu(SahteSurucu):
    """`durdur` çağrısında çalışma zamanı hatası veren sürücü."""

    async def durdur(self, konteyner_id: str) -> None:
        raise UstSaglayiciHatasi("Model boşaltılamadı (sahte).")


class _YavasBaslatanSurucu(SahteSurucu):
    """Konteyner başlatmayı geciktirir: iki isteğin iç içe geçmesini sağlar."""

    def __init__(self, gecikme: float = 0.2) -> None:
        super().__init__(docker_var=True, gpu_var=True)
        self.gecikme = gecikme

    async def baslat(self, bdm: dict[str, object], manifest: dict[str, object]) -> str:
        await asyncio.sleep(self.gecikme)
        return await super().baslat(bdm, manifest)  # type: ignore[arg-type]


class _SahteKonteyner:
    """`docker` SDK konteyner nesnesinin sağlık sondası için gereken yüzü."""

    def __init__(self, *, etiketler: dict[str, str] | None = None, durum: str = "running") -> None:
        self.labels = etiketler if etiketler is not None else {}
        self.status = durum
        self.id = "sahte-konteyner"

    def reload(self) -> None:
        return None

    def stop(self, timeout: int = 10) -> None:
        self.status = "exited"

    def remove(self, force: bool = False) -> None:
        return None


class _SahteKonteynerler:
    def __init__(self, konteyner: _SahteKonteyner) -> None:
        self._konteyner = konteyner
        self.son_ayarlar: dict[str, object] = {}

    def get(self, ad: str) -> _SahteKonteyner:
        if ad != self._konteyner.id:
            raise RuntimeError("no such container")
        return self._konteyner

    def run(self, image: str, **ayarlar: object) -> _SahteKonteyner:
        self.son_ayarlar = dict(ayarlar)
        etiketler = ayarlar.get("labels") or {}
        self._konteyner.labels = dict(etiketler)  # type: ignore[arg-type]
        return self._konteyner


class _SahteImajlar:
    def get(self, image: str) -> object:
        return object()

    def pull(self, image: str) -> object:
        return object()


class _SahteDockerIstemcisi:
    """`docker.from_env()` yerine geçen istemci (Docker'sız sağlık sondası ölçümü)."""

    def __init__(self, konteyner: _SahteKonteyner) -> None:
        self.containers = _SahteKonteynerler(konteyner)
        self.images = _SahteImajlar()


@pytest.fixture
async def personel(yardimci):
    return yardimci.basliklar(await yardimci.yonetici())


async def test_taslak_hazir_calisiyor_durdu(istemci, personel, surucu, manifest):
    bdm_id = await _bdm_ekle("vllm", BdmDurumu.taslak)

    # taslak → calisiyor geçişi yok
    yanit = await istemci.post(f"{UC}/{bdm_id}/baslat", headers=personel)
    assert yanit.status_code == 409
    assert yanit.json()["hata"]["kod"] == "gecersiz_gecis"

    # taslak → hazir
    await _durum_yaz(bdm_id, BdmDurumu.hazir)

    yanit = await istemci.post(f"{UC}/{bdm_id}/baslat", headers=personel)
    assert yanit.status_code == 200
    govde = yanit.json()
    konteyner_id = govde["konteyner_id"]
    assert govde["durum"] == "calisiyor"
    assert konteyner_id in surucu.konteynerler

    kayit = await _bdm_oku(bdm_id)
    assert kayit.durum == BdmDurumu.calisiyor
    assert kayit.konteyner == {
        "image": "vllm/vllm-openai:latest",
        "gpu": True,
        "port": 8000,
        "bellek_gb": 12,
        "konteyner_id": konteyner_id,
    }

    yanit = await istemci.get(f"{UC}/{bdm_id}/durum", headers=personel)
    assert yanit.json() == {
        "durum": "calisiyor",
        "konteyner_id": konteyner_id,
        "saglik": {"calisiyor": True, "hazir": True, "mesaj": "Çalışıyor."},
    }

    yanit = await istemci.get(f"{UC}/{bdm_id}/saglik", headers=personel)
    saglik = yanit.json()
    assert (saglik["calisiyor"], saglik["hazir"]) == (True, True)
    assert saglik["ayrinti"]["konteyner_id"] == konteyner_id

    yanit = await istemci.post(f"{UC}/{bdm_id}/durdur", headers=personel)
    assert yanit.status_code == 200
    assert yanit.json() == {"durum": "durdu"}
    assert (await _bdm_oku(bdm_id)).durum == BdmDurumu.durdu

    yanit = await istemci.post(f"{UC}/{bdm_id}/durdur", headers=personel)
    assert yanit.status_code == 409
    assert yanit.json()["hata"]["kod"] == "gecersiz_gecis"

    yanit = await istemci.get(f"{UC}/{bdm_id}/saglik", headers=personel)
    assert yanit.json()["calisiyor"] is False

    assert {"bdm.baslatildi", "bdm.durduruldu"} <= await _eylemler(bdm_id)


async def test_yeniden_baslat_yeni_konteyner(istemci, personel, surucu, manifest):
    bdm_id = await _bdm_ekle("vllm", BdmDurumu.hazir)
    yanit = await istemci.post(f"{UC}/{bdm_id}/baslat", headers=personel)
    assert yanit.status_code == 200

    yanit = await istemci.post(f"{UC}/{bdm_id}/yeniden-baslat", headers=personel)
    assert yanit.status_code == 200
    govde = yanit.json()
    assert govde["durum"] == "calisiyor"
    assert govde["konteyner_id"] in surucu.konteynerler

    # yeniden başlatma: eski konteyner durdurulup silinir, yenisi başlatılır
    assert [ad for ad, _ in surucu.cagrilar] == ["baslat", "durdur", "sil", "baslat"]
    assert len(surucu.konteynerler) == 1

    kayit = await _bdm_oku(bdm_id)
    assert kayit.konteyner["konteyner_id"] == govde["konteyner_id"]
    assert "bdm.yeniden_baslatildi" in await _eylemler(bdm_id)


async def test_gunlukler_sse_akisi(istemci, personel, surucu, manifest):
    bdm_id = await _bdm_ekle("vllm", BdmDurumu.hazir)

    # konteyner yokken günlük istenemez
    yanit = await istemci.get(f"{UC}/{bdm_id}/gunlukler", headers=personel)
    assert yanit.status_code == 503
    assert yanit.json()["hata"]["kod"] == "surucu_yok"

    await istemci.post(f"{UC}/{bdm_id}/baslat", headers=personel)

    async with istemci.stream(
        "GET", f"{UC}/{bdm_id}/gunlukler?satir=2", headers=personel
    ) as akis:
        assert akis.status_code == 200
        assert akis.headers["content-type"].startswith("text/event-stream")
        govde = "".join([parca async for parca in akis.aiter_text()])

    assert govde.count("event: satir") == 2
    assert '"metin": "model yuklendi"' in govde
    assert '"metin": "hazir"' in govde


async def test_vllm_gpu_yok_503(istemci, personel, surucu_gpusuz, manifest):
    bdm_id = await _bdm_ekle("vllm", BdmDurumu.hazir)

    yanit = await istemci.post(f"{UC}/{bdm_id}/baslat", headers=personel)
    assert yanit.status_code == 503
    hata = yanit.json()["hata"]
    assert hata["kod"] == "surucu_yok"
    assert hata["mesaj"] == (
        "Bu model GPU gerektirir; Ollama gibi CPU uyumlu bir sağlayıcı seçin "
        "veya GPU çalışma zamanını kurun."
    )
    # Başarısız başlatma `hata`ya çekilir; kayıt "çalışıyor" gibi görünmez.
    kayit = await _bdm_oku(bdm_id)
    assert kayit.durum == BdmDurumu.hata
    assert kayit.konteyner is None
    assert "bdm.baslatilamadi" in await _eylemler(bdm_id)


async def test_surucu_durum_sozlugu(istemci, personel, surucu):
    yanit = await istemci.get(f"{UC}/surucu/durum", headers=personel)
    assert yanit.status_code == 200
    assert yanit.json() == {
        "surucu": "sahte",
        "docker": True,
        "gpu": True,
        "gpu_listesi": ["NVIDIA GeForce RTX 4090"],
        "image_onbellek": ["ollama/ollama:latest"],
        "mesaj": "",
    }


async def test_yol_guncelle_konteyner_kaydini_korur(istemci, personel, surucu, manifest):
    bdm_id = await _bdm_ekle("vllm", BdmDurumu.hazir)
    konteyner_id = (
        await istemci.post(f"{UC}/{bdm_id}/baslat", headers=personel)
    ).json()["konteyner_id"]

    yanit = await istemci.patch(
        f"{UC}/{bdm_id}/yol",
        headers=personel,
        json={"takma_ad": "hizli-model", "oncelik": 5},
    )
    assert yanit.status_code == 200
    konteyner = yanit.json()["konteyner"]
    assert konteyner["yol"] == {"takma_ad": "hizli-model", "oncelik": 5}
    assert konteyner["konteyner_id"] == konteyner_id

    kayit = await _bdm_oku(bdm_id)
    assert kayit.konteyner["yol"]["takma_ad"] == "hizli-model"
    assert kayit.konteyner["konteyner_id"] == konteyner_id


async def test_yonetim_uclari_personel_ister(istemci, yardimci):
    bdm_id = await _bdm_ekle("vllm", BdmDurumu.hazir)

    yanit = await istemci.post(f"{UC}/{bdm_id}/baslat")
    assert yanit.status_code == 401
    assert yanit.json()["hata"]["kod"] == "kimlik_gerekli"

    son_kullanici = await yardimci.kullanici_ekle()
    basliklar = yardimci.basliklar(son_kullanici)
    for yontem, yol in (
        ("GET", f"{UC}/{bdm_id}/durum"),
        ("GET", f"{UC}/{bdm_id}/saglik"),
        ("GET", f"{UC}/surucu/durum"),
    ):
        yanit = await istemci.request(yontem, yol, headers=basliklar)
        assert yanit.status_code == 403
        assert yanit.json()["hata"]["kod"] == "yetki_yok"


def _port_bos_mu(port: int) -> bool:
    with socket.socket() as yuvak:
        yuvak.settimeout(0.5)
        return yuvak.connect_ex(("127.0.0.1", port)) != 0


@pytest.mark.skipif(
    os.environ.get("KUTYAI_TEST_DOCKER") != "1",
    reason="Gerçek Docker entegrasyonu için KUTYAI_TEST_DOCKER=1 gerekir.",
)
async def test_docker_surucusu_gercek_konteyner():
    """Gerçek Docker + ollama/ollama imajı ile açma, sağlık, günlük ve kapatma."""
    from arkauc.app.cekirdek.hatalar import SurucuYok
    from arkauc.app.servisler.konteyner_docker import DockerSurucusu

    surucu = DockerSurucusu()
    try:
        durum = await surucu.durum()
    except SurucuYok as hata:
        pytest.skip(f"Docker çalışma zamanına ulaşılamadı: {hata.mesaj}")
    image = "ollama/ollama:latest"
    if image not in durum.image_onbellek:
        pytest.skip(f"{image} yerel imaj önbelleğinde yok.")
    if not _port_bos_mu(11434):
        pytest.skip("11434 portu kullanımda; entegrasyon konteyneri başlatılamaz.")

    bdm = {
        "id": 0,
        "slug": "entegrasyon-ollama",
        "temel_url": "http://localhost:11434/v1",
        "upstream_model": "llama3",
    }
    manifest = {
        "image": image,
        "komut": [],
        "port": 11434,
        "gpu": False,
        "bellek_gb": 2,
        "ortam": {},
    }

    konteyner_id = await surucu.baslat(bdm, manifest)
    try:
        saglik = await surucu.saglik(konteyner_id)
        assert saglik.calisiyor is True

        akis = surucu.gunlukler(konteyner_id, 20)
        satirlar: list[str] = []
        try:
            while len(satirlar) < 3:
                satirlar.append(await asyncio.wait_for(anext(akis), timeout=30))
        except (StopAsyncIteration, asyncio.TimeoutError):
            pass
        finally:
            await akis.aclose()
        assert satirlar, "Konteyner günlüğü okunamadı."
    finally:
        await surucu.durdur(konteyner_id)
        await surucu.sil(konteyner_id)

    assert (await surucu.saglik(konteyner_id)).calisiyor is False


# -- Dalga 1 gözlem bulguları: regresyon testleri ---------------------------


async def test_yerel_durdur_modeli_bosaltir(istemci, personel, manifest, sahte_sunucu):
    """`POST /{id}/durdur` gerçekten Ollama'ya `keep_alive: 0` isteği gönderir."""
    from arkauc.app.servisler.konteyner_yerel import YerelSurucusu

    surucu_ata(YerelSurucusu(temel_url=sahte_sunucu.temel_url))
    try:
        bdm_id = await _bdm_ekle(
            "ollama",
            BdmDurumu.hazir,
            temel_url=f"{sahte_sunucu.temel_url}/v1",
            upstream_model="llama3",
        )
        yanit = await istemci.post(f"{UC}/{bdm_id}/baslat", headers=personel)
        assert yanit.status_code == 200

        yanit = await istemci.post(f"{UC}/{bdm_id}/durdur", headers=personel)
        assert yanit.status_code == 200
        assert yanit.json() == {"durum": "durdu"}

        assert sahte_sunucu.uretim_govdeleri() == [
            {"model": "llama3", "keep_alive": 0, "prompt": ""}
        ]
        assert (await _bdm_oku(bdm_id)).durum == BdmDurumu.durdu
    finally:
        surucu_temizle()


async def test_yerel_durdur_kayit_yoksa_hata_verir():
    from arkauc.app.servisler.konteyner_yerel import YerelSurucusu

    with pytest.raises(SurucuYok):
        await YerelSurucusu().durdur("yerel:bilinmeyen")


async def test_yerel_durdur_basarisiz_istekte_ust_saglayici_hatasi(sahte_sunucu):
    from arkauc.app.servisler.konteyner_yerel import YerelSurucusu

    surucu = YerelSurucusu()
    await surucu.baslat(
        {
            "slug": "bozuk",
            "temel_url": f"{sahte_sunucu.temel_url}/v1",
            "upstream_model": "llama3",
        },
        {},
    )
    sahte_sunucu.yanit_kodu = 500
    with pytest.raises(UstSaglayiciHatasi):
        await surucu.durdur("yerel:bozuk")


async def test_yerel_saglik_ve_gunlukler_bdm_adresini_kullanir(
    istemci, personel, manifest, sahte_sunucu
):
    """Sağlık ve günlükler varsayılan 11434'e değil BDM'nin adresine bakar."""
    from arkauc.app.servisler.konteyner_yerel import YerelSurucusu

    surucu_ata(YerelSurucusu(temel_url=sahte_sunucu.temel_url))
    try:
        bdm_id = await _bdm_ekle(
            "ollama",
            BdmDurumu.hazir,
            temel_url=f"{sahte_sunucu.temel_url}/v1",
            upstream_model="llama3",
        )
        assert (await istemci.post(f"{UC}/{bdm_id}/baslat", headers=personel)).status_code == 200

        saglik = (await istemci.get(f"{UC}/{bdm_id}/saglik", headers=personel)).json()
        assert (saglik["calisiyor"], saglik["hazir"]) == (True, True)
        assert saglik["ayrinti"]["temel_url"] == sahte_sunucu.temel_url
        assert saglik["ayrinti"]["adres_kaynagi"] == "bellek"
        assert saglik["ayrinti"]["modeller"] == ["llama3"]

        govde = (await istemci.get(f"{UC}/{bdm_id}/gunlukler", headers=personel)).text
        assert sahte_sunucu.temel_url in govde
        assert "11434" not in govde
    finally:
        surucu_temizle()


async def test_gunlukler_konteyner_yokken_hata_zarfi(istemci, personel, surucu):
    """Konteyner kaydı var ama konteyner yoksa SSE başlamaz: 503 hata zarfı."""
    bdm_id = await _bdm_ekle(
        "vllm", BdmDurumu.hazir, konteyner={"konteyner_id": "boyle-bir-konteyner-yok"}
    )

    yanit = await istemci.get(f"{UC}/{bdm_id}/gunlukler", headers=personel)
    assert yanit.status_code == 503
    assert yanit.json()["hata"]["kod"] == "surucu_yok"
    assert yanit.headers["content-type"].startswith("application/json")


async def test_gunlukler_akis_ortasinda_hata_cercevesi(istemci, personel):
    """Akış ortasında kopan sürücü `event: hata` + hata zarfı üretir."""
    surucu_ata(_KopanSurucu())
    try:
        bdm_id = await _bdm_ekle("vllm", BdmDurumu.hazir, konteyner={"konteyner_id": "kopan-1"})
        async with istemci.stream("GET", f"{UC}/{bdm_id}/gunlukler", headers=personel) as akis:
            assert akis.status_code == 200
            govde = "".join([parca async for parca in akis.aiter_text()])
    finally:
        surucu_temizle()

    assert '"metin": "ilk satır"' in govde
    assert "event: hata" in govde
    assert '"hata"' in govde and '"kod": "surucu_yok"' in govde


async def test_gunlukler_nabiz_gonderir(monkeypatch):
    """Satır üretmeyen konteynerde akış askıda kalmaz, `: nabız` gönderilir."""
    monkeypatch.setattr(gunlukler, "ILK_SATIR_ZAMAN_ASIMI", 0.02)
    monkeypatch.setattr(gunlukler, "NABIZ_SANIYE", 0.02)
    asili = _AsiliSurucu()

    akis = await gunlukler.akis(asili, "asili-1", 200)
    try:
        parca = await asyncio.wait_for(anext(akis), timeout=2)
        assert ": nabız" in parca
    finally:
        # İstemci bağlantıyı bıraktığında akış askıda kalmadan kapanmalı.
        await asyncio.wait_for(akis.aclose(), timeout=2)
        asili.devam.set()

    assert ": nabız" in parca


async def test_hata_durumundan_durdur_ile_kurtarma(istemci, personel, manifest, surucu):
    """`hata` durumundan `durdur` 200; `baslat` 409 kalır."""
    bdm_id = await _bdm_ekle("vllm", BdmDurumu.hazir)
    assert (await istemci.post(f"{UC}/{bdm_id}/baslat", headers=personel)).status_code == 200
    await _durum_yaz(bdm_id, BdmDurumu.hata)

    yanit = await istemci.post(f"{UC}/{bdm_id}/baslat", headers=personel)
    assert yanit.status_code == 409
    assert yanit.json()["hata"]["kod"] == "gecersiz_gecis"

    yanit = await istemci.post(f"{UC}/{bdm_id}/durdur", headers=personel)
    assert yanit.status_code == 200
    assert yanit.json() == {"durum": "durdu"}
    assert (await _bdm_oku(bdm_id)).durum == BdmDurumu.durdu
    assert "bdm.durduruldu" in await _eylemler(bdm_id)

    assert (await istemci.post(f"{UC}/{bdm_id}/baslat", headers=personel)).status_code == 200


async def test_hata_kurtarmasi_calisma_zamani_hatasinda_kilitlenmez(istemci, personel):
    """Konteyner kaydı yoksa ya da sürücü hata verirse `hata`dan çıkış yine mümkün."""
    surucu_ata(_DurdurmaHatasiSurucusu())
    try:
        kimliksiz = await _bdm_ekle("vllm", BdmDurumu.hata, slug="hata-kimliksiz")
        yanit = await istemci.post(f"{UC}/{kimliksiz}/durdur", headers=personel)
        assert yanit.status_code == 200
        assert (await _bdm_oku(kimliksiz)).durum == BdmDurumu.durdu

        kayitli = await _bdm_ekle(
            "vllm", BdmDurumu.hata, slug="hata-kayitli", konteyner={"konteyner_id": "kopan-9"}
        )
        yanit = await istemci.post(f"{UC}/{kayitli}/durdur", headers=personel)
        assert yanit.status_code == 200
        assert (await _bdm_oku(kayitli)).durum == BdmDurumu.durdu
    finally:
        surucu_temizle()


async def test_calisirken_durdurma_hatasi_yutulmaz(istemci, personel):
    """`calisiyor`dan çıkışta sürücü hatası 502 olarak bildirilir, durum değişmez."""
    surucu_ata(_DurdurmaHatasiSurucusu())
    try:
        bdm_id = await _bdm_ekle(
            "vllm", BdmDurumu.calisiyor, konteyner={"konteyner_id": "kopan-10"}
        )
        yanit = await istemci.post(f"{UC}/{bdm_id}/durdur", headers=personel)
        assert yanit.status_code == 502
        assert yanit.json()["hata"]["kod"] == "ust_saglayici_hatasi"
        assert (await _bdm_oku(bdm_id)).durum == BdmDurumu.calisiyor
    finally:
        surucu_temizle()


async def test_yol_guncelleme_denetim_izine_yazilir(istemci, personel, surucu):
    bdm_id = await _bdm_ekle("vllm", BdmDurumu.hazir)

    yanit = await istemci.patch(
        f"{UC}/{bdm_id}/yol",
        headers=personel,
        json={"oncelik": 7, "takma_ad": "hizli"},
    )
    assert yanit.status_code == 200

    async with oturum_fabrikasi()() as oturum:
        satir = (
            (
                await oturum.execute(
                    sa.select(IslemKaydi).where(
                        IslemKaydi.hedef_tur == "bdm",
                        IslemKaydi.hedef_id == str(bdm_id),
                        IslemKaydi.eylem == "bdm.yol_guncellendi",
                    )
                )
            )
            .scalars()
            .one()
        )
    assert satir.ayrinti["yol"] == {"oncelik": 7, "takma_ad": "hizli"}


async def test_docker_saglik_sondasi_manifest_adresini_kullanir(monkeypatch, sahte_sunucu):
    """Manifest `saglik_url` üretiyorsa hazır bilgisi HTTP sondasından gelir."""
    from arkauc.app.servisler.konteyner_docker import DockerSurucusu

    konteyner = _SahteKonteyner()
    surucu = DockerSurucusu()
    monkeypatch.setattr(surucu, "istemci", lambda: _SahteDockerIstemcisi(konteyner))
    saglik_url = f"{sahte_sunucu.temel_url}/saglik"

    konteyner_id = await surucu.baslat(
        {"slug": "docker-test"},
        {"image": "nginx:alpine", "komut": [], "saglik_url": saglik_url},
    )
    saglik = await surucu.saglik(konteyner_id)
    assert (saglik.calisiyor, saglik.hazir) == (True, True)
    assert saglik.ayrinti["saglik_url"] == saglik_url
    assert saglik.ayrinti["saglik_kaynagi"] == "saglik_url"

    sahte_sunucu.saglik_kodu = 503
    saglik = await surucu.saglik(konteyner_id)
    assert (saglik.calisiyor, saglik.hazir) == (True, False)

    etiketsiz = _SahteKonteyner()
    etiketsiz_surucu = DockerSurucusu()
    monkeypatch.setattr(etiketsiz_surucu, "istemci", lambda: _SahteDockerIstemcisi(etiketsiz))
    kimlik = await etiketsiz_surucu.baslat({"slug": "etiketsiz"}, {"image": "nginx:alpine"})
    saglik = await etiketsiz_surucu.saglik(kimlik)
    assert saglik.hazir is True
    assert saglik.ayrinti["saglik_kaynagi"] == "konteyner_durumu"
    assert saglik.ayrinti["saglik_url_yok"] is True


async def test_docker_baslat_manifest_birimlerini_volume_olarak_baglar(monkeypatch):
    """Manifest `birimler` alanı `containers.run(volumes=...)` çağrısına dönüşür."""
    from arkauc.app.servisler.konteyner_docker import DockerSurucusu

    konteyner = _SahteKonteyner()
    istemci = _SahteDockerIstemcisi(konteyner)
    surucu = DockerSurucusu()
    monkeypatch.setattr(surucu, "istemci", lambda: istemci)

    await surucu.baslat(
        {"slug": "hacimli"},
        {
            "image": "nginx:alpine",
            "komut": [],
            "birimler": [
                {
                    "kaynak": "E:/kutyai-app/bdm_veritabani/hf-onbellek",
                    "hedef": "/root/.cache/huggingface",
                    "mod": "rw",
                },
                {"kaynak": "E:/kutyai-app/gecici", "hedef": "/veri", "mod": "ro"},
            ],
        },
    )
    # Windows yol biçimi Docker'a olduğu gibi geçer.
    assert istemci.containers.son_ayarlar["volumes"] == {
        "E:/kutyai-app/bdm_veritabani/hf-onbellek": {
            "bind": "/root/.cache/huggingface",
            "mode": "rw",
        },
        "E:/kutyai-app/gecici": {"bind": "/veri", "mode": "ro"},
    }

    # `birimler` yoksa `volumes` hiç gönderilmez.
    istemci.containers.son_ayarlar = {}
    await surucu.baslat({"slug": "hacimsiz"}, {"image": "nginx:alpine", "komut": []})
    assert "volumes" not in istemci.containers.son_ayarlar

    # `mod` verilmezse okuma-yazma varsayılır.
    await surucu.baslat(
        {"slug": "modsuz"},
        {
            "image": "nginx:alpine",
            "birimler": [{"kaynak": "E:/kutyai-app/x", "hedef": "/x"}],
        },
    )
    assert istemci.containers.son_ayarlar["volumes"] == {
        "E:/kutyai-app/x": {"bind": "/x", "mode": "rw"}
    }


async def test_es_zamanli_baslat_tek_konteyner_baslatir(istemci, personel, manifest):
    """İki eşzamanlı `baslat` isteğinden yalnız biri konteyner açar; diğeri 409."""
    sahte = _YavasBaslatanSurucu()
    surucu_ata(sahte)
    try:
        bdm_id = await _bdm_ekle("vllm", BdmDurumu.hazir)
        yanitlar = await asyncio.gather(
            istemci.post(f"{UC}/{bdm_id}/baslat", headers=personel),
            istemci.post(f"{UC}/{bdm_id}/baslat", headers=personel),
        )
        assert sorted(y.status_code for y in yanitlar) == [200, 409], [
            y.text for y in yanitlar
        ]
        kaybeden = next(y for y in yanitlar if y.status_code == 409)
        assert kaybeden.json()["hata"]["kod"] == "gecersiz_gecis"

        # Sürücüde TEK konteyner var ve kayıt onu gösteriyor.
        assert len(sahte.konteynerler) == 1
        kayit = await _bdm_oku(bdm_id)
        assert kayit.durum == BdmDurumu.calisiyor
        assert kayit.konteyner["konteyner_id"] == next(iter(sahte.konteynerler))
    finally:
        surucu_temizle()


async def test_es_zamanli_yeniden_baslat_tek_konteyner_baslatir(istemci, personel, manifest):
    """İki eşzamanlı `yeniden-baslat` isteğinden yalnız biri konteyner açar."""
    sahte = _YavasBaslatanSurucu()
    surucu_ata(sahte)
    try:
        bdm_id = await _bdm_ekle("vllm", BdmDurumu.durdu)
        yanitlar = await asyncio.gather(
            istemci.post(f"{UC}/{bdm_id}/yeniden-baslat", headers=personel),
            istemci.post(f"{UC}/{bdm_id}/yeniden-baslat", headers=personel),
        )
        assert sorted(y.status_code for y in yanitlar) == [200, 409], [
            y.text for y in yanitlar
        ]
        assert len(sahte.konteynerler) == 1
        kayit = await _bdm_oku(bdm_id)
        assert kayit.konteyner["konteyner_id"] == next(iter(sahte.konteynerler))
    finally:
        surucu_temizle()


async def test_baslatma_hatasinda_durum_hata_konteyner_kaydi_temizlenir(
    istemci, personel, manifest
):
    """Başarısız başlatma `hata`ya çekilir; konteyner kaydı silinir, `yol` korunur."""
    sahte = SahteSurucu(docker_var=True, gpu_var=True)
    sahte.baslatma_hatasi = SurucuYok("Konteyner başlatılamadı.")
    surucu_ata(sahte)
    try:
        bdm_id = await _bdm_ekle(
            "vllm",
            BdmDurumu.durdu,
            konteyner={"konteyner_id": "eski-1", "yol": {"oncelik": 3}},
        )
        yanit = await istemci.post(f"{UC}/{bdm_id}/baslat", headers=personel)
        assert yanit.status_code == 503

        kayit = await _bdm_oku(bdm_id)
        assert kayit.durum == BdmDurumu.hata
        assert kayit.konteyner == {"yol": {"oncelik": 3}}
        assert "bdm.baslatilamadi" in await _eylemler(bdm_id)
    finally:
        surucu_temizle()


async def test_docker_istemcisi_ayarlardaki_soketi_kullanir(monkeypatch):
    """`KUTYAI_DOCKER_SOKETI` doluysa istemci o adrese bağlanır, boşsa varsayılan."""
    docker = pytest.importorskip("docker")
    from arkauc.app.cekirdek.ayarlar import ayarlar
    from arkauc.app.servisler.konteyner_docker import DockerSurucusu

    cagrilar: list[str] = []
    monkeypatch.setattr(docker, "DockerClient", lambda base_url=None: cagrilar.append(base_url) or "istemci")
    monkeypatch.setattr(docker, "from_env", lambda: cagrilar.append("varsayilan") or "istemci")

    monkeypatch.setattr(ayarlar, "docker_soketi", "unix:///var/run/vekil-docker.sock")
    assert DockerSurucusu().istemci() == "istemci"
    assert cagrilar == ["unix:///var/run/vekil-docker.sock"]

    monkeypatch.setattr(ayarlar, "docker_soketi", "")
    assert DockerSurucusu().istemci() == "istemci"
    assert cagrilar[-1] == "varsayilan"


async def test_surucu_hata_mesajlari_ic_ayrinti_sizdirmaz(monkeypatch, sahte_sunucu):
    """Hata mesajları sabit ve Türkçe; istisna/soket ayrıntısı istemciye dönmez."""
    from arkauc.app.servisler.konteyner_docker import DockerSurucusu
    from arkauc.app.servisler.konteyner_yerel import YerelSurucusu

    ic_metin = "npipe:////./pipe/docker_engine erişim engellendi"

    def patlat(*args: object, **kwargs: object) -> object:
        raise RuntimeError(ic_metin)

    konteyner = _SahteKonteyner()
    istemci = _SahteDockerIstemcisi(konteyner)
    surucu = DockerSurucusu()
    monkeypatch.setattr(surucu, "istemci", lambda: istemci)

    # imaj çekilemedi
    monkeypatch.setattr(istemci.images, "get", patlat)
    monkeypatch.setattr(istemci.images, "pull", patlat)
    with pytest.raises(SurucuYok) as hata:
        await surucu.baslat({"slug": "sizinti"}, {"image": "yok-imaj"})
    assert hata.value.mesaj == "Konteyner imajı çekilemedi."
    assert hata.value.ayrinti == {"image": "yok-imaj"}

    # konteyner başlatılamadı
    monkeypatch.setattr(istemci.images, "get", lambda image: object())
    monkeypatch.setattr(istemci.containers, "run", patlat)
    with pytest.raises(SurucuYok) as hata:
        await surucu.baslat({"slug": "sizinti"}, {"image": "nginx:alpine"})
    assert hata.value.mesaj == "Konteyner başlatılamadı."
    assert hata.value.ayrinti == {"image": "nginx:alpine", "ad": "kutyai-sizinti"}

    # konteyner durdurulamadı
    monkeypatch.setattr(konteyner, "stop", patlat)
    with pytest.raises(SurucuYok) as hata:
        await surucu.durdur(konteyner.id)
    assert hata.value.mesaj == "Konteyner durdurulamadı."
    assert ic_metin not in str(hata.value.ayrinti)

    # yerel sürücü: model boşaltma isteği hata döndü
    yerel = YerelSurucusu()
    await yerel.baslat(
        {
            "slug": "bozuk-model",
            "temel_url": f"{sahte_sunucu.temel_url}/v1",
            "upstream_model": "llama3",
        },
        {},
    )
    sahte_sunucu.yanit_kodu = 500
    with pytest.raises(UstSaglayiciHatasi) as hata:
        await yerel.durdur("yerel:bozuk-model")
    assert hata.value.mesaj == "Ollama sunucusu model boşaltma isteğine 500 döndü."
    assert hata.value.ayrinti == {"temel_url": sahte_sunucu.temel_url, "model": "llama3"}

    # yerel sürücü: sunucuya ulaşılamıyor (istisna metni istemciye dönmez)
    monkeypatch.setattr(httpx, "post", patlat)
    with pytest.raises(UstSaglayiciHatasi) as hata:
        await yerel.durdur("yerel:bozuk-model")
    assert hata.value.mesaj == "Ollama sunucusuna ulaşılamadı; model bellekten boşaltılamadı."
    assert ic_metin not in str(hata.value.ayrinti)


# --------------------------------------------------------------------------
# Organizasyon izolasyonu
# --------------------------------------------------------------------------


async def test_yonetim_uclari_organizasyon_ile_sinirli(istemci, yardimci):
    """Başka organizasyonun BDM'i yönetim uçlarında `404` gibi davranır."""
    bdm_id = await _bdm_ekle(durum=BdmDurumu.durdu)
    sahip = await yardimci.yonetici()
    alfa = await yardimci.organizasyon("Alfa Yönetim", sahibi=sahip)
    beta = await yardimci.organizasyon("Beta Yönetim", sahibi=sahip)
    async with oturum_fabrikasi()() as oturum:
        kayit = await oturum.get(Bdm, bdm_id)
        assert kayit is not None
        kayit.org_id = alfa.id
        await oturum.commit()

    beta_basliklar = yardimci.org_basliklari(sahip, beta)
    for yol in ("baslat", "durdur", "yeniden-baslat"):
        yanit = await istemci.post(f"{UC}/{bdm_id}/{yol}", headers=beta_basliklar)
        assert yanit.status_code == 404, yol
        assert yanit.json()["hata"]["kod"] == "bulunamadi", yol

    for yol in ("durum", "saglik", "gunlukler"):
        yanit = await istemci.get(f"{UC}/{bdm_id}/{yol}", headers=beta_basliklar)
        assert yanit.status_code == 404, yol

    yol_guncelle = await istemci.patch(
        f"{UC}/{bdm_id}/yol", json={"oncelik": 3}, headers=beta_basliklar
    )
    assert yol_guncelle.status_code == 404

    alfa_basliklar = yardimci.org_basliklari(sahip, alfa)
    assert (
        await istemci.get(f"{UC}/{bdm_id}/durum", headers=alfa_basliklar)
    ).status_code == 200
