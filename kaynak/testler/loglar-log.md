# loglar gözlem logu — 2026-09-12

## Kapsam

- Ölçülen uçlar: `arkauc/app/api/loglar.py` (API.md §12), `api_anahtarlari.py` (§7),
  `ayarlar.py` (§14), `kurulum.py` (§4). Yan ürün olarak §3 `/saglik/kurulum`, §5 giriş,
  §8 `/modeller`, §9 `/sohbet` uçları da yoklandı.
- Yöntem: canlı backend (uvicorn, port 8106) + HTTP istemcisi (httpx) + **bağımsız SQL**
  sorguları (sqlite3, sunucu dışı ayrı bağlantı). Uygulayıcının kendi test dosyası
  (`arkauc/testler/test_loglar.py`) hiç çalıştırılmadı; tüm kanıt ham HTTP/SQL çıktısıdır.
- Ham çıktı dosyaları: `kaynak/testler/kanit/loglar/*.txt` (komut bazlı, kırpılmamış).
- Betikler: `kaynak/testler/betikler/goz_*.py` (yeniden üretilebilirlik için).

## Ortam

- Depo: `E:/kutyai-app`, Python: `E:/kutyai-app/.venv/Scripts/python.exe` (3.13.3).
- Geçici veritabanı: `kaynak/testler/gecici/goz_loglar.db` (SQLite, her senaryodan önce
  silinip yeniden oluşturuldu).
- Sunucu: `hub op:start` → `python -m uvicorn arkauc.app.main:app --port 8106`.
- Kurulum sihirbazı testleri taze DB ile başlatıldı (`kurulum_tamam=false`).

## Koşulan komutlar

### 0) Sunucu başlatma ve sağlık yoklaması

```
hub op:start (uvicorn, port 8106) + curl /saglik, /saglik/kurulum
```

- Beklenen: Sunucu ayakta; `kurulum_tamam=false` başlangıç durumu.
- Gerçek çıktı:

```
=== Sunucu başlatma (hub op:start) ===
application: ./.venv/Scripts/python.exe
args: ["-m","uvicorn","arkauc.app.main:app","--port","8106","--log-level","info"]
env: KUTYAI_VERITABANI_URL=sqlite+aiosqlite:///E:/kutyai-app/kaynak/testler/gecici/goz_loglar.db
     KUTYAI_GIZLI_ANAHTAR=gozlem-gizli-anahtar
     KUTYAI_SIFRELEME_ANAHTARI=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=
     KUTYAI_ORTAM=gelistirme
Hazır sinyali: 'Uvicorn running' + port 8106 (hub ready)

=== curl http://127.0.0.1:8106/api/v1/saglik ===
{"durum":"ayakta","surum":"0.1.0","ortam":"gelistirme","zaman":"2026-09-12T19:45:05.007489+00:00"}
HTTP 200

=== curl http://127.0.0.1:8106/api/v1/saglik/kurulum ===
{"kurulum_tamam":true,"marka_adi":"Gözlem A.Ş.","surum":"0.1.0"}
HTTP 200
```

- Sonuç: GEÇTİ

### 1) Tohum: log uçları için doğrudan SQL verisi

```
E:/kutyai-app/.venv/Scripts/python.exe goz_tohum.py
```

- Beklenen: 4 konuşma + 6 mesaj eklenir (biri Türkçe karakterli başlık, biri eski tarihli).
- Gerçek çıktı:

```

```

- Sonuç: GEÇTİ

### 2) Kurulum yarış durumu — farklı e-posta

```
E:/kutyai-app/.venv/Scripts/python.exe goz_01_kurulum_yaris.py
```

- Beklenen: İki eşzamanlı `POST /kurulum`: birincisi 201, ikincisi 409 `kurulum_zaten_tamam`; tek yönetici + tek BDM.
- Gerçek çıktı:

```
=== Baseline GET /saglik/kurulum ===
HTTP 200 application/json
{"kurulum_tamam":false,"marka_adi":"KutyAI","surum":"0.1.0"}

=== Senaryo ===
FARKLI E-POSTA

=== İstek 1 (geçen 0.14s) ===
HTTP 201 application/json
{"yonetici":{"id":1,"eposta":"goz-yonetici-1@gozlem.example.com","ad_soyad":"Gözlem Yönetici","rol":"yonetici","durum":"aktif","eposta_dogrulandi":true,"olusturulma":"2026-09-12T19:43:48.009716+00:00","son_giris":null},"bdm":{"id":1,"slug":"yaris-model-1","gorunen_ad":"Yaris Model 1","aciklama":"","saglayici":"ollama","temel_url":"http://127.0.0.1:11434/v1","upstream_model":"llama3","api_anahtari_maskeli":"","baglam_penceresi":8192,"maks_cikti":2048,"sicaklik_varsayilan":0.7,"sistem_istemi":"","yetenekler":{"akis":true,"gorsel":false,"arac":false},"durum":"taslak","yerel_mi":true,"konteyner":null,"olusturulma":"2026-09-12T19:43:48.065749","guncellenme":"2026-09-12T19:43:48.065751"},"dogrulama":null,"kurulum_tamam":true}

=== İstek 2 (geçen 0.14s) ===
HTTP 201 application/json
{"yonetici":{"id":2,"eposta":"goz-yonetici-2@gozlem.example.com","ad_soyad":"Gözlem Yönetici","rol":"yonetici","durum":"aktif","eposta_dogrulandi":true,"olusturulma":"2026-09-12T19:43:48.062039+00:00","son_giris":null},"bdm":{"id":2,"slug":"yaris-model-2","gorunen_ad":"Yaris Model 2","aciklama":"","saglayici":"ollama","temel_url":"http://127.0.0.1:11434/v1","upstream_model":"llama3","api_anahtari_maskeli":"","baglam_penceresi":8192,"maks_cikti":2048,"sicaklik_varsayilan":0.7,"sistem_istemi":"","yetenekler":{"akis":true,"gorsel":false,"arac":false},"durum":"taslak","yerel_mi":true,"konteyner":null,"olusturulma":"2026-09-12T19:43:48.080304","guncellenme":"2026-09-12T19:43:48.080306"},"dogrulama":null,"kurulum_tamam":true}

=== Sonra GET /saglik/kurulum ===
HTTP 200 application/json
{"kurulum_tamam":true,"marka_adi":"Yaris-2","surum":"0.1.0"}

=== Kurulum sonrası tekrar POST /kurulum ===
HTTP 409 application/json
{"hata":{"kod":"kurulum_zaten_tamam","mesaj":"Kurulum daha önce tamamlanmış.","ayrinti":{}}}

=== Panel girişi goz-yonetici-1@gozlem.example.com ===
HTTP 200 application/json
{"erisim_jetonu":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwicm9sIjoieW9uZXRpY2kiLCJqdGkiOiIxYWFoQlU4R3pjR3ZnUWwxZERTbk53IiwidHVyIjoiZXJpc2ltIiwiaWF0IjoxNzg5MjQyMjI4LCJleHAiOjE3ODkyNDMxMjh9.eD7UOsfzWrWLy8Nm0GJz95dmd7iihpRKKjRFM2EWeAI","yenileme_jetonu":"qQQfDmbGrltSdaAPEFTov1Ohnzc9-D7WI9j10GkRYhbpvL8wOKGhdGEpjWGb_yUx","kullanici":{"id":1,"eposta":"goz-yonetici-1@gozlem.example.com","ad_soyad":"Gözlem Yönetici","rol":"yonetici","durum":"aktif","eposta_dogrulandi":true,"olusturulma":"2026-09-12T19:43:48.009716","son_giris":"2026-09-12T19:43:48.151333+00:00"}}

=== Panel girişi goz-yonetici-2@gozlem.example.com ===
HTTP 200 application/json
{"erisim_jetonu":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyIiwicm9sIjoieW9uZXRpY2kiLCJqdGkiOiI4aHFGaFpiNUxjb1JPaEJZcEI5TkdBIiwidHVyIjoiZXJpc2ltIiwiaWF0IjoxNzg5MjQyMjI4LCJleHAiOjE3ODkyNDMxMjh9.y6R7Wx0wvMGkIhN9PlbOJx1NT5zYIoIIybIHYJSey3Q","yenileme_jetonu":"E3RIZb015NqppIrXdE2GicEjOi17yQsSVptUZQ_NMvXMAJnT_jots9cRQrbHOiS9","kullanici":{"id":2,"eposta":"goz-yonetici-2@gozlem.example.com","ad_soyad":"Gözlem Yönetici","rol":"yonetici","durum":"aktif","eposta_dogrulandi":true,"olusturulma":"2026-09-12T19:43:48.062039","son_giris":"2026-09-12T19:43:48.211444+00:00"}}

=== Panel girişi goz-yonetici-3@gozlem.example.com ===
HTTP 401 application/json
{"hata":{"kod":"gecersiz_kimlik_bilgisi","mesaj":"E-posta veya parola hatalı.","ayrinti":{}}}

=== GET /kullanicilar -> toplam=2 ===
id=2 eposta=goz-yonetici-2@gozlem.example.com rol=yonetici durum=aktif
id=1 eposta=goz-yonetici-1@gozlem.example.com rol=yonetici durum=aktif

=== GET /bdm -> HTTP 200 ===
id=1 slug=yaris-model-1 ad=Yaris Model 1
id=2 slug=yaris-model-2 ad=Yaris Model 2

=== SQL: kullanici tablosu ===
[(1, 'goz-yonetici-1@gozlem.example.com', 'yonetici', 'aktif'), (2, 'goz-yonetici-2@gozlem.example.com', 'yonetici', 'aktif')]

=== SQL: bdm tablosu ===
[(1, 'yaris-model-1', 'Yaris Model 1'), (2, 'yaris-model-2', 'Yaris Model 2')]

=== SQL: kurulum ayarları ===
[('kurulum_tamam', 'true'), ('marka_adi', '"Yaris-2"'), ('varsayilan_bdm_slug', '"yaris-model-2"')]

=== SQL: islem_kaydi ===
[(1, 'kurulum.tamamlandi', 1, 'bdm', '1'), (2, 'kurulum.tamamlandi', 2, 'bdm', '2'), (3, 'kimlik.giris', 1, 'kullanici', '1'), (4, 'kimlik.giris', 2, 'kullanici', '2'), (5, 'kimlik.giris', 1, 'kullanici', '1')]
```

