# modeller gözlem logu — 2026-09-12

## Kapsam
- API.md §8 (Model kataloğu: `/modeller`, `/saglayicilar`, `/bdm` CRUD + `/kopyala`), §1 (hata zarfı), §2 (`Bdm`, `BdmOzet` tipleri)
- spec §4.4 (`izinli_modeller`, `boş=tümü`), §4.5 (`bdm` tablosu), §7.3 (`arkauc/app/api/modeller.py`)
- Denetlenen birim: `arkauc/app/api/modeller.py` + hizmet katmanı `bdm_listesi/katalog.py`, `bdm_listesi/saglayicilar.py`
- Yöntem: canlı backend (`uvicorn arkauc.app.main:app --port 8102`, geçici SQLite) üzerinden HTTP. Ürün kodu değiştirilmedi.
- Fikstür: `kaynak/testler/betikler/modeller_*.py` betikleri; BDM durumları (`hazir`, `calisiyor`, `durdu`, `hata`, `taslak`) `durum` alanı uçlardan yazılamadığı için geçici veritabanında doğrudan `UPDATE bdm SET durum=...` ile kuruldu.

Ortam değişkenleri (tüm komutlarda):

````
KUTYAI_VERITABANI_URL=sqlite+aiosqlite:///E:/kutyai-app/kaynak/testler/gecici/modeller.db
KUTYAI_GIZLI_ANAHTAR=gozlem-gizli-anahtar
KUTYAI_SIFRELEME_ANAHTARI=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=
````

## Koşulan komutlar

### 1) `./.venv/Scripts/python.exe kaynak/testler/betikler/modeller_00_kur.py` (fikstür)
- Beklenen: kurulum `201`, 6 BDM oluşur, durumlar yazılır, API anahtarları üretilir.
- Gerçek çıktı (kırpıldı):

````
--- POST /kurulum
HTTP 201
{
  "yonetici": {
    "id": 1,
    "eposta": "admin@gozlem.example.com",
    "ad_soyad": "Gozlem Yonetici",
    "rol": "yonetici",
    "durum": "aktif",
    "eposta_dogrulandi": true,
    "olusturulma": "2026-09-12T19:42:16.512573+00:00",
    "son_giris": null
  },
  "bdm": {
    "id": 1,
    "slug": "gozlem-gpt",
    "gorunen_ad": "Gozlem GPT",
    "aciklama": "",
    "saglayici": "openai",
    "temel_url": "https://api.openai.com/v1",
    "upstream_model": "gpt-4o-mini",
    "api_anahtari_maskeli": "sk-c***7890",
    "baglam_penceresi": 128000,
    "maks_cikti": 4096,
    "sicaklik_varsayilan": 0.7,
    "sistem_istemi": "",
    "yetenekler": {
      "akis": true,
      "gorsel": false,
      "arac": false
    },
    "durum": "taslak",
    "yerel_mi": false,
    "konteyner": null,
    "olusturulma": "2026-09-12T19:42:16.518108",
    "guncellenme": "2026-09-12T19:42:16.518110"
  },
  "dogrulama": null,
  "kurulum_tamam": true
}

````

````
--- bdm tablosu (id, slug, durum)
[
  [
    1,
    "gozlem-gpt",
    "hazir"
  ],
  [
    2,
    "musteri-asistani-cgiosu",
    "hazir"
  ],
  [
    3,
    "taslak-bdm",
    "taslak"
  ],
  [
    4,
    "durdu-bdm",
    "durdu"
  ],
  [
    5,
    "hata-bdm",
    "hata"
  ],
  [
    6,
    "gozlem-calisan",
    "calisiyor"
  ]
]

````
- Sonuç: GEÇTİ

### 2) `./.venv/Scripts/python.exe kaynak/testler/betikler/modeller_12_ozet.py`
- Beklenen: `/modeller` yalnız `hazir|calisiyor` döndürür; anahtarın izin listesi süzülür; kimliksiz `401`.
- Gerçek çıktı:

````
GET /modeller [admin JWT] -> HTTP 200 [(6, 'gozlem-calisan', 'calisiyor'), (1, 'gozlem-gpt', 'hazir')]
GET /modeller [operator JWT] -> HTTP 200 [(6, 'gozlem-calisan', 'calisiyor'), (1, 'gozlem-gpt', 'hazir')]
GET /modeller [son_kullanici JWT] -> HTTP 200 [(6, 'gozlem-calisan', 'calisiyor'), (1, 'gozlem-gpt', 'hazir')]
GET /modeller [anahtar izinli_modeller=[]] -> HTTP 200 [(6, 'gozlem-calisan', 'calisiyor'), (1, 'gozlem-gpt', 'hazir')]
GET /modeller [anahtar izinli_modeller=['musteri-asistani-cgiosu']] -> HTTP 200 []
GET /modeller [anahtar izinli_modeller=['6']] -> HTTP 200 [(6, 'gozlem-calisan', 'calisiyor')]
GET /modeller [kimliksiz] -> HTTP 401 {'hata': {'kod': 'kimlik_gerekli', 'mesaj': 'Bu işlem için giriş yapmalısınız.', 'ayrinti': {}}}

GET /bdm [admin] -> HTTP 200 [(6, 'gozlem-calisan', 'calisiyor'), (4, 'durdu-bdm', 'durdu'), (1, 'gozlem-gpt', 'hazir'), (5, 'hata-bdm', 'hata'), (13, 'operator-modeli', 'taslak'), (8, 'sizinti-kopya', 'taslak'), (7, 'sizinti-testi', 'taslak'), (9, 'test-model', 'taslak'), (11, 'gusioc-iigusoc', 'taslak'), (10, 'sirket-ici-cozum-araci', 'taslak'), (12, 'sirket-ici-cozum-araci-2', 'taslak')]
````
- Sonuç: GEÇTİ (durum süzgeci ve izin listesi doğru; `izinli_modeller=[]` = tümü, spec §4.4 ile uyumlu)

### 3) `./.venv/Scripts/python.exe kaynak/testler/betikler/modeller_01_liste.py` (tam gövde, yönetici)
- Beklenen: `BdmOzet` alan kümesi API.md §2 ile birebir.
- Gerçek çıktı (yalnız yönetici bloğu):

````
--- GET /modeller (admin JWT)
HTTP 200
[
  {
    "id": 6,
    "slug": "gozlem-calisan",
    "gorunen_ad": "Gozlem Calisan",
    "aciklama": "",
    "saglayici": "openai",
    "baglam_penceresi": 8192,
    "yetenekler": {
      "akis": true,
      "gorsel": false,
      "arac": false
    },
    "durum": "calisiyor"
  },
  {
    "id": 1,
    "slug": "gozlem-gpt",
    "gorunen_ad": "Gozlem GPT",
    "aciklama": "",
    "saglayici": "openai",
    "baglam_penceresi": 128000,
    "yetenekler": {
      "akis": true,
      "gorsel": false,
      "arac": false
    },
    "durum": "hazir"
  },
  {
    "id": 2,
    "slug": "musteri-asistani-cgiosu",
    "gorunen_ad": "Müşteri Asistanı ÇĞİÖŞÜ",
    "aciklama": "",
    "saglayici": "openai",
    "baglam_penceresi": 8192,
    "yetenekler": {
      "akis": true,
      "gorsel": false,
      "arac": false
    },
    "durum": "hazir"
  }
]

````
- Sonuç: GEÇTİ

### 4) `./.venv/Scripts/python.exe kaynak/testler/betikler/modeller_02_sohbet_suzgec.py`
- Beklenen: izin listesinde olmayan model için `/sohbet` reddeder (`403 yetki_yok`).
- Gerçek çıktı:

````
--- POST /sohbet bdm_id=6 (izinli_modeller=['musteri-asistani-cgiosu'] anahtari)
HTTP 403
{
  "hata": {
    "kod": "yetki_yok",
    "mesaj": "Bu API anahtarı seçilen model için yetkili değil.",
    "ayrinti": {}
  }
}

--- POST /sohbet bdm_slug=gozlem-calisan (izinli_modeller=['musteri-asistani-cgiosu'] anahtari)
HTTP 403
{
  "hata": {
    "kod": "yetki_yok",
    "mesaj": "Bu API anahtarı seçilen model için yetkili değil.",
    "ayrinti": {}
  }
}

--- POST /sohbet bdm_id=3 taslak BDM (izinli_modeller=[] anahtari)
HTTP 503
{
  "hata": {
    "kod": "bdm_hazir_degil",
    "mesaj": "Seçilen model şu anda kullanıma hazır değil.",
    "ayrinti": {
      "bdm_id": 3,
      "durum": "taslak"
    }
  }
}

