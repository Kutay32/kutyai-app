# sohbet gözlem logu — 2026-09-12

Bağımsız gözlem ajanı: `GozSohbet`. Ürün kodu **değiştirilmedi**; yalnızca
`kaynak/testler/` altına kanıt betikleri ve geçici veritabanı yazıldı.

## Kapsam

- API.md §1 (hata zarfı), §9 (sohbet + SSE biçimi), §13 (kullanım)
- spec §7.4 (sohbet uçları), §6 (hata zarfı / sunucu tarafı ayrıntı), §11 (maskeleme)
- `arkauc/app/api/sohbet.py`, `arkauc/app/api/kullanim.py`,
  `arkauc/app/servisler/upstream.py`, `arkauc/app/servisler/akış.py`,
  `arkauc/app/servisler/kota.py`, `bdm_konusma_gecmisi/yazici.py`,
  `bdm_konusma_gecmisi/sorgu.py`

## Ortam

| Bileşen | Değer |
|---|---|
| Backend | `http://127.0.0.1:8105` (`hub` süreç adı `sohbet-backend`) |
| Sahte upstream | `http://127.0.0.1:8191` (`hub` süreç adı `sahte-upstream-sohbet`) |
| Veritabanı | `kaynak/testler/gecici/sohbet-gozlem.db` (geçici SQLite) |
| Upstream istek kaydı | `kaynak/testler/gecici/sahte_upstream_istekler.jsonl` |

**Sapma:** Görev metni sahte upstream için 8199 numaralı portu veriyordu; 8199
o sırada başka bir gözlem ajanının süreci tarafından dinleniyordu
(`netstat -ano` → `127.0.0.1:8199 LISTENING 15648`). Çakışmamak için **8191**
kullanıldı. Sahte upstream `kaynak/testler/betikler/sahte_upstream_sohbet.py`
dosyasındadır; `/v1/chat/completions` üzerinde gerçek SSE üretir, gelen her
isteği JSONL'e yazar ve `model` alanına göre davranış değiştirir
(`hata-500`, `kati` = OpenAI rol doğrulaması yapan katı sunucu, `yavas` = 10×0.5 sn,
`kir` = 3 parça sonra bağlantıyı koparır).

Kurulum: yönetici `admin@acme.com`, son kullanıcılar `a@acme.com` / `b@acme.com`,
API anahtarları `K1`/`K2` (sahipsiz), BDM'ler `sahte-akis` (hazır), `kati-saglayici`,
`taslak-model`, `yavas-model`, `kiran-model`.

---

## Koşulan komutlar

### 0) Ortam kurulumu

```
./.venv/Scripts/python.exe kaynak/testler/betikler/gozlem_sohbet_kurulum.py
```

- Beklenen: `/saglik` 200, kurulum 201, BDM `hazir`, iki kullanıcı doğrulanmış, iki anahtar üretilmiş.
- Gerçek çıktı:

```
=== 1) GET /saglik
200 {"durum":"ayakta","surum":"0.1.0","ortam":"test","zaman":"2026-09-12T19:40:19.066246+00:00"}

=== 3) SQLite: BDM durumunu hazir yap
bdm durum: [(1, 'sahte-akis', 'hazir', 'http://127.0.0.1:8191/v1', 'sahte-akis')]

=== 4) POST /kimlik/panel-giris (yonetici)
200 True {"erisim_jetonu":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

=== 5) Kullanici A kayit + dogrula + giris
A kayit 201 ... "eposta":"a@acme.com","rol":"son_kullanici","durum":"beklemede"
A dogrula 200 {"dogrulandi":true}
A giris 200

=== 5) Kullanici B kayit + dogrula + giris
B kayit 201 ... "eposta":"b@acme.com" ...
B dogrula 200 {"dogrulandi":true}
B giris 200

=== 6) API anahtarlari K1, K2
K1 201 kuty_URBFf2E 9IUq
K2 201 kuty_HLAPTYF p8y3
```

- Sonuç: GEÇTİ

---

### 1) Gerçek SSE akışı — olay sırası ve parça birleşimi (çürütme hedefi 1)

```
./.venv/Scripts/python.exe kaynak/testler/betikler/gozlem_sohbet_akis.py
```

- Beklenen: `baslangic` → `parca`* → `kullanim` → `bitti`; parçaların birleşimi tam yanıt.
- Gerçek çıktı (kırpılmış, değiştirilmemiş):