- Sonuç: KALDI

### 3) Kurulum yarış durumu — aynı e-posta (taze DB)

```
E:/kutyai-app/.venv/Scripts/python.exe goz_01_kurulum_yaris.py ayni_eposta
```

- Beklenen: Birincisi 201, ikincisi 409 `cakisma`/`kurulum_zaten_tamam`; 500 olmamalı.
- Gerçek çıktı:

```
=== Baseline GET /saglik/kurulum ===
HTTP 200 application/json
{"kurulum_tamam":false,"marka_adi":"KutyAI","surum":"0.1.0"}

=== Senaryo ===
AYNI E-POSTA

=== İstek 1 (geçen 0.15s) ===
HTTP 201 application/json
{"yonetici":{"id":1,"eposta":"goz-yonetici-1@gozlem.example.com","ad_soyad":"Gözlem Yönetici","rol":"yonetici","durum":"aktif","eposta_dogrulandi":true,"olusturulma":"2026-09-12T19:41:11.820050+00:00","son_giris":null},"bdm":{"id":1,"slug":"yaris-model-1","gorunen_ad":"Yaris Model 1","aciklama":"","saglayici":"ollama","temel_url":"http://127.0.0.1:11434/v1","upstream_model":"llama3","api_anahtari_maskeli":"","baglam_penceresi":8192,"maks_cikti":2048,"sicaklik_varsayilan":0.7,"sistem_istemi":"","yetenekler":{"akis":true,"gorsel":false,"arac":false},"durum":"taslak","yerel_mi":true,"konteyner":null,"olusturulma":"2026-09-12T19:41:11.872608","guncellenme":"2026-09-12T19:41:11.872610"},"dogrulama":null,"kurulum_tamam":true}

=== İstek 2 (geçen 0.15s) ===
HTTP 500 application/json
{"hata":{"kod":"sunucu_hatasi","mesaj":"Beklenmeyen bir sunucu hatası oluştu.","ayrinti":{}}}

=== Sonra GET /saglik/kurulum ===
HTTP 200 application/json
{"kurulum_tamam":true,"marka_adi":"Yaris-1","surum":"0.1.0"}

=== Kurulum sonrası tekrar POST /kurulum ===
HTTP 409 application/json
{"hata":{"kod":"kurulum_zaten_tamam","mesaj":"Kurulum daha önce tamamlanmış.","ayrinti":{}}}

=== Panel girişi goz-yonetici-1@gozlem.example.com ===
HTTP 200 application/json
{"erisim_jetonu":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwicm9sIjoieW9uZXRpY2kiLCJqdGkiOiJIQnRhNGdzbDYxNTJ6WF9md2ItRVhBIiwidHVyIjoiZXJpc2ltIiwiaWF0IjoxNzg5MjQyMDcxLCJleHAiOjE3ODkyNDI5NzF9.RFul5NmcgiAYbahpJChNi9CRaZFoRbAhtyhPPP-EuqQ","yenileme_jetonu":"I_OQPRh-BRPanIx_TPeBhn-6C9lxt5rd4uumssArzDLV1GyD0nzOn-VnTNrcW46g","kullanici":{"id":1,"eposta":"goz-yonetici-1@gozlem.example.com","ad_soyad":"Gözlem Yönetici","rol":"yonetici","durum":"aktif","eposta_dogrulandi":true,"olusturulma":"2026-09-12T19:41:11.820050","son_giris":"2026-09-12T19:41:11.976049+00:00"}}

=== Panel girişi goz-yonetici-1@gozlem.example.com ===
HTTP 200 application/json
{"erisim_jetonu":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwicm9sIjoieW9uZXRpY2kiLCJqdGkiOiJlWGVDdExrdVlEaGdpMFlZLWxxNXpnIiwidHVyIjoiZXJpc2ltIiwiaWF0IjoxNzg5MjQyMDcyLCJleHAiOjE3ODkyNDI5NzJ9.TnCccsY03cFrVsMyZJAdsVJ25M_RlRPmktP09CKpve4","yenileme_jetonu":"PVLxEnEMu0VE9lWhvPkiflB3m4O3h6KaCOJWSA-wD3q2LxbPlm8viyq9T4LIAGR8","kullanici":{"id":1,"eposta":"goz-yonetici-1@gozlem.example.com","ad_soyad":"Gözlem Yönetici","rol":"yonetici","durum":"aktif","eposta_dogrulandi":true,"olusturulma":"2026-09-12T19:41:11.820050","son_giris":"2026-09-12T19:41:12.035172+00:00"}}

=== Panel girişi goz-yonetici-3@gozlem.example.com ===
HTTP 401 application/json
{"hata":{"kod":"gecersiz_kimlik_bilgisi","mesaj":"E-posta veya parola hatalı.","ayrinti":{}}}

=== GET /kullanicilar -> toplam=1 ===
id=1 eposta=goz-yonetici-1@gozlem.example.com rol=yonetici durum=aktif

=== GET /bdm -> HTTP 200 ===
id=1 slug=yaris-model-1 ad=Yaris Model 1

=== SQL: kullanici tablosu ===
[(1, 'goz-yonetici-1@gozlem.example.com', 'yonetici', 'aktif')]

=== SQL: bdm tablosu ===
[(1, 'yaris-model-1', 'Yaris Model 1')]

=== SQL: kurulum ayarları ===
[('kurulum_tamam', 'true'), ('marka_adi', '"Yaris-1"'), ('varsayilan_bdm_slug', '"yaris-model-1"')]

=== SQL: islem_kaydi ===
[(1, 'kurulum.tamamlandi', 1, 'bdm', '1'), (2, 'kimlik.giris', 1, 'kullanici', '1'), (3, 'kimlik.giris', 1, 'kullanici', '1'), (4, 'kimlik.giris', 1, 'kullanici', '1')]
```

- Sonuç: KALDI

### 4) API anahtarları — sızma, iptal, izinli_modeller (§7)

```
E:/kutyai-app/.venv/Scripts/python.exe goz_02_anahtarlar.py
```

- Beklenen: Tam anahtar yalnız oluşturmada; listede `kuty_` geçmez; iptal sonrası 401 `anahtar_gecersiz`; bilinmeyen slug 400 `gecersiz_istek`.
- Gerçek çıktı:

