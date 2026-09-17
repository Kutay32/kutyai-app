"""Model katalogu uclari testleri: /modeller, /bdm, /saglayicilar (spec §7.3)."""

from __future__ import annotations

import sqlalchemy as sa

from arkauc.app.cekirdek import guvenlik
from bdm_veritabani.modeller import Bdm, BdmDurumu, IslemKaydi, Rol, UyelikRolu
from bdm_veritabani.oturum import oturum_fabrikasi

BDM_GOVDESI: dict[str, object] = {
    "gorunen_ad": "Test GPT",
    "aciklama": "Deneme modeli",
    "saglayici": "openai",
    "temel_url": "https://api.openai.com/v1",
    "upstream_model": "gpt-4o-mini",
    "api_anahtari": "sk-test-1234567890abcdef",
    "baglam_penceresi": 128000,
    "maks_cikti": 4096,
    "sicaklik_varsayilan": 0.7,
    "sistem_istemi": "Kısa ve net yanıt ver.",
    "yerel_mi": False,
}


async def _bdm_olustur(istemci, yardimci, kullanici, **degisiklik) -> dict:
    yanit = await istemci.post(
        "/api/v1/bdm",
        json={**BDM_GOVDESI, **degisiklik},
        headers=yardimci.basliklar(kullanici),
    )
    assert yanit.status_code == 201, yanit.text
    return yanit.json()


async def _durum_ayarla(bdm_id: int, durum: BdmDurumu) -> None:
    async with oturum_fabrikasi()() as oturum:
        bdm = await oturum.get(Bdm, bdm_id)
        assert bdm is not None
        bdm.durum = durum
        await oturum.commit()


# --- yetki -----------------------------------------------------------------


async def test_bdm_kimlik_istemez(istemci):
    yanit = await istemci.get("/api/v1/bdm")
    assert yanit.status_code == 401
    assert yanit.json()["hata"]["kod"] == "kimlik_gerekli"


async def test_bdm_son_kullaniciya_kapali(istemci, yardimci):
    kullanici = await yardimci.kullanici_ekle(rol=Rol.son_kullanici)
    yanit = await istemci.get("/api/v1/bdm", headers=yardimci.basliklar(kullanici))
    assert yanit.status_code == 403
    assert yanit.json()["hata"]["kod"] == "yetki_yok"


async def test_modeller_kimlik_istemez(istemci):
    yanit = await istemci.get("/api/v1/modeller")
    assert yanit.status_code == 401
    assert yanit.json()["hata"]["kod"] == "kimlik_gerekli"


async def test_saglayicilar_kimlik_gerekmez(istemci):
    yanit = await istemci.get("/api/v1/saglayicilar")
    assert yanit.status_code == 200
    saglayicilar = {kayit["ad"] for kayit in yanit.json()}
    assert {"openai", "ollama", "vllm", "ozel"} <= saglayicilar
    vllm = next(k for k in yanit.json() if k["ad"] == "vllm")
    assert vllm["gpu_gerekir"] is True and vllm["varsayilan_port"] == 8000


# --- BDM CRUD --------------------------------------------------------------


async def test_yonetici_bdm_olusturur_listeler_gunceller_siler(istemci, yardimci):
    yonetici = await yardimci.yonetici()

    olusan = await _bdm_olustur(istemci, yardimci, yonetici)
    assert olusan["slug"] == "test-gpt"
    assert olusan["durum"] == "taslak"
    assert olusan["saglayici"] == "openai"
    assert olusan["baglam_penceresi"] == 128000

    liste = await istemci.get("/api/v1/bdm", headers=yardimci.basliklar(yonetici))
    assert liste.status_code == 200
    assert [kayit["id"] for kayit in liste.json()] == [olusan["id"]]

    guncel = await istemci.patch(
        f"/api/v1/bdm/{olusan['id']}",
        json={"gorunen_ad": "Test GPT 4o", "maks_cikti": 8192},
        headers=yardimci.basliklar(yonetici),
    )
    assert guncel.status_code == 200
    assert guncel.json()["gorunen_ad"] == "Test GPT 4o"
    assert guncel.json()["maks_cikti"] == 8192
    assert guncel.json()["upstream_model"] == "gpt-4o-mini"

    silme = await istemci.delete(
        f"/api/v1/bdm/{olusan['id']}", headers=yardimci.basliklar(yonetici)
    )
    assert silme.status_code == 204
    assert silme.content == b""

    bos = await istemci.get("/api/v1/bdm", headers=yardimci.basliklar(yonetici))
    assert bos.json() == []


