"""05 — GPU koruması ve manifest içeriği (süreç içi ASGI + sürücü ikamesi).

Bu betik ürün kodunu değiştirmez; yalnızca `surucu_ata` ile sürücü ikame eder
(bu, ürün kodunun kendi test kancasıdır) ve `bdm_yönetim_ucu` yollarını
gerçek ASGI uygulaması üzerinden çağırır.

Ortam: ayrı bir SQLite dosyası (gecici/gpu.db); canlı sunucunun veritabanına
dokunmaz.
"""

from __future__ import annotations

import asyncio
import os
import pathlib
import sys

KOK = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(KOK))

GECICI = KOK / "kaynak" / "testler" / "gecici"
os.environ["KUTYAI_ORTAM"] = "test"
os.environ["KUTYAI_VERITABANI_URL"] = f"sqlite+aiosqlite:///{(GECICI / 'gpu.db').as_posix()}"
os.environ["KUTYAI_GIZLI_ANAHTAR"] = "gozlem-gizli-anahtar"
os.environ["KUTYAI_SIFRELEME_ANAHTARI"] = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="

import json  # noqa: E402

import httpx  # noqa: E402

from arkauc.app.cekirdek import guvenlik  # noqa: E402
from arkauc.app.cekirdek.hatalar import SurucuYok  # noqa: E402
from arkauc.app.servisler.konteyner import SahteSurucu, surucu_ata, surucu_temizle  # noqa: E402
from bdm_hazırlama_ucu.manifest import manifest_uret  # noqa: E402
from bdm_veritabani.modeller import Bdm, BdmDurumu, Kullanici, Rol, Saglayici  # noqa: E402
from bdm_veritabani.oturum import motoru_sifirla, oturum_fabrikasi, tablolari_olustur  # noqa: E402
from bdm_veritabani.tohum import tohumla  # noqa: E402

UC = "/api/v1/bdm/yonetim"


class CokenSurucu(SahteSurucu):
    """Docker kapalıyken gerçek sürücünün davranışı: `durum()` SurucuYok fırlatır."""

    ad = "coken"

    async def durum(self):  # type: ignore[override]
        raise SurucuYok("Docker çalışma zamanına ulaşılamadı. Docker kurulu ve çalışır durumda olmalıdır.")


async def _hazirla(saglayici: str) -> tuple[int, dict[str, str]]:
    await motoru_sifirla()
    from bdm_veritabani.oturum import tablolari_sil  # noqa: PLC0415

    await tablolari_sil()
    await tablolari_olustur()
    await tohumla()
    async with oturum_fabrikasi()() as oturum:
        kullanici = Kullanici(
            eposta="goz@kutyai.example.com",
            ad_soyad="Gözlem",
            sifre_hash=guvenlik.sifre_hashle("Parola123!"),
            rol=Rol.yonetici,
            durum="aktif",
            eposta_dogrulandi=True,
        )
        oturum.add(kullanici)
        bdm = Bdm(
            slug=f"gpu-{saglayici}",
            gorunen_ad=f"GPU {saglayici}",
            saglayici=Saglayici(saglayici),
            temel_url="http://127.0.0.1:8000/v1",
            upstream_model="mistralai/Mistral-7B-Instruct-v0.2",
            durum=BdmDurumu.hazir,
            yerel_mi=True,
            yetenekler={"akis": True, "gorsel": False, "arac": False},
        )
        oturum.add(bdm)
        await oturum.commit()
        await oturum.refresh(bdm)
        await oturum.refresh(kullanici)
        basliklar = {"Authorization": f"Bearer {guvenlik.erisim_jetonu_uret(kullanici.id, 'yonetici')[0]}"}
        return bdm.id, basliklar


async def main() -> None:
    print("== 1) manifest_uret çıktısı (gerçek hazırlama modülü) ==")
    for saglayici in ("ollama", "vllm", "tgi", "ozel"):
        bdm = Bdm(
            slug=f"m-{saglayici}",
            gorunen_ad="M",
            saglayici=Saglayici(saglayici),
            temel_url="http://127.0.0.1:1/v1",
            upstream_model="mistralai/Mistral-7B-Instruct-v0.2",
            durum=BdmDurumu.hazir,
            yerel_mi=saglayici in ("ollama", "vllm", "tgi"),
            yetenekler={},
            konteyner=None,
        )
        try:
            uretilen = manifest_uret(bdm)
            print(f"  {saglayici:<8} anahtarlar={sorted(uretilen)} saglik_url var mı? {'saglik_url' in uretilen}")
            print(f"           {json.dumps(uretilen, ensure_ascii=False)}")
        except Exception as hata:
            print(f"  {saglayici:<8} {type(hata).__name__}: {hata}")

    print("\n== 2) GPU'suz sürücü (gpu_var=False) + vllm: sessiz CPU düşüşü var mı? ==")
    for saglayici in ("vllm", "tgi"):
        bdm_id, basliklar = await _hazirla(saglayici)
        sahte = SahteSurucu(docker_var=True, gpu_var=False)
        surucu_ata(sahte)
        from arkauc.app.main import uygulama_olustur  # noqa: PLC0415

        uygulama = uygulama_olustur()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=uygulama), base_url="http://test") as c:
            yanit = await c.post(f"{UC}/{bdm_id}/baslat", headers=basliklar)
        print(f"  {saglayici}: HTTP {yanit.status_code} {yanit.text[:260]}")
        print(f"    sürücüye başlat çağrısı yapıldı mı? {('baslat' in [a for a, _ in sahte.cagrilar])} (False olmalı: sessiz düşüş yok)")
        surucu_temizle()
        await motoru_sifirla()

    print("\n== 3) GPU'lu sürücü (gpu_var=True) + vllm: 200 ve konteyner_id ==")
    bdm_id, basliklar = await _hazirla("vllm")
    sahte = SahteSurucu(docker_var=True, gpu_var=True)
    surucu_ata(sahte)
    from arkauc.app.main import uygulama_olustur  # noqa: PLC0415

    uygulama = uygulama_olustur()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=uygulama), base_url="http://test") as c:
        yanit = await c.post(f"{UC}/{bdm_id}/baslat", headers=basliklar)
    print(f"  HTTP {yanit.status_code} {yanit.text[:200]}")
    print(f"  sürücüye iletilen manifest = {json.dumps(sahte.cagrilar[0][1]['manifest'], ensure_ascii=False) if sahte.cagrilar else 'yok'}")
    surucu_temizle()
    await motoru_sifirla()

    print("\n== 4) Docker kapalı (durum() SurucuYok) + vllm: hangi 503 mesajı? ==")
    bdm_id, basliklar = await _hazirla("vllm")
    surucu_ata(CokenSurucu(docker_var=False, gpu_var=False))
    uygulama = uygulama_olustur()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=uygulama), base_url="http://test") as c:
        yanit = await c.post(f"{UC}/{bdm_id}/baslat", headers=basliklar)
        print(f"  HTTP {yanit.status_code} {yanit.text[:260]}")
        yanit = await c.get(f"{UC}/surucu/durum", headers=basliklar)
        print(f"  GET surucu/durum → HTTP {yanit.status_code} {yanit.text[:260]}")
    surucu_temizle()
    await motoru_sifirla()


if __name__ == "__main__":
    asyncio.run(main())