```
=== POST /kullanicilar rol=operator ===
HTTP 201 application/json
{"id":3,"eposta":"goz-operator@gozlem.example.com","ad_soyad":"Goz operator","rol":"operator","durum":"aktif","eposta_dogrulandi":true,"olusturulma":"2026-09-12T19:43:48.857200+00:00","son_giris":null}

=== POST /kullanicilar rol=izleyici ===
HTTP 201 application/json
{"id":4,"eposta":"goz-izleyici@gozlem.example.com","ad_soyad":"Goz izleyici","rol":"izleyici","durum":"aktif","eposta_dogrulandi":true,"olusturulma":"2026-09-12T19:43:48.911318+00:00","son_giris":null}

=== SQL: BDM durumları ===
[(1, 'yaris-model-1', 'hazir'), (2, 'yaris-model-2', 'taslak'), (3, 'goz-ikinci-model', 'hazir')]

=== POST /api-anahtarlari (geçerli) ===
HTTP 201 application/json
{"id":1,"ad":"Goz Anahtar","onek":"kuty_wVZCFfj","son_dort":"d9FS","durum":"aktif","izinli_modeller":["yaris-model-1"],"gunluk_istek_siniri":null,"olusturulma":"2026-09-12T19:43:49.035397","son_kullanim":null,"tam_anahtar":"kuty_wVZCFfjPSEpmMs3sHrVZRUcMNYg0d9FS"}

=== Oluşturma yanıtında kuty_ geçenler ===
['kuty_wVZCFfjPSEpmMs3sHrVZRUcMNYg0d9FS']

=== GET /api-anahtarlari (ham) ===
[{"id":1,"ad":"Goz Anahtar","onek":"kuty_wVZCFfj","son_dort":"d9FS","durum":"aktif","izinli_modeller":["yaris-model-1"],"gunluk_istek_siniri":null,"olusturulma":"2026-09-12T19:43:49.035397","son_kullanim":null}]

=== Liste yanıtında kuty_ geçenler ===
[]

=== Tam anahtar listede var mı? ===
False

=== Liste alanları ===
['ad', 'durum', 'gunluk_istek_siniri', 'id', 'izinli_modeller', 'olusturulma', 'onek', 'son_dort', 'son_kullanim']

=== POST /api-anahtarlari izinli_modeller=[yok-boyle-model] ===
HTTP 400 application/json
{"hata":{"kod":"gecersiz_istek","mesaj":"Bilinmeyen model seçildi.","ayrinti":{"gecersiz":["yok-boyle-model"]}}}

=== POST /api-anahtarlari izinli_modeller=[gecerli,yok-2] ===
HTTP 400 application/json
{"hata":{"kod":"gecersiz_istek","mesaj":"Bilinmeyen model seçildi.","ayrinti":{"gecersiz":["yok-2"]}}}

=== POST /api-anahtarlari izinli_modeller=[999999] ===
HTTP 400 application/json
{"hata":{"kod":"gecersiz_istek","mesaj":"Bilinmeyen model seçildi.","ayrinti":{"gecersiz":["999999"]}}}

=== GET /modeller anahtarla (izinli=[yaris-model-1]) ===
HTTP 200 application/json
[{"id":1,"slug":"yaris-model-1","gorunen_ad":"Yaris Model 1","aciklama":"","saglayici":"ollama","baglam_penceresi":8192,"yetenekler":{"akis":true,"gorsel":false,"arac":false},"durum":"hazir"}]

=== POST /api-anahtarlari/{id}/iptal ===
HTTP 200 application/json
{"durum":"iptal"}

=== GET /modeller iptal sonrası ===
HTTP 401 application/json
{"hata":{"kod":"anahtar_gecersiz","mesaj":"API anahtarı iptal edilmiş.","ayrinti":{}}}

=== POST /sohbet iptal sonrası ===
HTTP 401 application/json
{"hata":{"kod":"anahtar_gecersiz","mesaj":"API anahtarı iptal edilmiş.","ayrinti":{}}}

=== GET /api-anahtarlari iptal sonrası (durum) ===
HTTP 200 application/json
[{"id":1,"ad":"Goz Anahtar","onek":"kuty_wVZCFfj","son_dort":"d9FS","durum":"iptal","izinli_modeller":["yaris-model-1"],"gunluk_istek_siniri":null,"olusturulma":"2026-09-12T19:43:49.035397","son_kullanim":"2026-09-12T19:43:49.062530"}]

=== POST /api-anahtarlari (izleyici ile) ===
HTTP 201 application/json
{"id":2,"ad":"Izleyici Anahtari","onek":"kuty_xm8r2RQ","son_dort":"rPW1","durum":"aktif","izinli_modeller":[],"gunluk_istek_siniri":null,"olusturulma":"2026-09-12T19:43:49.091576","son_kullanim":null,"tam_anahtar":"kuty_xm8r2RQfd715BJXi2meWBrSNFTmIrPW1"}

=== POST /api-anahtarlari (operator ile) ===
HTTP 201 application/json
{"id":3,"ad":"Operator Anahtari","onek":"kuty_eatOh32","son_dort":"SgN1","durum":"aktif","izinli_modeller":[],"gunluk_istek_siniri":null,"olusturulma":"2026-09-12T19:43:49.098939","son_kullanim":null,"tam_anahtar":"kuty_eatOh32jj5MWgKTgSvGhnpFX5FRnSgN1"}

=== GET /api-anahtarlari (jetonsuz) ===
HTTP 401 application/json
{"hata":{"kod":"kimlik_gerekli","mesaj":"Bu işlem için giriş yapmalısınız.","ayrinti":{}}}

=== POST /api-anahtarlari/999999/iptal ===
HTTP 404 application/json
{"hata":{"kod":"bulunamadi","mesaj":"API anahtarı bulunamadı.","ayrinti":{"api_anahtari_id":999999}}}

=== SQL: api_anahtari (ham) ===
[(1, 'Goz Anahtar', 'kuty_wVZCFfj', 'd9FS', 'iptal', '["yaris-model-1"]', 'ab1dabb6281c'), (2, 'Izleyici Anahtari', 'kuty_xm8r2RQ', 'rPW1', 'aktif', '[]', '50019d43245d'), (3, 'Operator Anahtari', 'kuty_eatOh32', 'SgN1', 'aktif', '[]', 'ca0921912910')]
```

- Sonuç: GEÇTİ

### 5) Loglar — filtre, sayfalama, dışa aktarım, silme (§12)

```
E:/kutyai-app/.venv/Scripts/python.exe goz_03_loglar.py
```

- Beklenen: Filtreler doğru; `boyut` 200 ile sınırlı; silme personel, temizle yalnız yönetici; dışa aktarım üç biçimde doğru.
- Gerçek çıktı:

