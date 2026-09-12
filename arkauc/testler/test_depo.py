"""Dalga 0 veri katmani testleri: katalog, maskeleme, yazici, sorgu, disa aktarim."""

from __future__ import annotations

import json

import pytest

from bdm_konusma_gecmisi import (
    disa_aktar,
    konusma_detayi,
    konusma_olustur,
    konusmalari_listele,
    kullanim_ozeti,
    kullanim_yaz,
    kurallari_yukle,
    maskele,
    mesaj_ekle,
    ust_saglayici_mesajlari,
)
from bdm_listesi import (
    BdmOlustur,
    bdm_listele,
    bdm_olustur,
    bdm_sozlugu,
    kullanilabilir_modeller,
    slug_uret,
    tohum_katalogunu_yukle,
)
from bdm_listesi.saglayicilar import saglayici_bilgisi
from bdm_veritabani.modeller import Bdm, BdmDurumu, KullanimDurumu, MesajRolu, Saglayici
from bdm_veritabani.oturum import oturum_fabrikasi


def ornek_bdm(**degisiklik) -> BdmOlustur:
    veri = {
        "gorunen_ad": "Deneme Modeli",
        "saglayici": "ollama",
        "upstream_model": "llama3",
    }
    veri.update(degisiklik)
    return BdmOlustur(**veri)  # type: ignore[arg-type]


def test_slug_uret_turkce_karakterleri_sadeler():
    assert slug_uret("Yerel Llama 3 (Ollama)") == "yerel-llama-3-ollama"
    assert slug_uret("Şişli Çözüm Özel") == "sisli-cozum-ozel"
    assert slug_uret("!!!") == "bdm"


def test_saglayici_matrisi_gpu_bilgisi_tasir():
    assert saglayici_bilgisi("vllm").gpu_gerekir is True
    assert saglayici_bilgisi("ollama").gpu_gerekir is False
    assert saglayici_bilgisi("ollama").yerel is True


async def test_bdm_olustur_varsayilanlari_uygular():
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_olustur(oturum, ornek_bdm())
        await oturum.commit()
        assert bdm.slug == "deneme-modeli"
        assert bdm.temel_url == "http://localhost:11434/v1"
        assert bdm.durum == BdmDurumu.taslak
        assert bdm.yerel_mi is True


async def test_bdm_olustur_ayni_addan_tekil_slug_uretir():
    async with oturum_fabrikasi()() as oturum:
        ilk = await bdm_olustur(oturum, ornek_bdm())
        ikinci = await bdm_olustur(oturum, ornek_bdm())
        await oturum.commit()
        assert ilk.slug == "deneme-modeli"
        assert ikinci.slug == "deneme-modeli-2"


async def test_bdm_sozlugu_upstream_anahtarini_maskeler():
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_olustur(
            oturum,
            ornek_bdm(
                gorunen_ad="Uzak Model",
                saglayici="openai",
                temel_url="https://api.openai.com/v1",
                api_anahtari="sk-cokgizli1234567890",
            ),
        )
        await oturum.commit()
        sozluk = bdm_sozlugu(bdm)
        assert sozluk["api_anahtari_maskeli"] == "sk-c***7890"
        assert "cokgizli" not in json.dumps(sozluk)


async def test_kullanilabilir_modeller_yalnizca_hazir_olanlari_dondurur():
    async with oturum_fabrikasi()() as oturum:
        taslak = await bdm_olustur(oturum, ornek_bdm(gorunen_ad="Taslak Model"))
        hazir = await bdm_olustur(oturum, ornek_bdm(gorunen_ad="Hazır Model"))
        hazir.durum = BdmDurumu.hazir
        await oturum.commit()

        modeller = await kullanilabilir_modeller(oturum)
        sluglar = {m["slug"] for m in modeller}
        assert sluglar == {hazir.slug}
        assert taslak.slug not in sluglar

        izinli = await kullanilabilir_modeller(oturum, izinli_modeller=["baska-model"])
        assert izinli == []


async def test_tohum_katalogu_sekiz_kayit_ekler():
    async with oturum_fabrikasi()() as oturum:
        eklenen = await tohum_katalogunu_yukle(oturum)
        await oturum.commit()
        assert eklenen == 8
        kayitlar = await bdm_listele(oturum)
        assert len(kayitlar) == 8
        saglayicilar = {k.saglayici for k in kayitlar}
        assert Saglayici.ollama in saglayicilar and Saglayici.vllm in saglayicilar


async def test_maskeleme_hassas_desenleri_temizler():
    async with oturum_fabrikasi()() as oturum:
        kurallar = await kurallari_yukle(oturum)

    metin = (
        "TCKN 12345678901, e-posta ayse.yilmaz@acme.com, "
        "telefon 0532 123 45 67, kart 4111 1111 1111 1111"
    )
    temiz = maskele(metin, kurallar)
    assert "12345678901" not in temiz
    assert "ayse.yilmaz@acme.com" not in temiz
    assert "4111 1111 1111 1111" not in temiz
    assert "[MASKELENDI:tckn]" in temiz
    assert "[MASKELENDI:eposta]" in temiz
    assert "[MASKELENDI:kredi_karti]" in temiz