```
durum: 200
basliklar: {'cache-control': 'no-cache', 'x-accel-buffering': 'no',
            'content-type': 'text/event-stream; charset=utf-8', 'transfer-encoding': 'chunked'}
  0.266s | event: baslangic
  0.266s | data: {"konusma_id": 1, "mesaj_id": 1}
  0.300s | event: parca
  0.300s | data: {"icerik": "YANIT: M"}
  ...
  0.868s | data: {"icerik": " 45 67"}
  0.870s | event: kullanim
  0.870s | data: {"token_girdi": 12, "token_cikti": 7, "gecikme_ms": 827}
  0.881s | event: bitti
  0.881s | data: {}

=== Olay sirasi
['baslangic', 'parca' ×28, 'kullanim', 'bitti']

=== Parcalarin birlestirilmesi
parca sayisi: 28
birlesik : YANIT: Merhaba, bana [MASKELENDI:eposta] adresinden ulasin; telefonum [MASKELENDI:telefon] ve TCKN [MASKELENDI:tckn]. Bu mesaj 60 karakterden uzun olmali ki baslik kirpilsin. | iletisim: ayse@acme.com | tel: 0532 123 45 67
beklenen : <aynı metin>
```

Birleşik metin beklenen ile **birebir aynı**; akış sırası sözleşmeye uygun,
`Content-Type: text/event-stream`, `Cache-Control: no-cache`,
`X-Accel-Buffering: no` başlıkları yerinde. `kullanim` olayı upstream `usage`
değerlerini taşıyor (`12/7`), `gecikme_ms` gerçek (SSE ilk olay 0.266 sn,
`gecikme_ms=827` upstream gecikmesini de kapsıyor).

- Sonuç: GEÇTİ

---

### 2) Maskeleme — DB ve upstream (çürütme hedefi 2)

Girdi mesajı: `Merhaba, bana ayse@acme.com adresinden ulasin; telefonum 0532 123 45 67 ve TCKN 12345678901. ...`

- Beklenen: DB'ye maskeli yazılır; upstream'e ham veri sızmaz.
- Gerçek çıktı:

```
=== SQLite: mesaj satirlari (ham)
(1, 1, 'kullanici', 'Merhaba, bana [MASKELENDI:eposta] adresinden ulasin; telefonum [MASKELENDI:telefon] ve TCKN [MASKELENDI:tckn]. ...', 12)
(2, 1, 'asistan', 'YANIT: Merhaba, bana [MASKELENDI:eposta] ... | iletisim: [MASKELENDI:eposta] | tel: [MASKELENDI:telefon]', 7)
baslik: [(1, 'Merhaba, bana [MASKELENDI:eposta] adresinden ulasin; telefon…', 61)]

=== Sahte upstream'e GIDEN istek govdesi (ham JSONL satiri)
{"olay": "istek", ..., "govde": {"model": "sahte-akis", "messages": [
  {"role": "kullanici", "content": "Merhaba, bana [MASKELENDI:eposta] adresinden ulasin; telefonum [MASKELENDI:telefon] ve TCKN [MASKELENDI:tckn]. ..."}],
  "stream": true, "temperature": 0.7, "max_tokens": 2048, "stream_options": {"include_usage": true}}}
```

E-posta, telefon ve TCKN hem veritabanında hem **upstream'e giden gövdede**
maskeli. Ham verinin hiçbir katmana sızmadığı bağımsız olarak doğrulandı:

```
grep -c "12345678901\|ayse@acme.com\|0532 123 45 67" kaynak/testler/gecici/sahte_upstream_istekler.jsonl
0
./.venv/Scripts/python.exe -c "... mesaj icerik / konusma.sistem_istemi LIKE ..."
12345678901 -> mesaj: 0 konusma.sistem_istemi: 0
ayse@acme.com -> mesaj: 0 konusma.sistem_istemi: 0
0532 123 45 67 -> mesaj: 0 konusma.sistem_istemi: 0
veli@ornek.com -> mesaj: 0 konusma.sistem_istemi: 1
```

Konuşma geçmişi ikinci turda upstream'e yine maskeli gidiyor
(`gozlem_sohbet_hata.py` 2.3 çıktısı: `asistan` mesajı içinde
`[MASKELENDI:eposta]`).