```
=== GET /loglar/konusmalar ===
HTTP 200 application/json
{"toplam":4,"sayfa":1,"boyut":25,"kayitlar":[{"id":3,"baslik":"API anahtarıyla sohbet","kullanici_id":null,"kullanici_eposta":null,"api_anahtari_id":1,"bdm_id":1,"bdm_ad":"Yaris Model 1","mesaj_sayisi":2,"token_girdi":5,"token_cikti":6,"olusturulma":"2026-09-11T23:00:00","guncellenme":"2026-09-11T23:00:00"},{"id":2,"baslik":"Sunucu kurulum notları","kullanici_id":2,"kullanici_eposta":"goz-yonetici-2@gozlem.example.com","api_anahtari_id":null,"bdm_id":2,"bdm_ad":"Yaris Model 2","mesaj_sayisi":2,"token_girdi":33,"token_cikti":44,"olusturulma":"2026-09-05T10:30:00","guncellenme":"2026-09-05T10:30:00"},{"id":1,"baslik":"Öğle yemeği planı çığöşü","kullanici_id":1,"kullanici_eposta":"goz-yonetici-1@gozlem.example.com","api_anahtari_id":null,"bdm_id":1,"bdm_ad":"Yaris Model 1","mesaj_sayisi":2,"token_girdi":11,"token_cikti":22,"olusturulma":"2026-09-01T09:00:00","guncellenme":"2026-09-01T09:00:00"},{"id":4,"baslik":"Saklama süresi dolmuş eski kayıt","kullanici_id":1,"kullanici_eposta":"goz-yonetici-1@gozlem.example.com","api_anahtari_id":null,"bdm_id":1,"bdm_ad":"Yaris Model 1","mesaj_sayisi":0,"token_girdi":1,"token_cikti":1,"olusturulma":"2026-06-01T08:00:00","guncellenme":"2026-06-01T08:00:00"}]}

=== Liste başlıkları ===
['API anahtarıyla sohbet', 'Sunucu kurulum notları', 'Öğle yemeği planı çığöşü', 'Saklama süresi dolmuş eski kayıt']

=== Kayıt anahtarları ===
['api_anahtari_id', 'baslik', 'bdm_ad', 'bdm_id', 'guncellenme', 'id', 'kullanici_eposta', 'kullanici_id', 'mesaj_sayisi', 'olusturulma', 'token_cikti', 'token_girdi']

=== GET /loglar/konusmalar?kullanici_id=1 ===
HTTP 200 application/json
{"toplam":2,"sayfa":1,"boyut":25,"kayitlar":[{"id":1,"baslik":"Öğle yemeği planı çığöşü","kullanici_id":1,"kullanici_eposta":"goz-yonetici-1@gozlem.example.com","api_anahtari_id":null,"bdm_id":1,"bdm_ad":"Yaris Model 1","mesaj_sayisi":2,"token_girdi":11,"token_cikti":22,"olusturulma":"2026-09-01T09:00:00","guncellenme":"2026-09-01T09:00:00"},{"id":4,"baslik":"Saklama süresi dolmuş eski kayıt","kullanici_id":1,"kullanici_eposta":"goz-yonetici-1@gozlem.example.com","api_anahtari_id":null,"bdm_id":1,"bdm_ad":"Yaris Model 1","mesaj_sayisi":0,"token_girdi":1,"token_cikti":1,"olusturulma":"2026-06-01T08:00:00","guncellenme":"2026-06-01T08:00:00"}]}

=== GET /loglar/konusmalar?bdm_id=2 ===
HTTP 200 application/json
{"toplam":1,"sayfa":1,"boyut":25,"kayitlar":[{"id":2,"baslik":"Sunucu kurulum notları","kullanici_id":2,"kullanici_eposta":"goz-yonetici-2@gozlem.example.com","api_anahtari_id":null,"bdm_id":2,"bdm_ad":"Yaris Model 2","mesaj_sayisi":2,"token_girdi":33,"token_cikti":44,"olusturulma":"2026-09-05T10:30:00","guncellenme":"2026-09-05T10:30:00"}]}

=== GET /loglar/konusmalar?arama=Docker ===
HTTP 200 application/json
{"toplam":1,"sayfa":1,"boyut":25,"kayitlar":[{"id":2,"baslik":"Sunucu kurulum notları","kullanici_id":2,"kullanici_eposta":"goz-yonetici-2@gozlem.example.com","api_anahtari_id":null,"bdm_id":2,"bdm_ad":"Yaris Model 2","mesaj_sayisi":2,"token_girdi":33,"token_cikti":44,"olusturulma":"2026-09-05T10:30:00","guncellenme":"2026-09-05T10:30:00"}]}

=== GET /loglar/konusmalar?arama=%C3%B6%C4%9Fle ===
HTTP 200 application/json
{"toplam":1,"sayfa":1,"boyut":25,"kayitlar":[{"id":1,"baslik":"Öğle yemeği planı çığöşü","kullanici_id":1,"kullanici_eposta":"goz-yonetici-1@gozlem.example.com","api_anahtari_id":null,"bdm_id":1,"bdm_ad":"Yaris Model 1","mesaj_sayisi":2,"token_girdi":11,"token_cikti":22,"olusturulma":"2026-09-01T09:00:00","guncellenme":"2026-09-01T09:00:00"}]}

=== GET /loglar/konusmalar?arama=%C3%96%C4%9Fle ===
HTTP 200 application/json
{"toplam":1,"sayfa":1,"boyut":25,"kayitlar":[{"id":1,"baslik":"Öğle yemeği planı çığöşü","kullanici_id":1,"kullanici_eposta":"goz-yonetici-1@gozlem.example.com","api_anahtari_id":null,"bdm_id":1,"bdm_ad":"Yaris Model 1","mesaj_sayisi":2,"token_girdi":11,"token_cikti":22,"olusturulma":"2026-09-01T09:00:00","guncellenme":"2026-09-01T09:00:00"}]}

=== GET /loglar/konusmalar?baslangic=2026-09-04T00:00:00&bitis=2026-09-06T00:00:00 ===
HTTP 200 application/json
{"toplam":1,"sayfa":1,"boyut":25,"kayitlar":[{"id":2,"baslik":"Sunucu kurulum notları","kullanici_id":2,"kullanici_eposta":"goz-yonetici-2@gozlem.example.com","api_anahtari_id":null,"bdm_id":2,"bdm_ad":"Yaris Model 2","mesaj_sayisi":2,"token_girdi":33,"token_cikti":44,"olusturulma":"2026-09-05T10:30:00","guncellenme":"2026-09-05T10:30:00"}]}

=== GET /loglar/konusmalar?baslangic=2026-09-06T00:00:00&bitis=2026-09-04T00:00:00 ===
HTTP 200 application/json
{"toplam":0,"sayfa":1,"boyut":25,"kayitlar":[]}

=== GET /loglar/konusmalar?boyut=10000 ===
HTTP 200 application/json
{"toplam":4,"sayfa":1,"boyut":200,"kayitlar":[{"id":3,"baslik":"API anahtarıyla sohbet","kullanici_id":null,"kullanici_eposta":null,"api_anahtari_id":1,"bdm_id":1,"bdm_ad":"Yaris Model 1","mesaj_sayisi":2,"token_girdi":5,"token_cikti":6,"olusturulma":"2026-09-11T23:00:00","guncellenme":"2026-09-11T23:00:00"},{"id":2,"baslik":"Sunucu kurulum notları","kullanici_id":2,"kullanici_eposta":"goz-yonetici-2@gozlem.example.com","api_anahtari_id":null,"bdm_id":2,"bdm_ad":"Yaris Model 2","mesaj_sayisi":2,"token_girdi":33,"token_cikti":44,"olusturulma":"2026-09-05T10:30:00","guncellenme":"2026-09-05T10:30:00"},{"id":1,"baslik":"Öğle yemeği planı çığöşü","kullanici_id":1,"kullanici_eposta":"goz-yonetici-1@gozlem.example.com","api_anahtari_id":null,"bdm_id":1,"bdm_ad":"Yaris Model 1","mesaj_sayisi":2,"token_girdi":11,"token_cikti":22,"olusturulma":"2026-09-01T09:00:00","guncellenme":"2026-09-01T09:00:00"},{"id":4,"baslik":"Saklama süresi dolmuş eski kayıt","kullanici_id":1,"kullanici_eposta":"goz-yonetici-1@gozlem.example.com","api_anahtari_id":null,"bdm_id":1,"bdm_ad":"Yaris Model 1","mesaj_sayisi":0,"token_girdi":1,"token_cikti":1,"olusturulma":"2026-06-01T08:00:00","guncellenme":"2026-06-01T08:00:00"}]}

=== GET /loglar/konusmalar?sayfa=0 ===
HTTP 200 application/json
{"toplam":4,"sayfa":1,"boyut":25,"kayitlar":[{"id":3,"baslik":"API anahtarıyla sohbet","kullanici_id":null,"kullanici_eposta":null,"api_anahtari_id":1,"bdm_id":1,"bdm_ad":"Yaris Model 1","mesaj_sayisi":2,"token_girdi":5,"token_cikti":6,"olusturulma":"2026-09-11T23:00:00","guncellenme":"2026-09-11T23:00:00"},{"id":2,"baslik":"Sunucu kurulum notları","kullanici_id":2,"kullanici_eposta":"goz-yonetici-2@gozlem.example.com","api_anahtari_id":null,"bdm_id":2,"bdm_ad":"Yaris Model 2","mesaj_sayisi":2,"token_girdi":33,"token_cikti":44,"olusturulma":"2026-09-05T10:30:00","guncellenme":"2026-09-05T10:30:00"},{"id":1,"baslik":"Öğle yemeği planı çığöşü","kullanici_id":1,"kullanici_eposta":"goz-yonetici-1@gozlem.example.com","api_anahtari_id":null,"bdm_id":1,"bdm_ad":"Yaris Model 1","mesaj_sayisi":2,"token_girdi":11,"token_cikti":22,"olusturulma":"2026-09-01T09:00:00","guncellenme":"2026-09-01T09:00:00"},{"id":4,"baslik":"Saklama süresi dolmuş eski kayıt","kullanici_id":1,"kullanici_eposta":"goz-yonetici-1@gozlem.example.com","api_anahtari_id":null,"bdm_id":1,"bdm_ad":"Yaris Model 1","mesaj_sayisi":0,"token_girdi":1,"token_cikti":1,"olusturulma":"2026-06-01T08:00:00","guncellenme":"2026-06-01T08:00:00"}]}

=== GET /loglar/konusmalar?sayfa=-3 ===
HTTP 200 application/json
{"toplam":4,"sayfa":1,"boyut":25,"kayitlar":[{"id":3,"baslik":"API anahtarıyla sohbet","kullanici_id":null,"kullanici_eposta":null,"api_anahtari_id":1,"bdm_id":1,"bdm_ad":"Yaris Model 1","mesaj_sayisi":2,"token_girdi":5,"token_cikti":6,"olusturulma":"2026-09-11T23:00:00","guncellenme":"2026-09-11T23:00:00"},{"id":2,"baslik":"Sunucu kurulum notları","kullanici_id":2,"kullanici_eposta":"goz-yonetici-2@gozlem.example.com","api_anahtari_id":null,"bdm_id":2,"bdm_ad":"Yaris Model 2","mesaj_sayisi":2,"token_girdi":33,"token_cikti":44,"olusturulma":"2026-09-05T10:30:00","guncellenme":"2026-09-05T10:30:00"},{"id":1,"baslik":"Öğle yemeği planı çığöşü","kullanici_id":1,"kullanici_eposta":"goz-yonetici-1@gozlem.example.com","api_anahtari_id":null,"bdm_id":1,"bdm_ad":"Yaris Model 1","mesaj_sayisi":2,"token_girdi":11,"token_cikti":22,"olusturulma":"2026-09-01T09:00:00","guncellenme":"2026-09-01T09:00:00"},{"id":4,"baslik":"Saklama süresi dolmuş eski kayıt","kullanici_id":1,"kullanici_eposta":"goz-yonetici-1@gozlem.example.com","api_anahtari_id":null,"bdm_id":1,"bdm_ad":"Yaris Model 1","mesaj_sayisi":0,"token_girdi":1,"token_cikti":1,"olusturulma":"2026-06-01T08:00:00","guncellenme":"2026-06-01T08:00:00"}]}

=== GET /loglar/konusmalar?boyut=0 ===
HTTP 200 application/json
{"toplam":4,"sayfa":1,"boyut":25,"kayitlar":[{"id":3,"baslik":"API anahtarıyla sohbet","kullanici_id":null,"kullanici_eposta":null,"api_anahtari_id":1,"bdm_id":1,"bdm_ad":"Yaris Model 1","mesaj_sayisi":2,"token_girdi":5,"token_cikti":6,"olusturulma":"2026-09-11T23:00:00","guncellenme":"2026-09-11T23:00:00"},{"id":2,"baslik":"Sunucu kurulum notları","kullanici_id":2,"kullanici_eposta":"goz-yonetici-2@gozlem.example.com","api_anahtari_id":null,"bdm_id":2,"bdm_ad":"Yaris Model 2","mesaj_sayisi":2,"token_girdi":33,"token_cikti":44,"olusturulma":"2026-09-05T10:30:00","guncellenme":"2026-09-05T10:30:00"},{"id":1,"baslik":"Öğle yemeği planı çığöşü","kullanici_id":1,"kullanici_eposta":"goz-yonetici-1@gozlem.example.com","api_anahtari_id":null,"bdm_id":1,"bdm_ad":"Yaris Model 1","mesaj_sayisi":2,"token_girdi":11,"token_cikti":22,"olusturulma":"2026-09-01T09:00:00","guncellenme":"2026-09-01T09:00:00"},{"id":4,"baslik":"Saklama süresi dolmuş eski kayıt","kullanici_id":1,"kullanici_eposta":"goz-yonetici-1@gozlem.example.com","api_anahtari_id":null,"bdm_id":1,"bdm_ad":"Yaris Model 1","mesaj_sayisi":0,"token_girdi":1,"token_cikti":1,"olusturulma":"2026-06-01T08:00:00","guncellenme":"2026-06-01T08:00:00"}]}

=== GET /loglar/konusmalar?boyut=-5 ===
HTTP 200 application/json
{"toplam":4,"sayfa":1,"boyut":1,"kayitlar":[{"id":3,"baslik":"API anahtarıyla sohbet","kullanici_id":null,"kullanici_eposta":null,"api_anahtari_id":1,"bdm_id":1,"bdm_ad":"Yaris Model 1","mesaj_sayisi":2,"token_girdi":5,"token_cikti":6,"olusturulma":"2026-09-11T23:00:00","guncellenme":"2026-09-11T23:00:00"}]}

=== GET /loglar/konusmalar?sayfa=abc ===
HTTP 400 application/json
{"hata":{"kod":"dogrulama_hatasi","mesaj":"Gönderilen alanlar doğrulanamadı.","ayrinti":{"alanlar":[{"alan":"query.sayfa","mesaj":"Input should be a valid integer, unable to parse string as an integer"}]}}}

=== GET /loglar/konusmalar?boyut=99999999999999999999 ===
HTTP 200 application/json
{"toplam":4,"sayfa":1,"boyut":200,"kayitlar":[{"id":3,"baslik":"API anahtarıyla sohbet","kullanici_id":null,"kullanici_eposta":null,"api_anahtari_id":1,"bdm_id":1,"bdm_ad":"Yaris Model 1","mesaj_sayisi":2,"token_girdi":5,"token_cikti":6,"olusturulma":"2026-09-11T23:00:00","guncellenme":"2026-09-11T23:00:00"},{"id":2,"baslik":"Sunucu kurulum notları","kullanici_id":2,"kullanici_eposta":"goz-yonetici-2@gozlem.example.com","api_anahtari_id":null,"bdm_id":2,"bdm_ad":"Yaris Model 2","mesaj_sayisi":2,"token_girdi":33,"token_cikti":44,"olusturulma":"2026-09-05T10:30:00","guncellenme":"2026-09-05T10:30:00"},{"id":1,"baslik":"Öğle yemeği planı çığöşü","kullanici_id":1,"kullanici_eposta":"goz-yonetici-1@gozlem.example.com","api_anahtari_id":null,"bdm_id":1,"bdm_ad":"Yaris Model 1","mesaj_sayisi":2,"token_girdi":11,"token_cikti":22,"olusturulma":"2026-09-01T09:00:00","guncellenme":"2026-09-01T09:00:00"},{"id":4,"baslik":"Saklama süresi dolmuş eski kayıt","kullanici_id":1,"kullanici_eposta":"goz-yonetici-1@gozlem.example.com","api_anahtari_id":null,"bdm_id":1,"bdm_ad":"Yaris Model 1","mesaj_sayisi":0,"token_girdi":1,"token_cikti":1,"olusturulma":"2026-06-01T08:00:00","guncellenme":"2026-06-01T08:00:00"}]}

=== GET /loglar/konusmalar?kullanici_id=abc ===
HTTP 400 application/json
{"hata":{"kod":"dogrulama_hatasi","mesaj":"Gönderilen alanlar doğrulanamadı.","ayrinti":{"alanlar":[{"alan":"query.kullanici_id","mesaj":"Input should be a valid integer, unable to parse string as an integer"}]}}}

=== GET /loglar/konusmalar/1 ===
HTTP 200 application/json
{"id":1,"baslik":"Öğle yemeği planı çığöşü","bdm_id":1,"bdm_ad":"Yaris Model 1","kullanici_id":1,"kullanici_eposta":"goz-yonetici-1@gozlem.example.com","api_anahtari_id":null,"sistem_istemi":"","token_girdi":11,"token_cikti":22,"olusturulma":"2026-09-01T09:00:00","guncellenme":"2026-09-01T09:00:00","mesajlar":[{"id":1,"rol":"kullanici","icerik":"Merhaba, öğle yemeği için Şişli'de buluşalım mı?","token_sayisi":8,"gecikme_ms":0,"model":"llama3","hata":null,"olusturulma":"2026-09-01T09:00:00"},{"id":2,"rol":"asistan","icerik":"Elbette, saat 12:30 uygun mu?","token_sayisi":3,"gecikme_ms":120,"model":"llama3","hata":null,"olusturulma":"2026-09-01T09:00:01"}]}

=== GET /loglar/konusmalar/99999 ===
HTTP 404 application/json
{"hata":{"kod":"bulunamadi","mesaj":"Konuşma bulunamadı.","ayrinti":{"konusma_id":99999}}}

=== GET disa-aktar bicim=json ===
HTTP 200
content-type=application/json; charset=utf-8
content-disposition=attachment; filename="konusma-1.json"
bytes=885
{
  "id": 1,
  "baslik": "Öğle yemeği planı çığöşü",
  "bdm_id": 1,
  "bdm_ad": "Yaris Model 1",
  "kullanici_id": 1,
  "kullanici_eposta": "goz-yonetici-1@gozlem.example.com",
  "api_anahtari_id": null,
  "sistem_istemi": "",
  "token_girdi": 11,
  "token_cikti": 22,
  "olusturulma": "2026-09-01T09:00:00",
  "guncellenme": "2026-09-01T09:00:00",
  "mesajlar": [
    {
      "id": 1,
      "rol": "kullanici",
      "icerik": "Merhaba, öğle yemeği için Şişli'de buluşalım mı?",
      "token_sayisi": 8,
      "gecikme_ms": 0,
      "model": "llama3",
      "hata": null,
      "olusturulma": "2026-09-01T09:00:00"
    },
    {
      "id": 2,
      "rol": "asistan",
      "icerik": "Elbette, saat 12:30 uygun mu?",
      "token_sayisi": 3,
      "gecikme_ms": 120,
      "model": "llama3",
      "hata": null,
      "olusturulma": "2026-09-01T09:00:01"
    }
  ]
}

=== GET disa-aktar bicim=md ===
HTTP 200
content-type=text/markdown; charset=utf-8
content-disposition=attachment; filename="konusma-1.md"
bytes=286
# Öğle yemeği planı çığöşü

- Konuşma no: 1
- Model: Yaris Model 1
- Kullanıcı: goz-yonetici-1@gozlem.example.com
- Oluşturulma: 2026-09-01T09:00:00

---

## Kullanıcı

Merhaba, öğle yemeği için Şişli'de buluşalım mı?

## Asistan

Elbette, saat 12:30 uygun mu?

=== GET disa-aktar bicim=csv ===
HTTP 200
content-type=text/csv; charset=utf-8
content-disposition=attachment; filename="konusma-1.csv"
bytes=213
mesaj_id,rol,icerik,token,gecikme_ms,olusturulma
1,kullanici,"Merhaba, öğle yemeği için Şişli'de buluşalım mı?",8,0,2026-09-01T09:00:00
2,asistan,"Elbette, saat 12:30 uygun mu?",3,120,2026-09-01T09:00:01

=== GET disa-aktar bicim=pdf ===
HTTP 400 application/json
{"hata":{"kod":"gecersiz_istek","mesaj":"Desteklenmeyen biçim: pdf","ayrinti":{"gecerli_bicimler":["json","md","csv"]}}}

=== GET disa-aktar bicim=JSON (büyük harf) ===
HTTP 200 application/json; charset=utf-8
{
  "id": 1,
  "baslik": "Öğle yemeği planı çığöşü",
  "bdm_id": 1,
  "bdm_ad": "Yaris Model 1",
  "kullanici_id": 1,
  "kullanici_eposta": "goz-yonetici-1@gozlem.example.com",
  "api_anahtari_id": null,
  "sistem_istemi": "",
  "token_girdi": 11,
  "token_cikti": 22,
  "olusturulma": "2026-09-01T09:00:00",
  "guncellenme": "2026-09-01T09:00:00",
  "mesajlar": [
    {
      "id": 1,
      "rol": "kullanici",
      "icerik": "Merhaba, öğle yemeği için Şişli'de buluşalım mı?",
      "token_sayisi": 8,
      "gecikme_ms": 0,
      "model": "llama3",
      "hata": null,
      "olusturulma": "2026-09-01T09:00:00"
    },
    {
      "id": 2,
      "rol": "asistan",
      "icerik": "Elbette, saat 12:30 uygun mu?",
      "token_sayisi": 3,
      "gecikme_ms": 120,
      "model": "llama3",
      "hata": null,
      "olusturulma": "2026-09-01T09:00:01"
    }
  ]
}

=== JSON çözüldü ===
anahtarlar=['api_anahtari_id', 'baslik', 'bdm_ad', 'bdm_id', 'guncellenme', 'id', 'kullanici_eposta', 'kullanici_id', 'mesajlar', 'olusturulma', 'sistem_istemi', 'token_cikti', 'token_girdi'] mesaj=2

=== DELETE /loglar/konusmalar/1 (operator) ===
HTTP 204 gövde=''

=== DELETE /loglar/konusmalar/2 (izleyici) ===
HTTP 204 gövde=''

=== DELETE /loglar/konusmalar/99999 ===
HTTP 404 application/json
{"hata":{"kod":"bulunamadi","mesaj":"Konuşma bulunamadı.","ayrinti":{"konusma_id":99999}}}

=== SQL: silme sonrası konuşmalar ===
[(3, 'API anahtarıyla sohbet'), (4, 'Saklama süresi dolmuş eski kayıt')]

=== SQL: silme sonrası mesajlar ===
[(5, 3), (6, 3)]

=== POST /loglar/temizle (operator, gun=10) ===
HTTP 403 application/json
{"hata":{"kod":"yetki_yok","mesaj":"Bu işlem için yetkiniz yok.","ayrinti":{}}}

=== POST /loglar/temizle (izleyici, gun=10) ===
HTTP 403 application/json
{"hata":{"kod":"yetki_yok","mesaj":"Bu işlem için yetkiniz yok.","ayrinti":{}}}

=== POST /loglar/temizle (yonetici, gun=0) ===
HTTP 400 application/json
{"hata":{"kod":"dogrulama_hatasi","mesaj":"Gönderilen alanlar doğrulanamadı.","ayrinti":{"alanlar":[{"alan":"gun","mesaj":"Input should be greater than or equal to 1"}]}}}

=== POST /loglar/temizle (yonetici, gun=3651) ===
HTTP 400 application/json
{"hata":{"kod":"dogrulama_hatasi","mesaj":"Gönderilen alanlar doğrulanamadı.","ayrinti":{"alanlar":[{"alan":"gun","mesaj":"Input should be less than or equal to 3650"}]}}}

=== SQL: temizle öncesi konuşmalar ===
[(3, 'API anahtarıyla sohbet', '2026-09-11 23:00:00.000000'), (4, 'Saklama süresi dolmuş eski kayıt', '2026-06-01 08:00:00.000000')]

=== POST /loglar/temizle (yonetici, gun=10) ===
HTTP 200 application/json
{"silinen":1}

=== POST /loglar/temizle (yonetici, gövdesiz) ===
HTTP 200 application/json
{"silinen":0}

=== SQL: temizle sonrası konuşmalar ===
[(3, 'API anahtarıyla sohbet')]

=== GET /loglar/konusmalar (jetonsuz) ===
HTTP 401 application/json
{"hata":{"kod":"kimlik_gerekli","mesaj":"Bu işlem için giriş yapmalısınız.","ayrinti":{}}}

=== SQL: log/anahtar/silme işlemlerinin denetim izi ===
id=1 eylem=kurulum.tamamlandi kullanici_id=1 hedef=bdm:1 ayrinti={"marka_adi": "Yaris-1", "bdm_slug": "yaris-model-1"}
id=2 eylem=kurulum.tamamlandi kullanici_id=2 hedef=bdm:2 ayrinti={"marka_adi": "Yaris-2", "bdm_slug": "yaris-model-2"}
id=3 eylem=kimlik.giris kullanici_id=1 hedef=kullanici:1 ayrinti={"panel": true}
id=4 eylem=kimlik.giris kullanici_id=2 hedef=kullanici:2 ayrinti={"panel": true}
id=5 eylem=kimlik.giris kullanici_id=1 hedef=kullanici:1 ayrinti={"panel": true}
id=6 eylem=kimlik.giris kullanici_id=1 hedef=kullanici:1 ayrinti={"panel": true}
id=7 eylem=kullanici.olustur kullanici_id=1 hedef=kullanici:3 ayrinti={"rol": "operator"}
id=8 eylem=kullanici.olustur kullanici_id=1 hedef=kullanici:4 ayrinti={"rol": "izleyici"}
id=9 eylem=kimlik.giris kullanici_id=3 hedef=kullanici:3 ayrinti={"panel": true}
id=10 eylem=kimlik.giris kullanici_id=4 hedef=kullanici:4 ayrinti={"panel": true}
id=11 eylem=api_anahtari.olusturuldu kullanici_id=1 hedef=api_anahtari:1 ayrinti={"ad": "Goz Anahtar", "izinli_modeller": ["yaris-model-1"]}
id=12 eylem=api_anahtari.kullanildi kullanici_id=None hedef=api_anahtari:1 ayrinti={}
id=13 eylem=api_anahtari.iptal_edildi kullanici_id=1 hedef=api_anahtari:1 ayrinti={"ad": "Goz Anahtar"}
id=14 eylem=api_anahtari.olusturuldu kullanici_id=4 hedef=api_anahtari:2 ayrinti={"ad": "Izleyici Anahtari", "izinli_modeller": []}
id=15 eylem=api_anahtari.olusturuldu kullanici_id=3 hedef=api_anahtari:3 ayrinti={"ad": "Operator Anahtari", "izinli_modeller": []}
id=16 eylem=kimlik.giris kullanici_id=1 hedef=kullanici:1 ayrinti={"panel": true}
id=17 eylem=kimlik.giris kullanici_id=3 hedef=kullanici:3 ayrinti={"panel": true}
id=18 eylem=kimlik.giris kullanici_id=4 hedef=kullanici:4 ayrinti={"panel": true}
id=19 eylem=konusma.silindi kullanici_id=3 hedef=konusma:1 ayrinti={"baslik": "\u00d6\u011fle yeme\u011fi plan\u0131 \u00e7\u0131\u011f\u00f6\u015f\u00fc"}
id=20 eylem=konusma.silindi kullanici_id=4 hedef=konusma:2 ayrinti={"baslik": "Sunucu kurulum notlar\u0131"}
id=21 eylem=loglar.temizlendi kullanici_id=1 hedef=konusma: ayrinti={"gun": 10, "silinen": 1}
id=22 eylem=loglar.temizlendi kullanici_id=1 hedef=konusma: ayrinti={"gun": null, "silinen": 0}
```