async def test_mesaj_yazimi_maskeler_baslik_uretir_ve_token_biriktirir():
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_olustur(oturum, ornek_bdm())
        konusma = await konusma_olustur(oturum, bdm_id=bdm.id)
        await mesaj_ekle(
            oturum,
            konusma=konusma,
            rol=MesajRolu.kullanici,
            icerik="Merhaba, beni ayse@acme.com adresinden arayın.",
            token_sayisi=11,
        )
        await mesaj_ekle(
            oturum,
            konusma=konusma,
            rol=MesajRolu.asistan,
            icerik="Elbette yardımcı olabilirim.",
            token_sayisi=7,
        )
        await oturum.commit()

        assert konusma.baslik == "Merhaba, beni [MASKELENDI:eposta] adresinden arayın."
        assert konusma.token_girdi == 11
        assert konusma.token_cikti == 7
        icerikler = [m.icerik for m in konusma.mesajlar]
        assert all("ayse@acme.com" not in i for i in icerikler)


async def test_konusma_basligi_ilk_mesajdan_uretilir():
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_olustur(oturum, ornek_bdm())
        konusma = await konusma_olustur(oturum, bdm_id=bdm.id)
        await mesaj_ekle(
            oturum,
            konusma=konusma,
            rol=MesajRolu.kullanici,
            icerik="Kısa soru",
        )
        await oturum.commit()
        assert konusma.baslik == "Kısa soru"


async def test_ust_saglayici_mesajlari_sirayi_korur():
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_olustur(oturum, ornek_bdm())
        konusma = await konusma_olustur(oturum, bdm_id=bdm.id)
        await mesaj_ekle(oturum, konusma=konusma, rol=MesajRolu.kullanici, icerik="bir")
        await mesaj_ekle(oturum, konusma=konusma, rol=MesajRolu.asistan, icerik="iki")
        await mesaj_ekle(oturum, konusma=konusma, rol=MesajRolu.kullanici, icerik="üç")
        await oturum.commit()

        mesajlar = await ust_saglayici_mesajlari(oturum, konusma)
        assert [m["content"] for m in mesajlar] == ["bir", "iki", "üç"]
        assert [m["role"] for m in mesajlar] == ["user", "assistant", "user"]


async def test_konusma_listesi_filtre_ve_sayfalama():
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_olustur(oturum, ornek_bdm())
        for sira in range(3):
            konusma = await konusma_olustur(oturum, bdm_id=bdm.id)
            await mesaj_ekle(
                oturum,
                konusma=konusma,
                rol=MesajRolu.kullanici,
                icerik=f"fatura sorusu {sira}",
            )
        diger = await konusma_olustur(oturum, bdm_id=bdm.id)
        await mesaj_ekle(oturum, konusma=diger, rol=MesajRolu.kullanici, icerik="kargo")
        await oturum.commit()

        sayfa = await konusmalari_listele(oturum, arama="fatura", sayfa=1, boyut=2)
        assert sayfa["toplam"] == 3
        assert len(sayfa["kayitlar"]) == 2

        ikinci = await konusmalari_listele(oturum, arama="fatura", sayfa=2, boyut=2)
        assert len(ikinci["kayitlar"]) == 1


async def test_kullanim_ozeti_durumlara_gore_sayar():
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_olustur(oturum, ornek_bdm())
        await kullanim_yaz(oturum, bdm_id=bdm.id, girdi_token=10, cikti_token=5, gecikme_ms=100)
        await kullanim_yaz(oturum, bdm_id=bdm.id, girdi_token=2, cikti_token=1, gecikme_ms=300)
        await kullanim_yaz(
            oturum,
            bdm_id=bdm.id,
            durum=KullanimDurumu.kota_asildi,
        )
        await oturum.commit()

        ozet = await kullanim_ozeti(oturum, gun=7)
        assert ozet["toplam_istek"] == 3
        assert ozet["basarili"] == 2
        assert ozet["kota_asimi"] == 1
        assert ozet["toplam_token"] == 18
        assert ozet["ortalama_gecikme_ms"] == 200


@pytest.mark.parametrize("bicim", ["json", "md", "csv"])
async def test_disa_aktarim_bicimleri(bicim):
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_olustur(oturum, ornek_bdm())
        konusma = await konusma_olustur(oturum, bdm_id=bdm.id)
        await mesaj_ekle(oturum, konusma=konusma, rol=MesajRolu.kullanici, icerik="merhaba")
        await oturum.commit()
        detay = await konusma_detayi(oturum, konusma)

    icerik, medya, dosya = disa_aktar(konusma, detay, bicim)
    assert "merhaba" in icerik
    assert dosya == f"konusma-{konusma.id}.{bicim}"
    assert medya.startswith("text/") or medya.startswith("application/json")