--- POST /sohbet bdm_id=6 (izinli_modeller=[] anahtari)
HTTP 502
{
  "hata": {
    "kod": "ust_saglayici_hatasi",
    "mesaj": "Model sağlayıcısı isteği yanıtlayamadı.",
    "ayrinti": {
      "durum": 401,
      "govde": "{ \"error\": { \"message\": \"Incorrect API key provided: sk-cokgi*****************7890. You can find your API key at https://platform.openai.com/account/api-keys.\", \"type\": \"invalid_request_error\", \"code\": \"invalid_api_key\", \"param\": null }, \"status\": 401 }"
    }
  }
}

--- konusma tablosu (id, bdm_id, baslik)
[
  [
    1,
    6,
    "Merhaba"
  ]
]
````
- Sonuç: GEÇTİ (hem `bdm_id` hem `bdm_slug` yolu 403; süzgeç atlatılamıyor)

### 5) `./.venv/Scripts/python.exe kaynak/testler/betikler/modeller_09_akis.py`
- Beklenen: `/sohbet/akis` de aynı süzgeci uygular.
- Gerçek çıktı:

````
--- POST /sohbet/akis bdm_id=6 (izinli_modeller=['musteri-asistani-cgiosu'] anahtari)
HTTP 403
{
  "hata": {
    "kod": "yetki_yok",
    "mesaj": "Bu API anahtarı seçilen model için yetkili değil.",
    "ayrinti": {}
  }
}

--- GET /sohbet/konusmalar/1 (kisitli anahtar)
HTTP 404
{
  "hata": {
    "kod": "bulunamadi",
    "mesaj": "Konuşma bulunamadı.",
    "ayrinti": {
      "konusma_id": 1
    }
  }
}

--- GET /sohbet/konusmalar (kisitli anahtar)
HTTP 200
{
  "toplam": 2,
  "sayfa": 1,
  "boyut": 25,
  "kayitlar": [
    {
      "id": 3,
      "baslik": "silme testi",
      "bdm_id": 2,
      "bdm_ad": null,
      "guncellenme": "2026-09-12T19:42:22.083849",
      "mesaj_sayisi": 1,
      "token_girdi": 2,
      "token_cikti": 0
    },
    {
      "id": 2,
      "baslik": "test",
      "bdm_id": 2,
      "bdm_ad": null,
      "guncellenme": "2026-09-12T19:42:20.918489",
      "mesaj_sayisi": 1,
      "token_girdi": 1,
      "token_cikti": 0
    }
  ]
}

````
- Sonuç: GEÇTİ (SSE ucu da `403 yetki_yok`)

### 6) `./.venv/Scripts/python.exe kaynak/testler/betikler/modeller_03_sizinti.py`
- Beklenen: upstream anahtarı hiçbir yanıtta ham hâlde görünmez; `PATCH` sonrası da maskeli kalır.
- Gerçek çıktı (PATCH bloğu ve tarama):

````
--- PATCH /bdm/{id} (yalniz aciklama)
HTTP 200
{
  "id": 7,
  "slug": "sizinti-testi",
  "gorunen_ad": "Sizinti Testi",
  "aciklama": "maskeli kalmali",
  "saglayici": "openai",
  "temel_url": "https://api.openai.com/v1",
  "upstream_model": "gpt-4o-mini",
  "api_anahtari_maskeli": "sk-c***7890",
  "baglam_penceresi": 8192,
  "maks_cikti": 2048,
  "sicaklik_varsayilan": 0.7,
  "sistem_istemi": "",
  "yetenekler": {
    "akis": true,
    "gorsel": false,
    "arac": false
  },
  "durum": "taslak",
  "yerel_mi": false,
  "konteyner": null,
  "olusturulma": "2026-09-12T19:42:20.848644",
  "guncellenme": "2026-09-12T19:42:20.858674"
}

````

````
=== HAM YANIT TARAMASI ===
GET /bdm: ['sk-']
GET /modeller: temiz
GET /saglayicilar: temiz
POST /bdm (api_anahtari=sk-cokgizli-...): ['sk-']
PATCH /bdm/{id} (yalniz aciklama): ['sk-']
PATCH /bdm/{id} (api_anahtari yeniden yazildi): ['sk-']
PATCH /bdm/{id} (api_anahtari temizlendi): temiz
PATCH /bdm/{id} (api_anahtari tekrar dolduruldu): ['sk-']
POST /bdm/{id}/kopyala: ['sk-']
POST /sohbet (502 govdesi): ['sk-']

