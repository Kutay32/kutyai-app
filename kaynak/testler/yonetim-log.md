# bdm_yönetim_ucu + konteyner sürücüleri gözlem logu — 2026-09-12

Bağımsız gözlem (Dalga 1 doğrulaması). Uygulayıcı testleri (`arkauc/testler/test_yonetim.py`)
kanıt olarak **kullanılmadı**; tüm sonuçlar canlı HTTP (uvicorn :8104), gerçek Docker
(29.7.2) ve doğrudan SQLite sorgularıyla üretildi. Ürün koduna yazılmadı.

## Kapsam

- `kaynak/API.md` §11 (BDM yönetimi — `/bdm/yonetim`), §1 (hata zarfı/kodları), §2 (`Bdm` tipi)
- `kaynak/spec/2026-09-12-kutyai-bdm-platformu-tasarim.md` §7.6 (uç listesi), §8 (router sözleşmesi), §10 (konteyner orkestrasyonu: `DeviceRequest`, port eşleme, sağlık sondası, GPU'suz ortamda 503)
- `kaynak/ISLETIM.md` §2 (durum makinesi, "Her geçiş denetim izine yazılır")
- İncelenen kod: `bdm_yönetim_ucu/*`, `arkauc/app/servisler/konteyner_docker.py`, `konteyner_yerel.py`, `konteyner.py`, `bdm_hazırlama_ucu/manifest.py` (manifest sözleşmesi için)

## Ortam

- Depo: `E:/kutyai-app`, Python: `./.venv/Scripts/python.exe`, canlı backend: `uvicorn arkauc.app.main:app --port 8104`, geçici DB: `kaynak/testler/gecici/yonetim.db`
- Makinede GPU **var**: `NVIDIA GeForce RTX 3080 Ti` (nvidia-smi çalışıyor) → "GPU'suz makine" senaryosu gerçek donanımda kurulamadı; sürücü ikamesiyle (`surucu_ata`, ürün kodunun kendi test kancası) ölçüldü ve bu açıkça belirtildi.
- Başlangıçta Docker daemon **kapalıydı** (`docker info` → `failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine`). `docker desktop start` ile **açıldı** (Server 29.7.2), gerçek konteyner testleri koşuldu, sonunda tekrar **kapatıldı** (ortam ilk haline döndürüldü).
- `ollama` sağlayıcısı için gerçek Ollama yok; `kaynak/testler/betikler/sahte_ollama.py` (127.0.0.1:11435) kullanıldı. Bu sunucu `/api/tags`, `/v1/models`, `/v1/chat/completions` ve `/api/generate` çağrılarını `gecici/fake_ollama.log` dosyasına yazar.

## Koşulan komutlar

### 1) `docker info` (ilk durum) ve `docker desktop start`

- Beklenen: daemon durumu belirlenir; kapalıysa sürücü kodu statik incelenir ve başlatma denenir.
- Gerçek çıktı:

```
Server:
failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine; check if the path is correct and if the daemon is running: open //./pipe/dockerDesktopLinuxEngine: Sistem belirtilen dosyayı bulamıyor.
---EXIT:1

$ docker desktop start
✓ Starting Docker Desktop
EXIT:0

$ docker info --format '{{.ServerVersion}}'
29.7.2
```

- Sonuç: GEÇTİ (Docker başlatıldı; gerçek konteyner testleri koşulabildi)

### 2) `./.venv/Scripts/python.exe kaynak/testler/betikler/00_kurulum.py`

- Beklenen: yönetici oluşturulur, gözlem BDM'leri hazırlanır.
- Gerçek çıktı:

```
kurulum zaten tamam (409); mevcut yönetici ile devam ediliyor.
kurulum tamam; yönetici id=None
vllm bdm id=2 durum=taslak konteyner=None
ollama bdm id=3 durum=taslak yerel_mi=True
ozel bdm id=4 durum=taslak yerel_mi=False
ollama(default) bdm id=5 durum=taslak
{"vllm": 2, "ollama": 3, "ozel": 4, "ollama_varsayilan": 5}
```

- Sonuç: GEÇTİ

### 3) `./.venv/Scripts/python.exe kaynak/testler/betikler/01_yasam_dongusu.py`

- Beklenen: `taslak`ta `baslat` 409; `durdu`da tekrar `durdur` 409; `hata`dan çıkış yolu belli; diğer tüm geçişler tablo halinde.
- Gerçek çıktı (kırpılmış, değiştirilmemiş):

```
| senaryo                     | kod | hata kodu          | sonuç                                   | yanıt özeti
|---|---|---|---|---|
| taslak→baslat                | 409 | gecersiz_gecis     | DB durum=taslak    | {'hata': {'kod': 'gecersiz_gecis', 'mesaj': "'taslak' durumundan 'calisiyor' durumuna geçilemez.',
| taslak→durdur                | 409 | gecersiz_gecis     | DB durum=taslak    | ... 'taslak' durumundan 'durdu' ...
| taslak→yeniden-baslat        | 409 | gecersiz_gecis     | DB durum=taslak    | ... 'taslak' durumundan 'calisiyor' ...
| hazir→baslat                 | 200 | -                  | DB durum=calisiyor | {'durum': 'calisiyor', 'konteyner_id': 'yerel:matris-hazir'}
| calisiyor→baslat             | 409 | gecersiz_gecis     | DB durum=calisiyor | ... 'calisiyor' durumundan 'calisiyor' ...
| calisiyor→yeniden-baslat     | 200 | -                  | DB durum=calisiyor | {'durum': 'calisiyor', 'konteyner_id': 'yerel:matris-hazir'}
| calisiyor→durdur             | 200 | -                  | DB durum=durdu     | {'durum': 'durdu'}
| durdu→durdur                 | 409 | gecersiz_gecis     | DB durum=durdu     | ... 'durdu' durumundan 'durdu' ...
| durdu→baslat                 | 200 | -                  | DB durum=calisiyor | {'durum': 'calisiyor', 'konteyner_id': 'yerel:matris-hazir'}
| durdu→yeniden-baslat         | 200 | -                  | DB durum=calisiyor | {'durum': 'calisiyor', 'konteyner_id': 'yerel:matris-durdu'}
| hazir→yeniden-baslat         | 409 | gecersiz_gecis     | DB durum=hazir     | ... 'hazir' durumundan 'calisiyor' ...
| hata→baslat                  | 409 | gecersiz_gecis     | DB durum=hata      | ... 'hata' durumundan 'calisiyor' ...
| hata→durdur                  | 409 | gecersiz_gecis     | DB durum=hata      | ... 'hata' durumundan 'durdu' ...
| hata→yeniden-baslat          | 409 | gecersiz_gecis     | DB durum=hata      | ... 'hata' durumundan 'calisiyor' ...

===== hata durumundan çıkış denemeleri =====
[PATCH /bdm/{id} durum=hazir] HTTP 200 ..."durum":"hata"...
  DB durum (PATCH sonrası) = hata
[POST /bdm/hazirlama/{id}/dogrula] HTTP 200 {"basarili":true,"gecikme_ms":4,"modeller":["llama3"],"mesaj":"Bağlantı başarılı; 1 model listelendi."}
  DB durum (doğrula sonrası) = hazir

===== Olmayan BDM =====
| yok→baslat                   | 404 | bulunamadi         | DB durum=kayıt yok   | {'hata': {'kod': 'bulunamadi', 'mesaj': 'BDM kaydı bulunamadı.', 'ayrinti': {'bdm_id': 999999}}}
[GET yok/durum] HTTP 404 {"hata":{"kod":"bulunamadi",...}}
```

- Sonuç: GEÇTİ (`taslak→baslat` 409, `durdu→durdur` 409, `hata`dan yönetim uçlarıyla çıkış yok — çıkış yalnız `POST /bdm/hazirlama/{id}/dogrula` ile)

### 4) `./.venv/Scripts/python.exe kaynak/testler/betikler/02_kalicilik_denetim_yetki.py`

- Beklenen: `baslat` yanıtı `konteyner_id` içerir ve DB'ye yazılır; `durdur` sonrası korunur; her geçiş denetim izine düşer; yetki matrisi 401/403.
- Gerçek çıktı (kırpılmış):

```
===== A) baslat başarısı: konteyner_id yanıtta + DB'de kalıcı mı? =====
[POST baslat] HTTP 200 {"durum":"calisiyor","konteyner_id":"yerel:kalicilik"}
  yanıttaki konteyner_id = 'yerel:kalicilik'
  DB durum=calisiyor konteyner={"image": "ollama/ollama:latest", "gpu": false, "port": 11434, "bellek_gb": 4.0, "konteyner_id": "yerel:kalicilik"}
  KALICI Mİ? True
[GET durum] HTTP 200 {"durum":"calisiyor","konteyner_id":"yerel:kalicilik","saglik":{"calisiyor":false,"hazir":false,"mesaj":"Ollama sunucusuna ulaşılamadı (http://localhost:11434): [WinError 10061] ..."}}

===== A2) durdur sonrası konteyner_id korunuyor mu? =====
[POST durdur] HTTP 200 {"durum":"durdu"}
  DB durum=durdu konteyner={... "konteyner_id": "yerel:kalicilik"}
  KORUNDU MU? True

===== B) Denetim izi: islem_kaydi satırları (doğrudan SQLite) =====
  (32, 1, 'bdm.olusturuldu', 'bdm', '16', '{"slug": "kalicilik", "saglayici": "ollama"}', '127.0.0.1', ...)
  (33, 1, 'bdm.baslatildi', 'bdm', '16', '{"konteyner_id": "yerel:kalicilik", "surucu": "yerel"}', '127.0.0.1', ...)
  (34, 1, 'bdm.durduruldu', 'bdm', '16', '{"konteyner_id": "yerel:kalicilik", "surucu": "yerel"}', '127.0.0.1', ...)
  satır sayısı = 3
  eylemler = ['bdm.olusturuldu', 'bdm.baslatildi', 'bdm.durduruldu']

===== C) PATCH /{id}/yol: nerede saklanıyor, baslat koruyor mu? =====
[PATCH yol (yanıt)] HTTP 200 {"id":17,...,"konteyner":{"image":"ollama/ollama:latest","gpu":false,"port":11434,"bellek_gb":4.0,"konteyner_id":"yerel:yol-testi","yol":{"oncelik":5,"takma_ad":"hizli-model"}},...}
  yanıt anahtarları = ['aciklama','api_anahtari_maskeli','baglam_penceresi','durum','gorunen_ad','guncellenme','id','konteyner','maks_cikti','olusturulma','saglayici','sicaklik_varsayilan','sistem_istemi','slug','temel_url','upstream_model','yerel_mi','yetenekler']
  DB konteyner = {..."yol": {"oncelik": 5, "takma_ad": "hizli-model"}}
[PATCH yol (boş gövde)] HTTP 200 ...
[PATCH yol (oncelik=9999)] HTTP 400 {"hata":{"kod":"dogrulama_hatasi",... "Input should be less than or equal to 1000"}}
[PATCH yol (takma_ad='')] HTTP 400 {"hata":{"kod":"dogrulama_hatasi",... "String should have at least 1 character"}}

===== C2) yeniden baslat sonrası yol korunuyor mu? =====
[POST yeniden-baslat] HTTP 200 {"durum":"calisiyor","konteyner_id":"yerel:yol-testi"}
  yol korundu mu? True

===== D) Yetki matrisi: anonim / son_kullanici =====
  ANONİM POST   /16/baslat             → 401 kimlik_gerekli
  ANONİM POST   /16/durdur             → 401 kimlik_gerekli
  ANONİM POST   /16/yeniden-baslat     → 401 kimlik_gerekli
  ANONİM GET    /16/durum              → 401 kimlik_gerekli
  ANONİM GET    /16/saglik             → 401 kimlik_gerekli
  ANONİM GET    /16/gunlukler          → 401 kimlik_gerekli
  ANONİM PATCH  /16/yol                → 401 kimlik_gerekli
  ANONİM GET    /surucu/durum          → 401 kimlik_gerekli
  SON_KULLANICI (tüm 8 uç)             → 403 yetki_yok
```

- Sonuç: GEÇTİ (kalıcılık, denetim izi, `yol` korunması, yetki matrisi sözleşmeye uygun)

### 5) `./.venv/Scripts/python.exe kaynak/testler/betikler/04_docker_surucu.py`

- Beklenen: `--gpus` device request, port eşleme, sağlık sondası ve log akışı gerçekten yapılır.
- Gerçek çıktı (kırpılmış):

```
== 1) durum() ==
{"surucu": "docker", "docker": true, "gpu": true, "gpu_listesi": ["NVIDIA GeForce RTX 3080 Ti"], "image_onbellek": [], "surum": "29.7.2", "mesaj": ""}

== 2) gerçek konteyner başlatma ==
konteyner_id = fc34fd8b6f693f9f755e436551e76659e4658e56e6861034a3780307b1b804d0
PortBindings = {"18080/tcp": [{"HostIp": "", "HostPort": "18080"}]}
Ports        = {"18080/tcp": [{"HostIp": "0.0.0.0", "HostPort": "18080"}, {"HostIp": "::", "HostPort": "18080"}]}
Labels       = {"kutyai.bdm": "docker-gozlem", "maintainer": "NGINX Docker Maintainers <...>"}
Env          = ["GOZLEM=1", "PATH=...", ...]
Memory       = 1073741824
DeviceRequests = null
Cmd          = ["nginx", "-g", "daemon off;"]
Durum        = running

== 3) sağlık sondası: manifest'te saglik_url YOK iken ==
{"calisiyor": true, "hazir": true, "mesaj": "Çalışıyor.", "ayrinti": {"konteyner_id": "fc34...", "durum": "running"}}
  ayrinti'da saglik_url var mı? -> False

== 4) port gerçekten yayınlanıyor mu ==
ULAŞILAMADI: Server disconnected without sending a response.

== 5) günlük akışı (gerçek konteyner) ==
  okunan satır sayısı = 5
  | 2026/09/12 19:42:56 [notice] 1#1: start worker process 34
  | ... (5 satır)

== 6) saglik_url etiketi VAR iken sonda çalışıyor mu (bozuk adres) ==
{"calisiyor": true, "hazir": false, "mesaj": "Sağlık adresine ulaşılamadı: Server disconnected without sending a response.", "ayrinti": {"konteyner_id": "b4fd...", "durum": "running", "saglik_url": "http://127.0.0.1:18081/health"}}

== 7) GPU device request gerçekten gönderiliyor mu (gpu=True) ==
  gpu=True ile başlatıldı: 776a4f1bb0f5cdef9f87690ffccd0424ace206c31bbba6bafc78b29e790bf329
  DeviceRequests = [{"Driver": "", "Count": -1, "DeviceIDs": [], "Capabilities": [["gpu"]], "Options": {}}]

== 8) durdur + sil ==
  durdur sonrası saglik: {"calisiyor": false, "mesaj": "Durduruldu."}
  konteyner silindi (containers.get hata verdi)

== 9) olmayan konteyner kimliğiyle durdur/sil/saglik ==
Durdurulacak konteyner bulunamadı: boyle-bir-konteyner-yok
  saglik: {"calisiyor": false, "hazir": false, "mesaj": "Konteyner bulunamadı."}
  gunlukler SurucuYok: Konteyner bulunamadı.
```

- Not: 4. adımdaki "ULAŞILAMADI" bir yarış durumudur (Docker proxy portu bağlar, nginx henüz dinlemiyor); `docker run -d -p 18090:80 nginx:alpine` + 4 sn bekleme ile `curl` → `HTTP:200` alındı. Port eşleme çalışıyor.
- Sonuç: GEÇTİ (`--gpus` device request, port eşleme, etiket, bellek sınırı, günlük akışı gerçek Docker'da doğrulandı) — sağlık sondası yalnız `saglik_url` etiketi varken çalışıyor (bkz. Bulgu 4)

### 6) `./.venv/Scripts/python.exe kaynak/testler/betikler/05_gpu_manifest.py`

- Beklenen: GPU yoksa `vllm`/`tgi` sessizce CPU'ya düşmeden 503 `surucu_yok`; manifest içeriği sözleşmeye uygun; Docker kapalıyken `surucu/durum` 200 + Türkçe.
- Gerçek çıktı (kırpılmış):

```
== 1) manifest_uret çıktısı (gerçek hazırlama modülü) ==
  vllm     anahtarlar=['bellek_gb', 'gpu', 'image', 'komut', 'ortam', 'port'] saglik_url var mı? False
           {"image": "vllm/vllm-openai:latest", "komut": ["vllm", "serve", "mistralai/Mistral-7B-Instruct-v0.2", "--port", "8000"], "port": 8000, "gpu": true, "bellek_gb": 14.0, "ortam": {}}
  tgi      anahtarlar=['bellek_gb', 'gpu', 'image', 'komut', 'ortam', 'port'] saglik_url var mı? False
  ozel     GecersizIstek: Bu sağlayıcı uzak sunucuda çalışır; konteyner manifesti üretilemez.

== 2) GPU'suz sürücü (gpu_var=False) + vllm: sessiz CPU düşüşü var mı? ==
  vllm: HTTP 503 {"hata":{"kod":"surucu_yok","mesaj":"Bu model GPU gerektirir; Ollama gibi CPU uyumlu bir sağlayıcı seçin veya GPU çalışma zamanını kurun.","ayrinti":{"saglayici":"vllm"}}}
    sürücüye başlat çağrısı yapıldı mı? False (False olmalı: sessiz düşüş yok)
  tgi: HTTP 503 {"hata":{"kod":"surucu_yok","mesaj":"Bu model GPU gerektirir; ..."}}  (sürücüye başlat çağrısı yok)

== 3) GPU'lu sürücü (gpu_var=True) + vllm: 200 ve konteyner_id ==
  HTTP 200 {"durum":"calisiyor","konteyner_id":"sahte-gpu-vllm-1"}

== 4) Docker kapalı (durum() SurucuYok) + vllm ==
  HTTP 503 {"hata":{"kod":"surucu_yok","mesaj":"Docker çalışma zamanına ulaşılamadı. Docker kurulu ve çalışır durumda olmalıdır.","ayrinti":{}}}
  GET surucu/durum → HTTP 200 {"surucu":"yok","docker":false,"gpu":false,"gpu_listesi":[],"image_onbellek":[],"mesaj":"Docker çalışma zamanına ulaşılamadı. ..."}
```

- Sonuç: GEÇTİ (GPU'suz + `vllm|tgi` → 503 `surucu_yok`, sürücüye başlat çağrısı yok ⇒ sessiz CPU düşüşü yok) — ancak manifest `saglik_url` üretmiyor (Bulgu 4)

### 7) `./.venv/Scripts/python.exe kaynak/testler/betikler/03_sse.py`

- Beklenen: konteyner yokken 503; olay biçimi `event: satir` + `data: {"metin": ...}`; akış kapanırken sızıntı/askıda kalma yok.
- Gerçek çıktı (kırpılmış):

```
== 1) konteyner kaydı YOKKEN ==
  HTTP 503 content-type=application/json
  | '{"hata":{"kod":"surucu_yok","mesaj":"Bu model için çalışan konteyner kaydı yok.","ayrinti":{"bdm_id":18}}}'

== 2) kayıt var, sürücü 'yerel' (olmayan Ollama) ==
  HTTP 200 content-type=text/event-stream; charset=utf-8
  başlıklar: cache-control=no-cache x-accel-buffering=no
  | 'event: satir\ndata: {"metin": "Ollama günlükleri REST üzerinden okunamaz; sunucu günlükleri için \'ollama serve\' çıktısına bakın (http://localhost:11434)."}\n\n'
  olay sayısı (event: satir) = 1

== 3) kayıt var ama konteyner Docker'da YOK (vllm/yel) ==
  HTTP 200 content-type=text/event-stream; charset=utf-8
  AKIŞ HATASI (RemoteProtocolError): peer closed connection without sending complete message body (incomplete chunked read)
  geçen süre = 0.28 sn, parça sayısı = 0

== 4) gerçek Docker konteyneri ile akış ==
  HTTP 200 content-type=text/event-stream; charset=utf-8
  AKIŞ HATASI (ReadTimeout): timed out
  geçen süre = 10.20 sn, parça sayısı = 5
  | 'event: satir\ndata: {"metin": "2026/09/12 19:44:05 [notice] 1#1: start worker process 49"}\n\n'
  | ... (5 olay) ...   olay sayısı (event: satir) = 5

== 5) satir parametresi doğrulaması ==
  satir=0     → HTTP 400 {"hata":{"kod":"dogrulama_hatasi",...}}
  satir=5000  → HTTP 400 ...
  satir=abc   → HTTP 400 ...
```

- Sonuç: KALDI (olay biçimi doğru; ancak 3. adımda 200 + kopan bağlantı — Bulgu 3; 4. adımda akış hiç kapanmıyor — Bulgu 7)

### 8) `./.venv/Scripts/python.exe kaynak/testler/betikler/06_iplik.py <sunucu-pid>`

- Beklenen: terk edilen SSE akışları iş parçacığı sızdırmaz / askıda kalmaz.
- Gerçek çıktı:

```
konteyner=55cf519dd494ca49…  sunucu pid=21296
T0 taban iş parçacığı sayısı = 3
  tur 1: HTTP 200, ilk parça 130 bayt; bağlantı TERK EDİLİYOR
  tur 1 sonrası iş parçacığı = 3
  tur 2: HTTP 200, ilk parça 130 bayt; bağlantı TERK EDİLİYOR
  tur 2 sonrası iş parçacığı = 3
  tur 3: HTTP 200, ilk parça 130 bayt; bağlantı TERK EDİLİYOR
  tur 3 sonrası iş parçacığı = 3
T1 (3 akış terk edildikten sonra) = 3 (taban 3, fark 0)
  diğer uç hâlâ çalışıyor mu? HTTP 200
T2 (konteyner durdurulduktan sonra) = 3
```

- Sonuç: GEÇTİ (iş parçacığı sızıntısı gözlenmedi)

### 9) `./.venv/Scripts/python.exe kaynak/testler/betikler/07_akis_sonu.py`

- Beklenen: günlük akışı mevcut satırlar bittikten sonra sonlanır ya da bloke kalır — hangisi olduğu ölçülür.
- Gerçek çıktı:

```
konteyner = f336ac54f10b6c57…
SONUÇ: 39 satırdan sonra 8 sn boyunca VERİ GELMEDİ ve akış KAPANMADI (bloke)

-- ek: `tail` sınırından sonra davranış (tail=2) --
  tail=2 → 2 satır sonra bloke (veri yok, kapanmadı)
```

- Sonuç: KALDI (akış hiç kapanmıyor, heartbeat yok — Bulgu 7)

### 10) `./.venv/Scripts/python.exe kaynak/testler/betikler/08_api_docker.py`

- Beklenen: canlı HTTP üzerinden gerçek Docker konteyneri ile `baslat`/`gunlukler`/`durdur`; `konteyner_id` yanıtta ve DB'de.
- Gerçek çıktı (kırpılmış):

```
== 1) POST /baslat (gerçek Docker) ==
[POST baslat] HTTP 200 {"durum":"calisiyor","konteyner_id":"5dd2c87fdac1337d330b0319fe6572fe08b16398919b661e10838d167a8e640c"}
  DB durum=calisiyor konteyner={"port": 18800, "image": "vllm/vllm-openai:latest", "gpu": true, "bellek_gb": 14.0, "konteyner_id": "5dd2c87f..."}
  KALICI Mİ? True

== 2) docker inspect ile doğrulama ==
  Image        = vllm/vllm-openai:latest
  Cmd          = ["vllm", "serve", "mistralai/Mistral-7B-Instruct-v0.2", "--port", "18800"]
  Labels       = {"kutyai.bdm": "docker-vllm", ...}
  PortBindings = {"18800/tcp": [{"HostIp": "", "HostPort": "18800"}]}
  DeviceRequests = [{"Driver": "", "Count": -1, "DeviceIDs": [], "Capabilities": [["gpu"]], "Options": {}}]
  Memory       = 15032385536
  State        = {"status": "exited", "exit": 127}
  günlük satırları = "/docker-entrypoint.sh: exec: line 47: vllm: not found"

== 3) GET /durum ve /saglik (kendi kendine ölmüş konteyner) ==
[GET durum] HTTP 200 {"durum":"calisiyor","konteyner_id":"5dd2c87f...","saglik":{"calisiyor":false,"hazir":false,"mesaj":"Durduruldu."}}
[GET saglik] HTTP 200 {"calisiyor":false,"hazir":false,"mesaj":"Durduruldu.","ayrinti":{"konteyner_id":"5dd2c87f...","durum":"exited"}}

== 4) GET /gunlukler (gerçek konteyner günlükleri) ==
  HTTP 200 text/event-stream; charset=utf-8
  | 'event: satir\ndata: {"metin": "/docker-entrypoint.sh: exec: line 47: vllm: not found"}\n\n'

== 5) POST /durdur (konteyner zaten çıkmış durumda) ==
[POST durdur] HTTP 200 {"durum":"durdu"}
  DB durum=durdu

== 6) denetim izi satırları ==
  ('bdm.baslatildi', '{"konteyner_id": "5dd2c87f...", "surucu": "docker"}', '127.0.0.1', ...)
  ('bdm.durduruldu', '{"konteyner_id": "5dd2c87f...", "surucu": "docker"}', '127.0.0.1', ...)
```

- Not: büyük imaj indirmemek için `nginx:alpine` yerel olarak `vllm/vllm-openai:latest` diye etiketlendi; konteyner komutu `vllm ...` bulunmadığı için süreç hemen çıktı (exit 127). Bu, gerçek bir Docker yaşam döngüsünü ve kendi kendine ölen konteyner davranışını gözlemeyi sağladı. Etiket ve konteyner sonunda silindi.
- Sonuç: GEÇTİ (baslat/gunlukler/durdur gerçek konteynerle çalışıyor; `konteyner_id` kalıcı) — ölen konteynerde `durum` hâlâ `calisiyor` (Bulgu 6)

### 11) `./.venv/Scripts/python.exe kaynak/testler/betikler/11_docker_yeniden.py`

- Beklenen: `yeniden-baslat` eski konteyneri kaldırır, yenisini başlatır, kimliği DB'ye yazar, denetim satırı ekler.
- Gerçek çıktı (kırpılmış):

```
== baslat ==
  HTTP 200 {"durum":"calisiyor","konteyner_id":"2129459be55e44ce37c6ce8b3b998b2e129638be9ec9c0111dd5dcc1e84a4b9e"}

== yeniden-baslat ==
  HTTP 200 {"durum":"calisiyor","konteyner_id":"4b07e8571cf011380706bcf09edec4e57fe02819a18fa5e89459a2aea06b35fa"}
  yeni konteyner kimliği farklı mı? True
  eski konteyner inspect → çıkış=1 çıktı=error: no such object: 2129459b...
  DB konteyner = {"port": 18810, "image": "vllm/vllm-openai:latest", "gpu": true, "bellek_gb": 14.0, "konteyner_id": "4b07e857..."}
  DB'deki kimlik yeni mi? True

== denetim izi ==
  ('bdm.baslatildi', '{"konteyner_id": "2129459b...", "surucu": "docker"}')
  ('bdm.yeniden_baslatildi', '{"konteyner_id": "4b07e857...", "surucu": "docker"}')
```

- Sonuç: GEÇTİ

### 12) `./.venv/Scripts/python.exe kaynak/testler/betikler/12_kapanis.py`

- Beklenen: yerel sürücü sağlığı BDM'nin kendi adresini yoklar; denetim izi tamdır.
- Gerçek çıktı (kırpılmış):

```
-- sahte Ollama (127.0.0.1:11435) AYAKTA; GET /{id}/saglik --
[GET bdm 16/saglik] HTTP 200 {"calisiyor":false,"hazir":false,"mesaj":"Ollama sunucusuna ulaşılamadı (http://localhost:11434): [WinError 10061] ...","ayrinti":{"konteyner_id":"yerel:kalicilik","temel_url":"http://localhost:11434","modeller":[]}}
[GET bdm 16/durum]  HTTP 200 {"durum":"durdu","konteyner_id":"yerel:kalicilik","saglik":{"calisiyor":false,...}}
[GET bdm 17/saglik] HTTP 200 {"calisiyor":false,"hazir":false,"mesaj":"Ollama sunucusuna ulaşılamadı (http://localhost:11434): ...","ayrinti":{"konteyner_id":"yerel:yol-testi","temel_url":"http://localhost:11434","modeller":[]}}
```
(`bdm 17`: `temel_url=http://127.0.0.1:11435/v1`, `durum=calisiyor`, `konteyner_id=yerel:yol-testi`)

```
== 2) Sahte Ollama'ya gelen istekler (ham günlük) ==
GET /api/tags
GET /api/tags
... (yalnız GET /api/tags ve GET /v1/models; HİÇ POST /api/generate yok)
```

```
== 3) Denetim izi dökümü (bdm hedefli) ==
  (10, 1, 'bdm.baslatildi', '7', '{"konteyner_id": "yerel:matris-hazir", "surucu": "yerel"}', ...)
  (11, 1, 'bdm.yeniden_baslatildi', '7', '{"konteyner_id": "yerel:matris-hazir", "surucu": "yerel"}', ...)
  (12, 1, 'bdm.durduruldu', '7', '{"konteyner_id": "yerel:matris-hazir", "surucu": "yerel"}', ...)
  (37, 1, 'bdm.yeniden_baslatildi', '17', '{"konteyner_id": "yerel:yol-testi", "surucu": "yerel"}', ...)

== 4) PATCH /{id}/yol denetim izi yazıyor mu? ==
  PATCH → HTTP 200
  bdm 16 için eylemler = ['bdm.olusturuldu', 'bdm.baslatildi', 'bdm.durduruldu']
```

- Sonuç: KALDI (yerel sürücü sağlığı yanlış adresi yokluyor — Bulgu 2; `durdur` modeli hiç boşaltmıyor — Bulgu 1; `PATCH /yol` denetim izi yazmıyor — Bulgu 8)

### 13) `./.venv/Scripts/python.exe kaynak/testler/betikler/09_docker_kapali.py` ve `10_docker_karsilastirma.py`

- Beklenen: Docker kapalıyken `GET /surucu/durum` 200 + `docker:false` + Türkçe mesaj (500 değil); Docker açıkken alanlar dolu.
- Gerçek çıktı:

```
== Docker AÇIK ==
[GET /surucu/durum [docker açık]] HTTP 200 {"surucu":"docker","docker":true,"gpu":true,"gpu_listesi":["NVIDIA GeForce RTX 3080 Ti"],"image_onbellek":["nginx:alpine"],"mesaj":""}
[GET /saglik/hazir [docker açık]] HTTP 200 {"durum":"hazir","veritabani":"tamam","surucu":{"ad":"docker","docker":true,"gpu":true,"mesaj":""},"surum":"0.1.0"}

== Docker KAPALI ==
$ docker info → çıkış=1
Server:
failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine; check if the path is correct and if the daemon is running: open //./pipe/dockerDesktopLinuxEngine: Sistem belirtilen dosyayı bulamıyor.
[GET /surucu/durum [docker kapalı]] HTTP 200 {"surucu":"yok","docker":false,"gpu":false,"gpu_listesi":[],"image_onbellek":[],"mesaj":"Docker çalışma zamanına ulaşılamadı. Docker kurulu ve çalışır durumda olmalıdır."}
[GET /saglik/hazir [docker kapalı]] HTTP 200 {"durum":"hazir","veritabani":"tamam","surucu":{"ad":"yok","docker":false,"gpu":false,"mesaj":"Docker çalışma zamanına ulaşılamadı. ..."},"surum":"0.1.0"}

== Docker KAPALIYKEN yaşam döngüsü uçları ==
[POST vllm/baslat (durdu→calisiyor)] HTTP 503 {"hata":{"kod":"surucu_yok","mesaj":"Docker çalışma zamanına ulaşılamadı. Docker kurulu ve çalışır durumda olmalıdır.","ayrinti":{}}}
[GET vllm/durum]  HTTP 200 {"durum":"durdu","konteyner_id":"5dd2c87f...","saglik":{"calisiyor":false,"hazir":false,"mesaj":"Docker çalışma zamanına ulaşılamadı. ..."}}
[GET vllm/saglik] HTTP 200 {"calisiyor":false,"hazir":false,"mesaj":"Docker çalışma zamanına ulaşılamadı. ...","ayrinti":{}}
[GET vllm/gunlukler] → httpx.RemoteProtocolError: peer closed connection without sending complete message body (incomplete chunked read)
```

- Sonuç: GEÇTİ (sürücü durumu her iki durumda da sözleşmeye uygun; 500 yok) — `/gunlukler` için Bulgu 3

### 14) `./.venv/Scripts/python.exe kaynak/testler/betikler/13_uzak_saglayici.py`

- Beklenen: uzak sağlayıcıda `baslat` davranışı belgelenir.
- Gerçek çıktı:

```
[POST ozel (uzak) baslat] HTTP 400 {"hata":{"kod":"gecersiz_istek","mesaj":"Bu sağlayıcı uzak sunucuda çalışır; konteyner manifesti üretilemez.","ayrinti":{"saglayici":"ozel"}}}
  DB durum=hazir
[POST ozel (uzak) durdur] HTTP 409 {"hata":{"kod":"gecersiz_gecis","mesaj":"'hazir' durumundan 'durdu' durumuna geçilemez.",...}}
[POST ollama (uzak adres) baslat] HTTP 200 {"durum":"calisiyor","konteyner_id":"yerel:ollama-gozlem"}
[POST ollama (uzak adres) durdur] HTTP 200 {"durum":"durdu"}
```

- Sonuç: KALDI (`openai|azure|openrouter|ozel` için `hazir→calisiyor` geçişi hiçbir yoldan yapılamıyor — Bulgu 10)

## Bulgular

- [BLOCKER] `arkauc/app/servisler/konteyner_yerel.py:82-88` (+ `arkauc/app/servisler/konteyner.py:164`) — `YerelSurucusu.durdur` hiçbir şey yapmıyor: kayıt yalnız `self._bdmler` içinde (satır 33) ve `baslat` her istekte yeni oluşturulan sürücü örneğine yazıyor; `surucu_al` her çağrıda `YerelSurucusu()` döndürdüğü için sonraki istekteki `durdur` sözlüğü boş bulup sessizce `return` ediyor (docstring "Modeli bellekten boşaltır" diyor). Sonuç: `POST /{id}/durdur` → `200 {"durum":"durdu"}` ve `islem_kaydi`'ye `bdm.durduruldu` yazılıyor, ama Ollama'ya hiç `POST /api/generate {keep_alive:0}` gitmiyor; model bellekten boşaltılmıyor. Beklenen: durdurulan modelin boşaltılması (ya da boşaltılamıyorsa hatanın bildirilmesi). Yeniden üretme: sahte Ollama 11435'te ayakta → `ollama` BDM (`temel_url=http://127.0.0.1:11435/v1`) → `hazir` → `baslat` (200) → `durdur` (200) → `gecici/fake_ollama.log` içinde `POST /api/generate` **yok**.
- [MAJOR] `arkauc/app/servisler/konteyner_yerel.py:106-115` (ve `:116-121`) — `saglik`/`gunlukler`, `self._bdmler` kaydı olmadığında (yani her istekte) `self._temel_url`'a yani **varsayılan `http://localhost:11434`**'e düşüyor; BDM'nin kendi `temel_url`'u tamamen yok sayılıyor. Kanıt: `bdm 17` (`temel_url=http://127.0.0.1:11435/v1`, `durum=calisiyor`, `konteyner_id=yerel:yol-testi`) için `GET /17/saglik` → `{"calisiyor":false,"mesaj":"Ollama sunucusuna ulaşılamadı (http://localhost:11434)..."}` — oysa 11435 ayakta ve BDM "çalışıyor". Beklenen: sağlık, BDM'nin kayıtlı adresini yoklamalı (`ayrinti.temel_url` = BDM'in adresi). Yeniden üretme: farklı portta bir Ollama'ya işaret eden BDM oluştur, `baslat`, ardından `GET /{id}/saglik`.
- [MAJOR] `bdm_yönetim_ucu/uc.py:109-114` + `arkauc/app/servisler/konteyner_docker.py:250` — konteyner kaydı **var** ama konteyner Docker'da yoksa (ya da Docker kapalıysa) hata, `StreamingResponse` gövdesi üretilirken oluşuyor; başlıklar çoktan gittiği için istemci `200 text/event-stream` alıp bağlantının ortasında kopuyor, hata zarfı/`event: hata` hiç gelmiyor. Kanıt: `GET /20/gunlukler` (`konteyner_id="boyle-bir-konteyner-yok"`) → `HTTP 200` + `RemoteProtocolError: peer closed connection without sending complete message body`; Docker kapalıyken kayıtlı `konteyner_id` ile aynı davranış. Beklenen: API.md §1/§11 gereği `503 surucu_yok` ya da akış içinde `event: hata` çerçevesi. Yeniden üretme: BDM'in `konteyner.konteyner_id` alanına var olmayan bir kimlik yaz, `GET /bdm/yonetim/{id}/gunlukler`.
- [MAJOR] `bdm_hazırlama_ucu/manifest.py:95-102` + `arkauc/app/servisler/konteyner_docker.py:227-230, 272-276` — Docker sürücüsünün HTTP sağlık sondası (`_http_sondasi`) yalnızca `manifest["saglik_url"]` varsa etkinleşiyor; `manifest_uret` bu anahtarı **hiçbir sağlayıcıda** üretmiyor (ölçüm: `ollama/vllm/tgi` için anahtarlar `['bellek_gb','gpu','image','komut','ortam','port']`). Bu yüzden üretimde `hazir` = "konteyner durumu running" oluyor; servis gerçekten hazır değilken bile `hazir:true` dönüyor (aynı konteynerde bir saniye sonra yapılan HTTP isteği "Server disconnected" ile başarısız oldu). Etiket elle verildiğinde sondanın çalıştığı doğrulandı (`saglik_url=http://127.0.0.1:18081/health` → `hazir:false`, `ayrinti.saglik_url` dolu). Beklenen: container'lı sağlayıcılar için manifest'te sağlık adresi (örn. `http://localhost:{port}/health` veya `/v1/models`) bulunmalı. Yeniden üretme: `manifest_uret` çıktısının anahtarlarını yazdır; BDM'i Docker ile başlat, `GET /{id}/saglik` → `ayrinti` içinde `saglik_url` yok.
- [MINOR] `bdm_yönetim_ucu/uc.py:119-133` — `PATCH /{id}/yol` alanları `bdm.konteyner["yol"]` altına yazıyor; bu anahtar ne API.md §2 `Bdm.konteyner` (`image?/gpu?/port?/bellek_gb?`) ne de spec §4.5 konteyner JSON'unda (`image,gpu,port,bellek_gb,argumanlar,konteyner_id`) tanımlı; spec'teki `argumanlar` ise hiç yazılmıyor. Değer `baslat`/`yeniden-baslat` sonrasında korunuyor (`_konteyner_kaydi` satır 77-86) ve yanıt tam bir `Bdm` sözlüğü. Beklenen: saklama yerinin sözleşmede tanımlı olması ya da `Bdm.konteyner` tipinin güncellenmesi. Yeniden üretme: `PATCH /{id}/yol {"takma_ad":"hizli-model","oncelik":5}` → yanıt `konteyner.yol` içeriyor.
- [MINOR] `arkauc/app/servisler/konteyner_docker.py:206-238` — kendi kendine ölen konteynerde (exit 127) `_saglik` mesajı "Durduruldu." dönerken `GET /{id}/durum` hâlâ `durum:"calisiyor"` bildiriyor; `hata` durumuna otomatik geçiş yok, panel iki uçtan çelişkili bilgi alıyor. Beklenen: ölmüş konteyner için net mesaj ("Konteyner çıktı, çıkış kodu 127") ve/veya `hata` durumuna geçiş. Yeniden üretme: `docker tag nginx:alpine vllm/vllm-openai:latest` → `baslat` (komut bulunamaz, exit 127) → `GET /{id}/durum`.
- [MINOR] `arkauc/app/servisler/konteyner_docker.py:249-266` — günlük akışı mevcut satırlar tükendikten sonra kapanmıyor ve hiçbir heartbeat/`event: bitti` üretmiyor; SSE bağlantısı süresiz açık kalıyor (`tail=2` için 2 satır, `tail=200` için 39 satır sonra 8 sn boyunca veri yok ve akış kapanmadı; HTTP istemcisi 10 sn'de `ReadTimeout` aldı). İstemci "yeni satır yok" ile "akış öldü" durumunu ayırt edemiyor. Beklenen: periyodik yorum satırı (heartbeat) veya belgelenmiş açık uçlu akış. Yeniden üretme: `kaynak/testler/betikler/07_akis_sonu.py`.
- [MINOR] `bdm_yönetim_ucu/uc.py:119-133` — `PATCH /{id}/yol` bir yapılandırma değişikliği olmasına rağmen `islem_kaydi` satırı yazmıyor (ölçüm: `bdm 16` için eylemler `['bdm.olusturuldu','bdm.baslatildi','bdm.durduruldu']`; PATCH sonrası yeni satır yok). Beklenen: denetim izi kapsamının netleştirilmesi (ISLETIM.md §2 yalnız yaşam döngüsü geçişlerini zorunlu kılıyor; yönlendirme değişikliği iz bırakmıyor). Yeniden üretme: `PATCH /{id}/yol` + `SELECT eylem FROM islem_kaydi WHERE hedef_id='16'`.
- [MINOR] `bdm_listesi/katalog.py:80-81` — `guncellenme` alanı yanıtlarda bazen `...T19:42:17.098084+00:00` (offset'li) bazen `...T19:42:17.098084` (offset'siz) dönüyor; aynı kaynağın `olusturulma` alanı offset'siz. Beklenen: API.md §2 gereği tek biçimli ISO-8601. Yeniden üretme: aynı BDM'e arka arkaya iki `PATCH /{id}/yol` isteği (`{}` ve `{"oncelik":5}`) → iki farklı biçim.
- [MINOR] `bdm_yönetim_ucu/yasam_dongusu.py:26-32` + `bdm_listesi/saglayicilar.py` — `openai|azure|openrouter|ozel` sağlayıcılarında `hazir→calisiyor` hiçbir yoldan yapılamıyor: `baslat` `400 gecersiz_istek` ("Bu sağlayıcı uzak sunucuda çalışır; konteyner manifesti üretilemez"), `durdu` ise `409`; panelde bu kayıtlar için "Başlat" düğmesi her zaman hata veriyor. Beklenen: uzak sağlayıcılarda `baslat` için ayrı bir kural (örn. `409 gecersiz_gecis`/no-op) veya durum makinesinin sağlayıcıya göre belgelenmesi. Yeniden üretme: `ozel` sağlayıcılı BDM → `durum=hazir` → `POST /{id}/baslat` → 400.

## Özet

10 bulgu (1 BLOCKER, 3 MAJOR, 6 MINOR).

- Doğrulananlar: durum makinesi (taslak→baslat 409, durdu→durdur 409, hata'dan yönetim uçlarıyla çıkış yok / çıkış `dogrula` ile), `baslat` başarısında `konteyner_id` yanıtta + DB'de kalıcı, `durdur` sonrası korunuyor, denetim izi her başlat/durdur/yeniden-başlat için yazılıyor (kullanıcı, IP, sürücü, konteyner kimliği), GPU'suz + `vllm|tgi` → 503 `surucu_yok` (sessiz CPU düşüşü yok, sürücüye başlat çağrısı yapılmıyor), Docker kapalıyken `GET /surucu/durum` 200 + `docker:false` + Türkçe mesaj, `/gunlukler` olay biçimi `event: satir` + `data: {"metin":...}`, `satir` sınırları 400, anonim 401 / `son_kullanici` 403 matrisinin 8 uçta tamamı, gerçek Docker ile port eşleme + `--gpus` `DeviceRequest(capabilities=[["gpu"]], count=-1)` + etiket + bellek sınırı + günlük akışı + `yeniden-baslat`'ta eski konteynerin gerçekten kaldırılması, terk edilen SSE akışlarında iş parçacığı sızıntısı olmaması.
- Doğrulanamayanlar: "GPU'suz makinede" senaryosu bu donanımda (RTX 3080 Ti) gerçek Docker ile kurulamadı; ölçüm sürücü ikamesiyle (`surucu_ata`) yapıldı. Gerçek Ollama sunucusu yoktu; `ollama` sağlayıcısı sahte sunucuyla (11435) denendi. `vllm/vllm-openai` ve `ghcr.io/...text-generation-inference` imajları indirilmedi (GB mertebesinde); Docker yolu `nginx:alpine` + yerel etiket ile gerçek konteyner üzerinden doğrulandı.
- Ortam: gözlem sonunda Docker daemon başlangıçtaki gibi **kapalı** bırakıldı; gözlem backend'i (8104) ve sahte Ollama (11435) `hub` ile **durduruldu**. Geri oynatmak için: `hub start` ile `goz-yonetim` (`uvicorn arkauc.app.main:app --port 8104`, `KUTYAI_VERITABANI_URL=sqlite+aiosqlite:///E:/kutyai-app/kaynak/testler/gecici/yonetim.db`) ve `goz-sahte-ollama` (`kaynak/testler/betikler/sahte_ollama.py`), ardından `betikler/00_kurulum.py` … `13_uzak_saglayici.py` sırasıyla.
- Ürün koduna yazılmadı (`git status --porcelain` → yalnız `?? kaynak/testler/`); betikler: `kaynak/testler/betikler/`.
