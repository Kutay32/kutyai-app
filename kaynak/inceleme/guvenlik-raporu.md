# Güvenlik incelemesi raporu — 2026-09-12

**Kapsam:** `arkauc/app/**`, `bdm_listesi/`, `bdm_konusma_gecmisi/`, `bdm_hazırlama_ucu/`, `bdm_yönetim_ucu/`, `bdm_veritabani/` ve istemcilerin (`onuc/`, `yonetim_paneli/`) okuma düzeyinde incelenmesi.

**Snapshot uyarısı:** İnceleme sırasında ağaç başka ajanlarca düzenleniyordu; bulgular aşağıdaki özetlere karşılık gelen ana sürüme aittir (yerel saat 2026-09-12 23:57): `arkauc/app/main.py` sha256 `2cbdd9dea9ceb5d5`, `arkauc/app/cekirdek/oran_siniri.py` sha256 `5669c5fa66568314`, `arkauc/app/api/kullanicilar.py` sha256 `e6131df36d3619b5`, `arkauc/app/api/loglar.py` sha256 `133207207059dcd6`. B1/B2 numaralı kırılmalar 186 yeşil test koşusundan sonraki düzeltme turunda girmiş görünüyor (`.pytest_cache/v/cache/lastfailed` boş, dosya mtime'ları 23:55–23:57).

## Yöntem

1. Sözleşme okuması: `kaynak/API.md` (bağlayıcı), `kaynak/GUVENLIK.md`, `kaynak/spec/...tasarim.md` §4–§11.
2. Backend kaynağının satır bazlı okunması (kimlik/JWT, bağımlılıklar, kota, upstream, konteyner sürücüleri, maskeleme, dışa aktarım, denetim izi, ayarlar, istemci `lib/` modülleri).
3. Dinamik doğrulama — geçici SQLite + ASGI istemcisi, `kaynak/testler/gecici/` altında:
   - `guvenlik_denetim.py`: oran sınırı, giriş zamanlaması, kayıt/sıfırlama numaralandırma, sıfırlama ele geçirme, JWT negatif testleri, yenileme rotasyonu, SSRF, kota yarışı, IDOR, rol matrisi, sır sızıntısı, CSV/maskeleme.
   - `guvenlik_denetim2.py`: SSRF ile upstream anahtarı sızdırma (casus sunucu gelen `Authorization` başlığını kaydetti), çıkış sonrası jeton, iç ağ/dosya şeması denemeleri, sıfırlama bağlantısının saklanması.
   - `guvenlik_denetim3.py`: KVKK maskeleme sınırı ve konteyner argv üretimi.
   - `son_durum.py`: kancasız açılış denemesi + incelenen dosyaların sha256/mtime özetleri.
4. **Ürün kodu değiştirilmedi.** Uygulama bu snapshot'ta açılamadığı için (B1) ölçüm betikleri yalnızca *import anındaki* 204 assert'ini ve ara katman kurulum imzasını runtime kancasıyla düzeltti; oran sınırlayıcı ve tüm uç mantığı aynen çalıştırıldı (kanca kaynakları betiklerin başındaki yorumlarda).

## Bulgular

### [BLOCKER] `arkauc/app/api/kullanicilar.py:129-135` ve `arkauc/app/api/loglar.py:178-183` — 204 dönüşlü uçlarda `-> None` uygulamanın hiç açılmamasına yol açıyor
- **Sorun:** İki `DELETE` ucu `status_code=204` ile tanımlı ve dönüş tipi `-> None`. `from __future__ import annotations` altında Python 3.13 + FastAPI 0.115.0 bu anotasyonu `NoneType`'a çözer; `APIRoute.__init__` içindeki `if self.response_model:` bloğu `AssertionError: Status code 204 must not have a response body` fırlatır. Modül import edilemediği için `arkauc.app.main` yüklenemez: **uygulama açılmaz ve test koleksiyonu toplanamaz**.
- **Beklenen:** Uygulama açılmalı; uçlar gövdesiz `204` dönmeli (`-> Response` ya da açık `response_model=None`).
- **Yeniden üretme:**
  ```powershell
  python -c "import arkauc.app.main"
  # AssertionError: Status code 204 must not have a response body
  python -m pytest arkauc/testler/test_dalga0.py -x -q
  # ERROR arkauc/testler/test_dalga0.py::test_saglik_ucu_ayakta - AssertionError: Status code 204 ...
  ```
- **Kanıt:** `kaynak/testler/gecici/son_durum.py` çıktısı (`{"import": {"hata": "AssertionError: Status code 204 must not have a response body", ...}}`); pytest koleksiyon hatası (`fastapi/routing.py:507`).

### [BLOCKER] `arkauc/app/cekirdek/oran_siniri.py:114` + `arkauc/app/main.py:124` — ara katman imzası Starlette ile uyumsuz: her istek TypeError
- **Sorun:** `OranSiniriMiddleware.__init__(self, uygulama: ASGIApp)`; Starlette ara katmanı `cls(app=app, *args, **kwargs)` biçiminde kurar (`starlette/applications.py:99`). İlk istekte `build_middleware_stack()` → `TypeError: OranSiniriMiddleware.__init__() got an unexpected keyword argument 'app'`. `main.py` import anında `app = uygulama_olustur()` çalıştırdığı için hata ilk HTTP isteğinde patlar ve hiçbir uç yanıt vermez.
- **Beklenen:** Parametre adı `app` olmalı (`def __init__(self, app: ASGIApp) -> None`).
- **Yeniden üretme:** B1 kancası uygulandıktan sonra tek bir istek yeterlidir; `kaynak/testler/gecici/guvenlik_denetim3.py` ilk koşusunda tam bu hatayla durdu (`TypeError: OranSiniriMiddleware.__init__() got an unexpected keyword argument 'app'`). Ölçümlerde ara katman `app` konumsal parametresiyle sarılarak çalıştırıldı ve oran sınırlama mantığı doğrulandı.
- **Not:** B1 giderilmeden bu hata görünmez; ikisi birlikte "uygulama hiç çalışmıyor" durumunu oluşturur.

### [BLOCKER] `bdm_listesi/sema.py:26,40` + `bdm_listesi/katalog.py:119-136,153-166` + `arkauc/app/servisler/upstream.py:53-70` + `bdm_hazırlama_ucu/dogrulama.py:155-186` — doğrulanmayan `temel_url` üzerinden SSRF ve upstream API anahtarı sızıntısı
- **Sorun:** `temel_url` yalnız `str, max_length=400` ve `rstrip("/")` ile doğrulanır; şema/alan adı/iç ağ kısıtı yoktur. Sunucu bu adrese istek atar ve **çözülmüş upstream anahtarını `Authorization: Bearer …` başlığında** gönderir (`upstream.basliklar`, `dogrulama._anahtari_coz` → `basliklar`). Aynı adres `/sohbet`, `/sohbet/akis`, `/bdm/hazirlama/{id}/dogrula`, `/bdm/hazirlama/{id}/cek` ve Ollama sürücüsünde (`konteyner_yerel._yokla/_bosalt`) kullanılır. API çözülmüş anahtarı hiçbir yanıtta döndürmediği için (yalnız `api_anahtari_maskeli`) bu yol **anahtarı dışarı sızdırmanın tek yolu** hâline gelir. Kurulum tamamlanmadan önce aynı istek **kimlik doğrulamasız** `POST /kurulum` (`dogrula: true`) ile de tetiklenir (`kurulum.py:157,179`).
- **Beklenen:** Yalnız http/https ve gerekliyse izinli alan adları; loopback/link-local/iç ağ adreslerinin reddi; anahtarın yalnız gerçek sağlayıcı adresine gitmesi (GUVENLIK.md §5).
- **Yeniden üretme (doğrulandı):** casus sunucu `http://127.0.0.1:<port>/v1` olarak tanımlanır; `yönetici` `api_anahtari="sk-gizli-upstream-anahtari-1234567890"` ile BDM oluşturur; `operatör` `PATCH /api/v1/bdm/{id}` ile `temel_url`'ü casus adrese çevirir (200); ardından `POST /api/v1/bdm/hazirlama/{id}/dogrula` ve `POST /api/v1/sohbet`. Casus sunucunun kaydettiği:
  ```
  GET  /v1/models           → authorization: Bearer sk-gizli-upstream-anahtari-1234567890
  POST /v1/chat/completions → authorization: Bearer sk-gizli-upstream-anahtari-1234567890
  ```
  Kimliksiz varyant: `POST /api/v1/kurulum` gövdesinde `bdm.temel_url = http://127.0.0.1:<port>/v1`, `dogrula: true` → 201 ve casus sunucu `GET /v1/models` aldı.
- **Ek gözlem:** `http://169.254.169.254/latest/meta-data` reddedilmiyor, bağlantı denemesi yapılıyor (günlükte "All connection attempts failed"); `file:///C:/Windows/win.ini` taşıma katmanında düşüyor ("Sağlayıcı adresi geçersiz.") — yani şema kısıtı uygulamada değil httpx'te.
- **Kanıt:** `guvenlik_denetim2.py` çıktısı (`ssrf_ile_anahtar_sizintisi.anahtar_sizdi: true`, `adres_dogrulama`), `guvenlik_denetim.py` çıktısı (`kurulum.ic_servise_giden_istekler`, `sohbet_ssrf.icerik: "IC-SERVIS-YANITI"`).

### [BLOCKER] `arkauc/app/api/kimlik.py:283-316` — SMTP tanımsızken sıfırlama bağlantısı isteyene dönüyor: kimlik doğrulamasız yönetici ele geçirme
- **Sorun:** `POST /kimlik/sifre-sifirlama-iste`, `smtp_tanimli_mi` false iken **tam sıfırlama jetonunu içeren bağlantıyı** yanıt gövdesine koyar (`gelistirme_baglantisi`). Varsayılan dağıtımda (`dagitim/.env.ornek`: `KUTYAI_SMTP_HOST=` boş) bu, yönetici dâhil herhangi bir hesabın parolasını kimlik doğrulaması olmadan değiştirmeye izin verir. Ortam kapısı yoktur: `ayarlar.uretim_mi` yalnız `dogrula()` içinde kullanılır; `KUTYAI_ORTAM=uretim` ile başlatılsa bile SMTP boşsa davranış aynıdır. Yanıt gövdesinin varlığı ayrıca hesap numaralandırma oracle'ıdır.
- **Beklenen:** API.md §5 alanı "yalnız SMTP tanımlı değilken" diye tanımlar; amacı "test/kurulum kolaylığı" olduğundan en azından `ortam=gelistirme` ile sınırlanmalı, üretimde dönmemelidir (GUVENLIK.md §6 kontrol listesi SMTP'yi zorunlu tutar).
- **Yeniden üretme (doğrulandı):**
  ```
  POST /api/v1/kimlik/sifre-sifirlama-iste  {"eposta": "sahip@denetim.com"}
    → 200 {"mesaj": "...", "gelistirme_baglantisi": "http://localhost:3000/sifre-sifirla?jeton=..."}
  POST /api/v1/kimlik/sifre-sifirla         {"jeton": "<bağlantıdan>", "yeni_parola": "EleGecirildi1!"}
    → 200
  POST /api/v1/kimlik/panel-giris           {"eposta": "sahip@denetim.com", "parola": "EleGecirildi1!"}
    → 200, kullanici.rol = "yonetici"
  ```
- **Kanıt:** `guvenlik_denetim.py` çıktısı `sifirlama_ele_gecirme: {baglanti_dondu: true, sifirla_kodu: 200, yeni_parolayla_giris: 200, rol: "yonetici"}`.
- **İlgili:** aynı bağlantı `ayar.son_sifirlama_baglantisi` alanına yazılıp orada kalıyor (bkz. MINOR-3).

### [MAJOR] `arkauc/app/cekirdek/oran_siniri.py:101-108` — oran sınırı `Authorization` başlığı döndürülerek atlatılabiliyor
- **Sorun:** Kova anahtarı, `Authorization` başlığı varsa onun özeti, yoksa istemci IP'sidir. `/kimlik/*` uçları bu başlığı hiç kullanmaz; saldırgan her istekte **farklı bir uydurma** `Authorization: Bearer x` göndererek sınırsız kova elde eder ve kimlik uçlarındaki 10 istek/dk sınırı etkisiz kalır.
- **Beklenen:** Kova anahtarı istemcinin seçemediği bir değere dayanmalı: `/kimlik/*` için IP (+ doğrulanmış kullanıcı varsa jeton), genel kural için IP; başlık yalnız doğrulanmış jetonla kullanılmalı.
- **Yeniden üretme (doğrulandı):** aynı istemci, aynı uç, aynı gövde:
  ```
  40 istek, Authorization YOK                        → 401×10, 429×30  (sınır çalışıyor, 0,45 sn)
  40 istek, her birinde farklı 'Bearer uydurma-jeton-N' → 401×40, 429×0   (sınır atlanıyor)
  ```
- **Kanıt:** `guvenlik_denetim.py` çıktısı `panel_giris_deneme: {401: 10, 429: 30}`, `panel_giris_jeton_rotasyonu: {401: 40}`, `sure_sn: 0.45`.

### [MAJOR] `arkauc/app/api/kimlik.py:103-105` — giriş yanıt süresinden kullanıcı numaralandırma
- **Sorun:** `if kullanici is None or not kimlik_servisi.parola_gecerli_mi(...)` kısa devre yapar; hesap yoksa argon2 doğrulaması hiç çalışmaz. Kayıtlı hesap ≈45 ms, kayıtsız hesap ≈2 ms (≈20× fark). Kod tabanında bu sızıntı için sabit maliyetli `zamanlama_dogrulamasi()` zaten var (`servisler/kimlik.py:45-54`) ama **yalnız** şifre sıfırlama isteğinde çağrılıyor (`api/kimlik.py:299`).
- **Beklenen:** `kullanici is None` dalında da aynı maliyetli argon2 doğrulaması yapılmalı; yanıt aynı `401 gecersiz_kimlik_bilgisi` kalmalı.
- **Yeniden üretme (doğrulandı):** aynı uca 15 kez aynı gövdeyle istek atılıp süreler ölçülür:
  ```
  POST /api/v1/kimlik/giris {"eposta":"sahip@denetim.com",  "parola":"YanlisParola1!"} → medyan 44,9 ms
  POST /api/v1/kimlik/giris {"eposta":"hic-yok@denetim.com", "parola":"YanlisParola1!"} → medyan  2,2 ms
  karşılaştırma: /kimlik/sifre-sifirlama-iste (sabit maliyetli yardımcı) → 58,8 ms / 47,0 ms
  ```
- **Kanıt:** `guvenlik_denetim.py` çıktısı `zamanlama_ms`.

### [MAJOR] `arkauc/app/servisler/kota.py:128-180` — kota denetimi ile sayacın artırılması arasında yarış: paralel isteklerle günlük limit aşılabiliyor
- **Sorun:** `kota_kontrol` sayacı okur, `kota_kullan` Python tarafında `kayit.kullanilan_gunluk += 1` ile artırır (satır 178); araya atomik koşullu bir `UPDATE` girmez. Paralel isteklerin tamamı eski sayacı okur ve limit aşılır (check-then-act / lost update; PostgreSQL'de de aynıdır).
- **Beklenen:** Denetim ve artırım tek atomik koşullu UPDATE ile yapılmalı; limit dolduğunda fazla istekler 429 almalı.
- **Yeniden üretme (doğrulandı):** `gunluk_istek_siniri=1` olan API anahtarıyla 6 istek `asyncio.gather` ile paralel gönderilir:
  ```
  paralel 6 istek → [200, 429, 429, 200, 429, 200]   (basarili: 3)
  7. istek (tek)  → 429
  ```
  İkinci koşuda `[429, 429, 200, 200, 429, 429]` (basarili: 2): tek istek hakkı olan anahtar 2–3 istek geçirdi.
- **Kanıt:** `guvenlik_denetim.py` çıktısı `kota_paralel`.

### [MINOR] `arkauc/app/api/kimlik.py:283-301` — kayıt/sıfırlama yanıtlarıyla hesap numaralandırma
- **Sorun:** `POST /kimlik/kayit` kayıtlı e-postada `409 cakisma`, yeni e-postada `201` döner (sözleşmede tanımlı, spec §6 "eposta/slug tekrarı") → tek istekle e-posta varlığı öğrenilir. Sıfırlama isteğinde yanıt gövdesi SMTP'siz ortamda `gelistirme_baglantisi` içerdiği için varlık yine ayırt edilir (GUVENLIK.md §4 "aynı yanıt" ilkesi yalnız sıfırlama isteği için konmuştur, ama gövde farkı ilkeyi bozar).
- **Beklenen:** Numaralandırma riski belgelenmeli ya da gövde farkı ortadan kaldırılmalı (bağlantı yalnız günlüğe).
- **Yeniden üretme:** `POST /kimlik/kayit {"eposta":"sahip@denetim.com"}` → 409; `{"eposta":"yeni-kayit@denetim.com"}` → 201. `POST /kimlik/sifre-sifirlama-iste` kayıtlı → `gelistirme_baglantisi` var, kayıtsız → yok (mesaj aynı).
- **Kanıt:** `guvenlik_denetim.py` çıktısı `kayit_numaralandirma`, `zamanlama_ms`.

### [MINOR] `arkauc/app/api/kimlik.py:306-330` — çıkış/parola sıfırlama erişim jetonunu iptal etmiyor
- **Sorun:** `/kimlik/cikis` yalnız yenileme jetonunu iptal eder; aynı oturumun erişim jetonu `exp`'e kadar (varsayılan 15 dk) çalışır. GUVENLIK.md §1 "Çıkış, şifre sıfırlama ve hesap pasifleştirmede tüm oturumlar iptal edilir" der. (Pasifleştirmede `bagimliliklar._jetonla_kullanici` durum denetimi erişimi anında keser; eksik olan, iptal listesi/`jeton_surumu` olmadığı için çıkış ve parola sıfırlama senaryolarıdır.)
- **Beklenen:** Ömür sınırı belgelenmeli ya da erişim jetonu için iptal/sürüm kontrolü eklenmeli.
- **Yeniden üretme (doğrulandı):** `/kimlik/panel-giris` ile alınan jetonlarla `POST /kimlik/cikis` (200) sonrası `GET /kimlik/ben` (eski erişim jetonu) → **200**; `POST /kimlik/yenile` (eski yenileme jetonu) → 401.
- **Kanıt:** `guvenlik_denetim2.py` çıktısı `cikis_sonrasi`.

### [MINOR] `arkauc/app/api/kimlik.py:315-316` — sıfırlama bağlantısı `ayar` tablosunda kalıcı
- **Sorun:** `ayar_yaz(oturum, "son_sifirlama_baglantisi", baglanti)` (ve doğrulama karşılığı, satır 184-185) 2 saat geçerli tam jetonu içeren bağlantıyı süresiz saklar. API üzerinden okunamıyor (doğrulandı: `/ayarlar` yanıtı jeton içermiyor) ama kayıt, jetonun ömrünü aşan bir sır tutuyor.
- **Beklenen:** Ya alan kaldırılmalı ya da yalnız "üretildi" bilgisi saklanmalı.
- **Yeniden üretme:** `POST /kimlik/sifre-sifirlama-iste` sonrası `SELECT deger FROM ayar WHERE anahtar='son_sifirlama_baglantisi'` → bağlantı; `GET /ayarlar` yanıtında jeton yok.
- **Kanıt:** `guvenlik_denetim2.py` çıktısı `sifirlama_jetonu_saklama: {baglanti_dondu: true, ayar_tablosunda_var: true, api_yanitinda_var: false}`.

### [MINOR] `bdm_hazırlama_ucu/manifest.py:57-68` — `upstream_model` doğrudan konteyner argv'sine giriyor (argüman enjeksiyonu)
- **Sorun:** vLLM/TGI için komut `[..., upstream_model, "--port", str(port)]` biçiminde kurulur; `konteyner_docker.py:166-169` bunu `command=[...]` olarak Docker'a verir. `upstream_model` serbest metin (max 200) olduğundan tek bir bayrak eklenebilir: `["vllm","serve","--trust-remote-code","--port","8000"]`. Görüntü adı sağlayıcı matrisinden geldiği, kabuk yorumlaması olmadığı ve alanı yalnız personel yazabildiği için etki sınırlıdır; ancak şema doğrulaması yoktur.
- **Beklenen:** `upstream_model` için `^[A-Za-z0-9._\-/:]+$` benzeri desen; en azından `-` ile başlayan değerlerin reddi.
- **Yeniden üretme:** `manifest.manifest_uret` doğrudan çağrılır (uç üzerinden erişim GPU gerektirir, `_gpu_denetle` 503 döner):
  ```python
  Bdm(saglayici=Saglayici.vllm, upstream_model="--trust-remote-code", ...)
  manifest_uret(bdm)["komut"]  # ["vllm", "serve", "--trust-remote-code", "--port", "8000"]
  ```
- **Kanıt:** `guvenlik_denetim3.py` çıktısı `konteyner_argv`.

### [MINOR] `arkauc/app/servisler/konteyner_docker.py:49` — `KUTYAI_DOCKER_SOKETI` ayarı hiç okunmuyor
- **Sorun:** Ayar tanımlı (`cekirdek/ayarlar.py:56`, `.env.ornek:41`, spec §5) ve `dagitim/OKUBENI.md` üretimde soketi vekil arkasına almayı öneriyor; ama `DockerSurucusu.istemci()` her zaman `docker.from_env()` çağırıyor. Dolayısıyla vekil soket adresi bu değişkenle verilemiyor; compose soketi doğrudan bağlıyor (imaja host-root yetkisi).
- **Beklenen:** `ayarlar.docker_soketi` doluysa `docker.DockerClient(base_url=...)`, boşsa `from_env()`.
- **Yeniden üretme:** `grep -rn "docker_soketi" arkauc/` → yalnız tanım satırı; `konteyner_docker.py` içinde tek istemci kurulumu `docker.from_env()`.
- **Kanıt:** kod okuması; `dagitim/docker-compose.yml:51` soket bağlaması (dağıtım dosyası kapsam dışı, yalnız bağlam).

### [MINOR] `arkauc/app/cekirdek/oran_siniri.py:106-108` — IP tabanlı kova ters vekil arkasında tüm kurulumu tek kovaya indiriyor
- **Sorun:** Anonim isteklerde kova anahtarı `scope["client"][0]`'dır; `X-Forwarded-For` işlenmez. `dagitim/nginx.conf` profili (tek giriş noktası) etkinken tüm anonim trafik vekil IP'sinde toplanır; `/api/v1/kimlik/*` için 10 istek/dk **tüm kurulum** için geçerli olur ve meşru kullanıcılar 429 alır (kimlik uçlarında kolay hizmet dışı bırakma).
- **Beklenen:** Güvenilir vekil arkasında `X-Forwarded-For`'un (yalnızca güvenilen vekilden) değerlendirilmesi ya da sınırın kullanıcı/jeton bazlı ayrıştırılması.
- **Yeniden üretme:** `curl -H 'X-Forwarded-For: 1.2.3.4'` ile ardışık isteklerde kova değişmez (tek kova); vekil arkasında tüm istemciler aynı `client` değerini taşır.
- **Kanıt:** kod okuması (`istemci_anahtari`) + `dagitim/nginx.conf` (bağlam).

## Onaylanan noktalar (dinamik olarak doğrulandı)

- **JWT sertleştirmesi:** `guvenlik.jeton_coz` `algorithms=["HS256"]` ile sabitlenmiş; yanlış anahtarla imzalanmış jeton → 401, `alg=none` jeton → 401, `tur` alanı denetleniyor, `exp` PyJWT tarafından doğrulanıyor.
- **Yenileme rotasyonu:** aynı yenileme jetonunun ikinci kullanımı 401; erişim jetonu yenileme olarak kullanılamıyor (401); jetonlar yalnız SHA-256 özetiyle saklanıyor (`oturum.jeton_hash`).
- **Şifre ve jetonlar:** argon2id + kullanıcı başına tuz; doğrulama/sıfırlama jetonları tek kullanımlık ve koşullu UPDATE ile atomik tüketiliyor; sıfırlama isteğinde sabit maliyetli argon2 çalışıyor (zamanlama farkı 58,8 / 47,0 ms).
- **IDOR:** A kullanıcısının konuşmasına B kullanıcısı `GET`, `PATCH`, `DELETE` → üçünde de **404**; kimliksiz → 401. Konuşma listesi yalnız çağıranın kapsamıyla süzülüyor (`konusma_sahibi_mi`).
- **Rol matrisi:** `izleyici` → API anahtarı okuma/yazma **403**, log silme **403**, log okuma 200; `operatör` → `/ayarlar` ve `/kullanicilar` **403**; `son_kullanici` → `/bdm`, `/loglar/*`, `/kullanim/ozet`, `/islem-kayitlari` **403**, `/kullanim/benim` 200 (yalnız kendi kayıtları).
- **Sır yönetimi:** upstream anahtarı yanıtlarda `sk-g***7890` / `hf-d***7890` maskeli; hiçbir yanıtta ham hâli yok; `smtp_sifre` Fernet ile (`gAAAAA…`) saklanıyor ve `/ayarlar` yanıtında dönmüyor; `islem_kaydi.ayrinti` içinde ne SMTP parolası ne upstream anahtarı var; `/bdm/hazirlama/{id}/manifest` gövdesindeki gizli ortam değerleri maskeli (`_ortami_maskele`). Not: ham anahtar yalnız yukarıdaki SSRF bulgusuyla dışarı çıkarılabiliyor.
- **SQL enjeksiyonu:** Tüm sorgular SQLAlchemy ORM ile parametreli; ham `text()` yalnız `SELECT 1` sağlık kontrolünde (`api/sistem.py:37`), araya kullanıcı verisi girmiyor. `ilike` desenleri parametre bağlanıyor.
- **CSV/dışa aktarım:** formül enjeksiyonu etkisizleştirilmiş (`'=1+1`), dosya adı sunucu üretimi (`konusma-5.csv`); başlık enjeksiyonu ve path traversal yok (`disa_aktarim.dosya_adi_uret`).
- **KVKK maskeleme:** kullanıcı mesajı hem kayda hem upstream'e maskelenmiş gidiyor (casus gövdesi: `TCKN [MASKELENDI:tckn] eposta [MASKELENDI:eposta]`); kayıt `[MASKELENDI:tckn]`/`[MASKELENDI:eposta]` içeriyor, ham TCKN yok. API.md §9'daki "istemciye ham" sınırı yalnız modelin ürettiği metne ilişkin ve o da kayıtta maskeleniyor.
- **İstemci XSS:** `onuc/components/sohbet/markdown-gorunumu.tsx` `react-markdown`'ı `rehype-raw` olmadan kullanıyor (ham HTML yorumlanmıyor); uygulama kodunda `dangerouslySetInnerHTML`/`innerHTML` yok. Jetonlar `localStorage`'da (XSS'e duyarlı, bilinen ödünleşim).
- **Hata zarfı:** istemciye traceback/upstream gövdesi sızmıyor (502'de yalnız durum kodu + sağlayıcı adı).
- **Yeni oran sınırlayıcı (başlık döndürülmediğinde):** `/api/v1/kimlik/*` 10 istek/dk, `/api/v1/sohbet` 60 istek/dk; 40 istekte 30'u 429 ile kesildi, kayıt ucu da kapsanıyor.

## Özet

13 bulgu (4 BLOCKER, 3 MAJOR, 6 MINOR). BLOCKER'ların ikisi (B1, B2) uygulamanın hiç açılmamasına/yanıt vermemesine yol açan mekanik kırılmalardır; üçüncüsü (B3) doğrulanmayan `temel_url` üzerinden SSRF + upstream API anahtarı sızdırma, dördüncüsü (B4) SMTP'siz varsayılan kurulumda kimlik doğrulamasız yönetici ele geçirmedir. İnceleme salt okunurdur; hiçbir ürün kodu değiştirilmedi.
