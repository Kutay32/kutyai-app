# kimlik gözlem logu — 2026-09-12

Bağımsız gözlemci: `GozKimlik` (Dalga 1 doğrulama). Ürün kodu **değiştirilmedi**; yalnızca
`kaynak/testler/` altına betik ve log yazıldı.

## Kapsam

- `kaynak/API.md` §1 (hata zarfı), §2 (`Kullanici`/`Sayfa<T>`), §5 (Kimlik), §6 (Kullanıcı yönetimi)
- `kaynak/spec/2026-09-12-kutyai-bdm-platformu-tasarim.md` §4.1 `kullanici`, §4.2 `oturum`,
  §4.3 `dogrulama_jetonu`, §4.10 `islem_kaydi`, §6 hata zarfı, §7.1/§7.2, §9 bağımlılık kuralları,
  §11 güvenlik
- İncelenen dosyalar: `arkauc/app/api/kimlik.py`, `arkauc/app/api/kullanicilar.py`,
  `arkauc/app/servisler/kimlik.py`, `arkauc/app/servisler/posta.py`,
  `arkauc/app/cekirdek/hatalar.py`, `arkauc/app/cekirdek/bagimliliklar.py`,
  `arkauc/app/cekirdek/guvenlik.py`

### Ortam / yeniden üretilebilirlik notu