--- bdm tablosu (id, slug, api_anahtari_sifreli)
(1, 'gozlem-gpt', 'gAAAAABqpasY3WllmE18m9HggIZQh8ff_Dt1a0V9Ny4XO1zX1kfCWgTCOuDPIuQXAj4eGB52Gx0vYBaOF8bCSm3COC2boZykTCi-pIfwDJgLlA8DTLCP7dI=')
(2, 'musteri-asistani-cgiosu', 'gAAAAABqpasY9EnU6bANszBjsBv7XIjpxn93iDGVEgeY1cPUFv55_PQ4GiGcD3FJH7HR8vt6GyJrqKMk9ng2_kcSce6kqPzbZmzqyZs2bJLl8xdaX_h4K5E=')
(3, 'taslak-bdm', 'gAAAAABqpasYBCenv37MOagUEUKpQU8Vsy7txX1EKoHEImmtYsdyTBimECa4q0YGCKC22KcHKaPRL6CFGPpSbeDWTwDQgD9FqeLOjo9x2_nNMn5faIiAxyc=')
(4, 'durdu-bdm', 'gAAAAABqpasYirUQy_TQH56yzLjuCZ2sxtMG1tAytE-lA0ZStxmkdXKMU6k0bAHUTl-uL4GfHlXTgF21T5Bk_elCGDMaBxzneqqOmlUjC59n6SPcSzC5G3c=')
````
- Sonuç: GEÇTİ (`sk-c***7890` maskesi tüm `Bdm` gövdelerinde sabit; ham anahtar `sk-cokgizli-GOZLEM-1234567890` ve `cokgizli` hiçbir yanıtta yok)

### 7) `./.venv/Scripts/python.exe kaynak/testler/betikler/modeller_04_silme.py`
- Beklenen: `durum=calisiyor` iken `409`; ilişkili konuşması olan BDM silinirken veri bütünlüğü korunur.
- Gerçek çıktı (çalışan BDM):

````
--- DELETE /bdm/6 (durum=calisiyor)
HTTP 409
{
  "hata": {
    "kod": "gecersiz_gecis",
    "mesaj": "Çalışan bir BDM silinemez. Önce durdurun.",
    "ayrinti": {
      "bdm_id": 6,
      "durum": "calisiyor"
    }
  }
}

````

- Gerçek çıktı (konuşması olan BDM — silme öncesi konuşmalar):

