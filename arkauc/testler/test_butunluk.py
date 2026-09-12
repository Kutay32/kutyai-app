"""Bütünlük testleri: yabancı anahtar zorlaması ve BDM silme koruması.

Bu testler gözlemci ajanların bulduğu iki BLOCKER'ı kilitler:
1) Upstream'e giden rol adları OpenAI sözleşmesine uygun olmalı.
2) Konuşması olan bir BDM silinemez; yetim kayıt oluşmaz.
"""

from __future__ import annotations

import pytest
import sqlalchemy as sa

from arkauc.app.cekirdek.hatalar import GecersizGecis
from bdm_konusma_gecmisi import (
    konusma_detayi,
    konusma_olustur,
    konusma_sahibi_mi,
    mesaj_ekle,
    ust_saglayici_mesajlari,
)
from bdm_listesi import BdmOlustur, bdm_olustur, bdm_sil
from bdm_veritabani.modeller import KullanimKaydi, Konusma, Mesaj, MesajRolu
from bdm_veritabani.oturum import oturum_fabrikasi


def ornek_bdm(**degisiklik) -> BdmOlustur:
    veri = {"gorunen_ad": "Bütünlük Modeli", "saglayici": "ollama", "upstream_model": "llama3"}
    veri.update(degisiklik)
    return BdmOlustur(**veri)  # type: ignore[arg-type]


async def test_sqlite_yabanci_anahtar_zorlamasi_acik():
    async with oturum_fabrikasi()() as oturum:
        deger = (await oturum.execute(sa.text("PRAGMA foreign_keys"))).scalar_one()
    assert int(deger) == 1


async def test_konusma_silinince_mesajlar_kaskad_silinir():
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_olustur(oturum, ornek_bdm())
        konusma = await konusma_olustur(oturum, bdm_id=bdm.id)
        await mesaj_ekle(oturum, konusma=konusma, rol=MesajRolu.kullanici, icerik="merhaba")
        await oturum.commit()
        konusma_id = konusma.id

        await oturum.delete(await oturum.get(Konusma, konusma_id))
        await oturum.commit()

        kalan = (
            await oturum.execute(
                sa.select(sa.func.count()).select_from(Mesaj).where(Mesaj.konusma_id == konusma_id)
            )
        ).scalar_one()
    assert int(kalan) == 0


async def test_konusmasi_olan_bdm_silinemez():
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_olustur(oturum, ornek_bdm())
        konusma = await konusma_olustur(oturum, bdm_id=bdm.id)
        await mesaj_ekle(oturum, konusma=konusma, rol=MesajRolu.kullanici, icerik="bir soru")
        await oturum.commit()

        with pytest.raises(GecersizGecis) as hata:
            await bdm_sil(oturum, bdm)
        assert hata.value.durum_kodu == 409
        assert hata.value.ayrinti["konusma_sayisi"] == 1

        kalan = (
            await oturum.execute(
                sa.select(sa.func.count()).select_from(Konusma).where(Konusma.bdm_id == bdm.id)
            )
        ).scalar_one()
    assert int(kalan) == 1


async def test_kullanim_kaydi_olan_bdm_silinemez():
    from bdm_konusma_gecmisi import kullanim_yaz

    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_olustur(oturum, ornek_bdm(gorunen_ad="Kullanım Modeli"))
        await kullanim_yaz(oturum, bdm_id=bdm.id, girdi_token=5, cikti_token=5)
        await oturum.commit()

        with pytest.raises(GecersizGecis):
            await bdm_sil(oturum, bdm)

        kalan = (
            await oturum.execute(
                sa.select(sa.func.count())
                .select_from(KullanimKaydi)
                .where(KullanimKaydi.bdm_id == bdm.id)
            )
        ).scalar_one()
    assert int(kalan) == 1


async def test_bagli_konusma_yoksa_bdm_silinebilir():
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_olustur(oturum, ornek_bdm(gorunen_ad="Boş Model"))
        await oturum.commit()
        bdm_id = bdm.id

        await bdm_sil(oturum, bdm)
        await oturum.commit()

        kalan = (
            await oturum.execute(
                sa.select(sa.func.count()).select_from(Konusma).where(Konusma.bdm_id == bdm_id)
            )
        ).scalar_one()
    assert int(kalan) == 0


@pytest.mark.parametrize(
    ("rol", "beklenen"),
    [
        (MesajRolu.kullanici, "user"),
        (MesajRolu.asistan, "assistant"),
    ],
)
async def test_upstream_rol_adlari_openai_sozlesmesinde(rol, beklenen):
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_olustur(oturum, ornek_bdm(gorunen_ad="Rol Modeli"))
        konusma = await konusma_olustur(oturum, bdm_id=bdm.id)
        await mesaj_ekle(oturum, konusma=konusma, rol=rol, icerik="içerik")
        await oturum.commit()

        mesajlar = await ust_saglayici_mesajlari(oturum, konusma)

    assert mesajlar == [{"role": beklenen, "content": "içerik"}]


async def test_yetenek_disi_roller_upstream_listesine_girmez():
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_olustur(oturum, ornek_bdm(gorunen_ad="Filtre Modeli"))
        konusma = await konusma_olustur(oturum, bdm_id=bdm.id)
        await mesaj_ekle(oturum, konusma=konusma, rol=MesajRolu.sistem, icerik="sistem")
        await mesaj_ekle(oturum, konusma=konusma, rol=MesajRolu.kullanici, icerik="soru")
        await oturum.commit()

        mesajlar = await ust_saglayici_mesajlari(oturum, konusma)

    assert mesajlar == [{"role": "user", "content": "soru"}]


async def test_detay_ve_sahiplik_yardimcilari_tutarli():
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_olustur(oturum, ornek_bdm(gorunen_ad="Sahiplik Modeli"))
        konusma = await konusma_olustur(oturum, bdm_id=bdm.id, kullanici_id=None)
        await mesaj_ekle(oturum, konusma=konusma, rol=MesajRolu.kullanici, icerik="soru")
        await oturum.commit()

        detay = await konusma_detayi(oturum, konusma)
        sahip = await konusma_sahibi_mi(oturum, konusma, kullanici_id=None, api_anahtari_id=None)

    assert detay["mesajlar"][0]["rol"] == "kullanici"
    assert sahip is False
