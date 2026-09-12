"""Kimlik ve kullanici yonetimi uclari (API.md §5, §6).

Kapsam: kayit → dogrula → giris → yenileme rotasyonu → cikis, yanlis parola,
dogrulanmamis kullanici, panel giris kapisi, kullanici yonetimi ve yetkileri,
parola sifirlama akisi.
"""

from __future__ import annotations

import asyncio
import socket
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

import sqlalchemy as sa

from arkauc.app.cekirdek import guvenlik
from arkauc.app.cekirdek.ayarlar import ayarlar
from arkauc.app.cekirdek.ayarlar_db import ayar_oku, ayar_yaz
from bdm_veritabani.modeller import (
    DogrulamaJetonu,
    IslemKaydi,
    JetonTuru,
    Kullanici,
    KullaniciDurumu,
    Oturum,
    Rol,
)
from bdm_veritabani.oturum import oturum_fabrikasi

PAROLA = "Parola123!"
YENI_PAROLA = "YeniParola456!"
KULLANICI_ALANLARI = {
    "id",
    "eposta",
    "ad_soyad",
    "rol",
    "durum",
    "eposta_dogrulandi",
    "olusturulma",
    "son_giris",
}


async def _kayit(istemci, eposta: str = "yeni@kutyai.local", parola: str = PAROLA):
    return await istemci.post(
        "/api/v1/kimlik/kayit",
        json={"eposta": eposta, "ad_soyad": "Yeni Kullanıcı", "parola": parola},
    )


def _jeton_coz(baglanti: str) -> str:
    return parse_qs(urlsplit(baglanti).query)["jeton"][0]