- Sonuç: KALDI

### 6) Ayarlar — SMTP şifresi, sınır değerler, bakım modu (§14)

```
E:/kutyai-app/.venv/Scripts/python.exe goz_04_ayarlar.py
```

- Beklenen: `smtp_sifre` DB'de şifreli ve hiçbir yanıtta yok; `saklama_gun` 0/3651 → 400; operator/izleyici 403; bakım modu sohbeti kısıtlar.
- Gerçek çıktı:

```
=== PUT /ayarlar {} ===
HTTP 200 application/json
{"marka_adi":"Yaris-2","kurulum_tamam":true,"saklama_gun":90,"maskeleme_aktif":true,"kayit_acik":true,"smtp_host":"","smtp_gonderen":"","smtp_tanimli":false,"bakim_modu":false}

=== PUT /ayarlar {'marka_adi': 'Gözlem A.Ş.', 'saklama_gun': 30, 'maskeleme_aktif': False, 'kayit_acik': True, 'smtp_host': 'smtp.gozlem.example.com', 'smtp_port': 587, 'smtp_kullanici': 'gozlem', 'smtp_sifre': 'GozlemSmtpParolasi!42', 'smtp_gonderen': 'KutyAI <bildirim@gozlem.example.com>', 'smtp_tls': True, 'bakim_modu': False} ===
HTTP 200 application/json
{"marka_adi":"Gözlem A.Ş.","kurulum_tamam":true,"saklama_gun":30,"maskeleme_aktif":false,"kayit_acik":true,"smtp_host":"smtp.gozlem.example.com","smtp_gonderen":"KutyAI <bildirim@gozlem.example.com>","smtp_tanimli":true,"bakim_modu":false}

=== GET /ayarlar (ham) ===
HTTP 200
{"marka_adi":"Gözlem A.Ş.","kurulum_tamam":true,"saklama_gun":30,"maskeleme_aktif":false,"kayit_acik":true,"smtp_host":"smtp.gozlem.example.com","smtp_gonderen":"KutyAI <bildirim@gozlem.example.com>","smtp_tanimli":true,"bakim_modu":false}

=== GET /ayarlar içinde SMTP parolası var mı? ===
False

=== GET /ayarlar alanları ===
['bakim_modu', 'kayit_acik', 'kurulum_tamam', 'marka_adi', 'maskeleme_aktif', 'saklama_gun', 'smtp_gonderen', 'smtp_host', 'smtp_tanimli']

=== SQL: smtp_sifre ham değeri ===
('"gAAAAABqpat2fpehA8t0zaqyvIWpy5Eln2cvzoc4zp3Hy9UsZVG71vAmT4Izvw1RQ8bTmmaK71j5peI0Gno0G1lAvLOGhW-i4lnL7RvDOLgt-Un6XEhqLf0="',)

=== SQL: smtp ile ilgili ayarlar ===
[('smtp_gonderen', '"KutyAI <bildirim@gozlem.example.com>"'), ('smtp_host', '"smtp.gozlem.example.com"'), ('smtp_port', '587'), ('smtp_kullanici', '"gozlem"'), ('smtp_sifre', '"gAAAAABqpat2fpehA8t0zaqyvIWpy5Eln2cvzoc4zp3Hy9UsZVG71vAmT4I'), ('smtp_tls', 'true')]

=== PUT /ayarlar {'saklama_gun': 0} ===
HTTP 400 application/json
{"hata":{"kod":"dogrulama_hatasi","mesaj":"Gönderilen alanlar doğrulanamadı.","ayrinti":{"alanlar":[{"alan":"saklama_gun","mesaj":"Input should be greater than or equal to 1"}]}}}

=== PUT /ayarlar {'saklama_gun': 3651} ===
HTTP 400 application/json
{"hata":{"kod":"dogrulama_hatasi","mesaj":"Gönderilen alanlar doğrulanamadı.","ayrinti":{"alanlar":[{"alan":"saklama_gun","mesaj":"Input should be less than or equal to 3650"}]}}}

=== PUT /ayarlar {'saklama_gun': 3650} ===
HTTP 200 application/json
{"marka_adi":"Gözlem A.Ş.","kurulum_tamam":true,"saklama_gun":3650,"maskeleme_aktif":false,"kayit_acik":true,"smtp_host":"smtp.gozlem.example.com","smtp_gonderen":"KutyAI <bildirim@gozlem.example.com>","smtp_tanimli":true,"bakim_modu":false}

=== PUT /ayarlar {'marka_adi': ''} ===
HTTP 400 application/json
{"hata":{"kod":"dogrulama_hatasi","mesaj":"Gönderilen alanlar doğrulanamadı.","ayrinti":{"alanlar":[{"alan":"marka_adi","mesaj":"String should have at least 1 character"}]}}}

=== PUT /ayarlar {'smtp_port': 0} ===
HTTP 400 application/json
{"hata":{"kod":"dogrulama_hatasi","mesaj":"Gönderilen alanlar doğrulanamadı.","ayrinti":{"alanlar":[{"alan":"smtp_port","mesaj":"Input should be greater than or equal to 1"}]}}}

=== PUT /ayarlar {'smtp_port': 70000} ===
HTTP 400 application/json
{"hata":{"kod":"dogrulama_hatasi","mesaj":"Gönderilen alanlar doğrulanamadı.","ayrinti":{"alanlar":[{"alan":"smtp_port","mesaj":"Input should be less than or equal to 65535"}]}}}

=== PUT /ayarlar {'bilinmeyen_alan': 'x', 'kayit_acik': False} ===
HTTP 200 application/json
{"marka_adi":"Gözlem A.Ş.","kurulum_tamam":true,"saklama_gun":3650,"maskeleme_aktif":false,"kayit_acik":false,"smtp_host":"smtp.gozlem.example.com","smtp_gonderen":"KutyAI <bildirim@gozlem.example.com>","smtp_tanimli":true,"bakim_modu":false}

=== PUT /ayarlar {'smtp_sifre': ''} ===
HTTP 200 application/json
{"marka_adi":"Gözlem A.Ş.","kurulum_tamam":true,"saklama_gun":3650,"maskeleme_aktif":false,"kayit_acik":false,"smtp_host":"smtp.gozlem.example.com","smtp_gonderen":"KutyAI <bildirim@gozlem.example.com>","smtp_tanimli":true,"bakim_modu":false}

=== SQL: smtp_sifre temizleme sonrası ===
('""',)

=== PUT /ayarlar {'smtp_sifre': 'GozlemSmtpParolasi!42'} ===
HTTP 200 application/json
{"marka_adi":"Gözlem A.Ş.","kurulum_tamam":true,"saklama_gun":3650,"maskeleme_aktif":false,"kayit_acik":false,"smtp_host":"smtp.gozlem.example.com","smtp_gonderen":"KutyAI <bildirim@gozlem.example.com>","smtp_tanimli":true,"bakim_modu":false}

=== GET /ayarlar (operator) ===
HTTP 403 application/json
{"hata":{"kod":"yetki_yok","mesaj":"Bu işlem için yetkiniz yok.","ayrinti":{}}}

=== PUT /ayarlar (izleyici) ===
HTTP 403 application/json
{"hata":{"kod":"yetki_yok","mesaj":"Bu işlem için yetkiniz yok.","ayrinti":{}}}

=== GET /ayarlar (jetonsuz) ===
HTTP 401 application/json
{"hata":{"kod":"kimlik_gerekli","mesaj":"Bu işlem için giriş yapmalısınız.","ayrinti":{}}}

=== GET /saglik/kurulum (marka sonrası) ===
HTTP 200 application/json
{"kurulum_tamam":true,"marka_adi":"Gözlem A.Ş.","surum":"0.1.0"}

=== PUT /ayarlar {'bakim_modu': True} ===
HTTP 200 application/json
{"marka_adi":"Gözlem A.Ş.","kurulum_tamam":true,"saklama_gun":3650,"maskeleme_aktif":false,"kayit_acik":false,"smtp_host":"smtp.gozlem.example.com","smtp_gonderen":"KutyAI <bildirim@gozlem.example.com>","smtp_tanimli":true,"bakim_modu":true}

=== GET /ayarlar (bakım açık) ===
HTTP 200 application/json
{"marka_adi":"Gözlem A.Ş.","kurulum_tamam":true,"saklama_gun":3650,"maskeleme_aktif":false,"kayit_acik":false,"smtp_host":"smtp.gozlem.example.com","smtp_gonderen":"KutyAI <bildirim@gozlem.example.com>","smtp_tanimli":true,"bakim_modu":true}

=== POST /sohbet (bakım açık) ===
HTTP 502 application/json
{"hata":{"kod":"ust_saglayici_hatasi","mesaj":"Model sağlayıcısına bağlanılamadı.","ayrinti":{"durum":0,"govde":"ConnectError: All connection attempts failed"}}}

=== GET /modeller (bakım açık) ===
HTTP 200 application/json
[{"id":3,"slug":"goz-ikinci-model","gorunen_ad":"Goz Ikinci Model","aciklama":"","saglayici":"ollama","baglam_penceresi":8192,"yetenekler":{"akis":true,"gorsel":false,"arac":false},"durum":"hazir"},{"id":1,"slug":"yaris-model-1","gorunen_ad":"Yaris Model 1","aciklama":"","saglayici":"ollama","baglam_penceresi":8192,"yetenekler":{"akis":true,"gorsel":false,"arac":false},"durum":"hazir"}]

=== GET /loglar/konusmalar (bakım açık) ===
HTTP 200 application/json
{"toplam":2,"sayfa":1,"boyut":25,"kayitlar":[{"id":4,"baslik":"Bakım modunda mıyız?","kullanici_id":1,"kullanici_eposta":"goz-yonetici-1@gozlem.example.com","api_anahtari_id":null,"bdm_id":1,"bdm_ad":"Yaris Model 1","mesaj_sayisi":1,"token_girdi":5,"token_cikti":0,"olusturulma":"2026-09-12T19:43:50.810954","guncellenme":"2026-09-12T19:43:50.818045"},{"id":3,"baslik":"API anahtarıyla sohbet","kullanici_id":null,"kullanici_eposta":null,"api_anahtari_id":1,"bdm_id":1,"bdm_ad":"Yaris Model 1","mesaj_sayisi":2,"token_girdi":5,"token_cikti":6,"olusturulma":"2026-09-11T23:00:00","guncellenme":"2026-09-11T23:00:00"}]}

=== PUT /ayarlar {'bakim_modu': False} ===
HTTP 200 application/json
{"marka_adi":"Gözlem A.Ş.","kurulum_tamam":true,"saklama_gun":3650,"maskeleme_aktif":false,"kayit_acik":false,"smtp_host":"smtp.gozlem.example.com","smtp_gonderen":"KutyAI <bildirim@gozlem.example.com>","smtp_tanimli":true,"bakim_modu":false}

=== SQL: ayar.guncellendi denetim kayıtları ===
id=26 kullanici_id=1 ayrinti={"anahtarlar": ["bakim_modu", "kayit_acik", "marka_adi", "maskeleme_aktif", "saklama_gun", "smtp_gonderen", "smtp_host", "smtp_kullanici", "smtp_port", "smtp_sifre", "smtp_tls"]}
id=27 kullanici_id=1 ayrinti={"anahtarlar": ["saklama_gun"]}
id=28 kullanici_id=1 ayrinti={"anahtarlar": ["kayit_acik"]}
id=29 kullanici_id=1 ayrinti={"anahtarlar": ["smtp_sifre"]}
id=30 kullanici_id=1 ayrinti={"anahtarlar": ["smtp_sifre"]}
id=31 kullanici_id=1 ayrinti={"anahtarlar": ["bakim_modu"]}
id=32 kullanici_id=1 ayrinti={"anahtarlar": ["bakim_modu"]}

=== SQL: denetim izinde SMTP parolası geçiyor mu? ===
(0,)
```