````
--- SILME ONCESI: konusma / bdm tablolari
[
  [
    1,
    6,
    "Merhaba",
    1
  ],
  [
    2,
    2,
    "test",
    1
  ],
  [
    3,
    2,
    "silme testi",
    1
  ]
]
[
  [
    1,
    "gozlem-gpt",
    "hazir"
  ],
````

- Gerçek çıktı (silme isteği ve sonrası):

````
--- DELETE /bdm/2 (konusmasi olan BDM)
HTTP 204
''

--- SILME SONRASI: konusma / bdm tablolari
[
  [
    1,
    6,
    "Merhaba",
    1
  ],
  [
    2,
    2,
    "test",
    1
  ],
  [
    3,
    2,
    "silme testi",
    1
  ]
]
[
  [
    1,
    "gozlem-gpt",
    "hazir"
  ],
  [
    3,
    "taslak-bdm",
    "taslak"
  ],
  [
    4,
    "durdu-bdm",
    "durdu"
  ],
  [
    5,
    "hata-bdm",
    "hata"
  ],
  [
    6,
    "gozlem-calisan",
    "calisiyor"
  ],
  [
    7,
    "sizinti-testi",
    "taslak"
  ],
  [
    8,
    "sizinti-kopya",
    "taslak"
  ]
]

--- yetim (orphan) konusma satirlari: bdm_id'si olmayan
[
  [
    2,
    2
  ],
  [
    3,
    2
  ]
]

````

````
--- PRAGMA foreign_keys (uygulamanin kullandigi motor ile)
PRAGMA foreign_keys = 0
````
- Sonuç: KALDI — `durum=calisiyor` 409 doğru; ancak konuşması olan BDM için `204` döndü ve `bdm_id=2` işaret eden 2 konuşma satırı (her biri 1 mesajlı) yetim kaldı.

### 8) `./.venv/Scripts/python.exe kaynak/testler/betikler/modeller_15_slug_ozet.py`
- Beklenen: aynı slug iki kez `409 cakisma`; Türkçe karakterler doğru sadeleşir.
- Gerçek çıktı (betik daha önce de koşulduğu için slug sonekleri ilerlemiş durumda; aynı slug için ilk deneme 201, ikinci deneme 409):

````
POST /bdm [slug=gozlem-cakisma (1. kez)] -> HTTP 201 slug/kod='gozlem-cakisma-uc'
POST /bdm [slug=gozlem-cakisma (2. kez)] -> HTTP 409 slug/kod='cakisma'
POST /bdm [Turkce ad (slug yok): Şirket Dışı Çözüm Aracı] -> HTTP 201 slug/kod='sirket-disi-cozum-araci-3'
POST /bdm [Turkce ad (slug yok): ĞÜŞİÖÇ ıİğüşöç] -> HTTP 201 slug/kod='gusioc-iigusoc-deneme-2'
POST /bdm [ayni ad 2. kez (slug yok)] -> HTTP 201 slug/kod='sirket-disi-cozum-araci-4'

POST /kimlik/panel-giris (yanlis parola) -> HTTP 401
{"hata": {"kod": "gecersiz_kimlik_bilgisi", "mesaj": "E-posta veya parola hatalı.", "ayrinti": {}}}
````

- İlk koşunun ham çıktısı (çakışma gövdesi):

````
--- POST /bdm slug=test-model (2. kez)
HTTP 409
{
  "hata": {
    "kod": "cakisma",
    "mesaj": "'test-model' slug'ı zaten kullanılıyor.",
    "ayrinti": {
      "alan": "slug"
    }
  }
}

````
- Sonuç: GEÇTİ (`409 cakisma`, `ayrinti.alan=slug`; `Şirket İçi Çözüm Aracı` → `sirket-ici-cozum-araci`, `ĞÜŞİÖÇ ıİğüşöç` → `gusioc-iigusoc`)

### 9) `./.venv/Scripts/python.exe kaynak/testler/betikler/modeller_06_saglayici_yetki.py`
- Beklenen: `GET /saglayicilar` kimliksiz `200`, 7 kayıt, alanlar API.md §8 ile birebir.
- Gerçek çıktı (7. kayıt + sayım + alan denetimi):

````
    "yerel": false,
    "gpu_gerekir": false,
    "akis_destegi": true,
    "api_anahtari_gerekir": false,
    "varsayilan_temel_url": "",
    "varsayilan_port": null,
    "konteyner_image": null,
    "aciklama": "OpenAI uyumlu herhangi bir adres."
  }
]

--- kayit sayisi: 7
openai: alanlar birebir mi = True -> ['ad', 'gorunen_ad', 'yerel', 'gpu_gerekir', 'akis_destegi', 'api_anahtari_gerekir', 'varsayilan_temel_url', 'varsayilan_port', 'konteyner_image', 'aciklama']
azure: alanlar birebir mi = True -> ['ad', 'gorunen_ad', 'yerel', 'gpu_gerekir', 'akis_destegi', 'api_anahtari_gerekir', 'varsayilan_temel_url', 'varsayilan_port', 'konteyner_image', 'aciklama']
openrouter: alanlar birebir mi = True -> ['ad', 'gorunen_ad', 'yerel', 'gpu_gerekir', 'akis_destegi', 'api_anahtari_gerekir', 'varsayilan_temel_url', 'varsayilan_port', 'konteyner_image', 'aciklama']
ollama: alanlar birebir mi = True -> ['ad', 'gorunen_ad', 'yerel', 'gpu_gerekir', 'akis_destegi', 'api_anahtari_gerekir', 'varsayilan_temel_url', 'varsayilan_port', 'konteyner_image', 'aciklama']
vllm: alanlar birebir mi = True -> ['ad', 'gorunen_ad', 'yerel', 'gpu_gerekir', 'akis_destegi', 'api_anahtari_gerekir', 'varsayilan_temel_url', 'varsayilan_port', 'konteyner_image', 'aciklama']
tgi: alanlar birebir mi = True -> ['ad', 'gorunen_ad', 'yerel', 'gpu_gerekir', 'akis_destegi', 'api_anahtari_gerekir', 'varsayilan_temel_url', 'varsayilan_port', 'konteyner_image', 'aciklama']
ozel: alanlar birebir mi = True -> ['ad', 'gorunen_ad', 'yerel', 'gpu_gerekir', 'akis_destegi', 'api_anahtari_gerekir', 'varsayilan_temel_url', 'varsayilan_port', 'konteyner_image', 'aciklama']