def _baslik(erisim: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {erisim}"}


async def test_kayit_dogrula_giris_yenile_cikis_akisi(istemci):
    yanit = await _kayit(istemci, "Yeni.User@Kutyai.Local")
    assert yanit.status_code == 201
    govde = yanit.json()
    assert set(govde["kullanici"]) == KULLANICI_ALANLARI
    assert govde["kullanici"]["eposta"] == "yeni.user@kutyai.local"
    assert govde["kullanici"]["rol"] == "son_kullanici"
    assert govde["kullanici"]["durum"] == "beklemede"
    assert govde["kullanici"]["eposta_dogrulandi"] is False
    assert govde["dogrulama_gerekli"] is True

    baglanti = govde["gelistirme_baglantisi"]
    assert baglanti == (
        f"{ayarlar.onuc_url.rstrip('/')}/dogrula?jeton={_jeton_coz(baglanti)}"
    )
    async with oturum_fabrikasi()() as oturum:
        # Jeton iceren baglanti `ayar` tablosunda saklanmaz (GUVENLIK.md).
        assert await ayar_oku(oturum, "son_dogrulama_baglantisi") is None
        kayit = (
            await oturum.execute(
                sa.select(DogrulamaJetonu).where(
                    DogrulamaJetonu.jeton_hash == guvenlik.ozet(_jeton_coz(baglanti))
                )
            )
        ).scalar_one()
        assert kayit.tur == JetonTuru.eposta_dogrulama
        kalan = kayit.son_kullanma.replace(tzinfo=timezone.utc) - datetime.now(
            timezone.utc
        )
        assert timedelta(hours=23) < kalan <= timedelta(hours=24)

    # dogrulama tek kullanimlik
    jeton = _jeton_coz(baglanti)
    dogrulama = await istemci.post("/api/v1/kimlik/dogrula", json={"jeton": jeton})
    assert dogrulama.status_code == 200
    assert dogrulama.json() == {"dogrulandi": True}
    tekrar = await istemci.post("/api/v1/kimlik/dogrula", json={"jeton": jeton})
    assert tekrar.status_code == 400
    assert tekrar.json()["hata"]["kod"] == "gecersiz_istek"

    async with oturum_fabrikasi()() as oturum:
        kullanilan = (
            await oturum.execute(
                sa.select(DogrulamaJetonu.kullanildi).where(
                    DogrulamaJetonu.jeton_hash == guvenlik.ozet(jeton)
                )
            )
        ).scalar_one()
        assert kullanilan is True

    async with oturum_fabrikasi()() as oturum:
        kullanici = (
            await oturum.execute(
                sa.select(Kullanici).where(Kullanici.eposta == "yeni.user@kutyai.local")
            )
        ).scalar_one()
        assert kullanici.durum == KullaniciDurumu.aktif
        assert kullanici.eposta_dogrulandi is True
        assert kullanici.son_giris is None

    # giris
    giris = await istemci.post(
        "/api/v1/kimlik/giris",
        json={"eposta": "Yeni.User@Kutyai.Local", "parola": PAROLA},
    )
    assert giris.status_code == 200
    giris_govdesi = giris.json()
    assert set(giris_govdesi) == {"erisim_jetonu", "yenileme_jetonu", "kullanici"}
    assert set(giris_govdesi["kullanici"]) == KULLANICI_ALANLARI
    ilk_yenileme = giris_govdesi["yenileme_jetonu"]

    async with oturum_fabrikasi()() as oturum:
        kullanici = (
            await oturum.execute(
                sa.select(Kullanici).where(Kullanici.eposta == "yeni.user@kutyai.local")
            )
        ).scalar_one()
        assert kullanici.son_giris is not None
        kayit = (
            await oturum.execute(
                sa.select(Oturum).where(Oturum.jeton_hash == guvenlik.ozet(ilk_yenileme))
            )
        ).scalar_one()
        assert kayit.iptal is False
        assert kayit.kullanici_id == kullanici.id

    # yenileme rotasyonu
    yenileme = await istemci.post(
        "/api/v1/kimlik/yenile", json={"yenileme_jetonu": ilk_yenileme}
    )
    assert yenileme.status_code == 200
    yeni_govde = yenileme.json()
    assert set(yeni_govde) == {"erisim_jetonu", "yenileme_jetonu"}
    assert yeni_govde["yenileme_jetonu"] != ilk_yenileme

    eski_jeton = await istemci.post(
        "/api/v1/kimlik/yenile", json={"yenileme_jetonu": ilk_yenileme}
    )
    assert eski_jeton.status_code == 401
    assert eski_jeton.json()["hata"]["kod"] == "jeton_gecersiz"

    async with oturum_fabrikasi()() as oturum:
        eski_kayit = (
            await oturum.execute(
                sa.select(Oturum).where(Oturum.jeton_hash == guvenlik.ozet(ilk_yenileme))
            )
        ).scalar_one()
        assert eski_kayit.iptal is True

    # ben
    ben = await istemci.get(
        "/api/v1/kimlik/ben", headers=_baslik(yeni_govde["erisim_jetonu"])
    )
    assert ben.status_code == 200
    assert ben.json()["eposta"] == "yeni.user@kutyai.local"

    # cikis: yeni yenileme jetonu iptal edilir
    cikis = await istemci.post(
        "/api/v1/kimlik/cikis",
        json={"yenileme_jetonu": yeni_govde["yenileme_jetonu"]},
        headers=_baslik(yeni_govde["erisim_jetonu"]),
    )
    assert cikis.status_code == 200
    assert cikis.json()["mesaj"]
    govdesiz = await istemci.post(
        "/api/v1/kimlik/cikis", headers=_baslik(yeni_govde["erisim_jetonu"])
    )
    assert govdesiz.status_code == 200
    sonrasi = await istemci.post(
        "/api/v1/kimlik/yenile", json={"yenileme_jetonu": yeni_govde["yenileme_jetonu"]}
    )
    assert sonrasi.status_code == 401

    async with oturum_fabrikasi()() as oturum:
        eylemler = set(
            (await oturum.execute(sa.select(IslemKaydi.eylem))).scalars().all()
        )
    assert {"kimlik.kayit", "kimlik.dogrula", "kimlik.giris", "kimlik.cikis"} <= eylemler


async def test_yanlis_parola_gecersiz_kimlik_bilgisi_dondurur(istemci, yardimci):
    kullanici = await yardimci.kullanici_ekle(eposta="parola@kutyai.local", rol=Rol.son_kullanici)
    yanit = await istemci.post(
        "/api/v1/kimlik/giris",
        json={"eposta": kullanici.eposta, "parola": "YanlisParola!"},
    )
    assert yanit.status_code == 401
    hata = yanit.json()["hata"]
    assert hata["kod"] == "gecersiz_kimlik_bilgisi"
    assert hata["mesaj"] == "E-posta veya parola hatalı."

    bilinmeyen = await istemci.post(
        "/api/v1/kimlik/giris",
        json={"eposta": "yok@kutyai.local", "parola": PAROLA},
    )
    assert bilinmeyen.status_code == 401
    assert bilinmeyen.json()["hata"]["kod"] == "gecersiz_kimlik_bilgisi"


async def test_dogrulanmamis_kullanici_giris_yapamaz(istemci, yardimci):
    await yardimci.kullanici_ekle(
        eposta="dogrulanmamis@kutyai.local",
        dogrulandi=False,
        durum=KullaniciDurumu.beklemede,
    )
    yanit = await istemci.post(
        "/api/v1/kimlik/giris",
        json={"eposta": "dogrulanmamis@kutyai.local", "parola": PAROLA},
    )
    assert yanit.status_code == 403
    assert yanit.json()["hata"]["kod"] == "eposta_dogrulanmadi"


async def test_pasif_kullanici_giris_yapamaz(istemci, yardimci):
    await yardimci.kullanici_ekle(
        eposta="pasif@kutyai.local", durum=KullaniciDurumu.pasif
    )
    yanit = await istemci.post(
        "/api/v1/kimlik/giris",
        json={"eposta": "pasif@kutyai.local", "parola": PAROLA},
    )
    assert yanit.status_code == 403
    assert yanit.json()["hata"]["kod"] == "yetki_yok"


async def test_panel_giris_yalniz_personel(istemci, yardimci):
    await yardimci.kullanici_ekle(eposta="son@kutyai.local", rol=Rol.son_kullanici)
    yanit = await istemci.post(
        "/api/v1/kimlik/panel-giris",
        json={"eposta": "son@kutyai.local", "parola": PAROLA},
    )
    assert yanit.status_code == 403
    assert yanit.json()["hata"]["kod"] == "yetki_yok"

    await yardimci.yonetici(eposta="yonetici@kutyai.local")
    panel = await istemci.post(
        "/api/v1/kimlik/panel-giris",
        json={"eposta": "yonetici@kutyai.local", "parola": PAROLA},
    )
    assert panel.status_code == 200
    assert panel.json()["kullanici"]["rol"] == "yonetici"

    ters = await istemci.post(
        "/api/v1/kimlik/giris",
        json={"eposta": "yonetici@kutyai.local", "parola": PAROLA},
    )
    assert ters.status_code == 403
    assert ters.json()["hata"]["kod"] == "yetki_yok"


async def test_tekrar_kayit_409(istemci):
    assert (await _kayit(istemci, "tekrar@kutyai.local")).status_code == 201
    ikinci = await _kayit(istemci, "TEKRAR@kutyai.local")
    assert ikinci.status_code == 409
    assert ikinci.json()["hata"]["kod"] == "cakisma"


async def test_kayit_kapaliyken_403(istemci):
    async with oturum_fabrikasi()() as oturum:
        await ayar_yaz(oturum, "kayit_acik", False)
        await oturum.commit()
    yanit = await _kayit(istemci, "kapali@kutyai.local")
    assert yanit.status_code == 403
    assert yanit.json()["hata"]["kod"] == "yetki_yok"


async def test_kisa_parola_gecersiz_istek(istemci):
    yanit = await _kayit(istemci, "kisa@kutyai.local", parola="kisa")
    assert yanit.status_code == 400
    assert yanit.json()["hata"]["kod"] == "gecersiz_istek"


async def test_gecersiz_dogrulama_jetonu_400(istemci):
    yanit = await istemci.post("/api/v1/kimlik/dogrula", json={"jeton": "uydurma-jeton"})
    assert yanit.status_code == 400
    assert yanit.json()["hata"]["kod"] == "gecersiz_istek"


async def test_pasif_kullanici_dogrulama_ile_geri_acilmaz(istemci, yardimci):
    kayit = await _kayit(istemci, "geri.acilmasin@kutyai.local")
    yonetici = await yardimci.yonetici()
    kullanici_id = (
        await istemci.get(
            "/api/v1/kullanicilar?arama=geri.acilmasin", headers=yardimci.basliklar(yonetici)
        )
    ).json()["kayitlar"][0]["id"]
    pasif = await istemci.delete(
        f"/api/v1/kullanicilar/{kullanici_id}", headers=yardimci.basliklar(yonetici)
    )
    assert pasif.status_code == 204

    dogrula = await istemci.post(
        "/api/v1/kimlik/dogrula",
        json={"jeton": _jeton_coz(kayit.json()["gelistirme_baglantisi"])},
    )
    assert dogrula.status_code == 200
    assert dogrula.json() == {"dogrulandi": True}
    async with oturum_fabrikasi()() as oturum:
        kullanici = await oturum.get(Kullanici, kullanici_id)
        assert kullanici.eposta_dogrulandi is True
        assert kullanici.durum == KullaniciDurumu.pasif

    giris = await istemci.post(
        "/api/v1/kimlik/giris",
        json={"eposta": "geri.acilmasin@kutyai.local", "parola": PAROLA},
    )
    assert giris.status_code == 403
    assert giris.json()["hata"]["kod"] == "yetki_yok"


async def test_suresi_gecmis_dogrulama_jetonu_400(istemci):
    kayit = await _kayit(istemci, "suresi.gecti@kutyai.local")
    jeton = _jeton_coz(kayit.json()["gelistirme_baglantisi"])
    async with oturum_fabrikasi()() as oturum:
        dogrulama = (
            await oturum.execute(
                sa.select(DogrulamaJetonu).where(
                    DogrulamaJetonu.jeton_hash == guvenlik.ozet(jeton)
                )
            )
        ).scalar_one()
        dogrulama.son_kullanma = datetime.now(timezone.utc) - timedelta(minutes=1)
        await oturum.commit()

    yanit = await istemci.post("/api/v1/kimlik/dogrula", json={"jeton": jeton})
    assert yanit.status_code == 400
    assert yanit.json()["hata"]["kod"] == "gecersiz_istek"


async def test_suresi_gecmis_yenileme_reddedilir(istemci, yardimci):
    kullanici = await yardimci.kullanici_ekle(eposta="suresiz@kutyai.local")
    giris = await istemci.post(
        "/api/v1/kimlik/giris",
        json={"eposta": kullanici.eposta, "parola": PAROLA},
    )
    yenileme_jetonu = giris.json()["yenileme_jetonu"]
    async with oturum_fabrikasi()() as oturum:
        kayit = (
            await oturum.execute(
                sa.select(Oturum).where(
                    Oturum.jeton_hash == guvenlik.ozet(yenileme_jetonu)
                )
            )
        ).scalar_one()
        kayit.son_kullanma = datetime.now(timezone.utc) - timedelta(minutes=1)
        await oturum.commit()

    yanit = await istemci.post(
        "/api/v1/kimlik/yenile", json={"yenileme_jetonu": yenileme_jetonu}
    )
    assert yanit.status_code == 401
    assert yanit.json()["hata"]["kod"] == "jeton_suresi_doldu"


async def test_ben_kimlik_gerekli(istemci):
    yanit = await istemci.get("/api/v1/kimlik/ben")
    assert yanit.status_code == 401
    assert yanit.json()["hata"]["kod"] == "kimlik_gerekli"


async def test_sifre_sifirlama_akisi(istemci, yardimci):
    kullanici = await yardimci.kullanici_ekle(eposta="sifirla@kutyai.local")
    giris = await istemci.post(
        "/api/v1/kimlik/giris",
        json={"eposta": kullanici.eposta, "parola": PAROLA},
    )
    eski_yenileme = giris.json()["yenileme_jetonu"]

    istek = await istemci.post(
        "/api/v1/kimlik/sifre-sifirlama-iste", json={"eposta": kullanici.eposta}
    )
    assert istek.status_code == 200
    baglanti = istek.json()["gelistirme_baglantisi"]
    assert baglanti == (
        f"{ayarlar.onuc_url.rstrip('/')}/sifre-sifirla?jeton={_jeton_coz(baglanti)}"
    )
    async with oturum_fabrikasi()() as oturum:
        # Jeton iceren baglanti `ayar` tablosunda saklanmaz (GUVENLIK.md).
        assert await ayar_oku(oturum, "son_sifirlama_baglantisi") is None
        kayit = (
            await oturum.execute(
                sa.select(DogrulamaJetonu).where(
                    DogrulamaJetonu.jeton_hash == guvenlik.ozet(_jeton_coz(baglanti))
                )
            )
        ).scalar_one()
        assert kayit.tur == JetonTuru.sifre_sifirlama
        assert kayit.kullanildi is False

    # kisa parola reddedilir
    kisa = await istemci.post(
        "/api/v1/kimlik/sifre-sifirla",
        json={"jeton": _jeton_coz(baglanti), "yeni_parola": "kisa"},
    )
    assert kisa.status_code == 400

    sifirla = await istemci.post(
        "/api/v1/kimlik/sifre-sifirla",
        json={"jeton": _jeton_coz(baglanti), "yeni_parola": YENI_PAROLA},
    )
    assert sifirla.status_code == 200
    assert sifirla.json()["mesaj"]

    tekrar = await istemci.post(
        "/api/v1/kimlik/sifre-sifirla",
        json={"jeton": _jeton_coz(baglanti), "yeni_parola": YENI_PAROLA},
    )
    assert tekrar.status_code == 400

    # tum acik oturumlar iptal edildi
    iptal = await istemci.post(
        "/api/v1/kimlik/yenile", json={"yenileme_jetonu": eski_yenileme}
    )
    assert iptal.status_code == 401

    # eski parola gecersiz, yeni parola gecerli
    eski = await istemci.post(
        "/api/v1/kimlik/giris",
        json={"eposta": kullanici.eposta, "parola": PAROLA},
    )
    assert eski.status_code == 401
    yeni = await istemci.post(
        "/api/v1/kimlik/giris",
        json={"eposta": kullanici.eposta, "parola": YENI_PAROLA},
    )
    assert yeni.status_code == 200


async def test_sifre_sifirlama_istegi_bilinmeyen_eposta_ayni_mesaj(istemci, yardimci):
    await yardimci.kullanici_ekle(eposta="var@kutyai.local")
    bilinen = await istemci.post(
        "/api/v1/kimlik/sifre-sifirlama-iste", json={"eposta": "var@kutyai.local"}
    )
    bilinmeyen = await istemci.post(
        "/api/v1/kimlik/sifre-sifirlama-iste", json={"eposta": "yok@kutyai.local"}
    )
    assert bilinmeyen.status_code == 200
    assert bilinmeyen.json()["mesaj"] == bilinen.json()["mesaj"]
    assert "gelistirme_baglantisi" not in bilinmeyen.json()


async def test_kullanicilar_listesi_yetki_ve_filtreler(istemci, yardimci):
    yonetici = await yardimci.yonetici(eposta="admin@kutyai.local")
    await yardimci.kullanici_ekle(eposta="aranan@kutyai.local", ad_soyad="Aranan Kişi")
    await yardimci.kullanici_ekle(eposta="baskasi@kutyai.local", rol=Rol.izleyici)

    yetkisiz = await istemci.get(
        "/api/v1/kullanicilar", headers=yardimci.basliklar(await yardimci.kullanici_ekle())
    )
    assert yetkisiz.status_code == 403
    assert yetkisiz.json()["hata"]["kod"] == "yetki_yok"

    anonim = await istemci.get("/api/v1/kullanicilar")
    assert anonim.status_code == 401

    basliklar = yardimci.basliklar(yonetici)
    liste = await istemci.get("/api/v1/kullanicilar", headers=basliklar)
    assert liste.status_code == 200
    govde = liste.json()
    assert set(govde) == {"toplam", "sayfa", "boyut", "kayitlar"}
    assert govde["toplam"] >= 4
    assert set(govde["kayitlar"][0]) == KULLANICI_ALANLARI

    arama = await istemci.get(
        "/api/v1/kullanicilar?arama=aranan", headers=basliklar
    )
    assert arama.status_code == 200
    assert arama.json()["toplam"] == 1
    assert arama.json()["kayitlar"][0]["eposta"] == "aranan@kutyai.local"

    rol_filtre = await istemci.get(
        "/api/v1/kullanicilar?rol=izleyici", headers=basliklar
    )
    assert rol_filtre.json()["toplam"] == 1
    assert rol_filtre.json()["kayitlar"][0]["rol"] == "izleyici"

    durum_filtre = await istemci.get(
        "/api/v1/kullanicilar?durum=pasif", headers=basliklar
    )
    assert durum_filtre.json()["toplam"] == 0

    sayfali = await istemci.get(
        "/api/v1/kullanicilar?sayfa=1&boyut=2", headers=basliklar
    )
    assert sayfali.json()["boyut"] == 2
    assert len(sayfali.json()["kayitlar"]) == 2
    ikinci_sayfa = await istemci.get(
        "/api/v1/kullanicilar?sayfa=2&boyut=2", headers=basliklar
    )
    assert len(ikinci_sayfa.json()["kayitlar"]) == 2
    assert (
        sayfali.json()["kayitlar"][0]["id"] != ikinci_sayfa.json()["kayitlar"][0]["id"]
    )


async def test_kayit_sonrasi_kullanici_personel_listesinde_gorunur(istemci, yardimci):
    await _kayit(istemci, "listelenen@kutyai.local")
    yonetici = await yardimci.yonetici()
    liste = await istemci.get(
        "/api/v1/kullanicilar?arama=listelenen", headers=yardimci.basliklar(yonetici)
    )
    assert liste.status_code == 200
    kayit = liste.json()["kayitlar"][0]
    assert kayit["eposta"] == "listelenen@kutyai.local"
    assert kayit["durum"] == "beklemede"


async def test_yonetici_kullanici_olusturur_gunceller_pasiflestirir(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    basliklar = yardimci.basliklar(yonetici)

    olustur = await istemci.post(
        "/api/v1/kullanicilar",
        json={
            "eposta": "Davet.Li@Kutyai.Local",
            "ad_soyad": "Davetli Kişi",
            "parola": PAROLA,
            "rol": "izleyici",
        },
        headers=basliklar,
    )
    assert olustur.status_code == 201
    yeni = olustur.json()
    assert yeni["eposta"] == "davet.li@kutyai.local"
    assert yeni["rol"] == "izleyici"
    assert yeni["durum"] == "aktif"
    assert yeni["eposta_dogrulandi"] is True

    tekrar = await istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": "davet.li@kutyai.local", "parola": PAROLA, "rol": "izleyici"},
        headers=basliklar,
    )
    assert tekrar.status_code == 409

    # davet edilen personel panel kapisindan giris yapabilir
    giris = await istemci.post(
        "/api/v1/kimlik/panel-giris",
        json={"eposta": "davet.li@kutyai.local", "parola": PAROLA},
    )
    assert giris.status_code == 200
    assert giris.json()["kullanici"]["rol"] == "izleyici"

    guncelle = await istemci.patch(
        f"/api/v1/kullanicilar/{yeni['id']}",
        json={"rol": "operator", "ad_soyad": "Güncel Kişi", "durum": "aktif"},
        headers=basliklar,
    )
    assert guncelle.status_code == 200
    assert guncelle.json()["rol"] == "operator"
    assert guncelle.json()["ad_soyad"] == "Güncel Kişi"

    pasiflestir = await istemci.delete(
        f"/api/v1/kullanicilar/{yeni['id']}", headers=basliklar
    )
    assert pasiflestir.status_code == 204
    assert pasiflestir.content == b""

    pasif_liste = await istemci.get(
        "/api/v1/kullanicilar?durum=pasif", headers=basliklar
    )
    assert [k["id"] for k in pasif_liste.json()["kayitlar"]] == [yeni["id"]]

    kendini = await istemci.delete(
        f"/api/v1/kullanicilar/{yonetici.id}", headers=basliklar
    )
    assert kendini.status_code == 409
    assert kendini.json()["hata"]["kod"] == "gecersiz_gecis"

    yok = await istemci.delete("/api/v1/kullanicilar/999999", headers=basliklar)
    assert yok.status_code == 404

    yetkisiz = await istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": "olmaz@kutyai.local", "parola": PAROLA, "rol": "izleyici"},
        headers=yardimci.basliklar(await yardimci.kullanici_ekle()),
    )
    assert yetkisiz.status_code == 403

    # personel olmayan kendi rolunu yukseltemez
    yukseltme = await istemci.patch(
        f"/api/v1/kullanicilar/{yeni['id']}",
        json={"rol": "yonetici"},
        headers=yardimci.basliklar(await yardimci.kullanici_ekle()),
    )
    assert yukseltme.status_code == 403
    assert yukseltme.json()["hata"]["kod"] == "yetki_yok"

    async with oturum_fabrikasi()() as oturum:
        kayitlar = (
            await oturum.execute(
                sa.select(IslemKaydi.eylem, IslemKaydi.hedef_id).where(
                    IslemKaydi.eylem.in_(
                        ["kullanici.olustur", "kullanici.guncelle", "kullanici.pasiflestir"]
                    )
                )
            )
        ).all()
    eylemler = {eylem for eylem, _ in kayitlar}
    assert eylemler == {"kullanici.olustur", "kullanici.guncelle", "kullanici.pasiflestir"}
    assert all(hedef == str(yeni["id"]) for _, hedef in kayitlar)


