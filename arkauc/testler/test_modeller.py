"""Model katalogu uclari testleri: /modeller, /bdm, /saglayicilar (spec §7.3)."""

from __future__ import annotations

from bdm_veritabani.modeller import Bdm, BdmDurumu, Rol
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
    olusan = await _bdm_olustur(istemci, yardimci, operator)

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