async def test_bdm_listesi_arama_ile_suzulur(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    await _bdm_olustur(istemci, yardimci, yonetici, gorunen_ad="Yerel Llama")
    await _bdm_olustur(
        istemci,
        yardimci,
        yonetici,
        gorunen_ad="Bulut GPT",
        saglayici="ollama",
        temel_url="http://localhost:11434/v1",
        upstream_model="llama3",
    )

    yanit = await istemci.get(
        "/api/v1/bdm", params={"arama": "llama"}, headers=yardimci.basliklar(yonetici)
    )
    assert yanit.status_code == 200
    assert [kayit["gorunen_ad"] for kayit in yanit.json()] == ["Yerel Llama"]


async def test_upstream_anahtari_yanitta_maskeli(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    olusan = await _bdm_olustur(istemci, yardimci, yonetici)

    assert olusan["api_anahtari_maskeli"] == "sk-t***cdef"
    assert "sk-test-1234567890abcdef" not in str(olusan)

    liste = await istemci.get("/api/v1/bdm", headers=yardimci.basliklar(yonetici))
    kayit = liste.json()[0]
    assert kayit["api_anahtari_maskeli"] == "sk-t***cdef"
    assert "sk-test-1234567890abcdef" not in liste.text


async def test_ayni_slug_409_cakisma(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    await _bdm_olustur(istemci, yardimci, yonetici, slug="sabit-slug")

    yanit = await istemci.post(
        "/api/v1/bdm",
        json={**BDM_GOVDESI, "slug": "sabit-slug"},
        headers=yardimci.basliklar(yonetici),
    )
    assert yanit.status_code == 409
    assert yanit.json()["hata"]["kod"] == "cakisma"


async def test_bilinmeyen_bdm_404(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    basliklar = yardimci.basliklar(yonetici)

    guncelle = await istemci.patch("/api/v1/bdm/9999", json={"aciklama": "yok"}, headers=basliklar)
    assert guncelle.status_code == 404
    assert guncelle.json()["hata"]["kod"] == "bulunamadi"

    silme = await istemci.delete("/api/v1/bdm/9999", headers=basliklar)
    assert silme.status_code == 404
    assert silme.json()["hata"]["kod"] == "bulunamadi"


async def test_operator_silemez_ve_kopyalayamaz(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    operator = await yardimci.kullanici_ekle(rol=Rol.operator)
    olusan = await _bdm_olustur(istemci, yardimci, yonetici)

    silme = await istemci.delete(
        f"/api/v1/bdm/{olusan['id']}", headers=yardimci.basliklar(operator)
    )
    assert silme.status_code == 403
    assert silme.json()["hata"]["kod"] == "yetki_yok"

    kopya = await istemci.post(
        f"/api/v1/bdm/{olusan['id']}/kopyala",
        json={"yeni_ad": "Kopya Model"},
        headers=yardimci.basliklar(operator),
    )
    assert kopya.status_code == 403

    yonetici_silme = await istemci.delete(
        f"/api/v1/bdm/{olusan['id']}", headers=yardimci.basliklar(yonetici)
    )
    assert yonetici_silme.status_code == 204


async def test_yonetici_bdm_kopyalar(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    kaynak = await _bdm_olustur(istemci, yardimci, yonetici)

    yanit = await istemci.post(
        f"/api/v1/bdm/{kaynak['id']}/kopyala",
        json={"yeni_ad": "Test GPT Kopya"},
        headers=yardimci.basliklar(yonetici),
    )
    assert yanit.status_code == 201, yanit.text
    kopya = yanit.json()
    assert kopya["id"] != kaynak["id"]
    assert kopya["slug"] == "test-gpt-kopya"
    assert kopya["durum"] == "taslak"
    assert kopya["api_anahtari_maskeli"] == kaynak["api_anahtari_maskeli"]


# --- saglayici adresi / upstream anahtari yetkisi (GUV-03) ------------------


async def test_operator_saglayici_alanlarini_degistiremez(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    operator = await yardimci.kullanici_ekle(rol=Rol.operator)
    olusan = await _bdm_olustur(istemci, yardimci, yonetici)

    for alan, deger in (
        ("temel_url", "http://127.0.0.1:9000/v1"),
        ("api_anahtari", "sk-casus-anahtar"),
        ("saglayici", "ollama"),
    ):
        yanit = await istemci.patch(
            f"/api/v1/bdm/{olusan['id']}",
            json={alan: deger},
            headers=yardimci.basliklar(operator),
        )
        assert yanit.status_code == 403, f"{alan}: {yanit.text}"
        hata = yanit.json()["hata"]
        assert hata["kod"] == "yetki_yok"
        assert hata["mesaj"] == (
            "Sağlayıcı adresi ve API anahtarını yalnız yönetici değiştirebilir."
        )

    liste = await istemci.get("/api/v1/bdm", headers=yardimci.basliklar(yonetici))
    kayit = liste.json()[0]
    assert kayit["temel_url"] == "https://api.openai.com/v1"
    assert kayit["saglayici"] == "openai"
    assert kayit["api_anahtari_maskeli"] == "sk-t***cdef"


async def test_operator_diger_alanlari_gunceller(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    operator = await yardimci.kullanici_ekle(rol=Rol.operator)
    olusan = await _bdm_olustur(istemci, yardimci, yonetici)

    yanit = await istemci.patch(
        f"/api/v1/bdm/{olusan['id']}",
        json={
            "aciklama": "Operatör güncelledi",
            "maks_cikti": 1024,
            "sicaklik_varsayilan": 0.2,
            "yetenekler": {"akis": True, "gorsel": True, "arac": False},
        },
        headers=yardimci.basliklar(operator),
    )
    assert yanit.status_code == 200, yanit.text
    assert yanit.json()["aciklama"] == "Operatör güncelledi"
    assert yanit.json()["maks_cikti"] == 1024
    assert yanit.json()["yetenekler"]["gorsel"] is True


async def test_yonetici_saglayici_adresini_degistirir(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    olusan = await _bdm_olustur(istemci, yardimci, yonetici)

    yanit = await istemci.patch(
        f"/api/v1/bdm/{olusan['id']}",
        json={"temel_url": "http://127.0.0.1:9000/v1/", "api_anahtari": "sk-yeni-anahtar-1234"},
        headers=yardimci.basliklar(yonetici),
    )
    assert yanit.status_code == 200, yanit.text
    assert yanit.json()["temel_url"] == "http://127.0.0.1:9000/v1"
    assert yanit.json()["api_anahtari_maskeli"] == "sk-y***1234"


async def test_operator_anahtar_veremeden_bdm_olusturur(istemci, yardimci):
    operator = await yardimci.kullanici_ekle(rol=Rol.operator)

    engelli = await istemci.post(
        "/api/v1/bdm",
        json={**BDM_GOVDESI, "api_anahtari": "sk-operator-anahtari"},
        headers=yardimci.basliklar(operator),
    )
    assert engelli.status_code == 403
    assert engelli.json()["hata"]["kod"] == "yetki_yok"
    assert engelli.json()["hata"]["mesaj"] == (
        "Sağlayıcı adresi ve API anahtarını yalnız yönetici değiştirebilir."
    )

    olusan = await _bdm_olustur(
        istemci,
        yardimci,
        operator,
        gorunen_ad="Operatör Yerel Model",
        saglayici="ollama",
        temel_url="http://localhost:11434/v1",
        api_anahtari="",
    )
    assert olusan["slug"] == "operator-yerel-model"
    assert olusan["api_anahtari_maskeli"] == ""


async def test_bdm_yasam_dongusu_denetim_izine_yazilir(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    olusan = await _bdm_olustur(istemci, yardimci, yonetici)
    basliklar = yardimci.basliklar(yonetici)

    await istemci.patch(
        f"/api/v1/bdm/{olusan['id']}", json={"aciklama": "iz"}, headers=basliklar
    )
    await istemci.delete(f"/api/v1/bdm/{olusan['id']}", headers=basliklar)

    async with oturum_fabrikasi()() as oturum:
        kayitlar = (
            await oturum.execute(
                sa.select(IslemKaydi.eylem, IslemKaydi.kullanici_id).where(
                    IslemKaydi.hedef_tur == "bdm"
                )
            )
        ).all()

    assert {(eylem, kullanici_id) for eylem, kullanici_id in kayitlar} == {
        ("bdm.olusturuldu", yonetici.id),
        ("bdm.guncellendi", yonetici.id),
        ("bdm.silindi", yonetici.id),
    }


async def test_calisan_bdm_silinemez(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    olusan = await _bdm_olustur(istemci, yardimci, yonetici)
    await _durum_ayarla(olusan["id"], BdmDurumu.calisiyor)

    yanit = await istemci.delete(
        f"/api/v1/bdm/{olusan['id']}", headers=yardimci.basliklar(yonetici)
    )
    assert yanit.status_code == 409
    assert yanit.json()["hata"]["kod"] == "gecersiz_gecis"

    await _durum_ayarla(olusan["id"], BdmDurumu.durdu)
    durdurulmus = await istemci.delete(
        f"/api/v1/bdm/{olusan['id']}", headers=yardimci.basliklar(yonetici)
    )
    assert durdurulmus.status_code == 204


# --- model katalogu --------------------------------------------------------


async def test_modeller_yalniz_hazir_ve_calisiyor_dondurur(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    basliklar = yardimci.basliklar(yonetici)

    hazir = await _bdm_olustur(istemci, yardimci, yonetici, gorunen_ad="Hazır Model")
    calisan = await _bdm_olustur(istemci, yardimci, yonetici, gorunen_ad="Çalışan Model")
    taslak = await _bdm_olustur(istemci, yardimci, yonetici, gorunen_ad="Taslak Model")
    await _durum_ayarla(hazir["id"], BdmDurumu.hazir)
    await _durum_ayarla(calisan["id"], BdmDurumu.calisiyor)
    await _durum_ayarla(taslak["id"], BdmDurumu.durdu)

    yanit = await istemci.get("/api/v1/modeller", headers=basliklar)
    assert yanit.status_code == 200
    kayitlar = {k["slug"]: k for k in yanit.json()}
    assert set(kayitlar) == {"hazir-model", "calisan-model"}
    assert kayitlar["hazir-model"]["durum"] == "hazir"
    assert "api_anahtari_maskeli" not in kayitlar["hazir-model"]


async def test_modeller_api_anahtari_izin_listesini_suzer(istemci, yardimci):
    yonetici = await yardimci.yonetici()
    izinli = await _bdm_olustur(istemci, yardimci, yonetici, gorunen_ad="İzinli Model")
    digeri = await _bdm_olustur(istemci, yardimci, yonetici, gorunen_ad="Diğer Model")
    await _durum_ayarla(izinli["id"], BdmDurumu.hazir)
    await _durum_ayarla(digeri["id"], BdmDurumu.calisiyor)

    _, tam = await yardimci.anahtar_ekle(izinli_modeller=["izinli-model"])
    anahtarli = await istemci.get(
        "/api/v1/modeller", headers=yardimci.anahtar_basliklari(tam)
    )
    assert anahtarli.status_code == 200
    assert [k["slug"] for k in anahtarli.json()] == ["izinli-model"]

    _, tam_id = await yardimci.anahtar_ekle(izinli_modeller=[str(digeri["id"])])
    kimlikle = await istemci.get(
        "/api/v1/modeller", headers=yardimci.anahtar_basliklari(tam_id)
    )
    assert [k["slug"] for k in kimlikle.json()] == ["diger-model"]

    _, sinirsiz = await yardimci.anahtar_ekle()
    tumu = await istemci.get(
        "/api/v1/modeller", headers=yardimci.anahtar_basliklari(sinirsiz)
    )
    assert {k["slug"] for k in tumu.json()} == {"izinli-model", "diger-model"}

    personel = await istemci.get("/api/v1/modeller", headers=yardimci.basliklar(yonetici))
    assert {k["slug"] for k in personel.json()} == {"izinli-model", "diger-model"}


# --- organizasyon izolasyonu ----------------------------------------------


async def test_bdm_olusturma_aktif_organizasyona_yazilir(istemci, yardimci):
    sahip = await yardimci.yonetici()
    alfa = await yardimci.organizasyon("Alfa", sahibi=sahip)
    beta = await yardimci.organizasyon("Beta", sahibi=sahip)

    yanit = await istemci.post(
        "/api/v1/bdm",
        json={**BDM_GOVDESI, "gorunen_ad": "Alfa Modeli"},
        headers=yardimci.org_basliklari(sahip, alfa),
    )
    assert yanit.status_code == 201, yanit.text

    async with oturum_fabrikasi()() as oturum:
        bdm = await oturum.get(Bdm, yanit.json()["id"])
        assert bdm is not None
        assert bdm.org_id == alfa.id
        denetim = (
            await oturum.execute(
                sa.select(IslemKaydi).where(IslemKaydi.eylem == "bdm.olusturuldu")
            )
        ).scalars().one()
        assert denetim.org_id == alfa.id

    alfa_liste = await istemci.get("/api/v1/bdm", headers=yardimci.org_basliklari(sahip, alfa))
    beta_liste = await istemci.get("/api/v1/bdm", headers=yardimci.org_basliklari(sahip, beta))
    assert [k["slug"] for k in alfa_liste.json()] == ["alfa-modeli"]
    assert beta_liste.json() == []


async def test_baska_organizasyonun_bdmsi_gorunmez_ve_degistirilemez(istemci, yardimci):
    sahip = await yardimci.yonetici()
    alfa = await yardimci.organizasyon("Alfa Kilit", sahibi=sahip)
    beta = await yardimci.organizasyon("Beta Kilit", sahibi=sahip)
    alfa_basliklar = yardimci.org_basliklari(sahip, alfa)
    beta_basliklar = yardimci.org_basliklari(sahip, beta)

    bdm = await _bdm_olustur(istemci, yardimci, sahip, gorunen_ad="Alfa Modeli")
    # Kurulum basligi olmadan varsayilan organizasyona yazilir; Alfa'ya tasiyalim.
    async with oturum_fabrikasi()() as oturum:
        kayit = await oturum.get(Bdm, bdm["id"])
        assert kayit is not None
        kayit.org_id = alfa.id
        await oturum.commit()

    assert (await istemci.get("/api/v1/bdm", headers=beta_basliklar)).json() == []
    guncelle = await istemci.patch(
        f"/api/v1/bdm/{bdm['id']}", json={"aciklama": "Beta değiştirdi"}, headers=beta_basliklar
    )
    assert guncelle.status_code == 404
    assert guncelle.json()["hata"]["kod"] == "bulunamadi"
    kopyala = await istemci.post(
        f"/api/v1/bdm/{bdm['id']}/kopyala",
        json={"yeni_ad": "Beta Kopya"},
        headers=beta_basliklar,
    )
    assert kopyala.status_code == 404
    sil = await istemci.delete(f"/api/v1/bdm/{bdm['id']}", headers=beta_basliklar)
    assert sil.status_code == 404
    assert (await istemci.get("/api/v1/modeller", headers=beta_basliklar)).json() == []

    assert [k["slug"] for k in (await istemci.get("/api/v1/bdm", headers=alfa_basliklar)).json()] == [
        "alfa-modeli"
    ]


async def test_modeller_aktif_organizasyonun_hazir_modellerini_dondurur(istemci, yardimci):
    sahip = await yardimci.yonetici()
    alfa = await yardimci.organizasyon("Alfa Katalog", sahibi=sahip)
    beta = await yardimci.organizasyon("Beta Katalog", sahibi=sahip)

    model_id = (await _bdm_olustur(istemci, yardimci, sahip, gorunen_ad="Alfa Hazır"))["id"]
    async with oturum_fabrikasi()() as oturum:
        kayit = await oturum.get(Bdm, model_id)
        assert kayit is not None
        kayit.org_id = alfa.id
        kayit.durum = BdmDurumu.hazir
        await oturum.commit()

    alfa_modeller = await istemci.get("/api/v1/modeller", headers=yardimci.org_basliklari(sahip, alfa))
    assert [k["slug"] for k in alfa_modeller.json()] == ["alfa-hazir"]
    beta_modeller = await istemci.get("/api/v1/modeller", headers=yardimci.org_basliklari(sahip, beta))
    assert beta_modeller.json() == []


async def test_askida_organizasyonun_api_anahtari_basligiyla_reddedilir(istemci, yardimci):
    """Askıya alınan organizasyon, başlıkla eşleşen API anahtarını da `403` ile keser."""
    sahip = await yardimci.yonetici()
    organizasyon = await yardimci.organizasyon("Askı Org", sahibi=sahip)
    basliklar = yardimci.org_basliklari(sahip, organizasyon)

    anahtar = await istemci.post(
        "/api/v1/api-anahtarlari",
        json={"ad": "Askı Anahtarı"},
        headers=basliklar,
    )
    assert anahtar.status_code == 201, anahtar.text
    anahtar_basliklari = {
        **yardimci.anahtar_basliklari(anahtar.json()["tam_anahtar"]),
        "X-Organizasyon": organizasyon.slug,
    }
    assert (await istemci.get("/api/v1/modeller", headers=anahtar_basliklari)).status_code == 200

    askiya = await istemci.patch(
        f"/api/v1/organizasyonlar/{organizasyon.id}",
        json={"durum": "askida"},
        headers=yardimci.basliklar(sahip),
    )
    assert askiya.status_code == 200, askiya.text

    baslikli = await istemci.get("/api/v1/modeller", headers=anahtar_basliklari)
    assert baslikli.status_code == 403, baslikli.text
    assert baslikli.json()["hata"]["kod"] == "yetki_yok"

    basliksiz = await istemci.get(
        "/api/v1/modeller",
        headers=yardimci.anahtar_basliklari(anahtar.json()["tam_anahtar"]),
    )
    assert basliksiz.status_code == 403

    # Jeton `org` claim'i de aynı kapıya takılır (varsayılan üyeliğe düşmez).
    jeton, _ = guvenlik.erisim_jetonu_uret(sahip.id, sahip.rol.value, organizasyon.id)
    claim = await istemci.get(
        "/api/v1/modeller", headers={"Authorization": f"Bearer {jeton}"}
    )
    assert claim.status_code == 403
    assert claim.json()["hata"]["kod"] == "yetki_yok"


async def test_uyelik_rolu_operator_olan_yonetici_saglayici_alanlarini_degistiremez(istemci, yardimci):
    """GUV-03 kararı üyelik rolünden verilir: global `yonetici` tek başına yetmez."""
    sahip = await yardimci.yonetici()
    organizasyon = await yardimci.organizasyon("Rol Org", sahibi=sahip)
    uye = await yardimci.yonetici()
    await yardimci.uye_yap(organizasyon, uye, UyelikRolu.operator)
    basliklar = yardimci.org_basliklari(uye, organizasyon)

    olusan = await istemci.post(
        "/api/v1/bdm",
        json={**BDM_GOVDESI, "gorunen_ad": "Rol Modeli"},
        headers=yardimci.org_basliklari(sahip, organizasyon),
    )
    assert olusan.status_code == 201, olusan.text
    bdm_id = olusan.json()["id"]
    for alan, deger in (
        ("temel_url", "http://127.0.0.1:9000/v1"),
        ("api_anahtari", "sk-operator-kacis"),
    ):
        yanit = await istemci.patch(
            f"/api/v1/bdm/{bdm_id}", json={alan: deger}, headers=basliklar
        )
        assert yanit.status_code == 403, f"{alan}: {yanit.text}"
        assert yanit.json()["hata"]["kod"] == "yetki_yok"

    anahtarla = await istemci.post(
        "/api/v1/bdm",
        json={**BDM_GOVDESI, "gorunen_ad": "Operatör Modeli", "api_anahtari": "sk-operator"},
        headers=basliklar,
    )
    assert anahtarla.status_code == 403

    # Korumasız alanlar operatör üyeliğinde serbest kalır.
    serbest = await istemci.patch(
        f"/api/v1/bdm/{bdm_id}", json={"aciklama": "Operatör"}, headers=basliklar
    )
    assert serbest.status_code == 200, serbest.text