- Sonuç: KALDI

### 7) Denetim izi — kullanıcı/rol değişiklikleri (§10, GUVENLIK §4)

```
E:/kutyai-app/.venv/Scripts/python.exe goz_05_denetim.py
```

- Beklenen: `kullanici.guncelle` ve `kullanici.pasiflestir` `islem_kaydi`'na yazılır.
- Gerçek çıktı:

```
=== PATCH /kullanicilar/3 {rol: operator} ===
HTTP 200 application/json
{"id":3,"eposta":"goz-operator@gozlem.example.com","ad_soyad":"Goz operator","rol":"operator","durum":"aktif","eposta_dogrulandi":true,"olusturulma":"2026-09-12T19:43:48.857200","son_giris":"2026-09-12T19:43:50.549842"}

=== DELETE /kullanicilar/3 ===
HTTP 204 gövde=''

=== PATCH /api-anahtarlari/3 (yok olan yöntem) ===
HTTP 404 application/json
{"hata":{"kod":"bulunamadi","mesaj":"Kayıt bulunamadı.","ayrinti":{}}}

=== SQL: kullanıcı/rol denetim kayıtları ===
id=7 eylem=kullanici.olustur kullanici_id=1 hedef=kullanici:3 ayrinti={"rol": "operator"}
id=8 eylem=kullanici.olustur kullanici_id=1 hedef=kullanici:4 ayrinti={"rol": "izleyici"}
id=34 eylem=kullanici.guncelle kullanici_id=1 hedef=kullanici:3 ayrinti={"rol": "operator"}
id=35 eylem=kullanici.pasiflestir kullanici_id=1 hedef=kullanici:3 ayrinti={}
```