Betikler `kaynak/testler/betikler/` altındadır. Bu klasörü başka gözlemci ajanlar da kullandığı
için `ortak.py` adı çakıştı (`GozYonetim` kendi `ortak.py`'sini yazdı); bu yüzden bu logdaki tüm
betikler **`gkimlik_`** önekiyle yeniden adlandırıldı ve ortak yardımcı `gkimlik_ortak.py` oldu.
Aşağıdaki komutlar bu hâliyle birebir çalıştırılmıştır.

Sunucu (canlı, port 8101, geçici SQLite):

```
hub start name=gozkimlik-api application=./.venv/Scripts/python.exe
         args=["-m","uvicorn","arkauc.app.main:app","--port","8101"]
         env={KUTYAI_VERITABANI_URL=sqlite+aiosqlite:///E:/kutyai-app/kaynak/testler/gecici/kimlik-gozlem.db,
              KUTYAI_GIZLI_ANAHTAR=gozlem-gizli-anahtar,
              KUTYAI_SIFRELEME_ANAHTARI=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=}
```

```
Started gozkimlik-api: ready pid=10128 uptime=1.0s restarts=0
Ready log matched: Uvicorn running
```

E-posta alanı boş olan yönetici hesabı tohum verisinde yok; bu yüzden "yönetici/operatör/izleyici"
ön koşulları betiklerde **geçici veritabanına** doğrudan `update kullanici set rol=...` ile
kurulmuştur (ürün koduna dokunulmadı).

---

## Koşulan komutlar

### 1) `./.venv/Scripts/python.exe kaynak/testler/betikler/gkimlik_01_jeton_rotasyon.py`

- Beklenen: ilk `yenile` 200 + yeni jeton çifti; **aynı** eski jetonla ikinci `yenile` 401
  (`jeton_gecersiz`); eski kayıt `iptal=1`.
- Gerçek çıktı:

```
### giris
{ "durum": 200, "alanlar": ["erisim_jetonu","kullanici","yenileme_jetonu"],
  "jetonlar": {"erisim":"eyJhbGciOiJI...LxIMLCkI92pc","yenileme":"O5O-ehslk4T4...e7iyDNFZ5dVU"} }
### 1. yenile (eski jeton)
{ "durum": 200, "alanlar": ["erisim_jetonu","yenileme_jetonu"], "yenileme_degisti": true }
### 2. yenile (AYNI eski jeton ile tekrar)
{ "durum": 401,
  "govde": {"hata": {"kod":"jeton_gecersiz","mesaj":"Oturum bilgisi geçersiz. Lütfen tekrar giriş yapın.","ayrinti":{}}} }
### 3. yenile (rotasyondan gelen yeni jeton)
{ "durum": 200, "govde": {"erisim_jetonu":"eyJhbGciOiJIUzI1NiIs...","yenileme_jetonu":"dFd997QuRTCrxKbBswhZLVe0TTc1uXmInF2iJ_0-msIss-1FG0UdppXlXxbvJRoM"} }
### rotasyon oncesi ERISIM jetonu hala gecerli mi
{ "durum": 200, "govde": {"id":1,"eposta":"goz-a696ab91aa@ornek.com","rol":"son_kullanici","durum":"aktif", ...} }
### oturum tablosu (dogrudan SQLite)
[ {"id":1,"kullanici_id":1,"iptal":1,"son_kullanma":"2026-10-12 19:39:06.223233", ...},
  {"id":2,"kullanici_id":1,"iptal":1,"son_kullanma":"2026-10-12 19:39:06.233469", ...},
  {"id":3,"kullanici_id":1,"iptal":0,"son_kullanma":"2026-10-12 19:39:06.245067", ...} ]
```

- Sonuç: **GEÇTİ** (sıralı kullanımda tek kullanımlık). Not: rotasyon sonrası **eski erişim
  jetonu** 15 dakika boyunca geçerli kalıyor (Bulgular MINOR-4).

### 2) `./.venv/Scripts/python.exe kaynak/testler/betikler/gkimlik_01b_eszamanli_yenile.py`

- Beklenen: aynı refresh jetonuyla eşzamanlı çağrılardan **en fazla biri** 200 almalı, diğerleri
  401; tek bir yeni oturum oluşmalı.
- Gerçek çıktı:

```
### hazirlik: goz-es-2c6af380eb@ornek.com girisi tamam, yenileme jetonu = oDeDEr1Tb2nx...GwUCgJ7NQH61
### eszamanli 0: durum=200 govde={'erisim_jetonu': 'eyJhbGciOiJIUzI1NiIs...', 'yenileme_jetonu': 'TuYqLWNuoWl6X94bePFVztSUacHYxHRwrF3SGhiAKmIxcPXfJACJgRXp3R_UZied'}
### eszamanli 1: durum=200 govde={'erisim_jetonu': 'eyJhbGciOiJIUzI1NiIs...', 'yenileme_jetonu': '3IsnBGKs2Ve5QCxMFvBYIFLc7y8rkwbUdhhiwrVEOmKNeaY6lXIMeVE5mh-ITiDx'}
### eszamanli 2: durum=200 govde={'erisim_jetonu': 'eyJhbGciOiJIUzI1NiIs...', 'yenileme_jetonu': 'EhRVz8cecpuJgGvzvnjHmfbDmhhD1w6DE7CxkporLUEbRvLB3GPJl77HvRez4tYY'}
### eszamanli 3: durum=200 govde={'erisim_jetonu': 'eyJhbGciOiJIUzI1NiIs...', 'yenileme_jetonu': '_-t_8fzQFRchg3UfC9FdyFHv8_DvFOUoNZiVl_5kME6td7CNQc0tQq64I-ASbJky'}
### eszamanli 4: durum=200 govde={'erisim_jetonu': 'eyJhbGciOiJIUzI1NiIs...', 'yenileme_jetonu': 'Q6oiw5eIm8C0TxQrOTzzCbYljZkwlZDCasJ7SMuwMHON0tz_d2o9CETg6_lIfQif'}
### oturum tablosu (son 10)
{'id': 4, 'iptal': 1, 'olusturulma': '2026-09-12 19:39:10.325494'}
{'id': 5, 'iptal': 0, 'olusturulma': '2026-09-12 19:39:10.548816'}
{'id': 6, 'iptal': 0, 'olusturulma': '2026-09-12 19:39:10.556365'}
{'id': 7, 'iptal': 0, 'olusturulma': '2026-09-12 19:39:10.562679'}
{'id': 8, 'iptal': 0, 'olusturulma': '2026-09-12 19:39:10.574964'}
{'id': 9, 'iptal': 0, 'olusturulma': '2026-09-12 19:39:10.592265'}
```

- Sonuç: **KALDI** — 5/5 istek 200 döndü ve tek jetonla 5 ayrı geçerli oturum üretildi
  (BLOCKER-1).

### 3) `./.venv/Scripts/python.exe kaynak/testler/betikler/gkimlik_02_kayit_cakisma.py`

- Beklenen: aynı e-posta (büyük/küçük harf ve boşluk farkı dahil) → 409 `cakisma`; 500 yok.
- Gerçek çıktı (kısaltıldı, değiştirilmedi):

```
### 1. kayit (karisik harf)
{ "durum": 201, "govde": {"kullanici": {"id":3,"eposta":"goz-karar-1694ff6c@ornek.com","durum":"beklemede", ...}, "dogrulama_gerekli": true, "gelistirme_baglantisi": "http://localhost:3000/dogrula?jeton=fzSjxFJLN-fLj4iedGAux_1jeia4v4YKahe2qLZquM8"} }
### 2. kayit (BIREBIR ayni e-posta)
{ "durum": 409, "govde": {"hata": {"kod":"cakisma","mesaj":"Bu e-posta adresi zaten kayıtlı.","ayrinti":{}}} }
### 3. kayit (kucuk harfli ayni e-posta)  -> 409 cakisma
### 4. kayit (BUYUK harfli ayni e-posta)  -> 409 cakisma
### 5. kayit (bastan/sondan bosluklu)     -> 409 cakisma
### kullanici tablosunda bu desen
[ {"id":3,"eposta":"goz-karar-1694ff6c@ornek.com","durum":"beklemede"} ]
### 6. kayit (7 karakter parola) -> 400 {"hata":{"kod":"gecersiz_istek","mesaj":"Parola en az 8 karakter olmalıdır.", ...}}
### 7. kayit (bos e-posta)       -> 400 {"hata":{"kod":"gecersiz_istek","mesaj":"E-posta adresi zorunludur.", ...}}
### 8. kayit (eposta alani yok)  -> 400 {"hata":{"kod":"dogrulama_hatasi","ayrinti":{"alanlar":[{"alan":"eposta","mesaj":"Field required"}]}}}
```

- Sonuç: **GEÇTİ** (sıralı senaryolarda). E-posta normalizasyonu (`strip().lower()`) çalışıyor.
  Eşzamanlı tekrar için bkz. komut 13 → **KALDI** (MAJOR-1).

### 4) `./.venv/Scripts/python.exe kaynak/testler/betikler/gkimlik_03_dogrulama_jetonu.py`

- Beklenen: aynı doğrulama jetonu ikinci kez kullanılamaz (400); süresi geçmiş jeton reddedilir.
- Gerçek çıktı:

```
### kayit+dogrula
{ "kayit": 201, "dogrula": {"dogrulandi": true}, "jeton": "tS_dPyOVPJN8...UuNBzOyJbVLg" }
### AYNI dogrulama jetonu ile 2. cagri
{ "durum": 400, "govde": {"hata": {"kod":"gecersiz_istek","mesaj":"Bu bağlantı daha önce kullanılmış.","ayrinti":{}}} }
### uydurma jeton
{ "durum": 400, "govde": {"hata": {"kod":"gecersiz_istek","mesaj":"Bağlantı geçersiz. Lütfen yeni bir bağlantı isteyin.", ...}} }
### DB'de son_kullanma 2020'ye cekildi
[ {"tur":"eposta_dogrulama","kullanildi":0,"son_kullanma":"2020-01-01 00:00:00.000000"} ]
### suresi gecmis jeton ile dogrula
{ "durum": 400, "govde": {"hata": {"kod":"gecersiz_istek","mesaj":"Bağlantının süresi doldu. Lütfen yeni bir bağlantı isteyin.", ...}} }
### dogrulama_jetonu tablosu (bu kullanicilar)
[ {"id":4,"kullanici_id":4,"tur":"eposta_dogrulama","kullanildi":1,"son_kullanma":"2026-09-13 19:39:27.204360"},
  {"id":5,"kullanici_id":5,"tur":"eposta_dogrulama","kullanildi":0,"son_kullanma":"2020-01-01 00:00:00.000000"} ]
### dogrulama sonrasi giris -> 200 ["erisim_jetonu","kullanici","yenileme_jetonu"]
### dogrulanmis hesapla tekrar kayit -> 409 cakisma
```

- Sonuç: **GEÇTİ** (sıralı kullanımda). Eşzamanlı kullanım için komut 13 → **KALDI** (MAJOR-2).

### 5) `./.venv/Scripts/python.exe kaynak/testler/betikler/gkimlik_04_sifre_sifirlama.py`

- Beklenen: sıfırlama sonrası eski refresh jetonları 401, eski parola 401, yeni parola 200;
  sıfırlama jetonu tek kullanımlık.
- Gerçek çıktı:

```
### sifre-sifirlama-iste
{ "durum": 200, "govde": {"mesaj":"E-posta adresiniz kayıtlıysa parola sıfırlama bağlantısı gönderildi.",
  "gelistirme_baglantisi":"http://localhost:3000/sifre-sifirla?jeton=U0xVYw687b6OumsWZv1FAg_aCtfCk_8XeJMBZJPeUoQ"} }
### sifre-sifirla
{ "durum": 200, "govde": {"mesaj":"Parolanız güncellendi. Yeni parolanızla giriş yapabilirsiniz."} }
### sifirlama SONRASI eski refresh jetonu ile /yenile
{ "durum": 401, "govde": {"hata": {"kod":"jeton_gecersiz", ...}} }
### eski parola ile /giris
{ "durum": 401, "govde": {"hata": {"kod":"gecersiz_kimlik_bilgisi","mesaj":"E-posta veya parola hatalı.","ayrinti":{}}} }
### yeni parola ile /giris -> 200 ["erisim_jetonu","kullanici","yenileme_jetonu"]
### AYNI sifirlama jetonu ile 2. sifirla
{ "durum": 400, "govde": {"hata": {"kod":"gecersiz_istek","mesaj":"Bu bağlantı daha önce kullanılmış.", ...}} }
### sifirlama oncesi ERISIM jetonu ile /ben -> 200 {"id":6,"eposta":"goz-4ca880f1d0@ornek.com", ...}
### ikinci sifirlama istegi ... -> 200, yeni gelistirme_baglantisi uretildi
### ilk sifirlama jetonu, ikinci istekten sonra -> 400 "Bu bağlantı daha önce kullanılmış."
### ikinci sifirlama jetonu -> 200 "Parolanız güncellendi..."
### oturum tablosu
[ {"id":11,"iptal":1}, {"id":12,"iptal":1} ]
```

- Sonuç: **GEÇTİ** (sıralı kullanımda; eski refresh jetonları ve eski parola geçersiz).
  Eşzamanlı kullanım için komut 13 → **KALDI** (MAJOR-3).

### 6) `./.venv/Scripts/python.exe kaynak/testler/betikler/gkimlik_05_zamanlama.py`

- Beklenen: bilinmeyen e-posta için de 200 + aynı mesaj; yanıt süresi hesaplar arasında
  ayırt edilebilir fark üretmemeli.
- Gerçek çıktı:

```
### bilinen e-posta
{ "durum": 200, "govde": {"mesaj":"E-posta adresiniz kayıtlıysa parola sıfırlama bağlantısı gönderildi.",
  "gelistirme_baglantisi":"http://localhost:3000/sifre-sifirla?jeton=J7nT2XQrVvj5hzgSrlgL6xuBdynQqHAH0hnw5t-jC84"} }
### bilinmeyen e-posta
{ "durum": 200, "govde": {"mesaj":"E-posta adresiniz kayıtlıysa parola sıfırlama bağlantısı gönderildi."} }
### mesaj ayni mi (bilinmeyende gelistirme_baglantisi yok): True
### sureler
{ "bilinen":   {"n":40,"ortanca_ms":14.82,"ortalama_ms":14.992,"min_ms":13.528,"maks_ms":16.74,"p90_ms":16.169},
  "bilinmeyen":{"n":40,"ortanca_ms":4.643,"ortalama_ms":4.728,"min_ms":3.918,"maks_ms":6.446,"p90_ms":5.805} }
### ortanca fark (bilinen - bilinmeyen) = 10.177 ms; oran = 3.19x
```

- Sonuç: **KALDI** — mesaj aynı, ancak süre dağılımları hiç örtüşmüyor (13.5–16.7 ms vs
  3.9–6.4 ms): hesap numaralandırma için zamanlama sızıntısı (MAJOR-4).

### 7) `./.venv/Scripts/python.exe kaynak/testler/betikler/gkimlik_06_rol_matrisi.py`

- Beklenen: `son_kullanici` → `/kimlik/panel-giris` 403, `/kimlik/giris` 200; personel →
  `/kimlik/giris` 403; anonim → `/kullanicilar` 401; yalnız yönetici `/kullanicilar`.
- Gerçek çıktı:

```
### son_kullanici /kimlik/giris        -> 200 ["erisim_jetonu","kullanici","yenileme_jetonu"]
### son_kullanici /kimlik/panel-giris  -> 403 {"hata":{"kod":"yetki_yok","mesaj":"Panele yalnızca personel hesapları giriş yapabilir.", ...}}
### operator /kimlik/panel-giris       -> 200 ["erisim_jetonu","kullanici","yenileme_jetonu"]
### operator /kimlik/giris             -> 403 {"hata":{"kod":"yetki_yok","mesaj":"Bu giriş kapısı yalnızca son kullanıcılar içindir.", ...}}
### izleyici /kimlik/panel-giris       -> 200
### izleyici /kullanicilar             -> 403 {"hata":{"kod":"yetki_yok", ...}}
### yonetici /kimlik/panel-giris       -> 200
### yonetici /kullanicilar             -> 200 {"toplam":11, "alanlar":["boyut","kayitlar","sayfa","toplam"], "ilk_kayit_alanlari":["ad_soyad","durum","eposta","eposta_dogrulandi","id","olusturulma","rol","son_giris"]}
### anonim /kullanicilar               -> 401 {"hata":{"kod":"kimlik_gerekli", ...}}
### anonim /kimlik/ben                  -> 401 {"hata":{"kod":"kimlik_gerekli", ...}}
### bozuk anahtar ile /kullanicilar    -> 401 {"hata":{"kod":"jeton_gecersiz", ...}}
### son_kullanici /kullanicilar        -> 403 yetki_yok
### son_kullanici POST /kullanicilar   -> 403 yetki_yok
```

- Sonuç: **GEÇTİ**.

### 8) `./.venv/Scripts/python.exe kaynak/testler/betikler/gkimlik_07_parola_taramasi.py`

- Beklenen: hiçbir yanıt gövdesinde parola/özet alanı bulunmamalı.
- Gerçek çıktı:

```
### taranan yanit sayisi: 19
### taranan desenler: 'parola', 'sifre', 'hash', 'argon2' (JSON anahtari), $argon2 (ham)
### parola sizintisi isabeti olan yanit sayisi: 0 / 19

### HAM: POST /kimlik/kayit
201
{"kullanici":{"id":12,"eposta":"goz-tarama-2c1c6c189e@ornek.com","ad_soyad":"Tarama","rol":"son_kullanici","durum":"beklemede","eposta_dogrulandi":false,"olusturulma":"2026-09-12T19:40:40.776594+00:00","son_giris":null},"dogrulama_gerekli":true,"gelistirme_baglantisi":"http://localhost:3000/dogrula?jeton=UR3iFsqYRa6kIzbRBxTdOcn8qlAUeXmG4YRCQ39QepA"}

### HAM: POST /kimlik/dogrula
200
{"dogrulandi":true}

### HAM: POST /kimlik/giris
200
{"erisim_jetonu":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...","yenileme_jetonu":"JQBgDb36KxXqzhMHqxa_w1U6dNJscM3sxxPbG9cUdWP1yXTwWq6-Y0K_WMcdTkx2","kullanici":{"id":12,"eposta":"goz-tarama-2c1c6c189e@ornek.com","ad_soyad":"Tarama","rol":"son_kullanici","durum":"aktif","eposta_dogrulandi":true,"olusturulma":"2026-09-12T19:40:40.776594","son_giris":"2026-09-12T19:40:40.853518+00:00"}}

### HAM: POST /kimlik/panel-giris (yanlis kapı)
403
{"hata":{"kod":"yetki_yok","mesaj":"Panele yalnızca personel hesapları giriş yapabilir.","ayrinti":{}}}
```

Taranan 19 yanıt: kayıt, doğrula, giriş, panel-giriş, yenile, çıkış, ben, şifre-sıfırlama-iste,
şifre-sıfırla (×2), yanlış parola girişi, olmayan e-posta girişi, kısa parola kaydı,
`GET/POST/PATCH/DELETE /kullanicilar` ve 404 gövdesi.

- Sonuç: **GEÇTİ** — `parola`/`sifre_hash`/`hash`/`argon2`/`$argon2` hiçbir yanıtta yok,
  düz metin parola sızıntısı yok.

### 9) `./.venv/Scripts/python.exe kaynak/testler/betikler/gkimlik_08_patch_denetim.py`

- Beklenen: kendini `pasif` yapma reddedilmeli (DELETE'teki gibi); rol yükseltmesi
  `islem_kaydi` tablosuna yazılmalı.
- Gerçek çıktı (kısaltıldı):

```
### yonetici Y1 id=15 eposta=goz-yon-denetim-4dfc3bb259@ornek.com
### POST /kullanicilar -> 201 id=16 rol=son_kullanici durum=aktif eposta_dogrulandi=true
### PATCH hedef rol=operator -> 200 {"id":16,"rol":"operator","ad_soyad":"Hedef Yeni", ...}
### islem_kaydi (kullanici.guncelle, hedef)
[ {"id":100,"kullanici_id":15,"eylem":"kullanici.guncelle","hedef_tur":"kullanici","hedef_id":"16",
   "ayrinti":"{\"rol\": \"operator\", \"ad_soyad\": \"Hedef Yeni\"}","ip":"127.0.0.1"} ]
### kullanici.guncelle kayit sayisi once=2 sonra=3
### PATCH hedef durum=pasif -> 200
### PATCH KENDINI durum=pasif
{ "durum": 200, "govde": {"id":15,"eposta":"goz-yon-denetim-4dfc3bb259@ornek.com","rol":"yonetici","durum":"pasif", ...} }
### Y1 DB satiri
[ {"id":15,"rol":"yonetici","durum":"pasif"} ]
### pasif sonrasi Y1 jetonu ile /kullanicilar -> 403 {"hata":{"kod":"yetki_yok","mesaj":"Hesabınız devre dışı bırakılmış.", ...}}
### pasif sonrasi Y1 ile panel-giris     -> 403 {"hata":{"kod":"yetki_yok","mesaj":"Hesabınız devre dışı bırakılmış. Yöneticiye başvurun.", ...}}
### Y1 izleri (ozet)
  kimlik.kayit / kimlik.dogrula / kimlik.giris {"panel":true} / kullanici.olustur {"rol":"son_kullanici"}
  kullanici.guncelle {"rol":"operator","ad_soyad":"Hedef Yeni"} / kullanici.guncelle {"durum":"pasif"} hedef=16
  kullanici.guncelle {"durum":"pasif"} hedef=15
### PATCH KENDI ROLUNU izleyici yap -> 200 {"id":17,"rol":"izleyici","durum":"aktif", ...}
### DELETE KENDINI -> 409 {"hata":{"kod":"cakisma","mesaj":"Kendi hesabınızı pasifleştiremezsiniz.","ayrinti":{}}}
### PATCH olmayan id -> 404 {"hata":{"kod":"bulunamadi","mesaj":"Kullanıcı bulunamadı.","ayrinti":{}}}
### PATCH gecersiz durum degeri -> 400 dogrulama_hatasi {"alan":"durum","mesaj":"Input should be 'aktif', 'beklemede' or 'pasif'"}
```

- Sonuç: **KALDI** — denetim izi ve rol yükseltme kaydı doğru (GEÇTİ), ancak
  `PATCH` ile **kendini pasif yapmak 200 ile kabul ediliyor** ve **kendi rolünü düşürmek**
  serbest (MAJOR-5); `DELETE` aynı işlemi 409 ile reddediyor → tutarsız koruma.

### 10) `./.venv/Scripts/python.exe kaynak/testler/betikler/gkimlik_09_hata_kodlari.py`

- Beklenen: üretilen her `kod`, API.md §1 tablosunda bulunmalı.
- Gerçek çıktı:

```
### API.md §1 tablosu
  400: ['dogrulama_hatasi', 'gecersiz_istek']
  401: ['anahtar_gecersiz', 'jeton_gecersiz', 'jeton_suresi_doldu', 'kimlik_gerekli']
  403: ['eposta_dogrulanmadi', 'yetki_yok']
  404: ['bulunamadi']
  409: ['cakisma', 'gecersiz_gecis', 'kurulum_zaten_tamam']
  429: ['kota_asildi', 'oran_siniri']
  500: ['sunucu_hatasi']
  502: ['ust_saglayici_hatasi']
  503: ['bdm_hazir_degil', 'surucu_yok', 'veritabani_yok']
### senaryo sonuclari  (ozet)
  400 gecersiz_istek        -> tabloda: true   "Bağlantı geçersiz. Lütfen yeni bir bağlantı isteyin."
  400 gecersiz_istek        -> tabloda: true   "Parola en az 8 karakter olmalıdır."
  400 dogrulama_hatasi      -> tabloda: true
  401 kimlik_gerekli        -> tabloda: true
  401 jeton_gecersiz        -> tabloda: true
  401 gecersiz_kimlik_bilgisi -> tabloda: FALSE "E-posta veya parola hatalı."   (yanlis parola)
  401 gecersiz_kimlik_bilgisi -> tabloda: FALSE "E-posta veya parola hatalı."   (olmayan e-posta)
  403 eposta_dogrulanmadi   -> tabloda: true
  403 yetki_yok             -> tabloda: true   (yetkisiz jeton ile PATCH -> 403, varlik sizmiyor)
  405 yontem_izinli_degil   -> tabloda: FALSE
### 409 cakisma -> tabloda: true  "Bu e-posta adresi zaten kayıtlı."
### tabloda OLMAYAN kodlar
  HTTP 401 kod=gecersiz_kimlik_bilgisi (yanlis parola)  
  HTTP 401 kod=gecersiz_kimlik_bilgisi (olmayan e-posta)
  HTTP 405 kod=yontem_izinli_degil
```

- Sonuç: **KALDI** — `gecersiz_kimlik_bilgisi` API.md §1 tablosunda yok (MAJOR-6a),
  `yontem_izinli_degil` de yok (MINOR-1).

### 11) `./.venv/Scripts/python.exe kaynak/testler/betikler/gkimlik_10_openapi.py`

- Beklenen: API.md §5/§6'daki her uç OpenAPI'de; yanıt alan adları (`erisim_jetonu`,
  `yenileme_jetonu`, `dogrulama_gerekli`) dokümanda birebir görünür.
- Gerçek çıktı (kısaltıldı):

```
### GET http://127.0.0.1:8101/api/openapi.json -> 200
### /kimlik ve /kullanicilar yollari
  GET    /api/v1/kimlik/ben                  operationId=ben_api_v1_kimlik_ben_get tags=['kimlik', 'kimlik']
  POST   /api/v1/kimlik/cikis                tags=['kimlik', 'kimlik']
  POST   /api/v1/kimlik/dogrula              tags=['kimlik', 'kimlik']
  POST   /api/v1/kimlik/giris                tags=['kimlik', 'kimlik']
  POST   /api/v1/kimlik/kayit                tags=['kimlik', 'kimlik']
  POST   /api/v1/kimlik/panel-giris          tags=['kimlik', 'kimlik']
  POST   /api/v1/kimlik/sifre-sifirla        tags=['kimlik', 'kimlik']
  POST   /api/v1/kimlik/sifre-sifirlama-iste tags=['kimlik', 'kimlik']
  POST   /api/v1/kimlik/yenile               tags=['kimlik', 'kimlik']
  GET    /api/v1/kullanicilar                tags=['kullanicilar', 'kullanicilar']
  POST   /api/v1/kullanicilar                tags=['kullanicilar', 'kullanicilar']
  DELETE /api/v1/kullanicilar/{kullanici_id} tags=['kullanicilar', 'kullanicilar']
  PATCH  /api/v1/kullanicilar/{kullanici_id} tags=['kullanicilar', 'kullanicilar']
### eksik uclar: []
### API.md'de olmayan fazladan uclar: []
### istek semalari
{"KayitIstegi":["eposta","ad_soyad","parola"], "GirisIstegi":["eposta","parola"],
 "YenilemeIstegi":["yenileme_jetonu"], "CikisIstegi":["yenileme_jetonu"], "SifirlamaIstegi":["eposta"],
 "SifreSifirlaIstegi":["jeton","yeni_parola"], "DogrulamaIstegi":["jeton"],
 "KullaniciOlusturIstegi":["eposta","ad_soyad","parola","rol"], "KullaniciGuncelleIstegi":["rol","durum","ad_soyad"]}
### yanit semalari (200/201 responses -> content schema)
  POST /api/v1/kimlik/giris -> 200: {'additionalProperties': True, 'type': 'object', 'title': 'Response Giris ...'}
  POST /api/v1/kimlik/giris -> 422: {'$ref': '#/components/schemas/HTTPValidationError'}
  POST /api/v1/kimlik/yenile -> 200: {'additionalProperties': True, ...}
  POST /api/v1/kimlik/kayit -> 201: {'additionalProperties': True, ...}
  GET  /api/v1/kimlik/ben -> 200: {'additionalProperties': True, ...}
  GET  /api/v1/kullanicilar -> 200: {'type':'object','additionalProperties': True, ...}
  POST /api/v1/kullanicilar -> 201: {'type':'object','additionalProperties': True, ...}
### gercek yanit alan adlari
  /kimlik/giris: ['erisim_jetonu', 'kullanici', 'yenileme_jetonu']
  /kimlik/giris.kullanici: ['ad_soyad','durum','eposta','eposta_dogrulandi','id','olusturulma','rol','son_giris']
  /kimlik/yenile: ['erisim_jetonu', 'yenileme_jetonu']
  birebir 'erisim_jetonu' var mi: True
  birebir 'yenileme_jetonu' var mi: True
  /kimlik/kayit: ['dogrulama_gerekli', 'gelistirme_baglantisi', 'kullanici']
  birebir 'dogrulama_gerekli' var mi: True
```

- Sonuç: **KALDI (kısmi)** — 13/13 uç eksiksiz, gerçek yanıtlarda alan adları birebir doğru;
  ancak OpenAPI'de **yanıt şemaları boş** (`additionalProperties: true`), bu yüzden
  `erisim_jetonu`/`yenileme_jetonu`/`dogrulama_gerekli` dokümanda hiç geçmiyor ve doğrulama
  hatası gerçekte 400 iken doküman 422 ilan ediyor (MINOR-2). `tags` çift yazılmış (MINOR-5).

### 12) `./.venv/Scripts/python.exe kaynak/testler/betikler/gkimlik_11_kenar_durumlar.py`

- Beklenen: jeton türleri karıştırılamaz; çıkış yalnız kendi oturumunu iptal eder; süresi dolmuş
  refresh 401; `kayit_acik=false` kaydı kapatır; gövde fazlalıkları yetki yükseltemez.
- Gerçek çıktı (kısaltıldı):

```
### A1 sifirlama jetonu /kimlik/dogrula'ya verilirse -> 400 "Bağlantı geçersiz. Lütfen yeni bir bağlantı isteyin."
### A2 dogrulama jetonu /kimlik/sifre-sifirla'ya verilirse -> 400 "Bağlantı geçersiz. ..."
### B1 B, A'nin jetonuyla /kimlik/cikis -> 200 {"mesaj":"Çıkış yapıldı."}
### B2 A'nin jetonu hala gecerli mi -> 200 {"erisim_jetonu":"...","yenileme_jetonu":"1ovpDGESEsMYSSvbk_dN1kFnOmFsNh8DVFSc8gzZ8lCk6GFocoEbsdoUvIR9tRDA"}
### B3 A kendi jetonuyla cikis -> 200
### B4 cikis sonrasi A'nin jetonu -> 401 jeton_gecersiz
### C1 suresi dolmus refresh jetonu -> 401 {"hata":{"kod":"jeton_suresi_doldu","mesaj":"Oturum süresi doldu. Lütfen tekrar giriş yapın.", ...}}
### C2 suresi dolmus oturumun ERISIM jetonu -> 200 {"id":26,"eposta":"goz-suresi-8091ac8652@ornek.com", ...}
### D1 kayit_acik=false iken /kimlik/kayit -> 403 {"hata":{"kod":"yetki_yok","mesaj":"Kayıt şu anda kapalı. Yöneticiye başvurun.", ...}}
### E1 /kimlik/kayit ile rol/durum enjeksiyonu -> 201 rol=son_kullanici durum=beklemede
### E2 DB satiri -> [{"rol":"son_kullanici","durum":"beklemede","eposta_dogrulandi":0}]
### F1 BUYUK harfli e-posta ile giris -> 200
### F2 bosluklu e-posta ile giris    -> 200
### G1 pasif kullaniciya sifirlama istegi -> 200 {"mesaj":"E-posta adresiniz kayıtlıysa ..."}   (bağlantı yok)
### G2 pasif kullanici girisi -> 403 yetki_yok
### H1 hedefi pasiflestir -> 200
### H2 pasiflestirilen hedefin refresh jetonu -> 401 jeton_gecersiz
### H3 pasiflestirilen hedefin erisim jetonu -> 403 yetki_yok "Hesabınız devre dışı bırakılmış."
### I1 anonim /kimlik/cikis -> 401 kimlik_gerekli
```

- Sonuç: **KALDI (iki küçük nokta)** — tüm güvenlik kontrolleri geçti, ancak B1'de başkasının
  refresh jetonu ile `/kimlik/cikis` 200 "Çıkış yapıldı." dönerken hiçbir şey iptal edilmiyor
  (MINOR-3) ve C2'de iptal/süresi dolmuş oturumun erişim jetonu hâlâ çalışıyor (MINOR-4).

### 13) `./.venv/Scripts/python.exe kaynak/testler/betikler/gkimlik_12_yaris.py`

- Beklenen: aynı e-posta ile paralel kayıtta **tek** 201, diğerleri 409 `cakisma`; aynı tek
  kullanımlık jetonla paralel çağrılarda **tek** başarı.
- Gerçek çıktı:

```
### A) ayni e-posta ile 5 paralel kayit
  0: 500 {"hata":{"kod":"sunucu_hatasi","mesaj":"Beklenmeyen bir sunucu hatası oluştu.","ayrinti":{}}}
  1: 500 {"hata":{"kod":"sunucu_hatasi", ...}}
  2: 201 {"kullanici":{"id":35,"eposta":"goz-yaris-aa7a23c6b3@ornek.com","rol":"son_kullanici","durum":"beklemede","eposta_dogrulandi":false, ...
  3: 500 {"hata":{"kod":"sunucu_hatasi", ...}}
  4: 500 {"hata":{"kod":"sunucu_hatasi", ...}}
### B) ayni e-posta dogrulama jetonuyla 5 paralel /kimlik/dogrula
  0: 200 {"dogrulandi":true}
  1: 200 {"dogrulandi":true}
  2: 200 {"dogrulandi":true}
  3: 200 {"dogrulandi":true}
  4: 200 {"dogrulandi":true}
### C) ayni sifirlama jetonuyla 5 paralel /kimlik/sifre-sifirla
  0: 200 {"mesaj":"Parolanız güncellendi. Yeni parolanızla giriş yapabilirsiniz."}
  1: 200 {"mesaj":"Parolanız güncellendi. ..."}
  2: 200 {"mesaj":"Parolanız güncellendi. ..."}
  3: 200 {"mesaj":"Parolanız güncellendi. ..."}
  4: 200 {"mesaj":"Parolanız güncellendi. ..."}
### DB: yarış e-postalari
[{'id': 32, 'eposta': 'goz-yaris-33467bdf2f@ornek.com', 'durum': 'beklemede', 'eposta_dogrulandi': 0}, ...]
### DB: dogrulama jetonlari
[{'id': 75, 'tur': 'eposta_dogrulama', 'kullanildi': 0}, {'id': 76, ... 'kullanildi': 1}, ...]
```

Sunucu günlüğü (`hub logs` / grep):

```
Beklenmeyen hata: POST /api/v1/kimlik/kayit
sqlite3.IntegrityError: UNIQUE constraint failed: kullanici.eposta
sqlalchemy.exc.IntegrityError: (sqlite3.IntegrityError) UNIQUE constraint failed: kullanici.eposta
```

- Sonuç: **KALDI** — (A) eşzamanlı tekrar kaydı 409 yerine 500 (MAJOR-1);
  (B) tek kullanımlık doğrulama jetonu 5/5 kabul (MAJOR-2);
  (C) tek kullanımlık sıfırlama jetonu 5/5 kabul, son parola yarışın kazananına göre belirsiz
  (MAJOR-3).

### 14) `./.venv/Scripts/python.exe kaynak/testler/betikler/gkimlik_13_kullanici_listesi.py`

- Beklenen: API.md §6 filtreleri (`rol`, `durum`, `arama`, `sayfa`, `boyut`) ve `Sayfa<T>` alanları;
  `POST /kullanicilar` tekrarı 409.
- Gerçek çıktı (kısaltıldı):

```
### POST /kullanicilar rol=operator -> 201 ; rol=izleyici -> 201
### GET /kullanicilar?rol=operator&arama=filtred21c03 -> 200 {"toplam":1,"sayfa":1,"boyut":25,"roller":["operator"]}
### GET /kullanicilar?durum=aktif&arama=...              -> 200 {"toplam":2,...,"roller":["izleyici","operator"]}
### GET /kullanicilar?arama=...                          -> 200 {"toplam":2,...}
### GET /kullanicilar?sayfa=1&boyut=1&arama=...          -> 200 {"toplam":2,"sayfa":1,"boyut":1,"kayit_sayisi":1}
### GET /kullanicilar?sayfa=0&boyut=0&arama=...          -> 200 {"toplam":2,"sayfa":1,"boyut":25}
### GET /kullanicilar?sayfa=2&boyut=200&arama=...        -> 200 {"toplam":2,"sayfa":2,"boyut":200,"kayit_sayisi":0}
### GET /kullanicilar?boyut=1000&arama=...               -> 200 {"boyut":200}   (üst sınır uygulandı)
### GET /kullanicilar?rol=gecersiz_rol -> 400 dogrulama_hatasi "Input should be 'yonetici', 'operator', 'izleyici' or 'son_kullanici'"
### GET /kullanicilar?sayfa=abc        -> 400 dogrulama_hatasi "Input should be a valid integer, ..."
### Sayfa<T> alan adlari: ['boyut','kayitlar','sayfa','toplam']
### Kullanici alanlari: ['ad_soyad','durum','eposta','eposta_dogrulandi','id','olusturulma','rol','son_giris']
### POST /kullanicilar ayni e-posta ile 5 paralel
  0: 500 sunucu_hatasi
  1: 201 {"id":40,"eposta":"goz-kul-yaris-fbd94549@ornek.com","rol":"izleyici","durum":"aktif","eposta_dogrulandi":true, ...}
  2: 500 sunucu_hatasi
  3: 500 sunucu_hatasi
  4: 500 sunucu_hatasi
```

- Sonuç: **GEÇTİ** (filtre/sayfalama/`Sayfa<T>` alanları API.md §2 ve §6 ile uyumlu);
  ancak eşzamanlı tekrar `POST /kullanicilar` için de 500 üretiyor (MAJOR-1).

### 15) `./.venv/Scripts/python.exe kaynak/testler/betikler/gkimlik_14_bicim.py`

- Beklenen: aynı alan her yanıtta aynı ISO-8601 biçiminde.
- Gerçek çıktı:

```
### /kimlik/panel-giris yanitindaki damgalar: {'olusturulma': '2026-09-12T19:43:03.692821', 'son_giris': '2026-09-12T19:43:03.777777+00:00'}
### POST /kullanicilar (hemen sonra): 2026-09-12T19:43:03.840997+00:00
### GET /kullanicilar (DB'den okuma): 2026-09-12T19:43:03.840997
### GET /kimlik/ben: {'olusturulma': '2026-09-12T19:43:03.692821', 'son_giris': '2026-09-12T19:43:03.777777'}
### /kimlik/giris -> 403 | e-posta dogrulanmamis olabilir        (izleyici rolü: kapı doğru çalışıyor)
### /kimlik/panel-giris (izleyici) -> 200 {'olusturulma': '2026-09-12T19:43:03.840997', 'son_giris': '2026-09-12T19:43:03.961284+00:00'}
### GET /api/docs -> 200
### GET /api/openapi.json -> 200
### GET /api/v1/openapi.json (API.md'de taban adres altinda degil) -> 404
```

- Sonuç: **KALDI (küçük)** — aynı alan yazıldığı anda `+00:00` ile, sonraki okumalarda ofsetsiz
  dönüyor (MINOR-6).

### 16) `./.venv/Scripts/python.exe kaynak/testler/betikler/gkimlik_15_anahtar.py`

- Beklenen: spec §9 — `gecerli_kullanici` yalnız JWT; `kuty_` anahtarı kimlik uçlarında kabul
  edilmemeli.
- Gerçek çıktı:

```
### gecerli kuty_ anahtari olusturuldu: kuty_5y66jr9zf...cb60
### GET /kimlik/ben -> 401 {"hata":{"kod":"jeton_gecersiz","mesaj":"Oturum bilgisi geçersiz. Lütfen tekrar giriş yapın.","ayrinti":{}}}
### GET /kullanicilar -> 401 {"hata":{"kod":"jeton_gecersiz", ...}}
### gecersiz kuty_ -> 401 {"hata":{"kod":"jeton_gecersiz", ...}}
### refresh jetonu Bearer olarak -> 401 {"hata":{"kod":"jeton_gecersiz", ...}}
```

- Sonuç: **GEÇTİ** (spec §9 ile uyumlu). Kod seçimi `anahtar_gecersiz` yerine `jeton_gecersiz`;
  §1 tablosunda ikisi de 401 altında listeli olduğu için ihlal sayılmadı.

### 17) İkincil çapraz kontrol — uygulayıcının kendi testleri

```
$ ./.venv/Scripts/python.exe -m pytest arkauc/testler/test_kimlik.py arkauc/testler/test_yonetim.py -q
..............................s                                          [100%]
Wall time: 21.84 seconds
```

- Sonuç: **GEÇTİ** (31 test, 1 atlandı). Bu bir **kanıt değil**, yalnızca ikincil çapraz
  kontroldür: yeşil olmasına karşın 1/2/13 numaralı komutlardaki yarış koşulları yakalanmıyor —
  testler eşzamanlılık senaryosu içermiyor.

### 18) `./.venv/Scripts/python.exe kaynak/testler/betikler/gkimlik_16_bos_govde.py`

- Beklenen: boş gövdeli `PATCH` hata üretmemeli; değişiklik yoksa denetim kaydı yazılmamalı.
- Gerçek çıktı:

```
### PATCH bos govde
{ "durum": 200, "govde": {"id":45,"eposta":"goz-hedef-bos-62d7356373@ornek.com","ad_soyad":"Bos",
  "rol":"izleyici","durum":"aktif","eposta_dogrulandi":true,"olusturulma":"2026-09-12T19:45:05.809340","son_giris":null},
  "islem_kaydi_once": 7, "islem_kaydi_sonra": 7 }
### PATCH bos govde (tekrar) -> 200 (ayni govde)
### sayfa/sayfa-boyutu tutarliligi -> {"toplam":6,"boyut":1,"kayit":1,"durum":200}
```

- Sonuç: **GEÇTİ** — boş gövde 200 döner, denetim kaydı yazılmaz (`islem_kaydi` 7→7).

---

## Bulgular

### BLOCKER-1 — `arkauc/app/servisler/kimlik.py:251-273` — yenileme jetonu yarışta çok kez kullanılabiliyor

- **Sorun:** `oturumu_yenile` önce kaydı okuyup `kayit.iptal` bayrağını denetliyor, sonra
  `kayit.iptal = True` yazıp yeni oturum açıyor. Okuma–denetim–yazma arasında kilitleme/serializasyon
  yok; istek başına ayrı `AsyncSession` kullanıldığı için eşzamanlı istekler aynı `iptal=False`
  durumunu görüyor. Koşan sunucuda **5/5 paralel istek 200** döndü ve tek jetonla **5 geçerli
  oturum** üretildi (komut 2).
- **Beklenen davranış:** spec §4.2 "Refresh rotasyonu: her yenilemede eski kayıt `iptal=true`,
  yeni kayıt üretilir" ve §11 "Refresh rotasyonu + iptal listesi" → jeton **tek kullanımlık**
  olmalı; aynı jetonla eşzamanlı ikinci çağrı `401 jeton_gecersiz` almalı.
- **Etki (güvenlik):** Çalınan refresh jetonu, meşru istemcinin rotasyonuyla birlikte paralel
  kullanıldığında saldırgan kendi geçerli oturum çiftini alır; rotasyonun amacı olan jeton hırsızlığı
  tespiti devre dışı kalır. Sıralı kullanım doğru engelleniyor, yalnız yarış penceresi açık.
- **Yeniden üretme:** `gkimlik_01b_eszamanli_yenile.py` (aynı jetonla `asyncio.gather` ile 5 ×
  `POST /kimlik/yenile`) → 5 × 200; `oturum` tablosunda 5 satır `iptal=0`.
- Öneri (uygulayıcıya): koşullu `UPDATE oturum SET iptal=1 WHERE jeton_hash=? AND iptal=0`
  + `rowcount==1` denetimi (atomik tüketim) veya `SELECT ... FOR UPDATE`.

### MAJOR-1 — `arkauc/app/api/kimlik.py:156-178` + `arkauc/app/servisler/kimlik.py:171-179` + `arkauc/app/api/kullanicilar.py:61-85` — eşzamanlı tekrar kayıt 409 yerine 500

- **Sorun:** "önce `kullanici_bul`, sonra `INSERT`" deseni yarışta `UNIQUE constraint failed:
  kullanici.eposta` üretiyor; `IntegrityError` yakalanmadığı için `500 sunucu_hatasi` dönüyor.
  Sunucu günlüğü: `Beklenmeyen hata: POST /api/v1/kimlik/kayit` +
  `sqlite3.IntegrityError: UNIQUE constraint failed: kullanici.eposta`.
- **Beklenen:** API.md §1/§6 → e-posta tekrarı `409 cakisma`. Sıralı istekte doğru; eşzamanlı
  istekte 5 denemenin 4'ü 500.
- **Yeniden üretme:** komut 13 — 5 paralel `POST /kimlik/kayit` (aynı e-posta) ve 5 paralel
  `POST /kullanicilar` (aynı e-posta) → 1 × 201, 4 × 500.

### MAJOR-2 — `arkauc/app/api/kimlik.py:204-211` + `arkauc/app/servisler/kimlik.py:334-353` — doğrulama jetonu yarışta çok kez tüketilebiliyor

- **Sorun:** `dogrulama_jetonu_tuket` `kullanildi` alanını yalnız okuyor; `kullanildi = True`
  yazan çağrı (`api/kimlik.py:211`) ile aynı istek içinde commit ediliyor → aynı jetonla paralel
  çağrılar denetimi geçiyor.
- **Beklenen:** spec §4.3 "Tek kullanımlık; kullanıldığında `kullanildi=true`" ve API.md §5
  `POST /kimlik/dogrula`.
- **Yeniden üretme:** komut 13/B — 5 paralel `POST /kimlik/dogrula` aynı jetonla → 5 × 200
  `{"dogrulandi":true}`. (Sıralı ikinci çağrı doğru şekilde 400 dönüyor.)

### MAJOR-3 — `arkauc/app/api/kimlik.py:327-346` — şifre sıfırlama jetonu yarışta çok kez tüketilebiliyor ve sonuç parolası belirsiz

- **Sorun:** MAJOR-2 ile aynı kök neden (`kayit.kullanildi = True` yalnız oku-denetle-yaz ile).
  Ek etki: 5 paralel `POST /kimlik/sifre-sifirla` **5 farklı yeni parolayı** da kabul ediyor;
  hangi parolanın kalıcı olduğu yarışın kazananına bağlı, kullanıcı kendi linkiyle belirlediği
  parolayla giriş yapamayabilir.
- **Beklenen:** tek kullanımlık jeton; ikinci kullanım 400.
- **Yeniden üretme:** komut 13/C → 5 × 200 "Parolanız güncellendi."

### MAJOR-4 — `arkauc/app/api/kimlik.py:291-301` — `sifre-sifirlama-iste` zamanlama sızıntısı

- **Sorun:** kayıtlı e-postada ek iş (jeton üretimi + `INSERT` + `ayar_yaz` + commit) yapılıyor,
  kayıtsızda erken dönülüyor. Ölçüm (40 tekrar, araya girmeli):
  kayıtlı **14.82 ms** ortanca (min 13.53 / maks 16.74), kayıtsız **4.64 ms** (min 3.92 / maks 6.45)
  → **10.18 ms / 3.19×**, dağılımlar hiç örtüşmüyor.
- **Beklenen:** mesaj aynı tutularak hesap numaralandırmanın engellenmesi amaçlanmış; süre farkı
  bu amacı boşa çıkarıyor (uzaktan ölçülebilir).
- **Yeniden üretme:** komut 6.

### MAJOR-5 — `arkauc/app/api/kullanicilar.py:87-120` (koruma yok) vs `:131-132` (koruma var) — kendini pasifleştirme/rol düşürme

- **Sorun:** `PATCH /kullanicilar/{id} {durum:"pasif"}` çağrısı **kendi hesabı için** 200 dönüyor
  (`Y1 DB satiri: [{"id":15,"rol":"yonetici","durum":"pasif"}]`); aynı işlemi yapan `DELETE`
  `409 cakisma "Kendi hesabınızı pasifleştiremezsiniz."` ile reddediliyor. Ayrıca
  `PATCH {rol:"izleyici"}` ile yönetici kendi rolünü düşürebiliyor (200).
- **Beklenen:** iki uç aynı kuralı uygulamalı; son yönetici kendini kilitleyip sistemi
  yönetilemez bırakmamalı (panel kurulumu dışında yönetici üretme yolu yok).
- **Yeniden üretme:** komut 9 — yönetici jetonuyla `PATCH /kullanicilar/{kendi_id} {"durum":"pasif"}`
  → 200; ardından aynı jetonla `GET /kullanicilar` → 403 `yetki_yok`.

### MAJOR-6 — `arkauc/app/servisler/kimlik.py:41-46` + `kaynak/API.md` §1 — `gecersiz_kimlik_bilgisi` tabloda yok

- **Sorun:** yanlış parola ve kayıtsız e-posta için `401 {"kod":"gecersiz_kimlik_bilgisi"}` dönüyor;
  API.md §1 (ve spec §6) tablosunda 401 için yalnız `kimlik_gerekli`, `jeton_gecersiz`,
  `jeton_suresi_doldu`, `anahtar_gecersiz` listeli.
- **Değerlendirme:** İki okuma mümkün — (a) tablo bağlayıcı sayılırsa **ihlal**, (b) tablo
  örnekleyici sayılırsa **sözleşme boşluğu**. API.md kendini "bağlayıcı sözleşme, alan adları
  değişmez" diye tanımlıyor ve `kod` da sözleşmenin parçası olduğundan bu bir **sözleşme
  boşluğu + ihlal**: arayüz ajanları kullanıcıya "e-posta veya parola hatalı" mesajını doğru
  gösterebilmek için tabloda olmayan bir koda özel dal yazmak zorunda. Ya API.md §1 tablosuna
  `gecersiz_kimlik_bilgisi` eklenmeli ya da kod tablodaki bir değere eşlenmeli
  (`kimlik_gerekli` uygun değil; yeni kod eklemek doğru çözüm).
- **Yeniden üretme:** komut 10 — `POST /kimlik/giris` yanlış parola / olmayan e-posta.

### MINOR-1 — `arkauc/app/cekirdek/hatalar.py:_HTTP_KODLARI` — 405 `yontem_izinli_degil` API.md §1'de yok

- `GET /kimlik/giris` → `405 {"kod":"yontem_izinli_degil"}`; tabloda 405 satırı yok. MAJOR-6 ile
  aynı sınıf, kapsamı kimlik modülü dışı. Yeniden üretme: komut 10.

### MINOR-2 — OpenAPI yanıt şemaları boş + doküman 422 ilan ediyor, gerçekte 400

- `GET /api/openapi.json`: `POST /kimlik/giris` 200 yanıtı `{additionalProperties: true}`;
  `erisim_jetonu`/`yenileme_jetonu`/`dogrulama_gerekli` dokümanda geçmiyor → arayüz ajanları
  tip üretemez. Ayrıca doğrulama hatası gerçekte `400 dogrulama_hatasi` iken OpenAPI `422
  HTTPValidationError` ilan ediyor. Uçların tamamı ve istek gövdeleri birebir doğru (komut 11).
- Yeniden üretme: komut 11.

### MINOR-3 — `/kimlik/cikis` başkasının refresh jetonuyla 200 "Çıkış yapıldı." döndürüyor (no-op)

- B kullanıcısı A'nın jetonunu gönderdiğinde `200 {"mesaj":"Çıkış yapıldı."}`, ancak A'nın oturumu
  iptal edilmiyor (`servisler/kimlik.py:276-287` sahiplik denetimi doğru, yanıt metni yanıltıcı).
  Yeniden üretme: komut 12/B1-B2.

### MINOR-4 — İptal edilmiş/süresi dolmuş oturumun **erişim** jetonu 15 dk geçerli kalıyor

- `/kimlik/cikis` sonrası (komut 12/B4'te refresh 401 olurken), parola sıfırlama sonrası
  (komut 5) ve süresi dolmuş refresh oturumunda (komut 12/C2) aynı oturumun erişim jetonu
  `/kimlik/ben` üzerinde 200 dönüyor. spec §9 `gecerli_kullanici` için "süre/**iptal kontrolü**"
  diyor; `jti` üretiliyor ama hiçbir yerde iptal listesi olarak kullanılmıyor
  (`cekirdek/bagimliliklar.py:_jetonla_kullanici` yalnız `durum != pasif` denetliyor).
- Etki: çıkış/parola değişimi sonrası jeton hırsızlığı `erisim_omru_dk` (15 dk) boyunca geçerli.

### MINOR-5 — OpenAPI etiketleri çift (`tags=['kimlik','kimlik']`)

- `main.py` `include_router(..., tags=[etiket])` + router'ın kendi `tags=["kimlik"]` birleşiyor.
  Kozmetik doküman kusuru. Yeniden üretme: komut 11.

### MINOR-6 — Aynı zaman alanı iki farklı ISO biçiminde

- `POST /kullanicilar` → `"olusturulma":"2026-09-12T19:43:03.840997+00:00"` (yazıldığı an),
  `GET /kullanicilar` → `"2026-09-12T19:43:03.840997"` (SQLite'tan okunuşta ofsetsiz).
  Aynı alan `/kimlik/panel-giris` yanıtında `son_giris` için `+00:00`, `/kimlik/ben` yanıtında
  ofsetsiz. Yeniden üretme: komut 15.

### Gözlem (bulgu değil)

- `gelistirme_baglantisi` alanı yalnız **kayıtlı ve aktif** e-posta için dönüyor; SMTP
  tanımsızken bu alan hesap varlığını kesin gösteren bir oracle'dır (komut 6). API.md §5 alanı
  meşru kıldığı için MINOR'a yazılmadı; `sifre-sifirlama-iste` sertleştirmesi yapılırken
  bilinmeyen e-postada da sahte bağlantı üretilmesi düşünülmeli.
- `/kimlik/cikis` anonim çağrıda 401 `kimlik_gerekli` döner; API.md §5 tablosunda yetki kolonu
  olmadığı için ihlal sayılmadı (spec §7.1 "kimlikli" diyor).
- `PATCH /kullanicilar/{id}` gövdesinde hiçbir alan verilmezse 200 + mevcut kayıt döner
  (denetim kaydı yazılmaz) — kabul edilebilir davranış (komut 18).
- `hedef_id` alanı `islem_kaydi`'da metin olarak saklanıyor (`"16"`); spec tip belirtmiyor.

---

## Özet

**14 bulgu: 1 BLOCKER, 6 MAJOR, 7 MINOR.**

- BLOCKER: yenileme jetonu eşzamanlı çağrılarda tek kullanımlık değil — aynı refresh jetonuyla
  5 paralel `POST /kimlik/yenile` isteğinin tamamı 200 dönüp 5 ayrı geçerli oturum üretiyor
  (yarış penceresi; sıralı kullanım doğru engelleniyor).

Geçen (çürütülemeyen) hedefler: sıralı refresh tek kullanımlığı, kayıt tekrarında 409 `cakisma`
ve büyük/küçük harf normalizasyonu, doğrulama jetonunun sıralı tek kullanımlığı ve süre denetimi,
sıfırlama sonrası eski refresh/eski parolanın reddi, rol matrisi (403/401/200), hiçbir yanıtta
parola alanı/özeti bulunmaması, rol değişikliğinin `islem_kaydi`'ya yazılması, API.md §5/§6
uçlarının tamamının OpenAPI'de bulunması ve yanıt alan adlarının birebir olması.

### Yeniden üretme özeti

| # | Komut | Sonuç |
|---|---|---|
| 1 | `gkimlik_01_jeton_rotasyon.py` | GEÇTİ |
| 2 | `gkimlik_01b_eszamanli_yenile.py` | KALDI (BLOCKER-1) |
| 3 | `gkimlik_02_kayit_cakisma.py` | GEÇTİ |
| 4 | `gkimlik_03_dogrulama_jetonu.py` | GEÇTİ |
| 5 | `gkimlik_04_sifre_sifirlama.py` | GEÇTİ |
| 6 | `gkimlik_05_zamanlama.py` | KALDI (MAJOR-4) |
| 7 | `gkimlik_06_rol_matrisi.py` | GEÇTİ |
| 8 | `gkimlik_07_parola_taramasi.py` | GEÇTİ |
| 9 | `gkimlik_08_patch_denetim.py` | KALDI (MAJOR-5) |
| 10 | `gkimlik_09_hata_kodlari.py` | KALDI (MAJOR-6, MINOR-1) |
| 11 | `gkimlik_10_openapi.py` | KALDI (MINOR-2, MINOR-5) |
| 12 | `gkimlik_11_kenar_durumlar.py` | KALDI (MINOR-3, MINOR-4) |
| 13 | `gkimlik_12_yaris.py` | KALDI (MAJOR-1, MAJOR-2, MAJOR-3) |
| 14 | `gkimlik_13_kullanici_listesi.py` | GEÇTİ (+ MAJOR-1 tekrarı) |
| 15 | `gkimlik_14_bicim.py` | KALDI (MINOR-6) |
| 16 | `gkimlik_15_anahtar.py` | GEÇTİ |
| 17 | `pytest arkauc/testler/test_kimlik.py test_yonetim.py` (ikincil) | GEÇTİ |
| 18 | `gkimlik_16_bos_govde.py` | GEÇTİ |