**Yanıt metninde maskeleme değerlendirmesi:** Ham upstream yanıtı olduğu gibi
döndürülüyor (hem `POST /sohbet` gövdesinde hem SSE `parca` olaylarında
`| iletisim: ayse@acme.com | tel: 0532 123 45 67` görünüyor) ama aynı içeriğin
veritabanına yazılan kopyası maskeli. Yani istemcinin gördüğü metin ile denetim
kaydı **tutarsız** (bkz. Bulgu 5). Kullanıcının ham verisi upstream'e
gitmediğinden bu bir sızıntı değildir; ancak sözleşme yanıt gövdesi için
maskeleme öngörmüyor — davranış açıkça belgelenmeli ya da yanıt da maskelenmeli.

- Sonuç: DB/upstream maskelemesi GEÇTİ; yanıt maskelemesi MINOR bulgu.

### 2b) `sistem_istemi` alanı (aynı hedefin ek kanıtı)

```
=== 6.2) Upstream'e giden son govde
{"model": "sahte-akis", "messages": [
  {"role": "system", "content": "Kullanicinin e-postasi veli@ornek.com, telefonu 0532 999 88 77"},
  {"role": "kullanici", "content": "Sistem istemi denemesi"}], ...}

=== 6.3) DB'de konusma.sistem_istemi (ham)
[(14, 'Kullanicinin e-postasi veli@ornek.com, telefonu 0532 999 88 77')]
```

- Beklenen: KVKK kuralı gereği kayıt anında maskeleme (spec §11).
- Sonuç: **KALDI** (Bulgu 2).

---

### 3) Konuşma başlığı (çürütme hedefi 3)

```
./.venv/Scripts/python.exe - <<'PY' ... (SQLite üzerinden doğrulama)
baslik      : 'Merhaba, bana [MASKELENDI:eposta] adresinden ulasin; telefon…'
uzunluk     : 61
ilk 60 karakter esit mi: True
son karakter: '…'
```

- Beklenen: başlık ilk mesajdan, 60 karakterde kırpılır.
- Gerçek: ilk **kullanıcı** mesajının maskelenmiş içeriğinin ilk 60 karakteri +
  `…` (toplam 61). Kısa mesajda kırpma yok: `[(15, 'Kisa', 4)]`.
  İkinci mesaj başlığı değiştirmiyor (`konusma 2` başlığı `Tek yanit denemesi:
  [MASKELENDI:eposta]` olarak kaldı).
- Sonuç: GEÇTİ

---

### 4) Kota aşımı (çürütme hedefi 4)

```
./.venv/Scripts/python.exe kaynak/testler/betikler/gozlem_sohbet_kota.py
```

- Beklenen: limit aşılınca 429 `kota_asildi` + `ayrinti.sifirlanma` gelecekte ISO;
  reddedilen istek konuşma/mesaj yaratmamalı.
- Gerçek çıktı:

```
=== 3.2) Kullanici A icin gunluk limit 2 (DB'ye dogrudan satir)
[(1, 'kullanici', 2, 2, None, 0, 0, '2026-09-13 00:00:00.000000', '2026-10-01 00:00:00.000000')]

-- istek 1: HTTP 200 | konusma 7->8 | mesaj 11->13
-- istek 2: HTTP 200 | konusma 8->9 | mesaj 13->15
-- istek 3: HTTP 429 | konusma 9->9 | mesaj 15->15
{"hata": {"kod": "kota_asildi", "mesaj": "Günlük istek kotanız doldu.",
          "ayrinti": {"kapsam": "kullanici", "sifirlanma": "2026-09-13T00:00:00Z", "bdm_id": 1}}}
-- istek 4: HTTP 429 | konusma 9->9 | mesaj 15->15

=== 3.3) 429 ayrintisindaki sifirlanma gelecekte mi?
simdi     : 2026-09-12T19:41:36.802309+00:00
sifirlanma: 2026-09-13T00:00:00+00:00
gelecekte mi: True

=== 3.4) Kota asimi akis ucunda
429 application/json {"hata":{"kod":"kota_asildi",...}}

=== 3.5) Kota satiri (sonrasi)
[(1, 'kullanici', 2, 2, None, 2, 38, '2026-09-13 00:00:00.000000', '2026-10-01 00:00:00.000000')]

=== 3.6) API anahtari kapsami: gunluk_istek_siniri=1
-- anahtar istegi 1: 200 {... "konusma_id": 10 ...}
-- anahtar istegi 2: 429 {"hata":{"kod":"kota_asildi","ayrinti":{"kapsam":"api_anahtari",...}}}
```