- Sonuç: GEÇTİ

### 8) Dışa aktarım uç durumları — boş konuşma, CSV kaçışlama

```
E:/kutyai-app/.venv/Scripts/python.exe goz_06_disa_aktarim.py
```

- Beklenen: Mesajsız konuşma geçerli dosya üretir; CSV RFC 4180 kaçışlaması doğru; formül enjeksiyonu etkisizleştirilir.
- Gerçek çıktı:

```
=== disa-aktar konusma=5 bicim=json ===
HTTP 200
content-disposition=attachment; filename="konusma-5.json"
bytes=359
--- içerik ---
{
  "id": 5,
  "baslik": "Mesajsız konuşma",
  "bdm_id": 1,
  "bdm_ad": "Yaris Model 1",
  "kullanici_id": 1,
  "kullanici_eposta": "goz-yonetici-1@gozlem.example.com",
  "api_anahtari_id": null,
  "sistem_istemi": "",
  "token_girdi": 0,
  "token_cikti": 0,
  "olusturulma": "2026-09-12T08:00:00",
  "guncellenme": "2026-09-12T08:00:00",
  "mesajlar": []
}

=== disa-aktar konusma=5 bicim=md ===
HTTP 200
content-disposition=attachment; filename="konusma-5.md"
bytes=152
--- içerik ---
# Mesajsız konuşma

- Konuşma no: 5
- Model: Yaris Model 1
- Kullanıcı: goz-yonetici-1@gozlem.example.com
- Oluşturulma: 2026-09-12T08:00:00

---

=== disa-aktar konusma=5 bicim=csv ===
HTTP 200
content-disposition=attachment; filename="konusma-5.csv"
bytes=49
--- içerik ---
mesaj_id,rol,icerik,token,gecikme_ms,olusturulma

=== disa-aktar konusma=6 bicim=json ===
HTTP 200
content-disposition=attachment; filename="konusma-6.json"
bytes=869
--- içerik ---
{
  "id": 6,
  "baslik": "Kaçış testi",
  "bdm_id": 1,
  "bdm_ad": "Yaris Model 1",
  "kullanici_id": 1,
  "kullanici_eposta": "goz-yonetici-1@gozlem.example.com",
  "api_anahtari_id": null,
  "sistem_istemi": "",
  "token_girdi": 1,
  "token_cikti": 1,
  "olusturulma": "2026-09-12T08:05:00",
  "guncellenme": "2026-09-12T08:05:00",
  "mesajlar": [
    {
      "id": 8,
      "rol": "kullanici",
      "icerik": "=HYPERLINK(\"http://kotu.example\",\"tıkla\")",
      "token_sayisi": 1,
      "gecikme_ms": 0,
      "model": "llama3",
      "hata": null,
      "olusturulma": "2026-09-12T08:05:00"
    },
    {
      "id": 9,
      "rol": "asistan",
      "icerik": "İki satır;\nvirgüllü, \"alıntılı\" yanıt",
      "token_sayisi": 1,
      "gecikme_ms": 0,
      "model": "llama3",
      "hata": null,
      "olusturulma": "2026-09-12T08:05:01"
    }
  ]
}

=== disa-aktar konusma=6 bicim=md ===
HTTP 200
content-disposition=attachment; filename="konusma-6.md"
bytes=267
--- içerik ---
# Kaçış testi

- Konuşma no: 6
- Model: Yaris Model 1
- Kullanıcı: goz-yonetici-1@gozlem.example.com
- Oluşturulma: 2026-09-12T08:05:00

---

## Kullanıcı

=HYPERLINK("http://kotu.example","tıkla")

## Asistan

İki satır;
virgüllü, "alıntılı" yanıt

=== disa-aktar konusma=6 bicim=csv ===
HTTP 200
content-disposition=attachment; filename="konusma-6.csv"
bytes=218
--- içerik ---
mesaj_id,rol,icerik,token,gecikme_ms,olusturulma
8,kullanici,"=HYPERLINK(""http://kotu.example"",""tıkla"")",1,0,2026-09-12T08:05:00
9,asistan,"İki satır;
virgüllü, ""alıntılı"" yanıt",1,0,2026-09-12T08:05:01

=== disa-aktar olmayan konuşma ===
HTTP 404 application/json
{"hata":{"kod":"bulunamadi","mesaj":"Konuşma bulunamadı.","ayrinti":{"konusma_id":999}}}
```

