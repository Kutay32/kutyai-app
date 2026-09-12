"""Altyapi testleri: oran sinirlayici, maskeleme ayari, saklama gorevi.

Spec denetiminin buldugu uc bosluk kapatildi; bu testler onlari kilitler:
1) Oran siniri hic uygulanmiyordu (spec §11).
2) `maskeleme_aktif` ayari etkisizdi (motor ortam degiskenini okuyordu).
3) Gunluk saklama gorevi yoktu (spec §11).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import sqlalchemy as sa

from arkauc.app.cekirdek import oran_siniri
from arkauc.app.cekirdek.ayarlar import ayarlar
from arkauc.app.cekirdek.ayarlar_db import ayar_yaz
from bdm_konusma_gecmisi import (
    eski_konusmalari_sil,
    konusma_olustur,
    maskele_metin,
    maskeleme_etkin,
    mesaj_ekle,
)
from bdm_listesi import BdmOlustur, bdm_olustur
from bdm_veritabani.modeller import Konusma, MesajRolu
from bdm_veritabani.oturum import oturum_fabrikasi


def test_kayan_pencere_limit_asimini_engeller():
    pencere = oran_siniri.KayanPencere()
    izinler = [pencere.izin("anahtar", limit=3, pencere_sn=60)[0] for _ in range(5)]
    assert izinler == [True, True, True, False, False]

    izin, yeniden_dene = pencere.izin("anahtar", limit=3, pencere_sn=60)
    assert izin is False
    assert yeniden_dene >= 1


def test_kayan_pencere_anahtarlari_bagimsiz():
    pencere = oran_siniri.KayanPencere()
    for _ in range(3):
        pencere.izin("a", limit=3, pencere_sn=60)
    assert pencere.izin("a", limit=3, pencere_sn=60)[0] is False
    assert pencere.izin("b", limit=3, pencere_sn=60)[0] is True


def test_kural_sec_en_spesifik_oneki_secer():
    assert oran_siniri.kural_sec("/api/v1/kimlik/giris").onek == "/api/v1/kimlik/"
    assert oran_siniri.kural_sec("/api/v1/sohbet/akis").onek == "/api/v1/sohbet"
    assert oran_siniri.kural_sec("/api/v1/bdm").onek == "/api/v1/"
    assert oran_siniri.kural_sec("/saglik") is None


async def test_kimlik_ucu_limit_asiminda_429_dondurur(istemci, monkeypatch):
    monkeypatch.setattr(ayarlar, "oran_siniri_kimlik_dk", 3)
    oran_siniri.sinirlayiciyi_sifirla()

    kodlar = []
    for _ in range(4):
        yanit = await istemci.post(
            "/api/v1/kimlik/sifre-sifirlama-iste", json={"eposta": "yok@kutyai.local"}
        )
        kodlar.append(yanit.status_code)

    assert kodlar[:3] == [200, 200, 200]
    assert kodlar[3] == 429
    son = yanit.json()["hata"]
    assert son["kod"] == "oran_siniri"
    assert son["ayrinti"]["yeniden_dene_sn"] >= 1


async def test_sohbet_ucu_limit_asiminda_429_dondurur(istemci, yardimci, monkeypatch):
    kullanici = await yardimci.kullanici_ekle()
    monkeypatch.setattr(ayarlar, "oran_siniri_istek_dk", 2)
    oran_siniri.sinirlayiciyi_sifirla()

    basliklar = yardimci.basliklar(kullanici)
    kodlar = []
    for _ in range(3):
        yanit = await istemci.get("/api/v1/sohbet/konusmalar", headers=basliklar)
        kodlar.append(yanit.status_code)

    assert kodlar[:2] == [200, 200]
    assert kodlar[2] == 429
    assert yanit.json()["hata"]["kod"] == "oran_siniri"


async def test_maskeleme_ayari_veritabanindan_okunur(istemci, yardimci):
    async with oturum_fabrikasi()() as oturum:
        assert await maskeleme_etkin(oturum) is True
        await ayar_yaz(oturum, "maskeleme_aktif", False)
        await oturum.commit()

    async with oturum_fabrikasi()() as oturum:
        assert await maskeleme_etkin(oturum) is False
        assert await maskele_metin(oturum, "ayse@acme.com") == "ayse@acme.com"

        await ayar_yaz(oturum, "maskeleme_aktif", True)
        await oturum.commit()

    async with oturum_fabrikasi()() as oturum:
        assert await maskele_metin(oturum, "ayse@acme.com") == "[MASKELENDI:eposta]"


async def test_panelden_kapatilan_maskeleme_mesaj_kaydini_etkiler():
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_olustur(
            oturum,
            BdmOlustur(gorunen_ad="Maske Modeli", saglayici="ollama", upstream_model="llama3"),
        )
        konusma = await konusma_olustur(oturum, bdm_id=bdm.id)
        await ayar_yaz(oturum, "maskeleme_aktif", False)
        await mesaj_ekle(
            oturum, konusma=konusma, rol=MesajRolu.kullanici, icerik="bana ayse@acme.com yaz"
        )
        await oturum.commit()

        kayitli = (
            await oturum.execute(
                sa.select(Konusma.baslik).where(Konusma.id == konusma.id)
            )
        ).scalar_one()

    assert "ayse@acme.com" in kayitli


async def test_eski_konusmalari_sil_saklama_suresini_uygular():
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_olustur(
            oturum,
            BdmOlustur(gorunen_ad="Saklama Modeli", saglayici="ollama", upstream_model="llama3"),
        )
        eski = await konusma_olustur(oturum, bdm_id=bdm.id)
        yeni = await konusma_olustur(oturum, bdm_id=bdm.id)
        await mesaj_ekle(oturum, konusma=eski, rol=MesajRolu.kullanici, icerik="eski kayıt")
        await mesaj_ekle(oturum, konusma=yeni, rol=MesajRolu.kullanici, icerik="yeni kayıt")
        await oturum.execute(
            sa.update(Konusma)
            .where(Konusma.id == eski.id)
            .values(olusturulma=datetime.now(timezone.utc) - timedelta(days=100))
        )
        await oturum.commit()

        silinen = await eski_konusmalari_sil(oturum, gun=30)
        await oturum.commit()

        kalan = (
            await oturum.execute(sa.select(sa.func.count()).select_from(Konusma))
        ).scalar_one()

    assert silinen == 1
    assert int(kalan) == 1
