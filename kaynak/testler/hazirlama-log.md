# hazırlama gözlem logu — 2026-09-12

Bağımsız gözlem (Dalga 1): `bdm_hazırlama_ucu/*` iddialarının çürütülmesi.
Ürün kodu **değiştirilmedi**; yalnızca `kaynak/testler/` altına betik ve log yazıldı.

## Kapsam

- `kaynak/API.md` §10 (BDM hazırlama — `/bdm/hazirlama`, `dogrula`/`cek`/`manifest`/`on-kontrol`, `503 surucu_yok`)
- `kaynak/API.md` §1 (hata kodları: `400 gecersiz_istek`, `401 kimlik_gerekli`, `403 yetki_yok`, `503 surucu_yok`)
- `kaynak/API.md` §9 (SSE çerçeve biçimi — hazırlama akışı için referans)
- `kaynak/API.md` §11 (`409 gecersiz_gecis` — durum makinesi)
- `kaynak/spec/2026-09-12-kutyai-bdm-platformu-tasarim.md` §7.5, §9, §10, §11
- Çürütme hedefleri 1–8 (görev tanımı)

## Ortam ve yöntem

- Depo: `E:/kutyai-app`, Python `./.venv/Scripts/python.exe` (3.13.3).
- Canlı backend: `hub` ile `uvicorn arkauc.app.main:app --port 8103`, geçici DB
  `sqlite+aiosqlite:///E:/kutyai-app/kaynak/testler/gecici/goz_hazirlama.db`,
  `KUTYAI_GIZLI_ANAHTAR=gozlem-gizli-anahtar`, `KUTYAI_SIFRELEME_ANAHTARI=AAAA…AAA=`.
- Sahte upstream: `kaynak/testler/betikler/sahte_upstream.py` (FastAPI/uvicorn, port 8199) —
  `/v1/models`, `/v1/chat/completions`, `/modeller401/v1/models` (401), `/api/pull` (NDJSON), `/_vuruslar` (sayaç).
- **Makine gerçeği (önemli):** bu makinede Docker çalışıyor (`docker 29.7.2`, Runtimes: `nvidia`) ve
  NVIDIA RTX 3080 Ti var. Bu yüzden "GPU yok" senaryosu canlı sunucuda üretilemez; spec §10'un kendi
  test kancası olan `SahteSurucu` + `surucu_ata()` ile **aynı HTTP yüzeyi ASGI üzerinden** sürüldü
  (gerçek router, gerçek kimlik, gerçek veritabanı). Ham kanıt: aşağıda komut 6.
- Ürün kodu hiçbir yerde değiştirilmedi; doğrulama için DB'de yalnızca geçici test DB'sinde
  `UPDATE bdm SET durum='calisiyor'` yapıldı (komut 3, adım 3).

## Koşulan komutlar

### 1) `./.venv/Scripts/python.exe kaynak/testler/betikler/sahte_upstream.py 8199` + `/_vuruslar`

- Beklenen: uçlar ayakta; `/v1/models` 200, `/modeller401/v1/models` 401, `/v1/chat/completions` 200.
- Gerçek çıktı:
```
models: 200
modeller401: 401 {"error":{"message":"invalid api key"}}
chat401: 200 {"id":"chatcmpl-sahte","object":"chat.completion","model":"x","choices":[{"index":0,"message":{"role":"assistant","content":"pong"},"finish_reason":"stop"}],"us
```
- Sonuç: GEÇTİ (sahte upstream gerçek bir ağ sunucusu olarak çalışıyor)

### 2) Canlı backend (port 8103) + `GET /api/v1/saglik`

- Beklenen: `{"durum":"ayakta",...}`; router'lar yüklü.
- Gerçek çıktı:
```
{"durum":"ayakta","surum":"0.1.0","ortam":"gelistirme","zaman":"2026-09-12T19:39:12.397666+00:00"}
```
- Sonuç: GEÇTİ

### 3) `./.venv/Scripts/python.exe kaynak/testler/betikler/hazirlama_gozlem.py` (canlı, 8103)

Ham çıktı (`kaynak/testler/gecici/canli_stdout.txt`), bölümler hâlinde:

**Hedef 1 — gerçek OpenAI-uyumlu sunucuya karşı doğrulama**
```
===== [1] POST /{id}/dogrula -> GERCEK sahte upstream (/v1/models 200) =====
HTTP 200 application/json
{"basarili": true, "gecikme_ms": 3, "modeller": ["sahte-model-kucuk", "sahte-model-buyuk"], "mesaj": "Bağlantı başarılı; 2 model listelendi."}
durum (GET /bdm): hazir
sahte upstream vurus sayaci: {"GET /v1/models":4,"GET /modeller401/v1/models":2,"POST /modeller401/v1/chat/completions":2,"GET /_vuruslar":3}
```
**Hedef 1 (yedek yol) — `/models` 401 → sohbet denemesi**
```
===== [1b] POST /{id}/dogrula -> /v1/models 401, sohbet yedegi =====
HTTP 200 application/json
{"basarili": true, "gecikme_ms": 5, "modeller": [], "mesaj": "Model listesi alınamadı ancak sohbet ucu yanıt verdi."}
durum (GET /bdm): hazir
sahte upstream vurus sayaci: {"GET /v1/models":4,"GET /modeller401/v1/models":3,"POST /modeller401/v1/chat/completions":3,"GET /_vuruslar":4}
```
- Sonuç: GEÇTİ — doğrulama gerçekten ağ üzerinden yapılıyor (`/_vuruslar` sayacı arttı), `hazir` yazıldı.

**Hedef 2 — kapalı port**
```
===== [2] POST /{id}/dogrula -> KAPALI port (8198) =====
HTTP 200 application/json
{"basarili": false, "gecikme_ms": 1004, "modeller": [], "mesaj": "Model sağlayıcısına bağlanılamadı. Adresi ve ağ erişimini kontrol edin."}
durum (GET /bdm): hata
```
```
===== [2b] POST /{id}/dogrula -> gecersiz port iceren URL (99999) =====
HTTP 200 application/json
{"basarili": false, "gecikme_ms": 1005, "modeller": [], "mesaj": "Model sağlayıcısına bağlanılamadı. Adresi ve ağ erişimini kontrol edin."}
```
```
===== [2c] POST /{id}/dogrula -> cozulemeyen ana makine (IDNA gecersiz) =====
HTTP 500 application/json
{"hata": {"kod": "sunucu_hatasi", "mesaj": "Beklenmeyen bir sunucu hatası oluştu.", "ayrinti": {}}}
```
- Sonuç: kapalı port için GEÇTİ (200 + Türkçe mesaj, `hata` durumu); **2c KALDI → BULGU-3**.

