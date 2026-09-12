"""Kota servisi ve kullanim uclari testleri (spec §4.9, §9, §13)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy as sa

from arkauc.app.api import sohbet as sohbet_ucu
from arkauc.app.cekirdek import guvenlik
from arkauc.app.cekirdek.hatalar import KotaAsildi
from arkauc.app.servisler.kota import (
    ay_sonu,
    gun_sonu,
    iso,
    kota_durumu,
    kota_kullan,
    kota_token_ekle,
)
from arkauc.testler.sahte_ust import SahteUst
from bdm_listesi import BdmOlustur, bdm_olustur
from bdm_veritabani.modeller import (
    ApiAnahtari,
    Bdm,
    BdmDurumu,
    Konusma,
    Kota,
    KotaKapsami,
    KullanimDurumu,
    KullanimKaydi,
    Mesaj,
    Saglayici,
)
from bdm_veritabani.oturum import oturum_fabrikasi

SOHBET = "/api/v1/sohbet"
AKIS = "/api/v1/sohbet/akis"


def _coz(deger: str) -> datetime:
    return datetime.fromisoformat(deger.replace("Z", "+00:00"))


async def bdm_ekle(*, durum: BdmDurumu = BdmDurumu.hazir) -> Bdm:
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_olustur(
            oturum,
            BdmOlustur(
                gorunen_ad="Kota Modeli",
                saglayici=Saglayici.ollama,
                temel_url="http://sahte.local/v1",
                upstream_model="sahte-model",
            ),
        )
        bdm.durum = durum
        await oturum.commit()
        await oturum.refresh(bdm)
        return bdm


async def kota_ekle(kapsam: KotaKapsami, kapsam_id: int, **alanlar: int) -> Kota:
    async with oturum_fabrikasi()() as oturum:
        kayit = Kota(kapsam=kapsam, kapsam_id=kapsam_id, **alanlar)
        oturum.add(kayit)
        await oturum.commit()
        await oturum.refresh(kayit)
        return kayit


async def anahtar_ekle(*, gunluk_istek_siniri: int | None = 1) -> ApiAnahtari:
    uretilen = guvenlik.api_anahtari_uret()
    async with oturum_fabrikasi()() as oturum:
        anahtar = ApiAnahtari(
            ad="Sınırlı Anahtar",
            onek=uretilen["onek"],
            anahtar_hash=uretilen["hash"],
            son_dort=uretilen["son_dort"],
            gunluk_istek_siniri=gunluk_istek_siniri,
        )
        oturum.add(anahtar)
        await oturum.commit()
        await oturum.refresh(anahtar)
        return anahtar


async def kullanim_durumlari() -> list[KullanimDurumu]:
    async with oturum_fabrikasi()() as oturum:
        return list((await oturum.execute(sa.select(KullanimKaydi.durum))).scalars())


async def test_kota_tanimli_degilse_istek_gecer(yardimci):
    kullanici = await yardimci.kullanici_ekle()
    anahtar = await anahtar_ekle(gunluk_istek_siniri=None)

    async with oturum_fabrikasi()() as oturum:
        await kota_kullan(
            oturum, kullanici_id=kullanici.id, api_anahtari_id=anahtar.id, token=500
        )
        durum = await kota_durumu(
            oturum, kullanici_id=kullanici.id, api_anahtari_id=anahtar.id
        )
        await oturum.commit()

    assert durum["kullanici"]["gunluk_istek"] is None
    assert durum["kullanici"]["aylik_token"] is None
    assert durum["kullanici"]["kullanilan_gunluk"] == 0
    assert durum["api_anahtari"]["kullanilan_aylik"] == 0


async def test_gunluk_istek_asimi(yardimci):
    kullanici = await yardimci.kullanici_ekle()
    await kota_ekle(KotaKapsami.kullanici, kullanici.id, gunluk_istek=2)

    async with oturum_fabrikasi()() as oturum:
        for _ in range(2):
            await kota_kullan(oturum, kullanici_id=kullanici.id, api_anahtari_id=None)
        with pytest.raises(KotaAsildi) as yakalanan:
            await kota_kullan(oturum, kullanici_id=kullanici.id, api_anahtari_id=None)
        durum = await kota_durumu(
            oturum, kullanici_id=kullanici.id, api_anahtari_id=None
        )
        await oturum.commit()

    assert yakalanan.value.durum_kodu == 429
    assert yakalanan.value.kod == "kota_asildi"
    assert yakalanan.value.ayrinti["kapsam"] == "kullanici"
    assert _coz(yakalanan.value.ayrinti["sifirlanma"]) > datetime.now(timezone.utc)
    assert durum["kullanici"]["kullanilan_gunluk"] == 2
    assert durum["kullanici"]["gunluk_istek"] == 2


async def test_aylik_token_asimi(yardimci):
    kullanici = await yardimci.kullanici_ekle()
    await kota_ekle(KotaKapsami.kullanici, kullanici.id, aylik_token=100)

    async with oturum_fabrikasi()() as oturum:
        await kota_kullan(
            oturum, kullanici_id=kullanici.id, api_anahtari_id=None, token=100
        )
        with pytest.raises(KotaAsildi) as yakalanan:
            await kota_kullan(oturum, kullanici_id=kullanici.id, api_anahtari_id=None)
        durum = await kota_durumu(
            oturum, kullanici_id=kullanici.id, api_anahtari_id=None
        )
        await oturum.commit()

    sifirlanma = _coz(yakalanan.value.ayrinti["sifirlanma"])
    assert sifirlanma == ay_sonu()
    assert sifirlanma > datetime.now(timezone.utc)
    assert durum["kullanici"]["kullanilan_aylik"] == 100


async def test_token_ekleme_sayaci_atomik_artirir(yardimci):
    kullanici = await yardimci.kullanici_ekle()
    await kota_ekle(KotaKapsami.kullanici, kullanici.id, aylik_token=1000)

    async with oturum_fabrikasi()() as oturum:
        await kota_kullan(oturum, kullanici_id=kullanici.id, api_anahtari_id=None)
        await kota_token_ekle(
            oturum, kullanici_id=kullanici.id, api_anahtari_id=None, token=19
        )
        await kota_token_ekle(
            oturum, kullanici_id=kullanici.id, api_anahtari_id=None, token=0
        )
        durum = await kota_durumu(
            oturum, kullanici_id=kullanici.id, api_anahtari_id=None
        )
        await oturum.commit()

    assert durum["kullanici"]["kullanilan_gunluk"] == 1
    assert durum["kullanici"]["kullanilan_aylik"] == 19


async def test_suresi_gecen_sayaclar_sifirlanir(yardimci):
    kullanici = await yardimci.kullanici_ekle()
    gecmis = datetime.now(timezone.utc) - timedelta(days=40)
    await kota_ekle(
        KotaKapsami.kullanici,
        kullanici.id,
        gunluk_istek=1,
        aylik_token=10,
        kullanilan_gunluk=1,
        kullanilan_aylik=10,
        gun_sifirlanma=gecmis,
        ay_sifirlanma=gecmis,
    )

    async with oturum_fabrikasi()() as oturum:
        await kota_kullan(oturum, kullanici_id=kullanici.id, api_anahtari_id=None)
        durum = await kota_durumu(
            oturum, kullanici_id=kullanici.id, api_anahtari_id=None
        )
        await oturum.commit()

    assert durum["kullanici"]["kullanilan_gunluk"] == 1
    assert durum["kullanici"]["kullanilan_aylik"] == 0
    assert _coz(durum["kullanici"]["gun_sifirlanma"]) == gun_sonu()
    assert _coz(durum["kullanici"]["ay_sifirlanma"]) == ay_sonu()


async def test_api_anahtari_gunluk_siniri_kapsami():
    anahtar = await anahtar_ekle(gunluk_istek_siniri=1)

    async with oturum_fabrikasi()() as oturum:
        await kota_kullan(oturum, kullanici_id=None, api_anahtari_id=anahtar.id, token=3)
        with pytest.raises(KotaAsildi) as yakalanan:
            await kota_kullan(oturum, kullanici_id=None, api_anahtari_id=anahtar.id)
        durum = await kota_durumu(oturum, kullanici_id=None, api_anahtari_id=anahtar.id)
        await oturum.commit()

    assert yakalanan.value.ayrinti["kapsam"] == "api_anahtari"
    assert durum["api_anahtari"]["gunluk_istek"] == 1
    assert durum["api_anahtari"]["kullanilan_gunluk"] == 1
    assert durum["api_anahtari"]["kullanilan_aylik"] == 3


async def test_iso_bicimi_utc_isaretlidir():
    assert iso(datetime(2026, 9, 13, tzinfo=timezone.utc)) == "2026-09-13T00:00:00Z"
    assert _coz(iso(datetime(2026, 9, 13, 12, 30, tzinfo=timezone.utc))).hour == 12


async def test_kota_asimi_429_ayrintili(istemci, yardimci, uygulama):
    bdm = await bdm_ekle()
    kullanici = await yardimci.kullanici_ekle()
    await kota_ekle(KotaKapsami.kullanici, kullanici.id, gunluk_istek=1)
    uygulama.dependency_overrides[sohbet_ucu.ust_saglayici] = SahteUst().saglayici
    basliklar = yardimci.basliklar(kullanici)

    ilk = await istemci.post(SOHBET, json={"bdm_id": bdm.id, "mesaj": "ilk"}, headers=basliklar)
    assert ilk.status_code == 200

    ikinci = await istemci.post(
        SOHBET, json={"bdm_id": bdm.id, "mesaj": "ikinci"}, headers=basliklar
    )
    assert ikinci.status_code == 429
    hata = ikinci.json()["hata"]
    assert hata["kod"] == "kota_asildi"
    assert _coz(hata["ayrinti"]["sifirlanma"]) > datetime.now(timezone.utc)
    assert hata["ayrinti"]["kapsam"] == "kullanici"

    akis = await istemci.post(AKIS, json={"bdm_id": bdm.id, "mesaj": "üçüncü"}, headers=basliklar)
    assert akis.status_code == 429
    assert akis.json()["hata"]["kod"] == "kota_asildi"

    durumlar = await kullanim_durumlari()
    assert durumlar.count(KullanimDurumu.kota_asildi) == 2
    assert durumlar.count(KullanimDurumu.basarili) == 1

    async with oturum_fabrikasi()() as oturum:
        konusma_sayisi = (
            await oturum.execute(sa.select(sa.func.count()).select_from(Konusma))
        ).scalar_one()
        mesaj_sayisi = (
            await oturum.execute(sa.select(sa.func.count()).select_from(Mesaj))
        ).scalar_one()
    assert (konusma_sayisi, mesaj_sayisi) == (1, 2)


async def test_kullanim_ozeti_ve_zaman_serisi(istemci, yardimci, uygulama):
    bdm = await bdm_ekle()
    yonetici = await yardimci.yonetici()
    kullanici = await yardimci.kullanici_ekle()
    uygulama.dependency_overrides[sohbet_ucu.ust_saglayici] = SahteUst().saglayici
    await istemci.post(
        SOHBET,
        json={"bdm_id": bdm.id, "mesaj": "selam"},
        headers=yardimci.basliklar(kullanici),
    )
    basliklar = yardimci.basliklar(yonetici)

    ozet = await istemci.get("/api/v1/kullanim/ozet?gun=7", headers=basliklar)
    assert ozet.status_code == 200
    assert set(ozet.json()) == {
        "toplam_istek",
        "toplam_token",
        "basarili",
        "hatali",
        "kota_asimi",
        "ortalama_gecikme_ms",
    }
    assert ozet.json()["toplam_istek"] == 1
    assert ozet.json()["toplam_token"] == 19
    assert ozet.json()["basarili"] == 1
    assert ozet.json()["hatali"] == 0

    seri = await istemci.get("/api/v1/kullanim/zaman-serisi?kirilim=bdm", headers=basliklar)
    assert seri.json()["seri"] == [{"etiket": bdm.gorunen_ad, "istek": 1, "token": 19}]
    kullanici_serisi = await istemci.get(
        "/api/v1/kullanim/zaman-serisi?kirilim=kullanici", headers=basliklar
    )
    assert kullanici_serisi.json()["seri"][0]["etiket"] == kullanici.eposta

    kotu = await istemci.get("/api/v1/kullanim/zaman-serisi?kirilim=yanlis", headers=basliklar)
    assert kotu.status_code == 400
    assert kotu.json()["hata"]["kod"] == "gecersiz_istek"
    assert (await istemci.get("/api/v1/kullanim/ozet", headers=yardimci.basliklar(kullanici))).status_code == 403
    assert (await istemci.get("/api/v1/kullanim/ozet")).status_code == 401


async def test_kisisel_kullanim_yalniz_kendi_kayitlarini_dondurur(istemci, yardimci, uygulama):
    bdm = await bdm_ekle()
    a = await yardimci.kullanici_ekle()
    b = await yardimci.kullanici_ekle()
    uygulama.dependency_overrides[sohbet_ucu.ust_saglayici] = SahteUst().saglayici
    for kullanici in (a, b):
        yanit = await istemci.post(
            SOHBET,
            json={"bdm_id": bdm.id, "mesaj": "selam"},
            headers=yardimci.basliklar(kullanici),
        )
        assert yanit.status_code == 200

    yanit = await istemci.get("/api/v1/kullanim/benim", headers=yardimci.basliklar(a))
    assert yanit.status_code == 200
    govde = yanit.json()
    assert set(govde) == {
        "gun",
        "toplam_istek",
        "toplam_token",
        "girdi_token",
        "cikti_token",
        "ortalama_gecikme_ms",
        "kota",
        "seri",
    }
    assert govde["gun"] == 30
    assert govde["toplam_istek"] == 1
    assert (govde["girdi_token"], govde["cikti_token"]) == (12, 7)
    assert govde["toplam_token"] == 19
    assert govde["ortalama_gecikme_ms"] > 0
    assert govde["kota"] is None
    assert govde["seri"] == [
        {"tarih": datetime.now(timezone.utc).date().isoformat(), "token": 19}
    ]

    b_govdesi = (
        await istemci.get("/api/v1/kullanim/benim", headers=yardimci.basliklar(b))
    ).json()
    assert b_govdesi["toplam_istek"] == 1
    assert b_govdesi["toplam_token"] == 19
    assert (await istemci.get("/api/v1/kullanim/benim")).status_code == 401


async def test_kisisel_kullanim_anahtar_kapsami_ve_kota(istemci, yardimci, uygulama):
    bdm = await bdm_ekle()
    uretilen = guvenlik.api_anahtari_uret()
    async with oturum_fabrikasi()() as oturum:
        anahtar = ApiAnahtari(
            ad="Kişisel Anahtar",
            onek=uretilen["onek"],
            anahtar_hash=uretilen["hash"],
            son_dort=uretilen["son_dort"],
        )
        oturum.add(anahtar)
        await oturum.commit()
        await oturum.refresh(anahtar)
    await kota_ekle(
        KotaKapsami.api_anahtari, anahtar.id, gunluk_istek=5, aylik_token=1000
    )
    anahtar_basliklari = yardimci.anahtar_basliklari(uretilen["tam"])
    uygulama.dependency_overrides[sohbet_ucu.ust_saglayici] = SahteUst().saglayici

    anahtar_yaniti = await istemci.post(
        SOHBET, json={"bdm_id": bdm.id, "mesaj": "selam"}, headers=anahtar_basliklari
    )
    assert anahtar_yaniti.status_code == 200
    yabanci = await yardimci.kullanici_ekle()
    await istemci.post(
        SOHBET,
        json={"bdm_id": bdm.id, "mesaj": "baskasi"},
        headers=yardimci.basliklar(yabanci),
    )

    govde = (
        await istemci.get("/api/v1/kullanim/benim", headers=anahtar_basliklari)
    ).json()
    assert govde["toplam_istek"] == 1
    assert govde["toplam_token"] == 19
    kota = govde["kota"]
    assert kota["gunluk_istek"] == 5
    assert kota["kullanilan_gunluk"] == 1
    assert kota["aylik_token"] == 1000
    assert kota["kullanilan_aylik"] == 19
    assert _coz(kota["gun_sifirlanma"]) > datetime.now(timezone.utc)
    assert _coz(kota["ay_sifirlanma"]) > datetime.now(timezone.utc)


async def test_es_zamanli_istekler_kota_sayacini_asamaz(istemci, yardimci, uygulama):
    bdm = await bdm_ekle()
    kullanici = await yardimci.kullanici_ekle()
    await kota_ekle(KotaKapsami.kullanici, kullanici.id, gunluk_istek=1)
    uygulama.dependency_overrides[sohbet_ucu.ust_saglayici] = SahteUst().saglayici
    basliklar = yardimci.basliklar(kullanici)

    yanitlar = await asyncio.gather(
        *(
            istemci.post(
                SOHBET,
                json={"bdm_id": bdm.id, "mesaj": f"eşzamanlı {sira}"},
                headers=basliklar,
            )
            for sira in range(2)
        )
    )

    assert sorted(yanit.status_code for yanit in yanitlar) == [200, 429]
    asan = next(yanit for yanit in yanitlar if yanit.status_code == 429)
    assert asan.json()["hata"]["kod"] == "kota_asildi"

    async with oturum_fabrikasi()() as oturum:
        kayit = (
            await oturum.execute(
                sa.select(Kota).where(
                    Kota.kapsam == KotaKapsami.kullanici,
                    Kota.kapsam_id == kullanici.id,
                )
            )
        ).scalar_one()
    assert kayit.kullanilan_gunluk == 1

    durumlar = await kullanim_durumlari()
    assert durumlar.count(KullanimDurumu.basarili) == 1
    assert durumlar.count(KullanimDurumu.kota_asildi) == 1


async def test_es_zamanli_anahtar_istekleri_gunluk_siniri_asamaz(istemci, yardimci, uygulama):
    bdm = await bdm_ekle()
    uretilen = guvenlik.api_anahtari_uret()
    async with oturum_fabrikasi()() as oturum:
        anahtar = ApiAnahtari(
            ad="Sınırlı Anahtar",
            onek=uretilen["onek"],
            anahtar_hash=uretilen["hash"],
            son_dort=uretilen["son_dort"],
            gunluk_istek_siniri=1,
        )
        oturum.add(anahtar)
        await oturum.commit()
        await oturum.refresh(anahtar)
    uygulama.dependency_overrides[sohbet_ucu.ust_saglayici] = SahteUst().saglayici
    basliklar = yardimci.anahtar_basliklari(uretilen["tam"])

    yanitlar = await asyncio.gather(
        *(
            istemci.post(
                SOHBET,
                json={"bdm_id": bdm.id, "mesaj": f"paralel {sira}"},
                headers=basliklar,
            )
            for sira in range(6)
        )
    )

    kodlar = [yanit.status_code for yanit in yanitlar]
    assert kodlar.count(200) == 1
    assert kodlar.count(429) == 5
    for yanit in yanitlar:
        if yanit.status_code == 429:
            assert yanit.json()["hata"]["kod"] == "kota_asildi"

    async with oturum_fabrikasi()() as oturum:
        kota_id = (
            await oturum.execute(
                sa.select(Kota.id).where(
                    Kota.kapsam == KotaKapsami.api_anahtari,
                    Kota.kapsam_id == anahtar.id,
                )
            )
        ).scalar_one()
        kayit = await oturum.get(Kota, kota_id)
    assert kayit.kullanilan_gunluk == 1
    durumlar = await kullanim_durumlari()
    assert durumlar.count(KullanimDurumu.basarili) == 1
    assert durumlar.count(KullanimDurumu.kota_asildi) == 5