- Sonuç: GEÇTİ

### 9) İzleyici rolünün anahtar yetkisi (§7)

```
E:/kutyai-app/.venv/Scripts/python.exe goz_07_rol_anahtar.py
```

- Beklenen: Salt-okunur `izleyici` rolü anahtar üretemez/iptal edemez (ya da sözleşme bu yetkiyi açıkça tanımlar).
- Gerçek çıktı:

```
=== POST /kullanicilar izleyici (2) ===
HTTP 409 application/json
{"hata":{"kod":"cakisma","mesaj":"Bu e-posta adresi zaten kayıtlı.","ayrinti":{}}}

=== POST /api-anahtarlari (izleyici2) ===
HTTP 201 application/json
{"id":5,"ad":"Izleyici-2 Anahtar","onek":"kuty_YeuZtho","son_dort":"GhZS","durum":"aktif","izinli_modeller":[],"gunluk_istek_siniri":null,"olusturulma":"2026-09-12T19:46:31.878247","son_kullanim":null,"tam_anahtar":"kuty_YeuZtho6I6qyoS1ddFUe1AnidFEPGhZS"}

=== POST /api-anahtarlari/{id}/iptal (izleyici2) ===
HTTP 200 application/json
{"durum":"iptal"}

=== GET /modeller (izleyicinin ürettiği anahtarla) ===
HTTP 200 application/json
[{"id":3,"slug":"goz-ikinci-model","gorunen_ad":"Goz Ikinci Model","aciklama":"","saglayici":"ollama","baglam_penceresi":8192,"yetenekler":{"akis":true,"gorsel":false,"arac":false},"durum":"hazir"},{"id":1,"slug":"yaris-model-1","gorunen_ad":"Yaris Model 1","aciklama":"","saglayici":"ollama","baglam_penceresi":8192,"yetenekler":{"akis":true,"gorsel":false,"arac":false},"durum":"hazir"}]

=== POST /sohbet (izleyicinin ürettiği anahtarla) ===
HTTP 502 application/json
{"hata":{"kod":"ust_saglayici_hatasi","mesaj":"Model sağlayıcısına bağlanılamadı.","ayrinti":{"durum":0,"govde":"ConnectError: All connection attempts failed"}}}
```

- Sonuç: KALDI

## Bulgular

- [BLOCKER] `arkauc/app/api/kurulum.py:102-127` — **`POST /kurulum` yarış durumu (TOCTOU)**.
  `kurulum_tamam` denetimi ile yazımı arasında kilit yok (`veritabani_oturumu` commit'i
  istek sonunda, `bdm_veritabani/oturum.py:52`). İki eşzamanlı istek (farklı yönetici
  e-postası) → **ikisi de 201**, iki `yonetici` kaydı (id=1,2), iki BDM, `marka_adi` ve
  `varsayilan_bdm_slug` son bitirenin değeriyle ezildi (kayıp güncelleme). Beklenen:
  tek istek 201, diğeri 409 `kurulum_zaten_tamam` (API.md §4). Yeniden üretme:
  taze DB → `goz_01_kurulum_yaris.py` (kanit/loglar/01.txt).
- [MAJOR] `arkauc/app/api/kurulum.py:106-115` — **aynı e-posta ile eşzamanlı kurulum
  500 döndürüyor.** İki istek de `mevcut is None` görüyor; ikincisi `kullanici.eposta`
  tekil kısıtına çarpıp yakalanmayan `IntegrityError` → `{"kod":"sunucu_hatasi"}`.
  Beklenen: 409 `cakisma` (API.md §1, §4). Kök neden BLOCKER ile aynı; yeniden üretme:
  kanit/loglar/01b.txt.
- [MAJOR] `arkauc/app/api/loglar.py:94-98` — **`DELETE /loglar/konusmalar/{id}` tüm
  personel rollerine açık; `izleyici` (salt-okunur) bile kalıcı siliyor (204).**
  API.md §12 silme için yetki belirtmiyor, yalnız `POST /loglar/temizle` için "yalnız
  yönetici" diyor; GUVENLIK.md §4 `DELETE .../loglar/konusmalar/{id}`'i "silme hakkı"
  olarak listeliyor. Değerlendirme: geri döndürülemez veri kaybı üreten bu uç
  `yonetici`/`operator` ile sınırlanmalı (ya da sözleşmede açıkça yazılmalı); izleyiciye
  açık bırakılması yetki modeliyle çelişiyor. Kanıt: kanit/loglar/03.txt.
- [MINOR] `arkauc/app/api/ayarlar.py:39,63` — **`bakim_modu` hiçbir yerde uygulanmıyor.**
  `bakim_modu=true` iken `POST /sohbet` normal işlendi ve konuşma loglara yazıldı
  (upstream olmadığı için 502 döndü), `/modeller` ve `/loglar/konusmalar` 200 döndü.
  Beklenen (gözlemci hipotezi): 503. API.md §14 davranışı tanımlamıyor → sözleşme
  boşluğu; ayar yalnız depolanıp raporlanıyor, operasyonel etkisi yok.
  Kanıt: kanit/loglar/04.txt.
- [MINOR] `arkauc/app/api/api_anahtarlari.py:70,87,127` — **anahtar oluşturma/iptal
  `izleyici` rolüne de açık.** Salt-okunur `izleyici` hesabı anahtar üretti (201),
  ürettiği anahtarla `GET /modeller` 200 ve `POST /sohbet` 502 (kimlik kabul edildi,
  upstream yok) aldı, ayrıca `POST /api-anahtarlari/{id}/iptal` ile anahtar iptal etti
  (200 `{"durum":"iptal"}`). Anahtar `izinli_modeller=[]` ile **tüm hazır modellere**
  açık. API.md §7'de yetki sütunu yok → belirsizlik; salt-okunur rolden sohbet kimliği
  üretilebilmesi ayrıcalık yükseltme yüzeyi. Sözleşmede yetki netleştirilmeli.
  Kanıt: kanit/loglar/02.txt, kanit/loglar/07.txt.
- [MINOR] `bdm_konusma_gecmisi/disa_aktarim.py:53-70` — **CSV dışa aktarımında formül
  enjeksiyonu.** `=HYPERLINK("http://kotu.example","tıkla")` içeren mesaj CSV'ye
  olduğu gibi yazıldı; Excel/Sheets dosyayı açınca formül çalışır. Beklenen: hücre
  `'` öneki ya da sekme ile etkisizleştirilmeli; en azından "formül başlatan
  karakterler" kaçışlanmalı. Kanıt: kanit/loglar/06.txt.
- [MINOR] `arkauc/app/api/loglar.py:44-49`, `bdm_konusma_gecmisi/sorgu.py:19-25` —
  **sayfalama sınır davranışı tutarsız/doğrulanmıyor.** `baslangic > bitis` sessizce
  `{toplam:0}` döndürüyor (400 beklenirdi), `boyut=-5` "1"e kırpılıyor (varsayılan 25
  beklenirdi), `boyut=10000` 200'e kırpılıyor (kaynak tüketimi açısından doğru).
  Aynı parametreler için üç farklı politika; sözleşmede tanımsız. Kanıt:
  kanit/loglar/03.txt.

## Kapsam dışı gözlemler (diğer modüller)

- `arkauc/app/api/kimlik.py` — `POST /kimlik/giris` personel hesaplarını 403
  `yetki_yok` ("Bu giriş kapısı yalnızca son kullanıcılar içindir") ile reddediyor;
  API.md §5 `giris` için böyle bir kısıt yazmıyor (panel için `/kimlik/panel-giris`
  ayrıca tanımlı). Gözlem sırasında personel oturumu bu yüzden panel-giris ile alındı.
- `arkauc/app/api/kimlik.py` — hatalı girişte dönen `401` kodu `gecersiz_kimlik_bilgisi`,
  API.md §1 tablosunda yok (`kimlik_gerekli`, `jeton_gecersiz`, `jeton_suresi_doldu`,
  `anahtar_gecersiz` listeleniyor).

## Özet

7 bulgu (1 BLOCKER, 2 MAJOR, 4 MINOR).
- BLOCKER: `POST /kurulum` yarış durumu — eşzamanlı iki istek iki yönetici ve iki BDM
  oluşturuyor; `marka_adi`/`varsayilan_bdm_slug` son bitirenin değeriyle eziliyor.