**Hedef 3 — `calisiyor` durumundaki BDM'e doğrulama**
```
===== [3] calisiyor durumundaki BDM'e POST /{id}/dogrula (basarisiz dogrulama) =====
dogrulama oncesi durum: calisiyor
HTTP 200 application/json
{"basarili": false, "gecikme_ms": 1002, "modeller": [], "mesaj": "Model sağlayıcısına bağlanılamadı. Adresi ve ağ erişimini kontrol edin."}
dogrulama sonrasi durum: hata
```
- Sonuç: KALDI → BULGU-2 (canlı: `calisiyor` → `hata`; ASGI kanıtı komut 5'te)

**Hedef 4 — `on-kontrol` (canlı makinede Docker+GPU var)**
```
===== [4] GET /{id}/on-kontrol (vllm ve ollama) — bu makinede Docker+GPU VAR =====
-- vllm:
HTTP 200 application/json
{"docker": true, "gpu": true, "disk_gb": 190.1, "image_var": false, "uygun": true, "uyarilar": ["'vllm/vllm-openai:latest' imajı yerel önbellekte yok; ilk çalıştırmada indirilecek."]}
-- ollama:
HTTP 200 application/json
{"docker": false, "gpu": false, "disk_gb": 190.1, "image_var": false, "uygun": true, "uyarilar": ["Docker bulunamadı; konteyner tabanlı hazırlama yapılamaz.", "'ollama/ollama:latest' imajı yerel önbellekte yok; ilk çalıştırmada indirilecek."]}
-- surucu durumu (yonetim):
HTTP 200 application/json
{"surucu": "docker", "docker": true, "gpu": true, "gpu_listesi": ["NVIDIA GeForce RTX 3080 Ti"], "image_onbellek": [], "mesaj": ""}
```
- Sonuç: canlı ortamda GPU var → "uygun=false" beklenemez; GPU'suz senaryo komut 5'te (GEÇTİ).
  Ollama için `uygun=true` iki ortamda da doğru. `docker:false` + imaj uyarısı çelişkisi → BULGU-5 (MINOR).

**Hedef 5 — `manifest`**
```
===== [5] POST /{id}/manifest (vllm, openai, ollama) =====
-- vllm:
HTTP 200 application/json
{"image": "vllm/vllm-openai:latest", "komut": ["vllm", "serve", "Qwen/Qwen2.5-7B-Instruct", "--port", "8000"], "port": 8000, "gpu": true, "bellek_gb": 14.0, "ortam": {"HF_TOKEN": "hf-g***BEEF"}}
   ham govdede 'DEADBEEF' var mi: False
-- openai:
HTTP 400 application/json
{"hata": {"kod": "gecersiz_istek", "mesaj": "Bu sağlayıcı uzak sunucuda çalışır; konteyner manifesti üretilemez.", "ayrinti": {"saglayici": "openai"}}}
   ham govdede 'DEADBEEF' var mi: False
-- ollama:
HTTP 200 application/json
{"image": "ollama/ollama:latest", "komut": ["ollama", "serve"], "port": 11434, "gpu": false, "bellek_gb": 4.0, "ortam": {"OLLAMA_HOST": "0.0.0.0:11434"}}
   ham govdede 'DEADBEEF' var mi: False
```
- Sonuç: GEÇTİ — image/komut/port doğru, uzak sağlayıcıda 400, ham anahtar (`hf-gizli-token-DEADBEEF`) sızmıyor.

**Hedef 6 — GPU yokken 503 (canlı makinede GPU olduğu için beklenen 503 değil)**
```
===== [6] vllm icin POST /cek ve /manifest (canli: GPU VAR) =====
-- vllm /cek:
HTTP 400 application/json
{"hata": {"kod": "gecersiz_istek", "mesaj": "Bu sağlayıcı için model indirme desteklenmiyor.", "ayrinti": {"saglayici": "vllm"}}}
-- vllm /manifest:
HTTP 200 application/json
{"image": "vllm/vllm-openai:latest", "komut": ["vllm", "serve", "Qwen/Qwen2.5-7B-Instruct", "--port", "8000"], "port": 8000, "gpu": true, "bellek_gb": 14.0, "ortam": {"HF_TOKEN": "hf-g***BEEF"}}
```
- Sonuç: GEÇTİ (GPU var → 503 beklenmez); GPU yok senaryosu komut 5.

**Hedef 7 — `cek` SSE**
```
===== [7] POST /{id}/cek (openai -> 400, ollama -> SSE) =====
-- openai:
HTTP 400 application/json
{"hata": {"kod": "gecersiz_istek", "mesaj": "Bu sağlayıcı için model indirme desteklenmiyor.", "ayrinti": {"saglayici": "openai"}}}
-- ollama / vllm:
   ollama:
HTTP 200 text/event-stream; charset=utf-8
event: ilerleme
data: {"yuzde": 0, "mesaj": "Manifest indiriliyor"}

event: ilerleme
data: {"yuzde": 25, "mesaj": "Model indiriliyor"}

event: ilerleme
data: {"yuzde": 90, "mesaj": "Model indiriliyor"}

event: ilerleme
data: {"yuzde": 90, "mesaj": "Bütünlük imzası doğrulanıyor"}

event: ilerleme
data: {"yuzde": 90, "mesaj": "Manifest yazılıyor"}

event: ilerleme
data: {"yuzde": 90, "mesaj": "Kullanılmayan katmanlar temizleniyor"}

event: ilerleme
data: {"yuzde": 100, "mesaj": "Model hazır"}

event: bitti
data: {}


   vllm:
HTTP 400 application/json
{"hata": {"kod": "gecersiz_istek", "mesaj": "Bu sağlayıcı için model indirme desteklenmiyor.", "ayrinti": {"saglayici": "vllm"}}}
```
```
===== [7b] POST /{id}/cek -> upstream kapali (SSE hata cercevesi) =====
ISTEMCI ISTISNASI: RemoteProtocolError: peer closed connection without sending complete message body (incomplete chunked read)
```
- Sonuç: mutlu yol GEÇTİ (çerçeve biçimi API.md §9/§10 ile uyumlu); kapalı upstream KALDI → BULGU-1.

**Hedef 8 — yetki**
```
===== [8] Anonim 401 / son_kullanici 403 =====
-- anonim on-kontrol:   HTTP 401 {"hata": {"kod": "kimlik_gerekli", "mesaj": "Bu işlem için giriş yapmalısınız.", "ayrinti": {}}}
-- anonim manifest:     HTTP 401 {"hata": {"kod": "kimlik_gerekli", ...}}
-- anonim cek:          HTTP 401 {"hata": {"kod": "kimlik_gerekli", ...}}
-- anonim dogrula:      HTTP 401 {"hata": {"kod": "kimlik_gerekli", ...}}
-- son kullanici giris: 200
-- son_kullanici on-kontrol: HTTP 403 {"hata": {"kod": "yetki_yok", "mesaj": "Bu işlem için yetkiniz yok.", "ayrinti": {}}}
-- son_kullanici manifest:   HTTP 403 {"hata": {"kod": "yetki_yok", ...}}
-- son_kullanici dogrula:    HTTP 403 {"hata": {"kod": "yetki_yok", ...}}
-- son_kullanici cek:        HTTP 403 {"hata": {"kod": "yetki_yok", ...}}
```
(ham çıktının tamamı: `kaynak/testler/gecici/canli_stdout.txt`)
- Sonuç: GEÇTİ

### 4) `./.venv/Scripts/python.exe kaynak/testler/betikler/hazirlama_cek_hata.py` (canlı, SSE hata yolu)

- Beklenen: `event: hata` + `event: bitti` çerçeveleri (spec §7.5/§9 ruhu) ya da en azından okunabilir Türkçe hata.
- Gerçek çıktı:
```
giris: 200
olustur: 201 8
ISTEMCI ISTISNASI: RemoteProtocolError: peer closed connection without sending complete message body (incomplete chunked read)
```
- Sunucu tarafı günlüğü (komut 6):
```
Beklenmeyen hata: POST /api/v1/bdm/hazirlama/8/cek
  File "E:\kutyai-app\bdm_hazırlama_ucu\uc.py", line 62, in _sse
  File "E:\kutyai-app\bdm_hazırlama_ucu\cekim.py", line 96, in cek_akisi
httpx.ConnectError: All connection attempts failed
```
- Sonuç: KALDI → BULGU-1

### 5) `./.venv/Scripts/python.exe kaynak/testler/betikler/hazirlama_asgi_gozlem.py` (SahteSurucu ile GPU yok/var)

Ham çıktı (`kaynak/testler/gecici/asgi_stdout.txt`):

**GPU YOK — `on-kontrol`**
```
===== [B1] GPU YOK: GET on-kontrol (vllm / tgi / ollama) =====
-- vllm:
HTTP 200 application/json
{"docker": false, "gpu": false, "disk_gb": 190.1, "image_var": false, "uygun": false, "uyarilar": ["Bu model GPU gerektirir; Ollama gibi CPU uyumlu bir sağlayıcı seçin veya GPU çalışma zamanını kurun.", "Docker bulunamadı; konteyner tabanlı hazırlama yapılamaz.", "'vllm/vllm-openai:latest' imajı yerel önbellekte yok; ilk çalıştırmada indirilecek."]}
-- tgi:
HTTP 200 application/json
{"docker": false, "gpu": false, "disk_gb": 190.1, "image_var": false, "uygun": false, "uyarilar": ["Bu model GPU gerektirir; ...", ...]}
-- ollama:
HTTP 200 application/json
{"docker": false, "gpu": false, "disk_gb": 190.1, "image_var": false, "uygun": true, "uyarilar": ["Docker bulunamadı; konteyner tabanlı hazırlama yapılamaz.", "'ollama/ollama:latest' imajı yerel önbellekte yok; ilk çalıştırmada indirilecek."]}
```
- Sonuç: GEÇTİ (vllm `uygun=false` + spec §10 GPU yönlendirme cümlesi birebir; ollama `uygun=true`)

**GPU YOK — `manifest` / `cek` → 503 `surucu_yok`**
```
===== [B2] GPU YOK: POST manifest (vllm / tgi / ollama) =====
-- vllm:
HTTP 503 application/json
{"hata": {"kod": "surucu_yok", "mesaj": "Bu model GPU gerektirir; Ollama gibi CPU uyumlu bir sağlayıcı seçin veya GPU çalışma zamanını kurun.", "ayrinti": {"saglayici": "vllm", "gpu_gerekli": true}}}
-- tgi:
HTTP 503 application/json
{"hata": {"kod": "surucu_yok", "mesaj": "Bu model GPU gerektirir; ...", "ayrinti": {"saglayici": "tgi", "gpu_gerekli": true}}}
-- ollama:
HTTP 200 application/json
{"image": "ollama/ollama:latest", "komut": ["ollama", "serve"], "port": 11434, "gpu": false, "bellek_gb": 4.0, "ortam": {"OLLAMA_HOST": "0.0.0.0:11434"}}

===== [B3] GPU YOK: POST cek (vllm / tgi) =====
-- vllm: HTTP 503 application/json {"hata": {"kod": "surucu_yok", ...}}
-- tgi:  HTTP 503 application/json {"hata": {"kod": "surucu_yok", ...}}
```
- Sonuç: GEÇTİ

**GPU VAR — `on-kontrol` / `manifest`**
```
===== [C2] GPU VAR: POST manifest (vllm — sir sizmasi kontrolu) =====
HTTP 200 application/json
{"image": "vllm/vllm-openai:latest", "komut": ["vllm", "serve", "Qwen/Qwen2.5-7B-Instruct", "--port", "8000"], "port": 8000, "gpu": true, "bellek_gb": 14.0, "ortam": {"HF_TOKEN": "hf-g***BEEF"}}
ham govdede 'DEADBEEF' var mi: False
ham govdede 'hf-gizli-token' var mi: False
```
- Sonuç: GEÇTİ

**Hedef 3 — durum makinesi kanıtı (başarılı doğrulama)**
```
===== [D1] calisiyor BDM: baslat -> durum -> dogrula (BASARILI) =====
-- durum: hazir
-- yonetim/baslat: HTTP 200 {"durum": "calisiyor", "konteyner_id": "sahte-asgi-ollama-1"}
-- yonetim/durum: HTTP 200 {"durum": "calisiyor", "konteyner_id": "sahte-asgi-ollama-1", "saglik": {"calisiyor": true, "hazir": true, "mesaj": "Çalışıyor."}}
-- tekrar dogrula (BASARILI): HTTP 200 {"basarili": true, ...}
-- dogrula sonrasi durum: hazir
-- yonetim/durum: HTTP 200 {"durum": "hazir", "konteyner_id": "sahte-asgi-ollama-1", "saglik": {"calisiyor": true, "hazir": true, "mesaj": "Çalışıyor."}}
-- yonetim/durdur: HTTP 409 {"hata": {"kod": "gecersiz_gecis", "mesaj": "'hazir' durumundan 'durdu' durumuna geçilemez.", ...}}
-- yonetim/saglik: HTTP 200 {"calisiyor": true, "hazir": true, "mesaj": "Çalışıyor.", "ayrinti": {"konteyner_id": "sahte-asgi-ollama-1"}}
```
**Hedef 3 — durum makinesi kanıtı (başarısız doğrulama; konteyner kilitli kalıyor)**
```
===== [D2] calisiyor BDM: adres degisir -> dogrula (BASARISIZ) =====
-- baslat: HTTP 200 {"durum": "calisiyor", "konteyner_id": "sahte-asgi-kapali-2"}
-- durum: calisiyor
-- dogrula (kapali port): HTTP 200 {"basarili": false, ...}
-- dogrula sonrasi durum: hata
-- yonetim/durum: HTTP 200 {"durum": "hata", "konteyner_id": "sahte-asgi-kapali-2", "saglik": {"calisiyor": true, "hazir": true, "mesaj": "Çalışıyor."}}
-- yonetim/durdur: HTTP 409 {"hata": {"kod": "gecersiz_gecis", "mesaj": "'hata' durumundan 'durdu' durumuna geçilemez.", ...}}
-- yonetim/baslat: HTTP 409 {"hata": {"kod": "gecersiz_gecis", "mesaj": "'hata' durumundan 'calisiyor' durumuna geçilemez.", ...}}
-- yonetim/yeniden-baslat: HTTP 409 {"hata": {"kod": "gecersiz_gecis", "mesaj": "'hata' durumundan 'calisiyor' durumuna geçilemez.", ...}}
-- yonetim/durum: HTTP 200 {"durum": "hata", "konteyner_id": "sahte-asgi-kapali-2", "saglik": {"calisiyor": true, ...}}
```
- Sonuç: KALDI → BULGU-2

**Hedef 7 — SSE hata çerçevesi (ASGI)**
```
===== [E1] POST cek — upstream kapali (SSE hata cercevesi) =====
HTTP 200 text/event-stream; charset=utf-8
govde uzunlugu: 0
''
```
- Sonuç: KALDI → BULGU-1

### 6) Sunucu günlükleri (`hub logs`, grep: `InvalidURL|Beklenmeyen hata|500 Internal`)

- Beklenen: doğrulama/indirme yollarında yakalanmamış istisna olmaması.
- Gerçek çıktı:
```
Beklenmeyen hata: POST /api/v1/bdm/hazirlama/8/cek
Beklenmeyen hata: POST /api/v1/bdm/hazirlama/15/dogrula
    raise InvalidURL(f"Invalid port: {port!r}")
httpx.InvalidURL: Invalid port: ':1'
INFO:     127.0.0.1:15677 - "POST /api/v1/bdm/hazirlama/15/dogrula HTTP/1.1" 500 Internal Server Error
    raise InvalidURL(f"Invalid port: {port!r}")
httpx.InvalidURL: Invalid port: ':1'
Beklenmeyen hata: POST /api/v1/bdm/hazirlama/19/cek
```
- Sonuç: KALDI → BULGU-3 (500) ve BULGU-1 (SSE)

### 7) Ortam gerçeği: `docker`/`nvidia-smi`

- Beklenen: görev tanımındaki "GPU'suz makine" varsayımının doğrulanması.
- Gerçek çıktı:
```
ping: True
Runtimes: ['io.containerd.runc.v2', 'nvidia', 'runc']
ServerVersion: 29.7.2
images: []
nvidia-smi: NVIDIA GeForce RTX 3080 Ti
```
- Sonuç: bu makinede Docker + GPU **var**; "GPU yok" senaryoları yalnızca `SahteSurucu` ile (komut 5) gözlenebildi.

## Bulgular

- **[BLOCKER] `bdm_hazırlama_ucu/uc.py:64` + `bdm_hazırlama_ucu/cekim.py:96`** —
  `POST /{id}/cek` akışında `httpx` taşıma hataları (`ConnectError`, `ReadTimeout`, …) yakalanmıyor:
  `_sse()` yalnızca `except KutyaiHatasi` tutuyor, `cek_akisi()` içindeki `istemci.stream(...)` ise
  `httpx.HTTPError` fırlatıyor. İstisna `StreamingResponse` gövdesi yazılırken patlıyor; HTTP yanıtı
  zaten `200 text/event-stream` olarak başladığı için hata işleyicisi 500 gönderemiyor ve bağlantı
  gövdesiz kapanıyor. Beklenen: `event: hata` + `event: bitti` çerçeveleri (API.md §9/§10 biçimi).
  Yeniden üretme: ollama sağlayıcılı BDM'in `temel_url`'i kapalı bir porta (ör. `http://127.0.0.1:8198/v1`)
  verilir, `POST /api/v1/bdm/hazirlama/{id}/cek` çağrılır → istemci
  `RemoteProtocolError: peer closed connection without sending complete message body`, gövde 0 bayt,
  sunucu günlüğünde `Beklenmeyen hata … httpx.ConnectError` (komut 4 ve komut 6).
  Aynı hata sınıfı `cekim.py` içindeki `yanit.aiter_lines()` sırasında da (akış ortasında kopma) oluşur.

- **[BLOCKER] `bdm_hazırlama_ucu/dogrulama.py:79` (`_sonuc`)** —
  `bdm.durum` doğrudan yazılıyor; `bdm_yönetim_ucu/yasam_dongusu.py`'deki `gecerli_gecisler`
  durum makinesi (ve API.md §11 `409 gecersiz_gecis`) atlanıyor. `calisiyor` durumundaki bir BDM'e
  doğrulama yapıldığında:
  (a) başarılı doğrulama `calisiyor → hazir` geçişini **yasa dışı** biçimde yapıyor
  (`gecerli_gecisler[calisiyor] = {durdu, hata}`);
  (b) her iki sonuçta da **çalışan konteyner kaydı korunuyor** ama durum `hazir`/`hata` olduğu için
  `POST /{id}/durdur` → `409 gecersiz_gecis`, `POST /{id}/baslat` (hata için) → `409`,
  `POST /{id}/yeniden-baslat` → `409`. Yani GPU tutan konteyner API üzerinden **durdurulamıyor**
  (`GET /{id}/saglik` hâlâ `calisiyor: true` dönerken). Beklenen: `dogrula` durum makinesini
  kullanmalı ya da `calisiyor` bir BDM'in durumuna dokunmamalı.
  Yeniden üretme: komut 5, [D1] ve [D2] blokları (ASGI; `SahteSurucu`), ek canlı kanıt komut 3 adım [3].

- **[MAJOR] `bdm_hazırlama_ucu/dogrulama.py:151` ve `:195` (ve `cekim.py:96`)** —
  yalnızca `httpx.HTTPError` yakalanıyor; `httpx.InvalidURL` bu hiyerarşinin dışında
  (`httpx.InvalidURL.__mro__ = (InvalidURL, Exception, BaseException, object)`), dolayısıyla
  bozuk `temel_url` (ör. `http://[::1/v1`) genel 500'e düşüyor: `{"kod": "sunucu_hatasi"}`.
  Beklenen: API.md §1 gereği `400 gecersiz_istek`/`dogrulama_hatasi` + Türkçe, kullanıcıya
  gösterilebilir mesaj (kapalı portta olduğu gibi) ve 500 olmaması.
  Yeniden üretme: `temel_url=http://[::1/v1` ile BDM oluştur, `POST /{id}/dogrula` → `500`;
  sunucu günlüğü: `httpx.InvalidURL: Invalid port: ':1'` (komut 3 adım [2c], komut 6).
  Not: `http://127.0.0.1:99999/v1` gibi bazı bozuk adresler bu yola girmiyor (taşıma katmanı
  `ConnectError` veriyor) — bu yüzden hata veren girdi dar ama panelden girilebilir türde.

- **[MINOR] `bdm_hazırlama_ucu/on_kontrol.py:69-77`** — `ollama` sağlayıcısı için
  `konteyner_image = "ollama/ollama:latest"` dolu olduğundan, çalışma zamanı `YerelSurucusu`
  (Ollama REST; `docker_var`/`image_onbellek` hep boş) seçildiğinde ön kontrol her zaman
  "Docker bulunamadı; konteyner tabanlı hazırlama yapılamaz." ve "'ollama/ollama:latest' imajı
  yerel önbellekte yok" uyarılarını üretiyor — oysa Ollama host üzerinde çalışan bir sunucudur ve
  Docker/imaj gerektirmez; `uygun` yine de `true` kaldığı için mesaj ile sonuç çelişiyor.
  Beklenen: ollama için imaj/Docker uyarıları gösterilmemeli ya da metin "Ollama sunucusu" bağlamına
  uyarlanmalı. Yeniden üretme: komut 3 adım [4] ve komut 5 [B1] ollama satırları.

- **[MINOR] `bdm_hazırlama_ucu/cekim.py:41-46` (`cek_destegi_denetle`)** — spec §7.5 `POST /{id}/cek`
  için "Ollama pull **/ HF snapshot**" diyor; uygulama yalnızca Ollama pull destekliyor, `vllm`/`tgi`
  için HF snapshot yolu yok (`400 gecersiz_istek`). Görev tanımındaki beklenti ("ollama dışı → Türkçe 400")
  karşılandığı için MINOR olarak kaydedildi; ancak gated modeller için manifest'te üretilen `HF_TOKEN`
  ile birlikte düşünüldüğünde spec'in HF indirme yolu eksik kalıyor. Kanıt: komut 3 adım [6]/[7].

## Özet

5 bulgu (2 BLOCKER, 1 MAJOR, 2 MINOR).

- BLOCKER-1: `POST /{id}/cek` — hatada SSE çerçevesi üretilmiyor, bağlantı gövdesiz kapanıyor (yakalanmayan `httpx` taşıma hatası).
- BLOCKER-2: `POST /{id}/dogrula` durum makinesini atlıyor; çalışan konteyner `hazir`/`hata` durumunda kilitleniyor ve API'den durdurulamıyor.
- MAJOR-3: bozuk `temel_url` (`httpx.InvalidURL`) → 500 `sunucu_hatasi` (Türkçe mesaj yok).
- MINOR-4: ollama ön kontrolünde Docker/imaj uyarıları yanıltıcı.
- MINOR-5: spec §7.5'teki HF snapshot indirme yolu uygulanmamış.