async def test_pasiflestirilen_kullanicinin_jetonlari_gecersiz(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    hedef = await yardimci.kullanici_ekle(eposta="kapatilacak@kutyai.local")
    giris = await istemci.post(
        "/api/v1/kimlik/giris",
        json={"eposta": hedef.eposta, "parola": PAROLA},
    )
    yenileme_jetonu = giris.json()["yenileme_jetonu"]

    pasiflestir = await istemci.delete(
        f"/api/v1/kullanicilar/{hedef.id}", headers=yardimci.basliklar(yonetici)
    )
    assert pasiflestir.status_code == 204

    yenile = await istemci.post(
        "/api/v1/kimlik/yenile", json={"yenileme_jetonu": yenileme_jetonu}
    )
    assert yenile.status_code == 401
    ben = await istemci.get(
        "/api/v1/kimlik/ben", headers=_baslik(giris.json()["erisim_jetonu"])
    )
    assert ben.status_code == 403
    assert ben.json()["hata"]["kod"] == "yetki_yok"


async def _smtp_ayarlarini_yaz(**degerler: object) -> None:
    async with oturum_fabrikasi()() as oturum:
        for anahtar, deger in degerler.items():
            await ayar_yaz(oturum, anahtar, deger)
        await oturum.commit()


def _kapali_port() -> int:
    """Bosta birakilmis yerel port: baglanti aninda reddedilir."""
    with socket.socket() as yuvak:
        yuvak.bind(("127.0.0.1", 0))
        return int(yuvak.getsockname()[1])


async def test_posta_surucusu_ayar_tablosundan_secilir(monkeypatch):
    from arkauc.app.servisler import posta

    monkeypatch.setattr(ayarlar, "smtp_host", "")
    async with oturum_fabrikasi()() as oturum:
        # tablo bos + ortam bos → konsol surucusu
        assert isinstance(await posta.surucu_sec(oturum), posta.KonsolPosta)

        # panelden girilen host → SMTP surucusu
        await ayar_yaz(oturum, "smtp_host", "smtp.kutyai.local")
        await ayar_yaz(oturum, "smtp_port", 2525)
        await oturum.flush()
        assert isinstance(await posta.surucu_sec(oturum), posta.SmtpPosta)
        yapilandirma = await posta.posta_ayarlarini_oku(oturum)
        assert yapilandirma.host == "smtp.kutyai.local"
        assert yapilandirma.port == 2525
        assert yapilandirma.tanimli_mi is True

        # tablodaki bos deger ortama duser
        await ayar_yaz(oturum, "smtp_host", "   ")
        await ayar_yaz(oturum, "smtp_port", None)
        await oturum.flush()
        monkeypatch.setattr(ayarlar, "smtp_host", "ortam.kutyai.local")
        assert isinstance(await posta.surucu_sec(oturum), posta.SmtpPosta)
        yapilandirma = await posta.posta_ayarlarini_oku(oturum)
        assert yapilandirma.host == "ortam.kutyai.local"
        assert yapilandirma.port == ayarlar.smtp_port

    taban = ayarlar.onuc_url.rstrip("/")
    assert posta.dogrulama_baglantisi("abc") == f"{taban}/dogrula?jeton=abc"
    assert posta.sifirlama_baglantisi("a b") == f"{taban}/sifre-sifirla?jeton=a%20b"


async def test_smtp_sifresi_fernet_cozulur():
    from arkauc.app.servisler import posta

    async with oturum_fabrikasi()() as oturum:
        await ayar_yaz(oturum, "smtp_sifre", guvenlik.sifrele("gizli-sifre"))
        await oturum.flush()
        assert (await posta.posta_ayarlarini_oku(oturum)).sifre == "gizli-sifre"

        # henuz sifrelenmemis eski kayit ham deger olarak kullanilir
        await ayar_yaz(oturum, "smtp_sifre", "ham-sifre")
        await oturum.flush()
        assert (await posta.posta_ayarlarini_oku(oturum)).sifre == "ham-sifre"


async def test_smtp_gonderim_hatasi_yutulur():
    from arkauc.app.servisler import posta

    await _smtp_ayarlarini_yaz(
        smtp_host="127.0.0.1", smtp_port=_kapali_port(), smtp_tls=False
    )
    async with oturum_fabrikasi()() as oturum:
        assert isinstance(await posta.surucu_sec(oturum), posta.SmtpPosta)
        assert (
            await posta.posta_gonder(oturum, "kime@kutyai.local", "Konu", "Gövde")
            is False
        )


async def test_panel_smtp_ayari_gelistirme_baglantisini_kapatir(istemci):
    await _smtp_ayarlarini_yaz(
        smtp_host="127.0.0.1", smtp_port=_kapali_port(), smtp_tls=False
    )

    yanit = await _kayit(istemci, "panelsmtp@kutyai.local")
    assert yanit.status_code == 201
    assert "gelistirme_baglantisi" not in yanit.json()
    async with oturum_fabrikasi()() as oturum:
        assert await ayar_oku(oturum, "son_dogrulama_baglantisi") is None


# --------------------------------------------------------------------------
# Eszamanlilik (tek kullanimlik jetonlar, eszamanli kayit)
# --------------------------------------------------------------------------


async def _giris_jetonlari(istemci, eposta: str) -> dict[str, str]:
    giris = await istemci.post(
        "/api/v1/kimlik/giris", json={"eposta": eposta, "parola": PAROLA}
    )
    assert giris.status_code == 200
    return giris.json()


async def test_eszamanli_yenileme_tek_kullanimlik(istemci, yardimci):
    kullanici = await yardimci.kullanici_ekle(eposta="yaris.yenile@kutyai.local")
    jetonlar = await _giris_jetonlari(istemci, kullanici.eposta)
    yenileme_jetonu = jetonlar["yenileme_jetonu"]

    yanitlar = await asyncio.gather(
        *[
            istemci.post(
                "/api/v1/kimlik/yenile",
                json={"yenileme_jetonu": yenileme_jetonu},
            )
            for _ in range(5)
        ]
    )

    kodlar = [y.status_code for y in yanitlar]
    assert kodlar.count(200) == 1
    assert kodlar.count(401) == 4
    assert all(
        y.json()["hata"]["kod"] == "jeton_gecersiz"
        for y in yanitlar
        if y.status_code == 401
    )

    async with oturum_fabrikasi()() as oturum:
        acik = (
            await oturum.execute(
                sa.select(sa.func.count())
                .select_from(Oturum)
                .where(
                    Oturum.kullanici_id == kullanici.id, Oturum.iptal.is_(False)
                )
            )
        ).scalar_one()
    assert acik == 1

    # Rotasyonu kazanan jeton gercekten kullanilabilir olmali.
    kazanan = next(y for y in yanitlar if y.status_code == 200).json()
    devam = await istemci.post(
        "/api/v1/kimlik/yenile",
        json={"yenileme_jetonu": kazanan["yenileme_jetonu"]},
    )
    assert devam.status_code == 200


async def test_eszamanli_kayit_409_dondurur(istemci):
    yanitlar = await asyncio.gather(
        *[_kayit(istemci, "yaris.kayit@kutyai.local") for _ in range(2)]
    )

    assert sorted(y.status_code for y in yanitlar) == [201, 409]
    cakisan = next(y for y in yanitlar if y.status_code == 409)
    assert cakisan.json()["hata"]["kod"] == "cakisma"

    async with oturum_fabrikasi()() as oturum:
        adet = (
            await oturum.execute(
                sa.select(sa.func.count())
                .select_from(Kullanici)
                .where(Kullanici.eposta == "yaris.kayit@kutyai.local")
            )
        ).scalar_one()
    assert adet == 1


async def test_eszamanli_kullanici_olusturma_409_dondurur(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    basliklar = yardimci.basliklar(yonetici)
    govde = {
        "eposta": "yaris.personel@kutyai.local",
        "parola": PAROLA,
        "rol": "izleyici",
    }

    yanitlar = await asyncio.gather(
        *[
            istemci.post("/api/v1/kullanicilar", json=govde, headers=basliklar)
            for _ in range(2)
        ]
    )

    assert sorted(y.status_code for y in yanitlar) == [201, 409]
    cakisan = next(y for y in yanitlar if y.status_code == 409)
    assert cakisan.json()["hata"]["kod"] == "cakisma"


async def test_eszamanli_dogrulama_tek_kullanimlik(istemci):
    kayit = await _kayit(istemci, "yaris.dogrula@kutyai.local")
    jeton = _jeton_coz(kayit.json()["gelistirme_baglantisi"])

    yanitlar = await asyncio.gather(
        *[
            istemci.post("/api/v1/kimlik/dogrula", json={"jeton": jeton})
            for _ in range(5)
        ]
    )

    kodlar = [y.status_code for y in yanitlar]
    assert kodlar.count(200) == 1
    assert kodlar.count(400) == 4

    async with oturum_fabrikasi()() as oturum:
        kayit_satiri = (
            await oturum.execute(
                sa.select(DogrulamaJetonu).where(
                    DogrulamaJetonu.jeton_hash == guvenlik.ozet(jeton)
                )
            )
        ).scalar_one()
        assert kayit_satiri.kullanildi is True


async def test_eszamanli_sifre_sifirlama_tek_kullanimlik(istemci, yardimci):
    kullanici = await yardimci.kullanici_ekle(eposta="yaris.sifirla@kutyai.local")
    istek = await istemci.post(
        "/api/v1/kimlik/sifre-sifirlama-iste", json={"eposta": kullanici.eposta}
    )
    jeton = _jeton_coz(istek.json()["gelistirme_baglantisi"])

    yanitlar = await asyncio.gather(
        *[
            istemci.post(
                "/api/v1/kimlik/sifre-sifirla",
                json={"jeton": jeton, "yeni_parola": YENI_PAROLA},
            )
            for _ in range(5)
        ]
    )

    kodlar = [y.status_code for y in yanitlar]
    assert kodlar.count(200) == 1
    assert kodlar.count(400) == 4

    # Kazanan sifirlama kalici olmali: yeni parola ile giris, eski parola ile 401.
    yeni = await istemci.post(
        "/api/v1/kimlik/giris",
        json={"eposta": kullanici.eposta, "parola": YENI_PAROLA},
    )
    assert yeni.status_code == 200
    eski = await istemci.post(
        "/api/v1/kimlik/giris",
        json={"eposta": kullanici.eposta, "parola": PAROLA},
    )
    assert eski.status_code == 401


# --------------------------------------------------------------------------
# Hesap numaralandirma zamanlamasi ve kendini kilitleme korumasi
# --------------------------------------------------------------------------


async def test_sifre_sifirlama_iste_ayni_maliyetli_dogrulama(
    istemci, yardimci, monkeypatch
):
    from arkauc.app.cekirdek import guvenlik as guvenlik_modulu

    bilinen_eposta = "zamanlama@kutyai.local"
    await yardimci.kullanici_ekle(eposta=bilinen_eposta)

    gercek_dogrula = guvenlik_modulu.sifre_dogrula
    cagrilar: list[tuple[float, str]] = []

    def sayan(sifre_hash: str, sifre: str):
        cagrilar.append((time.perf_counter(), sifre_hash))
        return gercek_dogrula(sifre_hash, sifre)

    monkeypatch.setattr(guvenlik_modulu, "sifre_dogrula", sayan)

    sureler: dict[str, list[float]] = {"bilinen": [], "bilinmeyen": []}
    for eposta, etiket in (
        (bilinen_eposta, "bilinen"),
        ("yok@kutyai.local", "bilinmeyen"),
    ):
        for _ in range(5):
            baslangic = time.perf_counter()
            yanit = await istemci.post(
                "/api/v1/kimlik/sifre-sifirlama-iste", json={"eposta": eposta}
            )
            sureler[etiket].append((time.perf_counter() - baslangic) * 1000)
            assert yanit.status_code == 200
            assert yanit.json()["mesaj"] == (
                "E-posta adresiniz kayıtlıysa parola sıfırlama bağlantısı gönderildi."
            )

    print(
        "sifre-sifirlama-iste zamanlama (ms): "
        f"bilinen={sorted(round(s, 1) for s in sureler['bilinen'])} "
        f"bilinmeyen={sorted(round(s, 1) for s in sureler['bilinmeyen'])}"
    )

    # Sabit maliyet: iki durumda da istek basina tam olarak bir argon2 dogrulamasi.
    assert len(cagrilar) == 10
    assert len({ozet for _, ozet in cagrilar}) == 1


async def test_yonetici_kendi_hesabini_kilitleyemez(istemci, yardimci):
    yonetici = await yardimci.yonetici(eposta="kilit@kutyai.local")
    basliklar = yardimci.basliklar(yonetici)

    rol = await istemci.patch(
        f"/api/v1/kullanicilar/{yonetici.id}",
        json={"rol": "izleyici"},
        headers=basliklar,
    )
    assert rol.status_code == 409
    assert rol.json()["hata"]["kod"] == "gecersiz_gecis"

    durum = await istemci.patch(
        f"/api/v1/kullanicilar/{yonetici.id}",
        json={"durum": "pasif"},
        headers=basliklar,
    )
    assert durum.status_code == 409
    assert durum.json()["hata"]["kod"] == "gecersiz_gecis"

    sil = await istemci.delete(
        f"/api/v1/kullanicilar/{yonetici.id}", headers=basliklar
    )
    assert sil.status_code == 409
    assert sil.json()["hata"]["kod"] == "gecersiz_gecis"

    # Ayni degerleri yeniden gondermek ya da ad degistirmek serbest.
    ayni = await istemci.patch(
        f"/api/v1/kullanicilar/{yonetici.id}",
        json={"rol": "yonetici", "durum": "aktif"},
        headers=basliklar,
    )
    assert ayni.status_code == 200
    ad = await istemci.patch(
        f"/api/v1/kullanicilar/{yonetici.id}",
        json={"ad_soyad": "Kilitli Yönetici"},
        headers=basliklar,
    )
    assert ad.status_code == 200
    assert ad.json()["ad_soyad"] == "Kilitli Yönetici"
    assert (await istemci.get("/api/v1/kullanicilar", headers=basliklar)).status_code == 200

    async with oturum_fabrikasi()() as oturum:
        satir = await oturum.get(Kullanici, yonetici.id)
        assert satir.rol == Rol.yonetici
        assert satir.durum == KullaniciDurumu.aktif


async def test_gelistirme_baglantisi_uretimde_donmez(istemci, yardimci, monkeypatch):
    monkeypatch.setattr(ayarlar, "ortam", "uretim")
    assert ayarlar.uretim_mi is True

    kayit = await _kayit(istemci, "uretim@kutyai.local")
    assert kayit.status_code == 201
    assert "gelistirme_baglantisi" not in kayit.json()

    await yardimci.kullanici_ekle(eposta="uretim.sifirla@kutyai.local")
    istek = await istemci.post(
        "/api/v1/kimlik/sifre-sifirlama-iste",
        json={"eposta": "uretim.sifirla@kutyai.local"},
    )
    assert istek.status_code == 200
    assert "gelistirme_baglantisi" not in istek.json()

    async with oturum_fabrikasi()() as oturum:
        # Baglanti hicbir kosulda yanitta ya da `ayar` tablosunda olmamali.
        assert await ayar_oku(oturum, "son_dogrulama_baglantisi") is None
        assert await ayar_oku(oturum, "son_sifirlama_baglantisi") is None
        # Akis bozulmuyor: sifirlama jetonu yine uretilir (posta ile iletilir).
        adet = (
            await oturum.execute(
                sa.select(sa.func.count())
                .select_from(DogrulamaJetonu)
                .where(DogrulamaJetonu.tur == JetonTuru.sifre_sifirlama)
            )
        ).scalar_one()
        assert adet == 1


async def test_giris_ayni_maliyetli_dogrulama(istemci, yardimci, monkeypatch):
    from arkauc.app.cekirdek import guvenlik as guvenlik_modulu

    bilinen_eposta = "giris.zamanlama@kutyai.local"
    await yardimci.kullanici_ekle(eposta=bilinen_eposta)

    gercek_dogrula = guvenlik_modulu.sifre_dogrula
    cagrilar: list[str] = []

    def sayan(sifre_hash: str, sifre: str):
        cagrilar.append(sifre_hash)
        return gercek_dogrula(sifre_hash, sifre)

    monkeypatch.setattr(guvenlik_modulu, "sifre_dogrula", sayan)

    sureler: dict[str, list[float]] = {"bilinen": [], "bilinmeyen": []}
    for eposta, etiket in (
        (bilinen_eposta, "bilinen"),
        ("yok@kutyai.local", "bilinmeyen"),
    ):
        for _ in range(3):
            baslangic = time.perf_counter()
            yanit = await istemci.post(
                "/api/v1/kimlik/giris",
                json={"eposta": eposta, "parola": "YanlisParola!"},
            )
            sureler[etiket].append((time.perf_counter() - baslangic) * 1000)
            assert yanit.status_code == 401
            assert yanit.json()["hata"]["kod"] == "gecersiz_kimlik_bilgisi"

    print(
        "kimlik/giris zamanlama (ms): "
        f"bilinen={sorted(round(s, 1) for s in sureler['bilinen'])} "
        f"bilinmeyen={sorted(round(s, 1) for s in sureler['bilinmeyen'])}"
    )

    # Sabit maliyet: iki durumda da istek basina tam olarak bir argon2 dogrulamasi.
    assert len(cagrilar) == 6


