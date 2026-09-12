"""Log, ayar ve API anahtarı uçlarının sözleşme testleri (API §7, §12, §14)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import sqlalchemy as sa

from arkauc.app.cekirdek import guvenlik
from arkauc.app.cekirdek.ayarlar_db import ayar_oku
from bdm_listesi import BdmOlustur, bdm_olustur
from bdm_veritabani.modeller import (
    AnahtarDurumu,
    ApiAnahtari,
    IslemKaydi,
    Konusma,
    Mesaj,
    MesajRolu,
    Rol,
)
from bdm_veritabani.oturum import oturum_fabrikasi


async def _bdm_olustur(ad: str = "Yerel Llama") -> int:
    """Katalog katmanıyla bir BDM ekler ve kimliğini döndürür."""
    async with oturum_fabrikasi()() as oturum:
        bdm = await bdm_olustur(
            oturum,
            BdmOlustur(
                gorunen_ad=ad,
                saglayici="ollama",
                temel_url="http://localhost:11434/v1",
                upstream_model="llama3",
            ),
        )
        await oturum.commit()
        return bdm.id


async def _konusma_ekle(
    bdm_id: int,
    *,
    kullanici_id: int | None = None,
    baslik: str = "Sohbet",
    icerik: str = "Merhaba dünya",
    gun_once: int = 0,
) -> int:
    """Konuşma + tek kullanıcı mesajı ekler; konuşma kimliğini döndürür."""
    zaman = datetime.now(timezone.utc) - timedelta(days=gun_once)
    async with oturum_fabrikasi()() as oturum:
        konusma = Konusma(
            kullanici_id=kullanici_id,
            bdm_id=bdm_id,
            baslik=baslik,
            token_girdi=7,
            token_cikti=11,
            olusturulma=zaman,
            guncellenme=zaman,
        )
        oturum.add(konusma)
        await oturum.flush()
        oturum.add(
            Mesaj(
                konusma_id=konusma.id,
                rol=MesajRolu.kullanici,
                icerik=icerik,
                token_sayisi=7,
            )
        )
        await oturum.commit()
        return konusma.id


async def _islem_eylemleri() -> list[str]:
    async with oturum_fabrikasi()() as oturum:
        return list(
            (await oturum.execute(sa.select(IslemKaydi.eylem).order_by(IslemKaydi.id)))
            .scalars()
            .all()
        )


# --------------------------------------------------------------------------
# Loglar
# --------------------------------------------------------------------------


async def test_konusma_loglari_filtreler_ve_sayfalar(istemci, yardimci):
    bdm_a = await _bdm_olustur("Yerel Llama")
    bdm_b = await _bdm_olustur("Bulut GPT")
    kullanici_a = await yardimci.kullanici_ekle()
    kullanici_b = await yardimci.kullanici_ekle()
    eski = await _konusma_ekle(
        bdm_a,
        kullanici_id=kullanici_a.id,
        baslik="Fatura sorusu",
        icerik="Faturamı göremiyorum",
        gun_once=10,
    )
    yeni = await _konusma_ekle(
        bdm_b, kullanici_id=kullanici_b.id, baslik="Kurulum", icerik="Kurulum nasıl"
    )
    basliklar = yardimci.basliklar(await yardimci.yonetici())

    yanit = await istemci.get("/api/v1/loglar/konusmalar", headers=basliklar)
    assert yanit.status_code == 200
    govde = yanit.json()
    assert (govde["toplam"], govde["sayfa"], govde["boyut"]) == (2, 1, 25)
    assert {kayit["id"] for kayit in govde["kayitlar"]} == {eski, yeni}
    kayit = next(k for k in govde["kayitlar"] if k["id"] == eski)
    assert kayit["baslik"] == "Fatura sorusu"
    assert kayit["kullanici_eposta"] == kullanici_a.eposta
    assert kayit["bdm_ad"] == "Yerel Llama"
    assert kayit["mesaj_sayisi"] == 1
    assert (kayit["token_girdi"], kayit["token_cikti"]) == (7, 11)

    yanit = await istemci.get(
        f"/api/v1/loglar/konusmalar?bdm_id={bdm_a}", headers=basliklar
    )
    assert [k["id"] for k in yanit.json()["kayitlar"]] == [eski]

    yanit = await istemci.get(
        f"/api/v1/loglar/konusmalar?kullanici_id={kullanici_b.id}", headers=basliklar
    )
    assert [k["id"] for k in yanit.json()["kayitlar"]] == [yeni]

    yanit = await istemci.get("/api/v1/loglar/konusmalar?arama=Faturamı", headers=basliklar)
    assert [k["id"] for k in yanit.json()["kayitlar"]] == [eski]

    esik = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat().replace("+00:00", "Z")
    yanit = await istemci.get(
        f"/api/v1/loglar/konusmalar?bitis={esik}", headers=basliklar
    )
    assert [k["id"] for k in yanit.json()["kayitlar"]] == [eski]

    yanit = await istemci.get(
        f"/api/v1/loglar/konusmalar?baslangic={esik}", headers=basliklar
    )
    assert [k["id"] for k in yanit.json()["kayitlar"]] == [yeni]

    yanit = await istemci.get(
        "/api/v1/loglar/konusmalar?sayfa=2&boyut=1", headers=basliklar
    )
    govde = yanit.json()
    assert (govde["toplam"], govde["sayfa"], govde["boyut"]) == (2, 2, 1)
    assert len(govde["kayitlar"]) == 1


async def test_konusma_detayi_mesajlarla_doner_ve_bulunamayan_404(istemci, yardimci):
    bdm_id = await _bdm_olustur()
    kullanici = await yardimci.kullanici_ekle()
    konusma_id = await _konusma_ekle(
        bdm_id, kullanici_id=kullanici.id, baslik="Destek", icerik="Şifremi unuttum"
    )
    basliklar = yardimci.basliklar(await yardimci.yonetici())

    yanit = await istemci.get(f"/api/v1/loglar/konusmalar/{konusma_id}", headers=basliklar)
    assert yanit.status_code == 200
    govde = yanit.json()
    assert govde["id"] == konusma_id
    assert govde["baslik"] == "Destek"
    assert govde["bdm_ad"] == "Yerel Llama"
    assert govde["kullanici_eposta"] == kullanici.eposta
    assert [mesaj["icerik"] for mesaj in govde["mesajlar"]] == ["Şifremi unuttum"]
    assert govde["mesajlar"][0]["rol"] == "kullanici"

    yanit = await istemci.get("/api/v1/loglar/konusmalar/999999", headers=basliklar)
    assert yanit.status_code == 404
    assert yanit.json()["hata"]["kod"] == "bulunamadi"


async def test_disa_aktarim_bicimleri_indirme_basligi_dondurur(istemci, yardimci):
    bdm_id = await _bdm_olustur()
    konusma_id = await _konusma_ekle(bdm_id, baslik="Rapor", icerik="Rapor içeriği")
    basliklar = yardimci.basliklar(await yardimci.yonetici())

    beklenenler = {
        "json": ("application/json", f'"baslik": "Rapor"'),
        "md": ("text/markdown", "# Rapor"),
        "csv": ("text/csv", "mesaj_id"),
    }
    for bicim, (medya, iz) in beklenenler.items():
        yanit = await istemci.get(
            f"/api/v1/loglar/konusmalar/{konusma_id}/disa-aktar?bicim={bicim}",
            headers=basliklar,
        )
        assert yanit.status_code == 200, bicim
        assert yanit.headers["content-disposition"] == (
            f'attachment; filename="konusma-{konusma_id}.{bicim}"'
        )
        assert yanit.headers["content-type"].startswith(medya)
        assert iz in yanit.text
        assert "Rapor içeriği" in yanit.text

    yanit = await istemci.get(
        f"/api/v1/loglar/konusmalar/{konusma_id}/disa-aktar?bicim=xml", headers=basliklar
    )
    assert yanit.status_code == 400
    assert yanit.json()["hata"]["kod"] == "gecersiz_istek"


async def test_konusma_silme_kalicidir_ve_denetlenir(istemci, yardimci):
    bdm_id = await _bdm_olustur()
    konusma_id = await _konusma_ekle(bdm_id)
    basliklar = yardimci.basliklar(await yardimci.yonetici())

    yanit = await istemci.delete(
        f"/api/v1/loglar/konusmalar/{konusma_id}", headers=basliklar
    )
    assert yanit.status_code == 204
    assert yanit.content == b""

    yanit = await istemci.get(f"/api/v1/loglar/konusmalar/{konusma_id}", headers=basliklar)
    assert yanit.status_code == 404

    async with oturum_fabrikasi()() as oturum:
        mesaj_sayisi = (
            await oturum.execute(
                sa.select(sa.func.count())
                .select_from(Mesaj)
                .where(Mesaj.konusma_id == konusma_id)
            )
        ).scalar_one()
    assert mesaj_sayisi == 0
    assert "konusma.silindi" in await _islem_eylemleri()


async def test_loglari_temizle_saklama_gunu_ve_yalniz_yonetici(istemci, yardimci):
    bdm_id = await _bdm_olustur()
    eski = await _konusma_ekle(bdm_id, baslik="Eski", gun_once=40)
    yeni = await _konusma_ekle(bdm_id, baslik="Yeni", gun_once=1)

    operator = await yardimci.kullanici_ekle(rol=Rol.operator)
    yanit = await istemci.post(
        "/api/v1/loglar/temizle",
        json={"gun": 30},
        headers=yardimci.basliklar(operator),
    )
    assert yanit.status_code == 403
    assert yanit.json()["hata"]["kod"] == "yetki_yok"

    yonetici = await yardimci.yonetici()
    yanit = await istemci.post(
        "/api/v1/loglar/temizle", json={"gun": 30}, headers=yardimci.basliklar(yonetici)
    )
    assert yanit.status_code == 200
    assert yanit.json() == {"silinen": 1}
    assert "loglar.temizlendi" in await _islem_eylemleri()

    yanit = await istemci.get("/api/v1/loglar/konusmalar", headers=yardimci.basliklar(yonetici))
    assert [kayit["id"] for kayit in yanit.json()["kayitlar"]] == [yeni]

    # Gövdesiz çağrı saklama gününü ayardan okur ve taze kaydı silmez.
    yanit = await istemci.post("/api/v1/loglar/temizle", headers=yardimci.basliklar(yonetici))
    assert yanit.status_code == 200
    assert yanit.json() == {"silinen": 0}


async def test_islem_kayitlari_denetim_izini_listeler(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    basliklar = yardimci.basliklar(yonetici)
    anahtar = (
        await istemci.post(
            "/api/v1/api-anahtarlari", json={"ad": "Denetim"}, headers=basliklar
        )
    ).json()
    await istemci.post(
        f"/api/v1/api-anahtarlari/{anahtar['id']}/iptal", headers=basliklar
    )

    izleyici = await yardimci.kullanici_ekle(rol=Rol.izleyici)
    yanit = await istemci.get(
        "/api/v1/islem-kayitlari", headers=yardimci.basliklar(izleyici)
    )
    assert yanit.status_code == 200
    govde = yanit.json()
    assert (govde["sayfa"], govde["boyut"]) == (1, 25)
    assert govde["toplam"] == 2
    assert [kayit["eylem"] for kayit in govde["kayitlar"]] == [
        "api_anahtari.iptal_edildi",
        "api_anahtari.olusturuldu",
    ]

    kayit = govde["kayitlar"][1]
    assert set(kayit) == {
        "id",
        "kullanici_id",
        "kullanici_eposta",
        "eylem",
        "hedef_tur",
        "hedef_id",
        "ayrinti",
        "ip",
        "olusturulma",
    }
    assert kayit["kullanici_id"] == yonetici.id
    assert kayit["kullanici_eposta"] == yonetici.eposta
    assert kayit["hedef_tur"] == "api_anahtari"
    assert kayit["hedef_id"] == str(anahtar["id"])
    assert kayit["ayrinti"]["ad"] == "Denetim"

    yanit = await istemci.get(
        "/api/v1/islem-kayitlari?eylem=api_anahtari.iptal_edildi", headers=basliklar
    )
    assert yanit.json()["toplam"] == 1
    assert yanit.json()["kayitlar"][0]["hedef_id"] == str(anahtar["id"])

    yanit = await istemci.get(
        "/api/v1/islem-kayitlari?eylem=boyle.bir.eylem.yok", headers=basliklar
    )
    assert yanit.json() == {"toplam": 0, "sayfa": 1, "boyut": 25, "kayitlar": []}

    yanit = await istemci.get(
        f"/api/v1/islem-kayitlari?kullanici_id={yonetici.id}", headers=basliklar
    )
    assert yanit.json()["toplam"] == 2
    yanit = await istemci.get("/api/v1/islem-kayitlari?kullanici_id=999999", headers=basliklar)
    assert yanit.json()["toplam"] == 0

    dun = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat().replace("+00:00", "Z")
    evvelsi_gun = (
        (datetime.now(timezone.utc) - timedelta(days=2)).isoformat().replace("+00:00", "Z")
    )
    yanit = await istemci.get(f"/api/v1/islem-kayitlari?baslangic={dun}", headers=basliklar)
    assert yanit.json()["toplam"] == 2
    yanit = await istemci.get(f"/api/v1/islem-kayitlari?bitis={dun}", headers=basliklar)
    assert yanit.json()["toplam"] == 0
    yanit = await istemci.get(
        f"/api/v1/islem-kayitlari?baslangic={dun}&bitis={evvelsi_gun}", headers=basliklar
    )
    assert yanit.status_code == 400
    assert yanit.json()["hata"]["kod"] == "gecersiz_istek"

    yanit = await istemci.get("/api/v1/islem-kayitlari?boyut=1&sayfa=2", headers=basliklar)
    govde = yanit.json()
    assert (govde["toplam"], govde["sayfa"], govde["boyut"]) == (2, 2, 1)
    assert [kayit["eylem"] for kayit in govde["kayitlar"]] == ["api_anahtari.olusturuldu"]

    for sorgu in ("sayfa=0", "boyut=0", "boyut=201"):
        yanit = await istemci.get(f"/api/v1/islem-kayitlari?{sorgu}", headers=basliklar)
        assert yanit.status_code == 400, sorgu
        assert yanit.json()["hata"]["kod"] == "dogrulama_hatasi", sorgu

    # Sahipsiz kayıtlar (kullanıcı silinmiş/sistem eylemi) yine listelenir.
    async with oturum_fabrikasi()() as oturum:
        oturum.add(IslemKaydi(eylem="sistem.bakim", hedef_tur="ayar", hedef_id="7"))
        await oturum.commit()
    yanit = await istemci.get(
        "/api/v1/islem-kayitlari?eylem=sistem.bakim", headers=basliklar
    )
    sahipsiz = yanit.json()["kayitlar"][0]
    assert sahipsiz["kullanici_id"] is None
    assert sahipsiz["kullanici_eposta"] is None
    assert sahipsiz["hedef_id"] == "7"


async def test_islem_kayitlari_kimlik_ister(istemci):
    yanit = await istemci.get("/api/v1/islem-kayitlari")
    assert yanit.status_code == 401
    assert yanit.json()["hata"]["kod"] == "kimlik_gerekli"


async def test_log_uclari_kimlik_ve_yetki_ister(istemci, yardimci):
    son_kullanici = await yardimci.kullanici_ekle(rol=Rol.son_kullanici)
    yanit = await istemci.get(
        "/api/v1/loglar/konusmalar", headers=yardimci.basliklar(son_kullanici)
    )
    assert yanit.status_code == 403
    assert yanit.json()["hata"]["kod"] == "yetki_yok"

    yanit = await istemci.get("/api/v1/loglar/konusmalar")
    assert yanit.status_code == 401
    assert yanit.json()["hata"]["kod"] == "kimlik_gerekli"


async def test_konusma_silme_izleyiciye_kapali_operator_ve_yoneticiye_acik(istemci, yardimci):
    bdm_id = await _bdm_olustur()
    konusma_id = await _konusma_ekle(bdm_id, baslik="İzleyici denemesi")
    izleyici = await yardimci.kullanici_ekle(rol=Rol.izleyici)
    izleyici_basliklari = yardimci.basliklar(izleyici)

    yanit = await istemci.delete(
        f"/api/v1/loglar/konusmalar/{konusma_id}", headers=izleyici_basliklari
    )
    assert yanit.status_code == 403
    assert yanit.json()["hata"]["kod"] == "yetki_yok"
    assert "konusma.silindi" not in await _islem_eylemleri()

    # İzleyici okumaya devam eder; silme yalnızca yazma yetkisini kısıtlar.
    yanit = await istemci.get(
        f"/api/v1/loglar/konusmalar/{konusma_id}", headers=izleyici_basliklari
    )
    assert yanit.status_code == 200

    operator = await yardimci.kullanici_ekle(rol=Rol.operator)
    yanit = await istemci.delete(
        f"/api/v1/loglar/konusmalar/{konusma_id}", headers=yardimci.basliklar(operator)
    )
    assert yanit.status_code == 204
    assert "konusma.silindi" in await _islem_eylemleri()


async def test_log_sayfalama_sinirlari_dogrulanir(istemci, yardimci):
    basliklar = yardimci.basliklar(await yardimci.yonetici())

    yanit = await istemci.get(
        "/api/v1/loglar/konusmalar"
        "?baslangic=2026-09-06T00:00:00Z&bitis=2026-09-04T00:00:00Z",
        headers=basliklar,
    )
    assert yanit.status_code == 400
    assert yanit.json()["hata"]["kod"] == "gecersiz_istek"

    for sorgu in ("boyut=-5", "boyut=0", "boyut=201", "boyut=10000", "sayfa=0", "sayfa=-3"):
        yanit = await istemci.get(f"/api/v1/loglar/konusmalar?{sorgu}", headers=basliklar)
        assert yanit.status_code == 400, sorgu
        assert yanit.json()["hata"]["kod"] == "dogrulama_hatasi", sorgu

    yanit = await istemci.get("/api/v1/loglar/konusmalar?boyut=200", headers=basliklar)
    assert yanit.status_code == 200
    assert yanit.json()["boyut"] == 200


# --------------------------------------------------------------------------
# API anahtarları
# --------------------------------------------------------------------------


async def test_api_anahtari_tam_anahtari_yalnizca_bir_kez_dondurur(istemci, yardimci):
    bdm_id = await _bdm_olustur()
    yonetici = await yardimci.yonetici()
    basliklar = yardimci.basliklar(yonetici)

    yanit = await istemci.post(
        "/api/v1/api-anahtarlari",
        json={"ad": "Panel Entegrasyonu", "izinli_modeller": [str(bdm_id)], "gunluk_istek_siniri": 500},
        headers=basliklar,
    )
    assert yanit.status_code == 201
    olusan = yanit.json()
    tam_anahtar = olusan["tam_anahtar"]
    assert tam_anahtar.startswith("kuty_")
    assert olusan["durum"] == "aktif"
    assert olusan["gunluk_istek_siniri"] == 500
    assert olusan["izinli_modeller"] == [str(bdm_id)]
    assert olusan["son_kullanim"] is None
    assert olusan["onek"] == tam_anahtar[: len(olusan["onek"])]
    assert olusan["son_dort"] == tam_anahtar[-4:]

    yanit = await istemci.get("/api/v1/api-anahtarlari", headers=basliklar)
    assert yanit.status_code == 200
    kayitlar = yanit.json()
    assert len(kayitlar) == 1
    kayit = kayitlar[0]
    assert kayit["id"] == olusan["id"]
    assert kayit["ad"] == "Panel Entegrasyonu"
    assert "tam_anahtar" not in kayit
    assert tam_anahtar not in yanit.text
    assert (kayit["onek"], kayit["son_dort"]) == (olusan["onek"], olusan["son_dort"])

    assert "api_anahtari.olusturuldu" in await _islem_eylemleri()


async def test_api_anahtari_iptali_kalicidir_ve_denetlenir(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    basliklar = yardimci.basliklar(yonetici)
    yanit = await istemci.post(
        "/api/v1/api-anahtarlari", json={"ad": "CLI"}, headers=basliklar
    )
    anahtar_id = yanit.json()["id"]

    yanit = await istemci.post(
        f"/api/v1/api-anahtarlari/{anahtar_id}/iptal", headers=basliklar
    )
    assert yanit.status_code == 200
    assert yanit.json() == {"durum": "iptal"}

    async with oturum_fabrikasi()() as oturum:
        durum = await oturum.get(ApiAnahtari, anahtar_id)
        assert durum is not None and durum.durum is AnahtarDurumu.iptal

    yanit = await istemci.get("/api/v1/api-anahtarlari", headers=basliklar)
    assert yanit.json()[0]["durum"] == "iptal"

    yanit = await istemci.post(
        "/api/v1/api-anahtarlari/999999/iptal", headers=basliklar
    )
    assert yanit.status_code == 404
    assert "api_anahtari.iptal_edildi" in await _islem_eylemleri()


async def test_api_anahtari_uclari_izleyiciye_kapali_operator_ve_yoneticiye_acik(
    istemci, yardimci
):
    izleyici = await yardimci.kullanici_ekle(rol=Rol.izleyici)
    izleyici_basliklari = yardimci.basliklar(izleyici)

    assert (
        await istemci.get("/api/v1/api-anahtarlari", headers=izleyici_basliklari)
    ).status_code == 403
    yanit = await istemci.post(
        "/api/v1/api-anahtarlari", json={"ad": "İzleyici Anahtarı"},
        headers=izleyici_basliklari,
    )
    assert yanit.status_code == 403
    assert yanit.json()["hata"]["kod"] == "yetki_yok"
    yanit = await istemci.post(
        "/api/v1/api-anahtarlari/1/iptal", headers=izleyici_basliklari
    )
    assert yanit.status_code == 403
    assert "api_anahtari.olusturuldu" not in await _islem_eylemleri()

    operator = await yardimci.kullanici_ekle(rol=Rol.operator)
    operator_basliklari = yardimci.basliklar(operator)
    yanit = await istemci.post(
        "/api/v1/api-anahtarlari", json={"ad": "Operatör Anahtarı"},
        headers=operator_basliklari,
    )
    assert yanit.status_code == 201
    anahtar_id = yanit.json()["id"]
    assert (
        await istemci.get("/api/v1/api-anahtarlari", headers=operator_basliklari)
    ).status_code == 200
    yanit = await istemci.post(
        f"/api/v1/api-anahtarlari/{anahtar_id}/iptal", headers=operator_basliklari
    )
    assert yanit.status_code == 200
    assert yanit.json() == {"durum": "iptal"}


async def test_api_anahtari_bilinmeyen_modeli_reddeder(istemci, yardimci):
    basliklar = yardimci.basliklar(await yardimci.yonetici())
    yanit = await istemci.post(
        "/api/v1/api-anahtarlari",
        json={"ad": "Geçersiz", "izinli_modeller": ["yok-boyle-slug"]},
        headers=basliklar,
    )
    assert yanit.status_code == 400
    hata = yanit.json()["hata"]
    assert hata["kod"] == "gecersiz_istek"
    assert hata["ayrinti"]["gecersiz"] == ["yok-boyle-slug"]

    yanit = await istemci.post(
        "/api/v1/api-anahtarlari",
        json={"ad": "Genel", "izinli_modeller": []},
        headers=basliklar,
    )
    assert yanit.status_code == 201
    assert yanit.json()["izinli_modeller"] == []

    son_kullanici = await yardimci.kullanici_ekle(rol=Rol.son_kullanici)
    yanit = await istemci.get(
        "/api/v1/api-anahtarlari", headers=yardimci.basliklar(son_kullanici)
    )
    assert yanit.status_code == 403


# --------------------------------------------------------------------------
# Ayarlar
# --------------------------------------------------------------------------


async def test_ayarlar_getirir_ve_gunceller_smtp_sifresi_donmez(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    basliklar = yardimci.basliklar(yonetici)

    yanit = await istemci.get("/api/v1/ayarlar", headers=basliklar)
    assert yanit.status_code == 200
    govde = yanit.json()
    assert set(govde) == {
        "marka_adi",
        "kurulum_tamam",
        "saklama_gun",
        "maskeleme_aktif",
        "kayit_acik",
        "smtp_host",
        "smtp_gonderen",
        "smtp_tanimli",
        "bakim_modu",
    }
    assert govde["marka_adi"] == "KutyAI"
    assert (govde["saklama_gun"], govde["maskeleme_aktif"]) == (90, True)
    assert govde["smtp_tanimli"] is False

    yanit = await istemci.put(
        "/api/v1/ayarlar",
        json={
            "marka_adi": "Acme AI",
            "saklama_gun": 30,
            "bakim_modu": True,
            "kayit_acik": False,
            "smtp_host": "smtp.acme.local",
            "smtp_port": 2525,
            "smtp_sifre": "gizli-parola",
            "smtp_gonderen": "Acme <bilgi@acme.local>",
        },
        headers=basliklar,
    )
    assert yanit.status_code == 200
    govde = yanit.json()
    assert "smtp_sifre" not in govde
    assert (govde["marka_adi"], govde["saklama_gun"]) == ("Acme AI", 30)
    assert (govde["bakim_modu"], govde["kayit_acik"]) == (True, False)
    assert govde["smtp_host"] == "smtp.acme.local"
    assert govde["smtp_tanimli"] is True

    yanit = await istemci.get("/api/v1/ayarlar", headers=basliklar)
    assert yanit.json() == govde
    assert "gizli-parola" not in yanit.text

    async with oturum_fabrikasi()() as oturum:
        saklanan = await ayar_oku(oturum, "smtp_sifre")
        assert saklanan != "gizli-parola"
        assert guvenlik.coz(saklanan) == "gizli-parola"
        satir = (
            await oturum.execute(
                sa.select(IslemKaydi).where(IslemKaydi.eylem == "ayar.guncellendi")
            )
        ).scalars().one()
        assert satir.kullanici_id == yonetici.id
        assert "smtp_sifre" in satir.ayrinti["anahtarlar"]
        assert satir.ayrinti["anahtarlar"] == sorted(satir.ayrinti["anahtarlar"])
        assert "gizli-parola" not in str(satir.ayrinti)


async def test_ayarlar_sinirlari_dogrular_ve_yalniz_yonetici(istemci, yardimci):
    operator = await yardimci.kullanici_ekle(rol=Rol.operator)
    assert (await istemci.get(
        "/api/v1/ayarlar", headers=yardimci.basliklar(operator)
    )).status_code == 403
    assert (await istemci.put(
        "/api/v1/ayarlar", json={"saklama_gun": 10}, headers=yardimci.basliklar(operator)
    )).status_code == 403
    assert (await istemci.get("/api/v1/ayarlar")).status_code == 401

    yonetici = await yardimci.yonetici()
    basliklar = yardimci.basliklar(yonetici)
    for deger in (0, 3651):
        yanit = await istemci.put(
            "/api/v1/ayarlar", json={"saklama_gun": deger}, headers=basliklar
        )
        assert yanit.status_code == 400, deger
        assert yanit.json()["hata"]["kod"] == "dogrulama_hatasi"

    yanit = await istemci.put(
        "/api/v1/ayarlar", json={"saklama_gun": 3650}, headers=basliklar
    )
    assert yanit.status_code == 200
    assert yanit.json()["saklama_gun"] == 3650
