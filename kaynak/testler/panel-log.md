# yonetim_paneli gözlem logu — 2026-09-12

## Kapsam
- API.md §4 (kurulum), §5 (kimlik), §8 (sağlayıcı/model kataloğu), §11 (`/bdm/yonetim/surucu/durum`), §12 (loglar), §13 (kullanım)
- spec §12.2 (`/kurulum` 4 adım, `/giris`, `/` kontrol paneli, menü sırası), §12.3 (tasarım dili), §12.1 oturum yenileme (401'de tek deneme)
- Ortam: gerçek tarayıcı (Chromium, OMP `browser` aracı), backend `http://localhost:8108` (geçici SQLite), panel `http://localhost:3001` (`NEXT_PUBLIC_API_URL=http://localhost:8108/api/v1`)

### Ortam kurulumu (tekrar üretilebilirlik)
```
hub start panel-api: ./.venv/Scripts/python.exe -m uvicorn arkauc.app.main:app --port 8108
  KUTYAI_VERITABANI_URL=sqlite+aiosqlite:///E:/kutyai-app/kaynak/testler/gecici/panel.db
  KUTYAI_GIZLI_ANAHTAR=gozlem-gizli-anahtar
  KUTYAI_SIFRELEME_ANAHTARI=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=
  KUTYAI_ORTAM=test
hub start panel-web: node node_modules/next/dist/bin/next dev -p 3001 (cwd yonetim_paneli, NEXT_PUBLIC_API_URL=http://localhost:8108/api/v1)
```
Yardımcı betikler: `kaynak/testler/betikler/panel_hesaplar.py`, `panel_konusma_tohum.py`, `panel_yenileme.py`, `panel_eszamanli_yenileme.py`.
Ekran görüntüleri: `kaynak/testler/kanit/*.png`, derlenmiş CSS kopyası: `kaynak/testler/kanit/panel-derlenmis.css`.

---

## Koşulan komutlar

### 1) `curl http://localhost:8108/api/v1/saglik/kurulum` + `/saglayicilar`
- Beklenen: `kurulum_tamam:false`, 7 sağlayıcı (API.md §8).
- Gerçek çıktı:
```
{"kurulum_tamam":false,"marka_adi":"KutyAI","surum":"0.1.0"}
7
openai https://api.openai.com/v1 True False False
azure  True False False
openrouter https://openrouter.ai/api/v1 True False False
ollama http://localhost:11434/v1 False False True
vllm http://localhost:8000/v1 False True True
tgi http://localhost:8080/v1 False True True
ozel  False False False
```
- Sonuç: GEÇTİ

### 2) `browser.open` → `http://localhost:3001/kurulum`, sayfa yüklemesinde ağ istekleri (`page.on("request"/"response")`)
- Beklenen: sağlayıcı listesi GERÇEKTEN API'den gelmeli (gömülü liste değil).
- Gerçek çıktı (yalnız 8108 istekleri):
```
>> GET http://localhost:3001/kurulum
<< 200 http://localhost:3001/kurulum
>> GET http://localhost:8108/api/v1/saglayicilar
>> GET http://localhost:8108/api/v1/saglik/kurulum
<< 200 http://localhost:8108/api/v1/saglayicilar
<< 200 http://localhost:8108/api/v1/saglik/kurulum
```
- Sonuç: GEÇTİ (kanıt: 9. komut — `<select>` seçenekleri bu yanıtla birebir aynı)

### 3) Adım 1 boş "İleri" (gerçek fare tıklaması)
- Beklenen: Türkçe alan hatası.
- Gerçek çıktı:
```
Marka adı*
Marka adı zorunludur.
Geri
İleri
```
- Sonuç: GEÇTİ — `kanit/kurulum-02-adim1-hata.png`

### 4) Adım 2 boş "İleri"
- Beklenen: her zorunlu alan için Türkçe mesaj.
- Gerçek çıktı:
```
Ad soyad*
Ad soyad zorunludur.
E-posta*
E-posta adresi zorunludur.
Parola*
Parola zorunludur.
Parola tekrar*
Parola tekrarı zorunludur.
```
- Sonuç: GEÇTİ — `kanit/kurulum-03-adim2-bos-hata.png`

### 5) Adım 2 geçersiz değerler (`bozuk-eposta`, `kisa`, `baska`)
- Beklenen: biçim/uzunluk/eşleşme mesajları.
- Gerçek çıktı:
```
E-posta*
Geçerli bir e-posta adresi girin.
Parola*
Parola en az 8 karakter olmalıdır.
Parola tekrar*
Parolalar eşleşmiyor.
```
- Sonuç: GEÇTİ — `kanit/kurulum-04-adim2-gecersiz.png`

### 6) "Geri" → adım 1, sonra "İleri" → adım 2 (değer korunumu, DOM değerleri okundu)
- Beklenen: adım geçişlerinde girilen değerler korunmalı.
- Gerçek çıktı:
```
{"geriSonrasi":{"marka":"Acme AI"},"ileriSonrasi":{"adsoyad":"Ayse Yilmaz","eposta":"admin@acme.com"}}
```
- Sonuç: GEÇTİ

### 7) Adım 3 sağlayıcı listesi ve varsayılanlar
- Beklenen: API.md §8 sağlayıcıları, otomatik seçilen CPU-uyumlu varsayılan ve `temel_url`.
- Gerçek çıktı:
```
"seçenekler":["openai|OpenAI","azure|Azure OpenAI","openrouter|OpenRouter","ollama|Ollama (yerel)","vllm|vLLM (yerel)","tgi|TGI (yerel)","ozel|Özel (OpenAI uyumlu)"]
"seçili":"ollama"
"Görünen ad=" "Temel adres=http://localhost:11434/v1" "Upstream model="
```
- Sonuç: GEÇTİ — `kanit/kurulum-05-adim3-bdm.png`, `kurulum-12-adim3-dolu.png`
- Not: API.md §8'de veya panelde `konusma` adlı bir alan yok; sağlayıcıya bağlı güncellenen alanlar `temel_url` ve `api_anahtari` görünürlüğüdür. `upstream_model` sağlayıcıya göre ön-doldurulmuyor (sözleşmede varsayılan model alanı yok). Ayrıntı 8. komutta.

### 8) Sağlayıcı değiştirme (`page.select`)
- Beklenen: `temel_url` sağlayıcının `varsayilan_temel_url` değerine güncellenmeli; API anahtarı yalnız `api_anahtari_gerekir=true` iken görünmeli.
- Gerçek çıktı:
```
openai  -> Temel adres=https://api.openai.com/v1 | alanlar: Görünen ad, Temel adres, Upstream model, API anahtarı
azure   -> Temel adres=                          | API anahtarı alanı var
vllm    -> Temel adres=http://localhost:8000/v1  | API anahtarı alanı YOK | GPU uyarı metni göründü
ozel    -> Temel adres=                          | API anahtarı alanı YOK
```
- Sonuç: GEÇTİ — `kanit/kurulum-06-adim3-openai.png`, `kurulum-07-adim3-azure.png`, `kurulum-08-adim3-vllm.png`

### 9) Adım 3 boş "İleri" ve geçersiz adres (`ftp://bozuk`)
- Gerçek çıktı:
```
Görünen ad zorunludur.
Temel adres zorunludur.
Upstream model zorunludur.
--- sonra ---
Adres http:// veya https:// ile başlamalıdır.
```
- Sonuç: GEÇTİ — `kanit/kurulum-09-adim3-bos-hata.png`

### 10) Sağlayıcı listesi ağ hatası (`/saglayicilar` isteği kesildi) ve "Yeniden dene"
- Beklenen: anlaşılır Türkçe hata + kurtarma.
- Gerçek çıktı (kesme açıkken):
```
Sağlayıcı listesi alınamadı
Sağlayıcı listesi alınamadı. Sunucu ayakta mı?
Yeniden dene
```
Kesme kaldırılıp "Yeniden dene" tıklandıktan sonra: `<select>` yeniden geldi, seçenekler `openai,azure,openrouter,ollama,vllm,tgi,ozel`.
- Sonuç: GEÇTİ — `kanit/kurulum-10-saglayici-ag-hatasi.png`, `kurulum-11-saglayici-yeniden-dene.png`

### 11) Sihirbaz uçtan uca (gerçek klavye girişi) → `POST /kurulum`
- Beklenen: 201 + `/giris?kurulum=tamam` + başarı bildirimi.
- Gerçek çıktı:
```
yollar: marka=klavye, adsoyad=klavye, eposta=klavye, parola=klavye, parolatekrar=klavye, gorunenad=klavye, upstream=klavye
adim3: {"secili":"ollama","temelAdres":["Görünen ad=Yerel Llama 3","Temel adres=http://localhost:11434/v1","Upstream model=llama3"]}
ağ: >> OPTIONS /api/v1/kurulum / >> POST /api/v1/kurulum / << 200 (preflight) / << 201 (POST)
201 gövdesi: {"yonetici":{"id":1,"eposta":"admin@acme.com",...,"rol":"yonetici","eposta_dogrulandi":true},
             "bdm":{"id":1,"slug":"yerel-llama-3",...,"durum":"hata",...}, ...}
sonrası: url=http://localhost:3001/giris?kurulum=tamam
         "Kurulum tamamlandı / Yönetici hesabınızla giriş yapabilirsiniz."
```
- Sonuç: GEÇTİ — `kanit/kurulum-13-adim4-ozet.png`, `kurulum-14-giris-basari.png`
- Not (bkz. Bulgu 2): 201 gövdesindeki `dogrulama` alanı hiç kullanılmıyor.

### 12) Kurulum bittikten sonra `/kurulum` yeniden açıldı
- Beklenen: `/giris`e yönlendirme (API.md §4, `/saglik/kurulum`).
- Gerçek çıktı:
```
url: http://localhost:3001/giris
istekler: >> GET /api/v1/saglik/kurulum ... << 200 ... << 200 (çift çağrı: React strict mode, geliştirme)
```
- Sonuç: GEÇTİ

### 13) Giriş senaryoları (`/giris`, gerçek etkileşim)
- Gerçek çıktı:
```
yanlış parola            -> "E-posta veya parola hatalı."                    (url /giris)
doğrulanmış son_kullanıcı-> "Bu hesap yönetim paneline giremez. Yönetici, operatör veya izleyici rolüyle giriş yapın."
doğrulanmamış son_kullanıcı -> "Bu hesap yönetim paneline giremez. ..." (aynı mesaj)
```
- Sonuç: KISMEN — kimlik bilgisi hatası ayrışıyor; "e-posta doğrulanmamış" mesajı hiçbir senaryoda çıkmıyor (bkz. Bulgu 3).
- Kanıt: `kanit/giris-01-yanlis-parola.png`, `giris-02-son-kullanici-403.png`, `giris-03-dogrulanmamis.png`

### 14) Başarılı giriş (`admin@acme.com`) → kontrol paneli veri blokları
- Beklenen: §3/§11/§12/§13 verileri gerçek uçlardan.
- Gerçek çıktı (ağ + ekran):
```
>> POST /api/v1/kimlik/panel-giris << 200
>> GET /api/v1/saglik | /bdm/yonetim/surucu/durum | /kullanim/ozet?gun=30 | /loglar/konusmalar?boyut=5  (hepsi 200)
Ekran: "Acme AI ... Ayakta Sürüm 0.1.0 / Ortam test / Sunucu zamanı 12 Eyl 2026 22:43"
       "Docker hazır / GPU hazır / Sürücü: docker / NVIDIA GeForce RTX 3080 Ti"
       "TOPLAM İSTEK 0 ... KOTA AŞIMI 0"  |  "Henüz konuşma yok"
```
- Sonuç: GEÇTİ — `kanit/panel-01-kontrol-paneli.png`
- Gözlem: aynı sayfa birkaç dakika sonra "Docker yok / GPU yok / Sürücü: yok" gösterdi (`/bdm/yonetim/surucu/durum` üç ardışık çağrıda da aynı); panel uçtaki değeri doğru yansıtıyor, fark arka uç algılamasından geliyor (kapsam dışı, `bdm_yönetim_ucu`).

### 15) Backend kapatıldı (`hub stop panel-api`) → `/` yeniden yüklendi
- Beklenen: her blok Türkçe hata + "Yeniden dene"; beyaz ekran/çökme yok.
- Gerçek çıktı:
```
"bloklar": 4 × "Veri alınamadı\n\nSunucuya ulaşılamadı. API adresini ve bağlantınızı kontrol edin.\n\nYeniden dene"
"yenidenDene":4
requestfailed: GET /api/v1/saglik :: net::ERR_CONNECTION_REFUSED, /saglik/kurulum, /bdm/yonetim/surucu/durum, /kullanim/ozet?gun=30, /loglar/konusmalar?boyut=5
marka adı yedek olarak "KutyAI" gösterildi
```
- Sonuç: GEÇTİ — `kanit/panel-02-backend-kapali.png`

### 16) Backend yeniden başlatıldı → 4 × "Yeniden dene"
- Gerçek çıktı: `kalan alert: 0` ve tüm bloklar gerçek veriyle doldu.
- Sonuç: GEÇTİ — `kanit/panel-03-yeniden-dene-sonrasi.png`

### 17) 500 enjeksiyonu (`/kullanim/ozet`, `/loglar/konusmalar` → 500 + hata zarfı)
- Beklenen: sözleşme mesajı gösterilmeli.
- Gerçek çıktı:
```
"bloklar":["Veri alınamadı\n\nKullanım verisi okunamadı (gözlem enjeksiyonu).\n\nYeniden dene",
           "Veri alınamadı\n\nLog sorgusu başarısız (gözlem enjeksiyonu).\n\nYeniden dene"]
```
- Sonuç: GEÇTİ — `kanit/panel-04-500-hatalari.png`

### 18) "Son Konuşmalar" bloğu gerçek kayıtla (geçici veritabanına tohum kaydı)
- Beklenen: tablo satırı başlık/kullanıcı/model/mesaj/tarih ile render edilmeli.
- Gerçek çıktı:
```
API: {"toplam":1,"kayitlar":[{"id":1,"baslik":"Gözlem konuşması [MASKELENDI:telefon]","kullanici_eposta":"admin@acme.com","bdm_ad":"Yerel Llama 3","mesaj_sayisi":2,...}]}
Panel: basliklar ["Başlık","Kullanıcı","Model","Mesaj","Tarih"]
       satır ["Gözlem konuşması [MASKELENDI:telefon]","admin@acme.com","Yerel Llama 3","2","12 Eyl 2026 19:50"]
```
- Sonuç: GEÇTİ — `kanit/panel-05-son-konusmalar-veri.png`

### 19) Oturum koruması 1: yalnız erişim jetonu silindi → `/` yeniden yüklendi
- Beklenen: `/giris`e yönlendirme.
- Gerçek çıktı:
```
giriş sonrası: ["kutyai.panel.yenileme","kutyai.panel.erisim","kutyai.panel.kullanici"]
erisim silindikten sonra: url=http://localhost:3001/giris, anahtarlar=["kutyai.panel.yenileme","kutyai.panel.kullanici"]
```
- Sonuç: GEÇTİ (yenileme jetonu depoda kalıyor — hijyen notu)

### 20) Oturum koruması 2: erişim jetonu bozuk + yenileme jetonu GEÇERLİ → `/` yeniden yüklendi
- Beklenen: 401 → tek yenileme denemesi → veri yüklenmeli, oturum korunmalı.
- Gerçek çıktı (ilk koşu):
```
>> GET .../bdm/yonetim/surucu/durum  << 401
>> POST /kimlik/yenile  << 200   (birkaç kez)
<< 401 /kimlik/yenile   (yinelenen istekler)
son durum: url=http://localhost:3001/giris, localStorage anahtar sayısı = 0
```
İkinci koşu (aynı senaryo, normal ağ): 12 × `POST /kimlik/yenile`, hepsi 200, oturum korundu.
Enjekte edilmiş tek 401 ile deterministik koşu:
```
giriş: 3 anahtar
olaylar: POST /kimlik/yenile #1 -> 401 enjekte | #2..#6 -> gerçek (200)
son: url=http://localhost:3001/giris, anahtarlar=[]
```
- Sonuç: KALDI — bkz. Bulgu 1.

### 21) API düzeyi: yenileme rotasyonu ve eşzamanlı yenileme (`betikler/panel_yenileme.py`, `panel_eszamanli_yenileme.py`)
- Gerçek çıktı:
```
panel_yenileme.py:
{"giris":{"durum":200,"rol":"yonetici"},"yenile_1":{"durum":200,"erisim_var":true},
 "yenile_2_ayni_jeton":{"durum":401,"govde":{"hata":{"kod":"jeton_gecersiz",...}}}}
panel_eszamanli_yenileme.py (aynı jetonla 6 eşzamanlı istek):
[200, 401, 401, 401, 401, 401]  — 5 × "jeton_gecersiz"
```
- Sonuç: GEÇTİ (sunucu davranışı doğru; panelin buna tepkisi Bulgu 1)

### 22) Oturum koruması 3: erişim jetonu silinmiş + `kullanici` kaydı yok
- Beklenen: `/giris`e yönlendirme ya da en azından hata.
- Gerçek çıktı (8 sn sonra, konsol hatası yok):
```
url=http://localhost:3001/, metin="Oturum kontrol ediliyor…", anahtarlar=["kutyai.panel.yenileme","kutyai.panel.erisim"]
```
- Sonuç: KALDI — bkz. Bulgu 4.

### 23) Kullanıcı menüsü ve çıkış
- Gerçek çıktı:
```
menü: "Ayse Yilmaz / admin@acme.com / Yönetici / Çıkış yap"
>> POST /api/v1/kimlik/cikis << 200
son: url=http://localhost:3001/giris, anahtarlar=[]
```
- Sonuç: GEÇTİ — `kanit/panel-06-kullanici-menusu.png`

### 24) Mobil 390×844 (dokunmatik bağlam)
- Beklenen: çekmece açılmalı, menü okunabilir, yatay taşma olmamalı.
- Gerçek çıktı:
```
yatayKaydirma (scrollWidth-clientWidth)=0 ; masaüstü <aside> display=none ; menü düğmesi var
çekmece açık: nav 287x68 @0,56 ; öğeler ["Kontrol Paneli -> /"] ; yazı 14px
```
- Sonuç: GEÇTİ — `kanit/mobil-01-kontrol-paneli-390.png`, `kanit/mobil-02-cekmece-390.png` (görsel doğrulama: çekmece açık, marka "Acme AI", "Kapat" düğmesi ve "Kontrol Paneli" öğesi okunabilir)

### 25) `npx tsc --noEmit`
- Gerçek çıktı:
```
TSC_EXIT=0
```
- Sonuç: GEÇTİ

### 26) `npm run build`
- Gerçek çıktı:
```
▲ Next.js 15.5.25
 ✓ Compiled successfully in 1262ms
   Linting and checking validity of types ...
 ✓ Generating static pages (6/6)
Route (app)                                 Size  First Load JS
┌ ○ /                                    6.18 kB         118 kB
├ ○ /_not-found                            123 B         103 kB
├ ○ /giris                                1.5 kB         117 kB
└ ○ /kurulum                             3.99 kB         120 kB
BUILD_EXIT=0
```
- Sonuç: GEÇTİ
- Not: `NEXT_PUBLIC_API_URL` derleme zamanında gömüldüğü için üretim derlemesi bu değişkenle yapılmalı; değişkensiz derlemede istemci `http://localhost:8000/api/v1` varsayılanına düşer (`lib/api.ts:3-5`).

### 27) Derlenmiş CSS'te tasarım sözleşmesi (`.next/static/css/4a582cad9c7af6b5.css`, 23400 bayt)
- Beklenen (spec §12.3): `sm:` yok, gradyan/purple/glassmorphism yok, kenarlık-odaklı focus.
- Gerçek çıktı:
```
[1] medya sorguları: @media (hover:hover) , @media (min-width:48rem)
[2] 40rem (sm) sayısı: 0
[3] purple|violet|indigo sayısı: 0
[4] backdrop-filter|backdrop-blur sayısı: 0
[5] linear-gradient|radial-gradient sayısı: 0
[6] focus-visible\:ring-2:focus-visible{--tw-ring-shadow:... calc(2px + ...) var(--tw-ring-color,currentcolor); box-shadow:...}
[7] focus\:border-neutral-900:focus{border-color:var(--color-neutral-900)}
[8] rose-300 ×3, rose-50 ×3, rose-500 ×5, rose-600 ×11, rose-700 ×5, rose-900 ×3
```
- Sonuç: KISMEN — yasaklı desenlerin hiçbiri yok (`sm:`, gradyan, purple/violet/indigo, backdrop-blur temiz); ancak odak göstergesi buton/bağlantılarda `ring-2` ile kurulmuş (bkz. Bulgu 5).
- Kopya: `kanit/panel-derlenmis.css`

### 28) Sağlayıcı listesi alınamazken adım 3'te "İleri"
- Beklenen: kullanıcıya neden ilerleyemediği söylenmeli.
- Gerçek çıktı (tıklama öncesi ve sonrası metin BİREBİR aynı, yeni hata yok):
```
... Sağlayıcı listesi alınamadı / Sağlayıcı listesi alınamadı. Sunucu ayakta mı? / Yeniden dene
Görünen ad*  Temel adres*  Upstream model*  ... Geri  İleri
"secVar":false  (select yok)
```
- Sonuç: KALDI — bkz. Bulgu 6 — `kanit/kurulum-15-saglayici-hatasi-ilerle.png`

### 29) API erişilemezken `/giris`
- Gerçek çıktı: `{"metin":"KutyAI / Yönetim paneline giriş yapın / E-posta* Parola* Giriş yap","formVar":true}`
- Sonuç: GEÇTİ (sonsuz "Yükleniyor…" yok)

### 30) Kurulum zaten tamamken `POST /kurulum` (409 `kurulum_zaten_tamam`)
- Beklenen: hata bandı değil, `/giris`e yönlendirme (API.md §4).
- Gerçek çıktı (sadık benzetim: 409 sonrası `/saglik/kurulum` → `kurulum_tamam:true`):
```
GET /saglik/kurulum -> 200 | POST /kurulum -> 409 | GET /saglik/kurulum -> 200
son: url=http://localhost:3001/giris | "Yönetim paneline giriş yapın / E-posta* Parola* Giriş yap"
```
- Sonuç: GEÇTİ

---

## Bulgular

- [BLOCKER] `yonetim_paneli/lib/api.ts:108-144` + `:150-161` — Eşzamanlı 401'lerde yenileme tekilleştirmesi yok: `yenilemeSozu` (108) yazılıyor fakat hiçbir yerde okunmuyor, bu yüzden her 401 kendi `POST /kimlik/yenile` isteğini başlatıyor (ölçüm: 4 blok için 12 istek). Backend yenileme jetonunu döndürdüğü için (`arkauc/app/servisler/kimlik.py:269` `kayit.iptal = True`) aynı jetonla eşzamanlı isteklerden bazıları 401 `jeton_gecersiz` alıyor (ölçüm: 6 eşzamanlı istek → 1×200 + 5×401). `istek()` (150-161) herhangi bir yenileme başarısız olduğunda koşulsuz `oturumTemizle()` (157) çağırıyor, böylece aynı anda 200 dönen yenilemelere rağmen oturum siliniyor. Beklenen: 401 başına tek paylaşılan yenileme denemesi ve yalnız yenileme gerçekten başarısızsa oturumun temizlenmesi. Yeniden üretme: giriş yap → DevTools/localStorage'da `kutyai.panel.erisim` değerini boz → `/` sayfasını yavaş ağda (veya rotasyon yarışında) yenile → bazı `/kimlik/yenile` yanıtları 401 döner → tüm anahtarlar silinir ve `/giris`e yönlendirilirsiniz. Kanıt: 20. ve 21. komutlar.
- [MAJOR] `yonetim_paneli/app/kurulum/page.tsx:217-218` — `POST /kurulum` yanıtındaki `dogrulama: {basarili, mesaj}` alanı hiç okunmuyor (`grep -rn "dogrulama" yonetim_paneli` yalnız `lib/tipler.ts:145` tip tanımını ve doğrulama yardımcı modülünü buluyor). Bağlantı doğrulaması başarısız olduğunda bile kullanıcıya yalnız "Kurulum tamamlandı" bildirimi gösteriliyor. Canlı koşuda model doğrulanamadı (`bdm.durum:"hata"`, ollama çalışmıyor) ve panel bunu hiç bildirmedi; oysa adım metni "Kurulum sonunda bağlantı doğrulanır" diyor. Beklenen: `dogrulama.basarili=false` iken kullanıcıya `dogrulama.mesaj` gösterilmeli. Yeniden üretme: 11. komutu çalıştırın, 201 gövdesindeki `bdm.durum` değerini ve ardından `/giris`te gösterilen bildirimi karşılaştırın.
- [MINOR] `yonetim_paneli/app/giris/page.tsx:84-86` — `eposta_dogrulanmadi` dalı ulaşılamaz: backend `panel-giris` için doğrulama kontrolünü yalnız `panel=False` durumunda yapıyor (`arkauc/app/api/kimlik.py:113`), rol kontrolü önce geldiği için (`:108-110`) doğrulanmamış bir `son_kullanici` 403 `yetki_yok` alıyor. Sonuç: "E-posta adresiniz doğrulanmamış." mesajı hiçbir senaryoda çıkmıyor; doğrulanmamış ve doğrulanmış son kullanıcı aynı mesajı görüyor (13. komut). Beklenen: ya dal kaldırılmalı ya da kullanıcıya doğrulama durumu bildirilmeli.
- [MINOR] `yonetim_paneli/app/(panel)/layout.tsx:19-29` — Erişim jetonu dururken `kutyai.panel.kullanici` kaydı yok/bozuksa (`kullaniciOku()` → `null`, `oturum.ts:48-57` bozuk JSON'u siler) arayüz sonsuza kadar "Oturum kontrol ediliyor…" ekranında kalıyor; `/giris`e yönlendirme yok ve konsolda hata çıkmıyor. Yeniden üretme: giriş yap → `localStorage.removeItem("kutyai.panel.kullanici")` → `/` yükle (8 sn gözlem; 22. komut).
- [MINOR] `yonetim_paneli/components/ui/stiller.ts:5` (ve kullanıldığı ~12 yer) — Odak göstergesi buton/bağlantılarda `focus-visible:ring-2 ring-neutral-900` ile kurulmuş; spec §12.3 kenarlık-odaklı gösterge istiyor (`focus:border-neutral-900 focus:ring-0`). Metin alanlarında kural doğru uygulanmış (`stiller.ts:9`). Derlenmiş CSS kanıtı: 27. komut [6]/[7].
- [MINOR] `yonetim_paneli/app/kurulum/page.tsx:160` + `:363-380` — Sağlayıcı listesi alınamadığında `<select>` bloğu hiç render edilmiyor (`:363` koşulu `!saglayicilar.hata`), ancak `ilerle()` (`:172-177`) yine de `hatalar.saglayici = "Sağlayıcı seçimi zorunludur."` (`:160`) yazıyor; mesajı gösterecek `Field` (`:364`) aynı dalın içinde olduğu için kullanıcı hiçbir açıklama görmeden adımda takılıyor (metin tıklama öncesi/sonrası birebir aynı; 28. komut). Beklenen: ya alan gizliyken zorunluluk denetimi atlanmalı ya da hata görünür bir yerde gösterilmeli.

### Bulgu olmayan gözlemler
- Sağlayıcı açıklamalarında Türkçe diakritikler eksik (kullanıcıya sihirbazda görünüyor): `bdm_listesi/saglayicilar.py:53,65,79,93` — "Azure uzerinde barindirilan…", "CPU veya GPU uzerinde yerel model calistirir.", "GPU uzerinde yuksek verimli cikarim." (kaynak arka uç; panel metni olduğu gibi gösteriyor).
- `/kurulum` sayfası kurulum tamamken de `GET /saglayicilar` çağırıyor (yönlendirme kararından önce) — gereksiz tek istek.
- Geliştirme kipinde React strict mode nedeniyle tüm bloklar iki kez çağrılıyor (üretim derlemesini etkilemez).
- `/bdm/yonetim/surucu/durum` aynı koşuda "docker hazır / GPU hazır / NVIDIA GeForce RTX 3080 Ti", sonraki koşularda "yok" döndü; panel uçtaki değeri doğru yansıtıyor (kapsam dışı: `bdm_yönetim_ucu`).
- Menüde yalnız "Kontrol Paneli" görünüyor; `components/panel/menu.ts:11-14` bunu bilinçli olarak `hazir:false` ile açıklıyor (dalga 2 sayfaları).

## Özet
6 bulgu (1 BLOCKER, 1 MAJOR, 4 MINOR).

BLOCKER özeti: eşzamanlı 401'lerde yenileme tekilleştirilmediği için (`lib/api.ts` içindeki `yenilemeSozu` hiç okunmuyor) sunucunun döndürdüğü yenileme jetonu rotasyonu yarışa giriyor ve tek bir başarısız yenileme yanıtı, geçerli oturumu tümden silip kullanıcıyı `/giris`e atıyor.
