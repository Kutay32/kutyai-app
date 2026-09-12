"""Yönetim ucu ve konteyner sürücüleri testleri (spec §7.6, §10)."""

from __future__ import annotations

import asyncio
import importlib
import os
import socket

import pytest
import sqlalchemy as sa

from arkauc.app.servisler.konteyner import SahteSurucu, surucu_ata, surucu_temizle
from bdm_veritabani.modeller import Bdm, BdmDurumu, IslemKaydi, Saglayici
from bdm_veritabani.oturum import oturum_fabrikasi

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


async def _bdm_ekle(saglayici: str = "vllm", durum: BdmDurumu = BdmDurumu.taslak) -> int:
    async with oturum_fabrikasi()() as oturum:
        bdm = Bdm(
            slug=f"{saglayici}-test",
            gorunen_ad=f"{saglayici} test modeli",
            saglayici=Saglayici(saglayici),
            temel_url="http://localhost:8000/v1",
            upstream_model="mistralai/Mistral-7B-Instruct-v0.2",
            durum=durum,
            yerel_mi=True,
            yetenekler={"akis": True, "gorsel": False, "arac": False},
        )
        oturum.add(bdm)
        await oturum.commit()
        await oturum.refresh(bdm)
        return bdm.id


async def _durum_yaz(bdm_id: int, durum: BdmDurumu) -> None:
    async with oturum_fabrikasi()() as oturum:
        bdm = await oturum.get(Bdm, bdm_id)
        assert bdm is not None
        yasam_dongusu.gecis_uygula(bdm, durum)
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
    assert (await _bdm_oku(bdm_id)).durum == BdmDurumu.hazir


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