````
- Sonuç: GEÇTİ

### 10) `./.venv/Scripts/python.exe kaynak/testler/betikler/modeller_13_yetki_ozet.py`
- Beklenen: anonim `401`; `son_kullanici` yazma/silme/kopyalamada `403`; `operator` silme/kopyalamada `403`, oluşturma/güncellemede yetkili.
- Gerçek çıktı:

````
GET    /bdm               [anonim       ] -> HTTP 401 kimlik_gerekli
GET    /modeller          [anonim       ] -> HTTP 401 kimlik_gerekli
POST   /bdm               [anonim       ] -> HTTP 401 kimlik_gerekli
DELETE /bdm/4             [anonim       ] -> HTTP 401 kimlik_gerekli
POST   /bdm/1/kopyala     [anonim       ] -> HTTP 401 kimlik_gerekli
GET    /bdm               [son_kullanici] -> HTTP 403 yetki_yok
GET    /modeller          [son_kullanici] -> HTTP 200 basarili
POST   /bdm               [son_kullanici] -> HTTP 403 yetki_yok
DELETE /bdm/4             [son_kullanici] -> HTTP 403 yetki_yok
POST   /bdm/1/kopyala     [son_kullanici] -> HTTP 403 yetki_yok
GET    /bdm               [operator     ] -> HTTP 200 basarili
GET    /modeller          [operator     ] -> HTTP 200 basarili
POST   /bdm               [operator     ] -> HTTP 201 basarili
DELETE /bdm/4             [operator     ] -> HTTP 403 yetki_yok
POST   /bdm/1/kopyala     [operator     ] -> HTTP 403 yetki_yok
GET    /bdm               [yonetici     ] -> HTTP 200 basarili
GET    /modeller          [yonetici     ] -> HTTP 200 basarili
POST   /bdm               [yonetici     ] -> HTTP 201 basarili
DELETE /bdm/4             [yonetici     ] -> HTTP 204 basarili
POST   /bdm/1/kopyala     [yonetici     ] -> HTTP 201 basarili
````
- Sonuç: GEÇTİ (beklenen tek istisna: `GET /modeller` bilinçli olarak sohbet istemcisine açık)

### 11) `./.venv/Scripts/python.exe kaynak/testler/betikler/modeller_07_openapi.py`
- Beklenen: API.md §8'deki 7 uç; fazladan uç veya parametre yok.
- Gerçek çıktı:

````
--- etiketi 'modeller' olan uclar ve parametreleri
GET    /api/v1/bdm              params=[('arama', 'query', False)] -
POST   /api/v1/bdm              params=[] govde
PATCH  /api/v1/bdm/{bdm_id}     params=[('bdm_id', 'path', True)] govde
DELETE /api/v1/bdm/{bdm_id}     params=[('bdm_id', 'path', True)] -
POST   /api/v1/bdm/{bdm_id}/kopyala params=[('bdm_id', 'path', True)] govde
GET    /api/v1/modeller         params=[] -
GET    /api/v1/saglayicilar     params=[] -

--- API.md §8 ile beklenen kume
[
  "GET /modeller",
  "GET /saglayicilar",
  "GET /bdm",
  "POST /bdm",
  "PATCH /bdm/{id}",
  "POST /bdm/{id}/kopyala",
  "DELETE /bdm/{id}"
]
````
- Sonuç: KALDI — uçlar birebir, ancak `GET /bdm` sözleşmede olmayan `arama` sorgu parametresi kabul ediyor.

### 12) `./.venv/Scripts/python.exe kaynak/testler/betikler/modeller_08_kenar.py`
- Beklenen: `arama` dışındaki davranışlar sözleşmeye uygun (`404 bulunamadi`, `400 dogrulama_hatasi`, iptal anahtar `401`).
- Gerçek çıktı (kırpıldı):

