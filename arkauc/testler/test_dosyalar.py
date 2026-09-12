"""Dosya uçları ve servisi — spec §3 kabul testleri.

Kapsam: gerçek multipart yükleme, MIME/boyut reddi, metin çıkarımı (PDF
opsiyonel), KVKK maskeleme, indirme başlıkları, silme, listeleme/sayfalama,
bağlam metni ve organizasyon izolasyonu.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import quote

import pytest

from arkauc.app.cekirdek.hatalar import Bulunamadi
from arkauc.app.servisler import dosya as dosya_servisi
from bdm_veritabani.modeller import Dosya, Organizasyon, Rol
from bdm_veritabani.oturum import oturum_fabrikasi
from bdm_veritabani.tohum import varsayilan_organizasyon

UC = "/api/v1/dosyalar"


@pytest.fixture(autouse=True)
def dosya_koku(tmp_path, monkeypatch):
    """Yuklemeleri depo dışına (geçici dizine) yönlendirir."""
    from arkauc.app.cekirdek.ayarlar import ayarlar

    monkeypatch.setattr(ayarlar, "dosya_dizini", tmp_path.as_posix())
    return tmp_path


def _pdf_olustur(metin: str) -> bytes:
    """İçinde düz metin taşıyan geçerli, küçük bir PDF üretir."""
    akis = f"BT /F1 24 Tf 72 720 Td ({metin}) Tj ET".encode("latin-1")
    nesneler = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R"
        b" /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(akis)).encode("ascii") + b" >>\nstream\n" + akis + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    govde = bytearray(b"%PDF-1.4\n")
    konumlar: list[int] = []
    for sira, nesne in enumerate(nesneler, start=1):
        konumlar.append(len(govde))
        govde += f"{sira} 0 obj\n".encode("ascii") + nesne + b"\nendobj\n"
    xref = len(govde)
    govde += f"xref\n0 {len(nesneler) + 1}\n".encode("ascii")
    govde += b"0000000000 65535 f \n"
    for konum in konumlar:
        govde += f"{konum:010d} 00000 n \n".encode("ascii")
    govde += (
        f"trailer\n<< /Size {len(nesneler) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    ).encode("ascii")
    return bytes(govde)


async def _yukle(
    istemci,
    basliklar: dict[str, str],
    *,
    ad: str = "not.txt",
    icerik: bytes = b"merhaba",
    mime: str = "text/plain",
):
    return await istemci.post(
        UC, headers=basliklar, files={"dosya": (ad, icerik, mime)}
    )


def _hata_kodu(yanit) -> str:
    return yanit.json()["hata"]["kod"]


async def _varsayilan_org(oturum) -> Organizasyon:
    return await varsayilan_organizasyon(oturum)


# --------------------------------------------------------------------------
# Yükleme, meta, metin çıkarımı, maskeleme
# --------------------------------------------------------------------------


async def test_yukleme_meta_disk_ve_maskeleme(istemci, yardimci, dosya_koku):
    yonetici = await yardimci.yonetici()
    icerik = "Müşteri e-postası: ayse.yilmaz@example.com\nRapor gövdesi.".encode("utf-8")

    yanit = await _yukle(
        istemci, yardimci.basliklar(yonetici), ad="rapor.txt", icerik=icerik
    )
    assert yanit.status_code == 201, yanit.text
    govde = yanit.json()
    assert govde["ad"] == "rapor.txt"
    assert govde["mime"] == "text/plain"
    assert govde["boyut"] == len(icerik)
    assert govde["sha256"] == hashlib.sha256(icerik).hexdigest()
    assert govde["kullanici_id"] == yonetici.id
    assert govde["metin_uzunluk"] == len(govde["metin"])
    # KVKK: çıkarılan metin maskelenmiş saklanır.
    assert "ayse.yilmaz@example.com" not in govde["metin"]
    assert "[MASKELENDI:eposta]" in govde["metin"]
    assert "Rapor gövdesi." in govde["metin"]

    # Disk yerleşimi: <kök>/<org_slug>/<hex32>, içerik birebir.
    dosyalar = [yol for yol in dosya_koku.rglob("*") if yol.is_file()]
    assert len(dosyalar) == 1
    assert dosyalar[0].parent.name == "varsayilan"
    assert len(dosyalar[0].name) == 32
    assert dosyalar[0].read_bytes() == icerik

    # Meta ucu aynı kaydı ve maskeli metni döndürür.
    detay = await istemci.get(f"{UC}/{govde['id']}", headers=yardimci.basliklar(yonetici))
    assert detay.status_code == 200
    assert detay.json()["sha256"] == govde["sha256"]
    assert "[MASKELENDI:eposta]" in detay.json()["metin"]


async def test_metin_cikarimi_utf8_bozuk_baytlarda_cokmez(istemci, yardimci, dosya_koku):
    yonetici = await yardimci.yonetici()
    icerik = b"gecerli \xff\xfe bozuk bayt"
    yanit = await _yukle(
        istemci, yardimci.basliklar(yonetici), ad="kirli.txt", icerik=icerik
    )
    assert yanit.status_code == 201
    metin = yanit.json()["metin"]
    assert metin.startswith("gecerli")
    assert "\ufffd" in metin  # errors="replace"


async def test_pdf_metin_cikarimi_opsiyonel(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    icerik = _pdf_olustur("KutyAI-PDF-Metni")
    yanit = await _yukle(
        istemci, yardimci.basliklar(yonetici), ad="belge.pdf", icerik=icerik, mime="application/pdf"
    )
    assert yanit.status_code == 201, yanit.text
    dosya_id = yanit.json()["id"]

    async with oturum_fabrikasi()() as oturum:
        kayit = await oturum.get(Dosya, dosya_id)
        assert kayit is not None
        metin, gerekce = await dosya_servisi.metin_cikar(kayit)

    if dosya_servisi._pdf_okuyucu() is None:
        # pypdf kurulu değil: uydurma metin yok, gerekçe döner.
        assert metin == ""
        assert gerekce == "dosya_metni_cikarilamadi"
        assert yanit.json()["metin"] == ""
        assert yanit.json()["metin_uzunluk"] == 0
    else:
        assert "KutyAI-PDF-Metni" in metin
        assert gerekce is None
        assert "KutyAI-PDF-Metni" in yanit.json()["metin"]


async def test_metin_cikarilamayan_tur_bos_metin_dondurur(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    # 1x1 saydam PNG.
    png = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
        "0000000a49444154789c6360000002000100ffff03000006000557bfabd4000000"
        "0049454e44ae426082"
    )
    yanit = await _yukle(
        istemci, yardimci.basliklar(yonetici), ad="nokta.png", icerik=png, mime="image/png"
    )
    assert yanit.status_code == 201
    assert yanit.json()["mime"] == "image/png"
    assert yanit.json()["metin"] == ""


# --------------------------------------------------------------------------
# Tür ve boyut reddi
# --------------------------------------------------------------------------


async def test_desteklenmeyen_tur_400(istemci, yardimci, dosya_koku):
    yonetici = await yardimci.yonetici()
    yanit = await _yukle(
        istemci,
        yardimci.basliklar(yonetici),
        ad="kotu.exe",
        icerik=b"MZ\x90\x00",
        mime="application/x-msdownload",
    )
    assert yanit.status_code == 400
    assert _hata_kodu(yanit) == "dosya_tur_desteklenmiyor"
    assert [yol for yol in dosya_koku.rglob("*") if yol.is_file()] == []


async def test_hata_mesaji_accept_language_ile_cevrilir(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    basliklar = {**yardimci.basliklar(yonetici), "Accept-Language": "en"}
    yanit = await _yukle(
        istemci,
        basliklar,
        ad="kotu.exe",
        icerik=b"MZ",
        mime="application/x-msdownload",
    )
    assert yanit.status_code == 400
    assert _hata_kodu(yanit) == "dosya_tur_desteklenmiyor"
    assert yanit.json()["hata"]["mesaj"] == "This file type is not supported."


async def test_octet_stream_uzantidan_cozulur_ve_bilinmeyen_uzanti_reddedilir(
    istemci, yardimci
):
    yonetici = await yardimci.yonetici()
    csv = "ad,soyad\nAyşe,Yılmaz\n".encode("utf-8")

    yanit = await _yukle(
        istemci,
        yardimci.basliklar(yonetici),
        ad="kayitlar.csv",
        icerik=csv,
        mime="application/octet-stream",
    )
    assert yanit.status_code == 201, yanit.text
    assert yanit.json()["mime"] == "text/csv"
    assert yanit.json()["metin"].startswith("ad,soyad")

    bilinmeyen = await _yukle(
        istemci,
        yardimci.basliklar(yonetici),
        ad="veri.xyz",
        icerik=b"???",
        mime="application/octet-stream",
    )
    assert bilinmeyen.status_code == 400
    assert _hata_kodu(bilinmeyen) == "dosya_tur_desteklenmiyor"


async def test_boyut_asimi_413_ve_diske_yazmaz(istemci, yardimci, dosya_koku, monkeypatch):
    from arkauc.app.cekirdek.ayarlar import ayarlar

    monkeypatch.setattr(ayarlar, "dosya_maks_mb", 1)
    yonetici = await yardimci.yonetici()
    icerik = b"x" * (1024 * 1024 + 1)

    yanit = await _yukle(istemci, yardimci.basliklar(yonetici), ad="buyuk.txt", icerik=icerik)
    assert yanit.status_code == 413
    assert _hata_kodu(yanit) == "dosya_cok_buyuk"
    assert yanit.json()["hata"]["ayrinti"]["sinir_mb"] == 1

    # Ne diskte ne veritabanında iz kalır.
    assert [yol for yol in dosya_koku.rglob("*") if yol.is_file()] == []
    liste = await istemci.get(UC, headers=yardimci.basliklar(yonetici))
    assert liste.json()["toplam"] == 0


async def test_sinir_altindaki_dosya_kabul_edilir(istemci, yardimci, monkeypatch):
    from arkauc.app.cekirdek.ayarlar import ayarlar

    monkeypatch.setattr(ayarlar, "dosya_maks_mb", 1)
    yonetici = await yardimci.yonetici()
    yanit = await _yukle(
        istemci, yardimci.basliklar(yonetici), icerik=b"y" * 1024
    )
    assert yanit.status_code == 201
    assert yanit.json()["boyut"] == 1024


# --------------------------------------------------------------------------
# İndirme, silme, listeleme
# --------------------------------------------------------------------------


async def test_indirme_icerik_ve_basliklar(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    ad = "rapor çıktısı.txt"
    icerik = "içerik ÇĞÜ".encode("utf-8")
    yukle = await _yukle(istemci, yardimci.basliklar(yonetici), ad=ad, icerik=icerik)
    dosya_id = yukle.json()["id"]

    yanit = await istemci.get(f"{UC}/{dosya_id}/icerik", headers=yardimci.basliklar(yonetici))
    assert yanit.status_code == 200
    assert yanit.content == icerik
    assert yanit.headers["content-type"].startswith("text/plain")

    serlik = yanit.headers["content-disposition"]
    assert serlik.startswith("attachment")
    assert "filename*=UTF-8''" in serlik
    assert quote(ad, safe="") in serlik


async def test_silme_204_disk_ve_kayit_temizlenir(istemci, yardimci, dosya_koku):
    yonetici = await yardimci.yonetici()
    yukle = await _yukle(istemci, yardimci.basliklar(yonetici), ad="silinecek.txt")
    dosya_id = yukle.json()["id"]
    assert len([y for y in dosya_koku.rglob("*") if y.is_file()]) == 1

    sil = await istemci.delete(f"{UC}/{dosya_id}", headers=yardimci.basliklar(yonetici))
    assert sil.status_code == 204
    assert sil.content == b""

    assert (
        await istemci.get(f"{UC}/{dosya_id}", headers=yardimci.basliklar(yonetici))
    ).status_code == 404
    assert [yol for yol in dosya_koku.rglob("*") if yol.is_file()] == []

    tekrar = await istemci.delete(f"{UC}/{dosya_id}", headers=yardimci.basliklar(yonetici))
    assert tekrar.status_code == 404
    assert _hata_kodu(tekrar) == "bulunamadi"


async def test_listeleme_sayfalama_ve_arama(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    basliklar = yardimci.basliklar(yonetici)
    for ad in ("alfa.txt", "beta.txt", "gama.txt"):
        assert (await _yukle(istemci, basliklar, ad=ad)).status_code == 201

    liste = (await istemci.get(UC, headers=basliklar)).json()
    assert liste["toplam"] == 3
    assert liste["sayfa"] == 1 and liste["boyut"] == 25
    assert [k["ad"] for k in liste["kayitlar"]] == ["gama.txt", "beta.txt", "alfa.txt"]

    arama = (await istemci.get(f"{UC}?arama=BETA", headers=basliklar)).json()
    assert arama["toplam"] == 1
    assert arama["kayitlar"][0]["ad"] == "beta.txt"

    ikinci = (await istemci.get(f"{UC}?sayfa=2&boyut=2", headers=basliklar)).json()
    assert ikinci["toplam"] == 3
    assert [k["ad"] for k in ikinci["kayitlar"]] == ["alfa.txt"]

    gecersiz = await istemci.get(f"{UC}?boyut=0", headers=basliklar)
    assert gecersiz.status_code == 400
    assert _hata_kodu(gecersiz) == "dogrulama_hatasi"


async def test_denetim_izi_yukleme_ve_silmeyi_kaydeder(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    basliklar = yardimci.basliklar(yonetici)
    dosya_id = (await _yukle(istemci, basliklar, ad="izlenen.txt")).json()["id"]
    assert (await istemci.delete(f"{UC}/{dosya_id}", headers=basliklar)).status_code == 204

    kayitlar = (
        await istemci.get("/api/v1/islem-kayitlari?eylem=dosya.yuklendi", headers=basliklar)
    ).json()["kayitlar"]
    assert len(kayitlar) == 1
    assert kayitlar[0]["hedef_tur"] == "dosya"
    assert kayitlar[0]["hedef_id"] == str(dosya_id)
    assert kayitlar[0]["ayrinti"]["ad"] == "izlenen.txt"

    silinen = (
        await istemci.get("/api/v1/islem-kayitlari?eylem=dosya.silindi", headers=basliklar)
    ).json()["kayitlar"]
    assert len(silinen) == 1
    assert silinen[0]["hedef_id"] == str(dosya_id)


# --------------------------------------------------------------------------
# Organizasyon izolasyonu ve yetki matrisi
# --------------------------------------------------------------------------


async def test_org_izolasyonu_ayni_kullanici_farkli_organizasyon(
    istemci, yardimci, dosya_koku
):
    sahip = await yardimci.yonetici()
    alfa = await yardimci.organizasyon("Alfa", sahibi=sahip)
    beta = await yardimci.organizasyon("Beta", sahibi=sahip)

    yukle = await _yukle(istemci, yardimci.org_basliklari(sahip, alfa), ad="gizli.txt")
    assert yukle.status_code == 201
    dosya_id = yukle.json()["id"]

    beta_basliklar = yardimci.org_basliklari(sahip, beta)
    assert (await istemci.get(f"{UC}/{dosya_id}", headers=beta_basliklar)).status_code == 404
    assert (
        await istemci.get(f"{UC}/{dosya_id}/icerik", headers=beta_basliklar)
    ).status_code == 404
    assert (await istemci.delete(f"{UC}/{dosya_id}", headers=beta_basliklar)).status_code == 404
    assert (await istemci.get(UC, headers=beta_basliklar)).json()["toplam"] == 0

    alfa_basliklar = yardimci.org_basliklari(sahip, alfa)
    assert (await istemci.get(f"{UC}/{dosya_id}", headers=alfa_basliklar)).status_code == 200
    assert any(
        yol.parent.name == alfa.slug for yol in dosya_koku.rglob("*") if yol.is_file()
    )


async def test_org_izolasyonu_baska_kullanicinin_dosyasi(istemci, yardimci):
    sahip = await yardimci.yonetici()
    organizasyon = await yardimci.organizasyon("Gizli", sahibi=sahip)
    yukle = await _yukle(istemci, yardimci.org_basliklari(sahip, organizasyon))
    dosya_id = yukle.json()["id"]

    yabanci = await yardimci.yonetici()
    # Üye olmadığı organizasyonu başlıkla istemek yetki hatası verir.
    assert (
        await istemci.get(f"{UC}/{dosya_id}", headers=yardimci.org_basliklari(yabanci, organizasyon))
    ).status_code == 403
    # Kendi (varsayılan) organizasyonunda ise kayıt görünmez.
    assert (await istemci.get(f"{UC}/{dosya_id}", headers=yardimci.basliklar(yabanci))).status_code == 404


async def test_yetki_matrisi_anonim_401_son_kullanici_403(istemci, yardimci):
    anonim_post = await _yukle(istemci, {})
    assert anonim_post.status_code == 401
    assert _hata_kodu(anonim_post) == "kimlik_gerekli"
    assert (await istemci.get(UC)).status_code == 401

    son_kullanici = await yardimci.kullanici_ekle(rol=Rol.son_kullanici)
    basliklar = yardimci.basliklar(son_kullanici)

    listeleme = await istemci.get(UC, headers=basliklar)
    assert listeleme.status_code == 403
    assert _hata_kodu(listeleme) == "yetki_yok"

    yukleme = await _yukle(istemci, basliklar)
    assert yukleme.status_code == 403
    assert _hata_kodu(yukleme) == "yetki_yok"

    indirme = await istemci.get(f"{UC}/1/icerik", headers=basliklar)
    assert indirme.status_code == 403

    silme = await istemci.delete(f"{UC}/1", headers=basliklar)
    assert silme.status_code == 403


async def test_izleyici_uyelik_okuyabilir_yazabilir(istemci, yardimci):
    """`izleyici` personel sayılır (PERSONEL_UYELIK_ROLLERI) ve yükleme yapabilir."""
    izleyici = await yardimci.kullanici_ekle(rol=Rol.izleyici)
    basliklar = yardimci.basliklar(izleyici)
    assert (await _yukle(istemci, basliklar, ad="izleyici.txt")).status_code == 201
    assert (await istemci.get(UC, headers=basliklar)).json()["toplam"] == 1


# --------------------------------------------------------------------------
# Bağlam metni (sohbet eki)
# --------------------------------------------------------------------------


async def test_baglam_metni_birlesir_kesilir_ve_org_denetler(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    basliklar = yardimci.basliklar(yonetici)
    bir = (await _yukle(istemci, basliklar, ad="bir.txt", icerik=b"Birinci icerik")).json()
    iki = (await _yukle(istemci, basliklar, ad="iki.txt", icerik=b"Ikinci icerik")).json()

    async with oturum_fabrikasi()() as oturum:
        org = await _varsayilan_org(oturum)
        metin = await dosya_servisi.baglam_metni(
            oturum, org.id, [bir["id"], iki["id"]], sinir=10000
        )
        assert metin == (
            f"--- bir.txt ---\nBirinci icerik\n--- iki.txt ---\nIkinci icerik"
        )

        kisa = await dosya_servisi.baglam_metni(
            oturum, org.id, [bir["id"], iki["id"]], sinir=12
        )
        assert kisa == "--- bir.txt "[:12]
        assert len(kisa) == 12

        # Metni çıkarılamamış (boş) dosyalar atlanır.
        bos = (
            await _yukle(
                istemci, basliklar, ad="bos.png", icerik=b"\x89PNG\r\n\x1a\n", mime="image/png"
            )
        ).json()
        sadece_bos = await dosya_servisi.baglam_metni(oturum, org.id, [bos["id"]], sinir=100)
        assert sadece_bos == ""

        # Organizasyon dışı id → 404.
        yabanci = await yardimci.organizasyon("Yabanci")
        with pytest.raises(Bulunamadi):
            await dosya_servisi.baglam_metni(oturum, yabanci.id, [bir["id"]], sinir=100)


async def test_icerik_oku_ham_baytlari_dondurur(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    icerik = b"\x00\x01\x02 ham bayt"
    dosya_id = (
        await _yukle(
            istemci,
            yardimci.basliklar(yonetici),
            ad="ham.bin.txt",
            icerik=icerik,
        )
    ).json()["id"]

    async with oturum_fabrikasi()() as oturum:
        org = await _varsayilan_org(oturum)
        kayit, baytlar = await dosya_servisi.icerik_oku(oturum, org.id, dosya_id)
        assert isinstance(kayit, Dosya)
        assert baytlar == icerik

        yabanci = await yardimci.organizasyon("Baska")
        with pytest.raises(Bulunamadi):
            await dosya_servisi.icerik_oku(oturum, yabanci.id, dosya_id)


async def test_dosya_getir_baska_org_icin_404(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    dosya_id = (await _yukle(istemci, yardimci.basliklar(yonetici))).json()["id"]
    diger = await yardimci.organizasyon("Digeri")

    async with oturum_fabrikasi()() as oturum:
        with pytest.raises(Bulunamadi):
            await dosya_servisi.dosya_getir(oturum, diger.id, dosya_id)