Reddedilen istek sayacı artırmıyor (`kullanilan_gunluk` 2'de kaldı), konuşma ve
mesaj **yaratmıyor** (9→9, 15→15) → veri kirliliği yok. `kota_asildi` kaydı
`konusma_id` NULL olarak düşüyor. Anahtar kapsamı da doğru çalışıyor.
`POST /sohbet/akis` de kota aşımında SSE yerine JSON 429 döndürüyor (sözleşmeye uygun).

- Sonuç: GEÇTİ

---

### 5) Kullanım kaydı durumları ve `/kullanim/ozet` (çürütme hedefi 5)

```
=== 3.7) GET /kullanim/ozet (personel)
200 {"toplam_istek": 16, "toplam_token": 114, "basarili": 6, "hatali": 5,
     "kota_asimi": 5, "ortalama_gecikme_ms": 314}

=== 3.8) Bagimsiz SQL ile karsilastirma (son 30 gun)
durum bazinda: [('basarili', 6, 72, 42), ('hata', 5, 0, 0), ('kota_asildi', 5, 0, 0)]
SQL toplam_istek: 16 | SQL toplam_token: 114
SQL ortalama_gecikme_ms: 314 (sum=2829, adet=9)
API ozet          : {'toplam_istek': 16, 'toplam_token': 114, 'basarili': 6,
                     'hatali': 5, 'kota_asimi': 5, 'ortalama_gecikme_ms': 314}
tum zamanlar durum bazinda: [('basarili', 6), ('hata', 5), ('kota_asildi', 5)]
```

Ayrıca (2.12) hata yollarında `durum='hata'` (girdi/çıktı token 0), başarılıda
`durum='basarili'`, kota reddinde `durum='kota_asildi'` yazıldığı SQL ile
doğrulandı. `/kullanim/ozet` sayıları bağımsız SQL ile **birebir** tutuyor.

- Sonuç: GEÇTİ

---

### 6) Upstream 500 → 502 + akışta `hata` olayı (çürütme hedefi 6)

```
./.venv/Scripts/python.exe kaynak/testler/betikler/gozlem_sohbet_hata.py
```

```
=== 2.8) POST /sohbet — upstream 500
502 {"hata": {"kod": "ust_saglayici_hatasi",
     "mesaj": "Model sağlayıcısı isteği yanıtlayamadı.",
     "ayrinti": {"durum": 500, "govde": "{\"error\":{\"message\":\"sahte saglayici hatasi\",\"type\":\"sahte\"}}"}}}

=== 2.9) POST /sohbet/akis — upstream 500
200 text/event-stream; charset=utf-8
   event: baslangic
   data: {"konusma_id": 7, "mesaj_id": 11}
   event: hata
   data: {"hata": {"kod": "ust_saglayici_hatasi", ..., "ayrinti": {"durum": 500, "govde": "{...}"}}}
```

HTTP 502 + `ust_saglayici_hatasi` doğru; akışta `hata` olayı hata zarfını
taşıyor. Ancak hata zarfı upstream gövdesini istemciye sızdırıyor (Bulgu 3) ve
`hata` sonrası `bitti` olayı gönderilmiyor (Bulgu 4).

Akış ortasında kopan upstream (`model=kir`) da doğru ele alınıyor:

```
   event: parca / {"icerik": "ilk "} ...
   event: hata
   data: {"hata": {"kod": "ust_saglayici_hatasi", "mesaj": "Model sağlayıcısına bağlanılamadı.",
          "ayrinti": {"durum": 0, "govde": "RemoteProtocolError: peer closed connection ..."}}}
kirilan akis mesajlari: [(27, 'kullanici', 'Kopacak')]      <- kismi yanit YAZILMADI
kirilan akis kullanim kaydi: [(21, 'hata', 0, 0, 882)]
```

- Sonuç: hata kodu ve akış davranışı GEÇTİ; zarf ayrıntısı KALDI (Bulgu 3/4).

---

### 7) Sahiplik (çürütme hedefi 7)

```
./.venv/Scripts/python.exe kaynak/testler/betikler/gozlem_sohbet_sahiplik.py
```

```
=== 4.2) B kullanicisi A'nin konusmasina erismeye calisir
GET    -> 404 {"hata":{"kod":"bulunamadi","mesaj":"Konuşma bulunamadı.","ayrinti":{"konusma_id":11}}}
PATCH  -> 404 ...
DELETE -> 404 ...
POST /sohbet (konusma_id) -> 404 ...
=== 4.3) B'nin konusma listesi -> {"toplam": 0, "kayitlar": []}
=== 4.4) A'nin konusmasi hala duruyor mu? -> GET (A) 200, DB baslik: [(11, "A'nin ozel konusmasi")]

=== 4.5) K1 anahtari ... K2 ve panel yoneticisi
K1 GET  -> 200
K2 GET  -> 404 | K2 PATCH -> 404 | K2 DEL -> 404
A JWT   -> 404 | A JWT (yeni mesaj) -> 404
K2 listesi: {"toplam": 0, "kayitlar": []}
```

Var olmayan ve başkasına ait konuşma aynı 404'ü veriyor (varlık sızıntısı yok),
403 yerine 404 tercih edilmiş — bilgi sızdırmadığı için doğru. B'nin listesi boş.

- Sonuç: GEÇTİ

---

### 8) Hazır olmayan BDM (çürütme hedefi 8)

```
=== 2.10) POST /sohbet — hazir olmayan (taslak) BDM
503 {"hata": {"kod": "bdm_hazir_degil", "mesaj": "Seçilen model şu anda kullanıma hazır değil.",
     "ayrinti": {"bdm_id": 3, "durum": "taslak"}}}
akis: 503 {"hata":{"kod":"bdm_hazir_degil",...}}
```

Konuşma sayısı 7'de kaldı → reddedilen istek kayıt yaratmıyor.

- Sonuç: GEÇTİ

---

### 9) İstemci akışı yarıda keserse (çürütme hedefi 9)

```
./.venv/Scripts/python.exe kaynak/testler/betikler/gozlem_sohbet_iptal.py
```

```
  0.20s | event: baslangic
  0.20s | data: {"konusma_id": 13, "mesaj_id": 22}
  0.72s | event: parca
  0.72s | data: {"icerik": "parca0 "}
--- baglanti kapatiliyor ---
... 4 sn bekleniyor ...

=== 5.3) Veritabani durumu (bagimsiz SQL)
mesajlar: [(22, 'kullanici', 'Yarida kesecegim')]
kullanim_kaydi: []

=== 5.4) Sahte upstream kaydi: iptal edildi mi?
{"olay": "akis_iptal_edildi", "model": "yavas", "zaman": 1789242133.4736}
```

- Beklenen: upstream isteği iptal edilir, yarım yanıt DB'ye yazılmaz.
- Gerçek: upstream tarafında akış iptal edildi, kısmi asistan mesajı **yazılmadı**,
  kullanım kaydı oluşmadı; yalnızca kullanıcı mesajı kaldı.
- Sonuç: GEÇTİ

---

### 10) PATCH başlık ve DELETE (çürütme hedefi 10)

```
=== 4.6) PATCH -> 200 {"id":11,"baslik":"Yeni Baslik"} | DB baslik: [('Yeni Baslik',)]
=== 4.7) DELETE -> 204 '' | mesaj sayisi: 2 -> 0 | konusma satiri: 0
         GET (silindikten sonra) -> 404
=== 4.8) oksuz mesaj: 0
         kullanim_kaydi'nda silinmis konusmaya bagli kayit: 1
```

PATCH ve DELETE çalışıyor, mesajlar ORM cascade ile siliniyor (öksüz mesaj yok).
Buna karşılık `kullanim_kaydi.konusma_id` silinen konuşmaya işaret etmeye devam
ediyor (Bulgu 6).

- Sonuç: GEÇTİ (MINOR bulgu ile)

---

### 11) `/kullanim/zaman-serisi` ve yetki denetimleri

```
./.venv/Scripts/python.exe kaynak/testler/betikler/gozlem_sohbet_kullanim.py
```

```
=== 7.1) kirilim=bdm
200 {"seri": [{"etiket": "Sahte Akis Modeli", "istek": 15, "token": 190},
              {"etiket": "Kati Saglayici", "istek": 5, "token": 0},
              {"etiket": "Kiran Model", "istek": 1, "token": 0}]}
=== 7.2) kirilim=kullanici
200 {"seri": [{"etiket": "a@acme.com", "istek": 15, "token": 114},
              {"etiket": "bilinmeyen", "istek": 3, "token": 38},
              {"etiket": "b@acme.com", "istek": 3, "token": 38}]}
=== 7.3) kirilim=xyz -> 400 {"hata":{"kod":"gecersiz_istek",...}}
=== 7.4) gun=0 -> 400 dogrulama_hatasi, gun=400 -> 400 dogrulama_hatasi
=== 7.5) jeton yok -> POST /sohbet 401 kimlik_gerekli; /sohbet/konusmalar 401; /kullanim/ozet 401
=== 7.6) son kullanici /kullanim/ozet -> 403 yetki_yok
=== 7.7) bos mesaj -> 400 dogrulama_hatasi; bdm yok -> 400 gecersiz_istek;
         bilinmeyen slug -> 404 bulunamadi
=== 7.8) SQL: [('Sahte Akis Modeli', 15, 190), ('Kiran Model', 1, 0), ('Kati Saglayici', 5, 0)]
```

Zaman serisi SQL ile birebir; anahtarla yapılan istekler `kullanici` kırılımında
`bilinmeyen` etiketiyle görünüyor (anahtarda `kullanici_id` yok — beklenen).

- Sonuç: GEÇTİ

---

### 12) Upstream'e giden rollerin ham kanıtı

```
grep -c "gecersiz_roller" kaynak/testler/gecici/sahte_upstream_istekler.jsonl
16
grep "gecersiz_roller" ... | head -4
{"olay": "gecersiz_roller", "roller": ["kullanici"], "model": "sahte-akis"}
{"olay": "gecersiz_roller", "roller": ["kullanici", "asistan", "kullanici"], "model": "sahte-akis"}
{"olay": "gecersiz_roller", "roller": ["kullanici"], "model": "kati"}
{"olay": "gecersiz_roller", "roller": ["kullanici"], "model": "kati"}
```

---

## Bulgular

- **[BLOCKER]** `bdm_konusma_gecmisi/yazici.py:137` — Upstream'e gönderilen
  `messages[].role` değerleri Türkçe enum değerleri (`kullanici`, `asistan`).
  OpenAI uyumlu sözleşmede bu alan `system|user|assistant|tool` olmalıdır
  (aynı depodaki `bdm_hazırlama_ucu/dogrulama.py:190` ping isteği `"role": "user"`
  kullanıyor; `sohbet.py:200` sistem mesajı için `"system"` kullanıyor — yani
  sözleşme niyeti İngilizce roller).
  - Kanıt: 16 istekte `roller: ["kullanici"]` / `["kullanici","asistan","kullanici"]`;
    katı rol doğrulaması yapan OpenAI uyumlu sunucuda istek 400 dönüyor ve
    sohbet 502'ye düşüyor (2.6 çıktısı: `Invalid value for 'messages[0].role'`).
  - Etki: gerçek sağlayıcılarda (OpenAI/Azure/vLLM rol enum'unu doğrular)
    **ilk mesajdan itibaren her sohbet isteği başarısız olur**; yalnızca rolü
    doğrulamayan hoşgörülü sunucularda çalışıyor. OpenAI resmî hata metni:
    `messages.n.role: '...' must be one of 'system', 'user', 'assistant', 'tool'`
    + HTTP 400 (help.openai.com makalesi "Valid Roles").
  - Yeniden üretme: `sahte_upstream_sohbet.py` ile `upstream_model=kati` BDM'e
    `POST /sohbet` → 502; JSONL'de `gecersiz_roller`.
  - Not: `arkauc/testler/test_sohbet.py:108` ve `arkauc/testler/test_depo.py:189`
    bu hatalı değerleri **sabitliyor**, bu yüzden uygulayıcı test paketi yeşil
    kalıyor.

- **[MAJOR]** `arkauc/app/api/sohbet.py:113` ve `:198-200` — İstekte gelen
  `sistem_istemi` maskelenmeden (a) `konusma.sistem_istemi` kolonuna yazılıyor,
  (b) upstream'e `system` mesajı olarak gidiyor.
  - Kanıt: `6.2`/`6.3`: `veli@ornek.com` ve `0532 999 88 77` ham hâlde hem
    upstream gövdesinde hem veritabanında.
  - Beklenen: spec §11 "Maskeleme kayıt anında uygulanır"; `kaynak/GUVENLIK.md`
    "ham kişisel veri veritabanına yazılmaz". `mesaj_ekle` yolu maskeliyor,
    `sistem_istemi` yolu maskelenmiyor — tutarsız.
  - Yeniden üretme: `gozlem_sohbet_ek.py` 6.1–6.3.

- **[MAJOR]** `arkauc/app/servisler/upstream.py:98-106` — Hata zarfının `ayrinti`
  alanı upstream yanıt gövdesini (`govde`) ve taşıma istisnası metnini istemciye
  döndürüyor; SSE `hata` olayında da aynen akıyor.
  - Kanıt: `2.8` (`"govde": "{\"error\":{\"message\":\"sahte saglayici hatasi\"...}"`),
    `6.5` (`"govde": "RemoteProtocolError: peer closed connection ..."`).
  - Beklenen: spec §6 — "Sunucu tarafı ayrıntı (traceback, upstream gövdesi)
    yalnızca log + `islem_kaydi`'na yazılır." İstemci yalnız `kod`/`mesaj`/gerekli
    alanları görmeliydi.
  - Etki: sağlayıcı iç hata metinleri, model adları, uç nokta ayrıntıları son
    kullanıcıya sızıyor; sağlayıcı hata gövdesi istek metnini yansıtırsa
    (bazı sağlayıcılar yansıtır) istemci verisi de sızabilir.
  - Yeniden üretme: `gozlem_sohbet_hata.py` 2.8/2.9, `gozlem_sohbet_ek.py` 6.5.

- **[MINOR]** `arkauc/app/servisler/akış.py:81-102` — Akış `hata` olayından sonra
  `bitti` olayı gönderilmiyor; akış doğrudan kapanıyor. Modül başlığı ve
  `sohbet_akis` docstring'i olay dizisini `baslangic → parca* → kullanim → hata? → bitti`
  olarak bildiriyor. İstemci `bitti`yi bekliyorsa (sözleşmeye göre bekler)
  bağlantı kapanana kadar bekler. Yeniden üretme: 2.7/2.9/6.5 çıktıları —
  `hata` sonrası satır yok.

- **[MINOR]** `arkauc/app/api/sohbet.py:238` / `arkauc/app/servisler/akış.py:110` —
  Yanıt metni (`POST /sohbet` gövdesindeki `icerik`, SSE `parca` olayları)
  maskelenmiyor; aynı içeriğin veritabanına yazılan kopyası maskeleniyor.
  Kayıt ile istemcinin gördüğü içerik ayrışıyor, denetim/dışa aktarım ile canlı
  yanıt tutarsız. Sızıntı değil (kullanıcı ham verisi upstream'e gitmiyor) ama
  sözleşmede yanıt maskelemesi tanımlı olmadığı için davranışın belgelenmesi ya
  da yanıtın da maskelenmesi gerekir. Yeniden üretme: 2. bölüm çıktısı —
  `parca` içinde `ayse@acme.com`, DB'de `[MASKELENDI:eposta]`.

- **[MINOR]** `kaynak/testler/gecici/sohbet-gozlem.db` gözlemi — Konuşma
  silindiğinde `kullanim_kaydi.konusma_id` öksüz kalıyor (silinen id'ye işaret
  eden 1 satır). Şema `ondelete="SET NULL"` diyor ancak SQLite bağlantısında
  `PRAGMA foreign_keys` açılmadığı için kısıt uygulanmıyor (ORM cascade'i
  sayesinde `mesaj` satırlarında öksüz kalmıyor: `oksuz mesaj: 0`). Yeniden
  üretme: `gozlem_sohbet_sahiplik.py` 4.7/4.8.

- **[MINOR - bilgi]** Hata yollarında konuşma ve kullanıcı mesajı veritabanında
  kalıyor (502 örneklerinde konuşma 3,4,5,6,7 ve 5 `hata` kaydı). Sözleşme bunu
  yasaklamıyor; denetim izi açısından makul. **Kota reddinde ve hazır olmayan
  BDM'de ise hiçbir kayıt oluşmuyor** (istenen davranış).

## Özet

7 bulgu (1 BLOCKER, 2 MAJOR, 4 MINOR).

BLOCKER: Sohbet isteklerinde upstream'e gönderilen mesaj rolleri Türkçe enum
değerleriyle (`kullanici`/`asistan`) yazıldığı için OpenAI uyumlu gerçek
sağlayıcılar isteği 400 ile reddediyor ve sohbet 502'ye düşüyor.