````
--- GET /bdm?arama=Slug Catismasi (API.md §8'de boyle bir parametre yok)
HTTP 200
[

--- arama sonucu kayit sayisi: 1

--- DELETE /bdm/9999
HTTP 404
{
  "hata": {
    "kod": "bulunamadi",
    "mesaj": "BDM kaydı bulunamadı.",
    "ayrinti": {
      "bdm_id": 9999
    }
  }
}


--- POST /bdm bilinmeyen saglayici
HTTP 400
{
  "hata": {
    "kod": "dogrulama_hatasi",
    "mesaj": "Gönderilen alanlar doğrulanamadı.",
    "ayrinti": {
      "alanlar": [
        {
          "alan": "saglayici",
          "mesaj": "Input should be 'openai', 'azure', 'openrouter', 'ollama', 'vllm', 'tgi' or 'ozel'"
        }
      ]
    }
  }
}


--- POST /api-anahtarlari/{id}/iptal
HTTP 200
{
  "durum": "iptal"
}

--- GET /modeller (iptal edilmis anahtar)
HTTP 401
{
  "hata": {
    "kod": "anahtar_gecersiz",
    "mesaj": "API anahtarı iptal edilmiş.",
    "ayrinti": {}
  }
}

````
- Sonuç: GEÇTİ

### 13) `./.venv/Scripts/python.exe kaynak/testler/betikler/modeller_10_yetim_etki.py`
- Beklenen: yetim konuşma kalırsa kullanıcı/denetim uçlarında görünür etkisi ölçülür.
- Gerçek çıktı:

````
--- GET /sohbet/konusmalar/2 (bdm_id=2 silinmis, yetim konusma)
HTTP 404
{
  "hata": {
    "kod": "bulunamadi",
    "mesaj": "Konuşma bulunamadı.",
    "ayrinti": {
      "konusma_id": 2
    }
  }
}

--- GET /sohbet/konusmalar (yonetici)
HTTP 200
{
  "toplam": 0,
  "sayfa": 1,
  "boyut": 25,
  "kayitlar": []
}

--- GET /loglar/konusmalar (yonetici)
HTTP 200
{
  "toplam": 3,
  "sayfa": 1,
  "boyut": 25,
  "kayitlar": [
    {
      "id": 3,
      "baslik": "silme testi",
      "kullanici_id": null,
      "kullanici_eposta": null,
      "api_anahtari_id": 2,
      "bdm_id": 2,
      "bdm_ad": null,
      "mesaj_sayisi": 1,
      "token_girdi": 2,
      "token_cikti": 0,
      "olusturulma": "2026-09-12T19:42:22.080894",
      "guncellenme": "2026-09-12T19:42:22.083849"
    },
    {
      "id": 2,
      "baslik": "test",
      "kullanici_id": null,
      "kullanici_eposta": null,
      "api_anahtari_id": 2,
      "bdm_id": 2,
      "bdm_ad": null,
      "mesaj_sayisi": 1,
      "token_girdi": 1,
      "token_cikti": 0,
      "olusturulma": "2026-09-12T19:42:20.915293",
      "guncellenme": "2026-09-12T19:42:20.918489"
    },
    {
      "id": 1,
      "baslik": "Merhaba",
      "kullanici_id": null,
      "kullanici_eposta": null,
      "api_anahtari_id": 1,
      "bdm_id": 6,
      "bdm_ad": "Gozlem Calisan",
      "mesaj_sayisi": 1,
      "token_girdi": 1,
      "token_cikti": 0,
      "olusturulma": "2026-09-12T19:42:19.401340",
      "guncellenme": "2026-09-12T19:42:19.407263"
    }
  ]
}

````
- Sonuç: KALDI — silinen BDM'in konuşması `GET /sohbet/konusmalar/{id}` ile `404` dönerken `GET /loglar/konusmalar` listesinde `bdm_ad: null` ile duruyor.

### 14) `./.venv/Scripts/python.exe kaynak/testler/betikler/modeller_11_alanlar.py`
- Beklenen: `Bdm` ve `BdmOzet` alan kümeleri API.md §2/§8 ile birebir.
- Gerçek çıktı:

````
GET /bdm kayit sayisi: 11
Bdm alan kumesi birebir: True
ornek: ['id', 'slug', 'gorunen_ad', 'aciklama', 'saglayici', 'temel_url', 'upstream_model', 'api_anahtari_maskeli', 'baglam_penceresi', 'maks_cikti', 'sicaklik_varsayilan', 'sistem_istemi', 'yetenekler', 'durum', 'yerel_mi', 'konteyner', 'olusturulma', 'guncellenme']

GET /modeller kayit sayisi: 2
BdmOzet alan kumesi birebir: True
ornek: ['id', 'slug', 'gorunen_ad', 'aciklama', 'saglayici', 'baglam_penceresi', 'yetenekler', 'durum']

durum kumesi (modeller): ['calisiyor', 'hazir']
durum kumesi (bdm): ['calisiyor', 'durdu', 'hata', 'hazir', 'taslak']
````
- Sonuç: GEÇTİ

## Bulgular

- [BLOCKER] `arkauc/app/api/modeller.py:154-169`, `bdm_listesi/katalog.py:202-204` — `DELETE /bdm/{id}` ilişkili `konusma`/`mesaj` satırları varken `204` dönüyor ve satırları yetim bırakıyor (sessiz veri bütünlüğü kaybı). Şema `konusma.bdm_id` için `ondelete="RESTRICT"` bildiriyor (`bdm_veritabani/modeller.py:248`), ancak motor SQLite'ta `PRAGMA foreign_keys` hiç açılmıyor (`bdm_veritabani/oturum.py:35`, kanıt: `PRAGMA foreign_keys = 0`) ve `bdm_sil` yalnız `oturum.delete(bdm)` çağırıyor; ilişki denetimi ya da kaskad yok. Beklenen: ilişkili kaydı olan BDM ya reddedilmeli (`409`) ya da bağlı konuşmalar birlikte silinmeli; hiçbir durumda var olmayan `bdm_id`'ye işaret eden satır kalmamalı. Yeniden üretme: (1) bir BDM içeren konuşma oluştur (`POST /sohbet` başarısız da olsa `konusma` satırı yazılıyor), (2) `DELETE /bdm/{id}` → `204`, (3) `SELECT k.id, k.bdm_id FROM konusma k LEFT JOIN bdm b ON b.id=k.bdm_id WHERE b.id IS NULL` → yetim satırlar. [INFERENCE] Aynı istek PostgreSQL'de FK kısıtı nedeniyle `IntegrityError` üretip genel işleyiciden `500 sunucu_hatasi` dönecektir (bu ortamda Postgres koşulmadı); her iki durumda da sözleşmedeki `204`/`409` davranışı sağlanmıyor.
- [MINOR] `arkauc/app/api/modeller.py:70` — `GET /bdm` sözleşmede olmayan `arama` sorgu parametresini kabul ediyor; API.md §8 `GET /bdm` için yalnız `Bdm[]` diyor, spec §7.3 de parametre saymıyor. Fazladan özellik de sözleşme ihlalidir. Kanıt: `GET /bdm?arama=Slug Catismasi` → `200` + 1 kayıt; OpenAPI'de `params=[('arama','query',False)]`. Yeniden üretme: `GET /api/v1/bdm?arama=<metin>`.
- [MINOR] `arkauc/app/servisler/upstream.py:195` (kapsam: sohbet/hazırlama; `/sohbet` yoklamasında görüldü) — `502` hata zarfının `ayrinti.govde` alanı upstream yanıt gövdesini olduğu gibi istemciye taşıyor. OpenAI'nin hata mesajı anahtarın ilk 8 karakterini (`sk-cokgi*****************7890`) açığa çıkarırken ürünün kendi maskesi `sk-c***7890`. Ham anahtar sızmıyor (`sk-cokgizli-GOZLEM-1234567890` ve `cokgizli` taraması temiz) ama maskeleme politikasından daha geniş bir açığa çıkarma. Yeniden üretme: geçersiz upstream anahtarlı bir BDM ile `POST /sohbet` → `502` gövdesi.

### Kapsam dışı gözlemler (modeller.py dışı, ekibe bilgi)
- `POST /kimlik/panel-giris` yanlış parolada `401` `gecersiz_kimlik_bilgisi` döndürüyor; bu kod API.md §1'in 401 listesinde (`kimlik_gerekli`, `jeton_gecersiz`, `jeton_suresi_doldu`, `anahtar_gecersiz`) yok. Kanıt: komut 8'in son satırları.
- `GET /sohbet/konusmalar` yanıtı API.md §9'daki `{toplam, kayitlar}` yerine ek `sayfa`/`boyut` alanları içeriyor; yetim konuşmalar `bdm_ad: null` olarak listeleniyor. Kanıt: komut 5 ve 13.

## Özet

**3 bulgu (1 BLOCKER, 0 MAJOR, 2 MINOR)** + 2 kapsam dışı gözlem.

BLOCKER: konuşması olan bir BDM `DELETE /bdm/{id}` ile `204` dönerek siliniyor ve bağlı `konusma`/`mesaj` satırları var olmayan `bdm_id`'ye işaret ederek yetim kalıyor (FK `RESTRICT` bildirilmiş olmasına rağmen SQLite'ta FK zorlaması kapalı).
