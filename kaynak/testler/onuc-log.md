# onuc gözlem logu — 2026-09-12

## Kapsam

- `kaynak/API.md` §5 (Kimlik), §9 (Sohbet), §13 (Kullanım)
- `kaynak/spec/2026-09-12-kutyai-bdm-platformu-tasarim.md` §12.1 (`onuc` sayfaları), §12.3 (tasarım dili), §13.2 (arayüz doğrulaması: `npm run build` + `tsc --noEmit` yeşil + gerçek tarayıcıda uçtan uca duman testi)
- Ortam: backend `http://localhost:8107` (geçici SQLite), arayüz `http://localhost:3000` (`NEXT_PUBLIC_API_URL=http://localhost:8107/api/v1`), gerçek Chromium (`browser`), viewport 1280×900 ve mobil 390×844.

Ortam değişkenleriyle başlatılan süreçler:

```
hub start onuc-backend  -> ./.venv/Scripts/python.exe -m uvicorn arkauc.app.main:app --port 8107
   KUTYAI_VERITABANI_URL=sqlite+aiosqlite:///E:/kutyai-app/kaynak/testler/gecici/onuc.db
   KUTYAI_GIZLI_ANAHTAR=gozlem-gizli-anahtar
   KUTYAI_SIFRELEME_ANAHTARI=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=
hub start onuc-dev      -> npm run dev (cwd onuc, NEXT_PUBLIC_API_URL=http://localhost:8107/api/v1)
```

Backend kapatılmadan önce `npm run build`/`npx tsc --noEmit` için yalnız arayüz süreci durduruldu (`.next` çakışmasını önlemek için).

---

## Koşulan komutlar

### 1) `python kaynak/testler/betikler/hazirlik.py`

- Beklenen: `/saglik` ve `/saglik/kurulum` 200; `POST /kimlik/kayit` 201 + `dogrulama_gerekli:true` + SMTP tanımsız olduğu için `gelistirme_baglantisi`.
- Gerçek çıktı:

```
GET /saglik -> 200 {"durum":"ayakta","surum":"0.1.0","ortam":"gelistirme","zaman":"2026-09-12T19:38:46.977347+00:00"}
GET /saglik/kurulum -> 200 {"kurulum_tamam":false,"marka_adi":"KutyAI","surum":"0.1.0"}
POST /kimlik/kayit -> 201 {"kullanici":{"id":1,"eposta":"sonda@ornek.com","ad_soyad":"Sonda","rol":"son_kullanici","durum":"beklemede","eposta_dogrulandi":false,"olusturulma":"2026-09-12T19:38:47.034126+00:00","son_giris":null},"dogrulama_gerekli":true,"gelistirme_baglantisi":"http://localhost:3000/dogrula?jeton=MsLNFHQ5mZYPqcjxkeburFfh37LkXsoplip8rYTQgOI"}
```

- Sonuç: GEÇTİ

### 2) `/kayit` uçtan uca kayıt (tarayıcı; alanlar React `input` olayı ile dolduruldu)

- Beklenen: 4 alan + `label[for]` bağı; gönderim sonrası kayıt ekranı, `dogrulama_gerekli` mesajı ve `gelistirme_baglantisi` bağlantısı; jeton `localStorage`'a yazılmaz.
- Gerçek çıktı (alan envanteri):

```
[{"etiket":"INPUT","name":"ad_soyad","id":"alan-_R_p5esnekndlb_","tip":"text","autocomplete":"name","aria":null,"label":"Ad soyad*"},
 {"etiket":"INPUT","name":"eposta","id":"alan-_R_195esnekndlb_","tip":"email","autocomplete":"email","aria":null,"label":"E-posta*"},
 {"etiket":"INPUT","name":"parola","id":"alan-_R_1p5esnekndlb_","tip":"password","autocomplete":"new-password","aria":"alan-_R_1p5esnekndlb_-yardim","label":"Parola*"},
 {"etiket":"INPUT","name":"parola_tekrar","id":"alan-_R_295esnekndlb_","tip":"password","autocomplete":"new-password","aria":null,"label":"Parola (tekrar)*"}]
```

```
["Göz Onuç","goz.onuc.2@ornek.com","parola1234","parola1234"]
{"url":"http://localhost:3000/kayit","govde":"KutyAI\n\nKurumsal büyük dil modeli platformu\n\nKayıt tamamlandı\n\nKayıt alındı. E-posta adresinize doğrulama bağlantısı gönderildi.\n\nBu ortamda e-posta gönderimi tanımlı değil; doğrulamayı bağlantıyla tamamlayabilirsiniz.\n\nE-postamı doğrula\nGiriş sayfasına dön\nKutyAI · Tüm işlemler kayıt altına alınır.\n\nHesabınız oluşturuldu.","baglantilar":["/","/dogrula?jeton=2_onhgBZj_-Rcy5cFoC4E0OtHHd12aD3hzfl77UoQmA","/giris"]}
```

- Sonuç: GEÇTİ

### 3) `GET /dogrula?jeton=…` (tarayıcı)

- Beklenen: jeton otomatik doğrulanır, başarı mesajı ve `/giris` bağlantısı; jeton yazılmaz.
- Gerçek çıktı:

```
{"url":"http://localhost:3000/dogrula?jeton=2_onhgBZj_-Rcy5cFoC4E0OtHHd12aD3hzfl77UoQmA","govde":"KutyAI\n\nKurumsal büyük dil modeli platformu\n\nDoğrulandı\n\nE-posta adresiniz doğrulandı. Artık giriş yapabilirsiniz.\n\nGiriş yapın\nKutyAI · Tüm işlemler kayıt altına alınır.","depo1":"[]"}
```

- Sonuç: GEÇTİ

### 4) `/giris` ile giriş (tarayıcı)

- Beklenen: jeton çifti `localStorage`'da, `/sohbet`'e yönlenme.
- Gerçek çıktı:

```
{"url":"http://localhost:3000/sohbet","depo":"{\"erisim\":\"eyJhbGciOiJIUzI1NiIs...\",\"yenileme\":\"5NTaW5m2mI9tW4cBUJQN...\",\"anahtarlar\":[\"kutyai.erisim_jetonu\",\"kutyai.yenileme_jetonu\"]}","govde":"KutyAI\nSohbet\nKullanım\nHesap\n\nGöz Onuç\n\nSon kullanıcı\n\nÇıkış\nSohbet yakında\n..."}
```

- Sonuç: GEÇTİ

### 5) Hata yolları — yanlış parola + doğrulanmamış kullanıcı (tarayıcı)

- Beklenen: Türkçe `role="alert"` mesajı, sayfada kalma, jeton yazılmaması; doğrulanmamış kullanıcıda anlaşılır yönlendirme.
- Gerçek çıktı:

```
YANLIS PAROLA: {"url":"http://localhost:3000/giris","rolAlert":["E-posta veya parola hatalı."],"depo":[],
 "govde":"KutyAI\n\nKurumsal büyük dil modeli platformu\n\nGiriş yap\n\nKurumsal hesabınızla devam edin.\n\nE-posta veya parola hatalı.\n\n..."}
DOGRULANMAMIS: {"url":"http://localhost:3000/giris","rolAlert":["Giriş yapmadan önce e-posta adresinizi doğrulamalısınız.\n\nE-posta adresinizi doğrulamak için doğrulama sayfasına gidin."],"depo":[]}
```

- Sonuç: GEÇTİ

### 6) Hata yolu — aynı e-posta ile ikinci kayıt (409 `cakisma`)

- Beklenen: Türkçe `role="alert"`, sayfada kalma.
- Gerçek çıktı:

```
{"url":"http://localhost:3000/kayit","alertler":["Bu e-posta adresi zaten kayıtlı."]}
```

- Sonuç: GEÇTİ

### 7) Hata yolu — istemci tarafı doğrulama (kısa parola / uyuşmayan parola)

- Gerçek çıktı:

```
kisa_parola: {"url":"http://localhost:3000/kayit","alertler":["Parola en az 8 karakter olmalı."]}
uyusmayan:   {"url":"http://localhost:3000/kayit","alertler":["Parolalar birbiriyle eşleşmiyor."]}
```

- Sonuç: GEÇTİ

### 8) 401 yenileme — süresi geçmiş erişim jetonu + geçerli yenileme jetonu (tarayıcı + CDP ağ izleme)

Jeton, `kaynak/testler/betikler/suresi_dolmus_jeton.py` ile imzası geçerli ama `exp`'i 2 saat geçmiş olarak üretildi (aynı `KUTYAI_GIZLI_ANAHTAR`); backend'in bu jetonu `401 jeton_suresi_doldu` ile reddettiği httpx ile doğrulandı:

```
401 {"hata":{"kod":"jeton_suresi_doldu","mesaj":"Oturum süresi doldu. Lütfen tekrar giriş yapın.","ayrinti":{}}}
401 {"hata":{"kod":"jeton_gecersiz","mesaj":"Oturum bilgisi geçersiz. Lütfen tekrar giriş yapın.","ayrinti":{}}}   # bozuk.jeton.x
```

`/hesap` ziyareti (tek korumalı istek):

```
["ISTEK GET http://localhost:8107/api/v1/kimlik/ben","YANIT 401 http://localhost:8107/api/v1/kimlik/ben",
 "ISTEK POST http://localhost:8107/api/v1/kimlik/yenile","ISTEK OPTIONS http://localhost:8107/api/v1/kimlik/yenile",
 "YANIT 200 http://localhost:8107/api/v1/kimlik/yenile","YANIT 200 http://localhost:8107/api/v1/kimlik/yenile",
 "ISTEK GET http://localhost:8107/api/v1/kimlik/ben","YANIT 200 http://localhost:8107/api/v1/kimlik/ben",
 "ISTEK GET http://localhost:8107/api/v1/kimlik/ben","ISTEK GET http://localhost:8107/api/v1/kimlik/ben",
 "YANIT 200 http://localhost:8107/api/v1/kimlik/ben","YANIT 200 http://localhost:8107/api/v1/kimlik/ben"]
sonrasi: {"url":"http://localhost:3000/hesap","erisimBasi":"eyJhbGciOiJIUzI1NiIsR5","yenilemeVar":true,"govde":"...Hesabım ... Göz Onuç ..."}
```

İki eşzamanlı 401 (`Promise.all` ile `/kullanim/ozet` + `/kullanim/zaman-serisi`, arayüz açıkken erişim jetonu bozularak):

```
["ISTEK GET /kullanim/ozet?gun=7","ISTEK GET /kullanim/zaman-serisi?gun=7&kirilim=bdm",
 "ISTEK OPTIONS /kullanim/ozet?gun=7","ISTEK OPTIONS /kullanim/zaman-serisi?gun=7&kirilim=bdm",
 "  YANIT 200 /kullanim/ozet?gun=7","  YANIT 200 /kullanim/zaman-serisi?gun=7&kirilim=bdm",
 "  YANIT 401 /kullanim/ozet?gun=7","ISTEK POST /kimlik/yenile",
 "  YANIT 401 /kullanim/zaman-serisi?gun=7&kirilim=bdm","  YANIT 200 /kimlik/yenile",
 "ISTEK GET /kullanim/ozet?gun=7","ISTEK GET /kullanim/zaman-serisi?gun=7&kirilim=bdm",
 "  YANIT 403 /kullanim/zaman-serisi?gun=7&kirilim=bdm","  YANIT 403 /kullanim/ozet?gun=7"]
sonrasi: {"url":"/kullanim","anahtarlar":["kutyai.erisim_jetonu","kutyai.yenileme_jetonu"]}   # oturum korundu, yenileme jetonu rotasyona uğradı
```

- Sonuç: GEÇTİ (tek `/kimlik/yenile`, istek tekrarı, döngü yok, oturum düşmüyor)

### 9) 401 yenileme — bozuk yenileme jetonu (tarayıcı + CDP ağ izleme)

- Beklenen: tek `/kimlik/yenile` denemesi, oturumun temizlenmesi ve `/giris`'e yönlenme.
- Gerçek çıktı:

```
{"sonrasi":{"url":"http://localhost:3000/giris","anahtarlar":[],"govde":"KutyAI\n\n... Giriş yap ..."},
 "olaylar":["ISTEK GET http://localhost:8107/api/v1/kimlik/ben","YANIT 401 http://localhost:8107/api/v1/kimlik/ben",
            "ISTEK POST http://localhost:8107/api/v1/kimlik/yenile","YANIT 401 http://localhost:8107/api/v1/kimlik/yenile"]}
```

- Sonuç: GEÇTİ

### 10) Oturumsuz korumalı rota davranışı (tarayıcı)

- Beklenen: `/sohbet`, `/hesap`, `/kullanim`, `/` → `/giris`.
- Gerçek çıktı:

```
{"oturumsuz_sohbet":"/giris","oturumsuz_hesap":"/giris","oturumsuz_kullanim":"/giris",
 "kok":"{\"yol\":\"/giris\",\"metin\":\"KutyAI\\n\\n... Giriş yap ...\"}"}
```

- Sonuç: GEÇTİ

### 11) `/sohbet` yer tutucu denetimi (tarayıcı + kaynak)

- Beklenen: sahte çalışan sohbet taklidi olmaması; dalga 2 kapsamı.
- Gerçek çıktı (`onuc/app/sohbet/page.tsx:13-34` statik kart, hiçbir `/sohbet*` uç çağrısı yok; tarayıcı metni):

```
"Sohbet yakında\n\nModel seçimi, akışlı yanıtlar ve konuşma geçmişi sonraki sürümde bu ekranda açılacak. ..."
ağ: yalnız GET /kimlik/ben (Korumali oturum denetimi); POST /sohbet*, /sohbet/akis çağrısı yok
```

- Sonuç: GEÇTİ — `/sohbet` ve `/sohbet/[id]` (spec §12.1), model seçici, SSE, konuşma geçmişi **Dalga 2 kapsamı**; bu dalgada yer tutucu ve sözleşme dışı davranış yok.

### 12) Erişilebilirlik DOM denetimi (7 rota, gerçek DOM)

Denetlenen: `input/select/textarea` → `labels`/`label[for]` bağı, `aria-describedby`/`aria-labelledby` hedeflerinin varlığı, pozitif `tabindex`, giriş odak sırası.

```
"/hesap":        {"alanSayisi":0,"sorunlar":[],"tabSirasi":["a:KutyAI","a:Sohbet","a:Kullanım","a:Hesap","button:Çıkış"]}
"/kullanim":     {"alanSayisi":0,"sorunlar":[],"tabSirasi":[...,"button:Son 7 gün","button:Son 30 gün","button:Son 90 gün"]}
"/sohbet":       {"alanSayisi":0,"sorunlar":[],"tabSirasi":[...,"a:Kullanımı görüntüle","a:Hesabım"]}
"/kayit":        {"alanSayisi":4,"sorunlar":[],"tabSirasi":["a:KutyAI","input:ad_soyad","input:eposta","input:parola","input:parola_tekrar","button:Hesap oluştur","a:Giriş yapın"]}
"/dogrula":      {"alanSayisi":1,"sorunlar":[],"tabSirasi":["a:KutyAI","input:jeton","button:Doğrula","a:Giriş sayfasına dön"]}
"/sifre-sifirla":{"alanSayisi":1,"sorunlar":[],"tabSirasi":["a:KutyAI","button:Bağlantı iste","button:Jetonla sıfırla","input:eposta","button:Sıfırlama bağlantısı g","a:Giriş sayfasına dön"]}
```

Klavye ile gerçek Tab sırası (`/giris`): `a:KutyAI → input:eposta → input:parola → button:Giriş yap → a:Parolamı unuttum → a:Kayıt olun → [nextjs-portal (yalnız geliştirme)] → body`.

- Sonuç: GEÇTİ (etiket bağı eksik alan yok, kırık `aria-describedby` yok, pozitif `tabindex` yok, sıra mantıklı)

### 13) Odak göstergesi denetimi (CDP `Emulation.setFocusEmulationEnabled`, 7 rota)

- Beklenen (spec §12.3): kenarlık-odaklı görünür odak göstergesi.
- Gerçek çıktı (odak öncesi/sonrası hesaplanan stil farkı olmayanlar):

```
/giris:         ["a:Parolamı unuttum","a:Kayıt olun"]
/kayit:         ["a:Giriş yapın"]
/dogrula:       ["a:Giriş sayfasına dön"]
/sifre-sifirla: ["a:Giriş sayfasına dön"]
/sohbet, /kullanim, /hesap: []
```

Örnek fark (odaklanınca gerçekten değişenler): `a:Sohbet` → `border: rgba(0,0,0,0) -> oklch(0.205 0 none)`.
Etkin nav bağlantısında (`/kullanim` sayfasındaki "Kullanım") odak öncesi/sonrası **görünür fark yok**: `border` zaten `oklch(0.205 0 none)`, tek değişen `--tw-ring-shadow` (0 genişlikte, görünmez).

- Sonuç: KALDI (MINOR bulgular 2 ve 3)

### 14) Mobil görünüm (viewport 390×844, deviceScaleFactor 2)

- Beklenen: yatay taşma/kırpılma yok.
- Gerçek çıktı:

```
/giris:        {"icGenislik":390,"belgeGenislik":390,"yatayTasma":false,"tasanlar":[]}
/kayit:        {"icGenislik":390,"belgeGenislik":390,"yatayTasma":false,"tasanlar":[]}
/dogrula:      {"icGenislik":390,"belgeGenislik":390,"yatayTasma":false,"tasanlar":[]}
/sifre-sifirla:{"icGenislik":390,"belgeGenislik":390,"yatayTasma":false,"tasanlar":[]}
/sohbet:       {"icGenislik":390,"belgeGenislik":390,"yatayTasma":false,"tasanlar":[]}
/kullanim:     {"icGenislik":390,"belgeGenislik":390,"yatayTasma":false,"tasanlar":[]}
/hesap:        {"icGenislik":390,"belgeGenislik":390,"yatayTasma":false,"tasanlar":[]}
```

Ekran görüntüleri: `kaynak/testler/kanit/mobil-giris.png`, `mobil-kayit.png`, `mobil-dogrula.png`, `mobil-sifre-sifirla.png`, `mobil-sohbet.png`, `mobil-kullanim.png`, `mobil-hesap.png` (PNG üstbilgisi: yedisi de 390×844). Görsel doğrulama sorgusu (`mobil-giris.png`, `mobil-kullanim.png`): "taşma, kırpılma veya üst üste binme bulunmuyor".

- Sonuç: GEÇTİ

### 15) Tasarım sözleşmesi taraması (kaynak + derlenmiş CSS + hesaplanan stil)

Kaynak (`grep -rnE "sm:|gradient|purple|violet|indigo|blur"` → `onuc/app`, `onuc/components`, `onuc/lib`): **hiç eşleşme yok**.

`python kaynak/testler/betikler/css_tara.py http://localhost:3000/_next/static/css/app/layout.css` (geliştirme CSS'i):

```
  sm_breakpoint_40rem: 0 eslesme
  sm_onekli_sinif: 0 eslesme
  gradyan: 3 eslesme -> ['gradient', 'gradient', 'gradient']
  purple_violet_indigo: 0 eslesme
  blur_backdrop: 0 eslesme
  md_breakpoint_48rem: 0 eslesme
  medya_sorgulari: ['@media (hover: hover)', '@media (prefers-reduced-motion: reduce)', '@media (width >= 48rem)']
```

`python kaynak/testler/betikler/css_tara.py kaynak/testler/gecici/ecb72ce630c80134.css` (üretim derlemesi, `onuc/.next/static/css/` kopyası):

```
  sm_breakpoint_40rem: 0 eslesme
  sm_onekli_sinif: 0 eslesme
  gradyan: 3 eslesme -> ['gradient', 'gradient', 'gradient']
  purple_violet_indigo: 0 eslesme
  blur_backdrop: 0 eslesme
  md_breakpoint_48rem: 1 eslesme -> ['min-width:48rem']
  medya_sorgulari: ['@media (hover:hover)', '@media (min-width:48rem)', '@media (prefers-reduced-motion:reduce)']
```

`gradient` eşleşmelerinin bağlamı (üçü de Tailwind `transition-colors` yardımcı sınıfının özel değişken listesi, gerçek gradyan değil):

```
'.transition-colors{transition-property:color,background-color,border-color,outline-color,text-decoration-color,fill,stroke,--tw-gradient-from,--tw-gradient-via,--tw-gradient-to;...'
```

`backdrop` eşleşmeleri yalnız Tailwind taban sıfırlamasındaki `::backdrop` seçicisi (`backdrop-filter`/`blur` yok):

```
'@layer base{*,::backdrop,:after,:before{box-sizing:border-box;border:0 solid;margin:0;padding:0}'
```

Odak kuralları (üretim CSS'i):

```
  .focus\:border-neutral-900:focus{border-color:var(--color-neutral-900)}
  .focus\:ring-0:focus{--tw-ring-shadow:var(--tw-ring-inset,) 0 0 0 calc(0px + var(--tw-ring-offset-width)) ...}
```

Hesaplanan stil taraması (7 rota, tüm elemanlar): `gradient`/`backdrop-filter`/`blur(` içeren eleman sayısı **0**.

- Sonuç: GEÇTİ (`sm:` yok, yalnız `md:` 48rem; gradyan/purple/violet/indigo/glassmorphism yok; odak kenarlık odaklı, `focus:ring-0` ile halka sıfır genişlikte)

### 16) `npm run build`

- Beklenen: hatasız derleme, 11 statik sayfa.
- Gerçek çıktı (`kaynak/testler/gecici/onuc-build.txt`):

```
> kutyai-onuc@0.1.0 build
> next build

   ▲ Next.js 15.5.25

   Creating an optimized production build ...
 ✓ Compiled successfully in 1359ms
   Linting and checking validity of types ...
   Collecting page data ...
   Generating static pages (0/11) ...
 ✓ Generating static pages (11/11)
   Finalizing page optimization ...
   Collecting build traces ...

Route (app)                                 Size  First Load JS
┌ ○ /                                      123 B         103 kB
├ ○ /_not-found                            992 B         104 kB
├ ○ /dogrula                             3.61 kB         119 kB
├ ○ /giris                               3.34 kB         118 kB
├ ○ /hesap                               1.34 kB         120 kB
├ ○ /kayit                               4.43 kB         120 kB
├ ○ /kullanim                            1.86 kB         120 kB
├ ○ /sifre-sifirla                       4.19 kB         119 kB
└ ○ /sohbet                                859 B         119 kB
+ First Load JS shared by all             103 kB
○  (Static)  prerendered as static content
EXIT=0
```

- Sonuç: GEÇTİ

### 17) `npx tsc --noEmit`

- Beklenen: çıktı yok, çıkış kodu 0.
- Gerçek çıktı (`kaynak/testler/gecici/onuc-tsc.txt`, 0 bayt):

```
EXIT=0
```

- Sonuç: GEÇTİ

### 18) `python kaynak/testler/betikler/kullanim_yetki.py`

- Beklenen: API.md §13 uçlarının son kullanıcı için erişilebilir olması.
- Gerçek çıktı:

```
POST /kimlik/giris -> 200
giris rolu: son_kullanici
GET /kullanim/ozet?gun=30 -> 403 {"hata":{"kod":"yetki_yok","mesaj":"Bu işlem için yetkiniz yok.","ayrinti":{}}}
GET /kullanim/zaman-serisi?gun=30&kirilim=bdm -> 403 {"hata":{"kod":"yetki_yok","mesaj":"Bu işlem için yetkiniz yok.","ayrinti":{}}}
GET /kimlik/ben -> 200 {"id":2,"eposta":"goz.onuc.2@ornek.com","ad_soyad":"Göz Onuç","rol":"son_kullanici","durum":"aktif","eposta_dogrulandi":true,...}
```

Tarayıcı karşılığı (`/kullanim` ziyareti):

```
{"url":"/kullanim","anahtarlar":["kutyai.erisim_jetonu","kutyai.yenileme_jetonu"],
 "metin":"KutyAI\nSohbet\nKullanım\nHesap\nÇıkış\n\nKullanım\n\nİstek, token ve gecikme özetiniz.\n\nSon 7 gün\nSon 30 gün\nSon 90 gün\n\nBu işlem için yetkiniz yok."}
```

- Sonuç: KALDI (bulgu 1)

### 19) Konsol/çalışma zamanı hata taraması (tarayıcı, 7 rota gezintisi)

- Gerçek çıktı:

```
{"yol":"http://localhost:3000/kullanim","kayitSayisi":4,
 "kayitlar":["ERROR: Failed to load resource: the server responded with a status of 403 (Forbidden)","... (4 kez, hepsi /kullanim uçları)"]}
```

React hidrasyon uyarısı, `pageerror` veya başka konsol hatası yok.

- Sonuç: GEÇTİ (403'ler bulgu 1'in sonucu)

### 20) `/sifre-sifirla` akışı (tarayıcı)

- Beklenen (API.md §5): bağlantı isteği mesajı, `gelistirme_baglantisi` varsa jetonla sıfırlama, ardından yeni parolayla giriş.
- Gerçek çıktı:

```
istek_sonucu: "E-posta adresiniz kayıtlıysa parola sıfırlama bağlantısı gönderildi."  (ekranda görünür yönlendirme yok)
"Jetonla sıfırla" sekmesindeki jeton alanı otomatik doldu: uzunluk 43
POST /kimlik/sifre-sifirla sonrası: {"alertler":["Parolanız güncellendi. Yeni parolanızla giriş yapabilirsiniz."]}
yeni parolayla /giris -> /sohbet (200)
```

- Sonuç: GEÇTİ (MINOR bulgu 4 ile birlikte)

---

## Bulgular

### 1) [BLOCKER] `/kullanim` sayfası son kullanıcı için hiçbir zaman veri gösteremiyor

- Yer: `onuc/app/kullanim/page.tsx:36-37` (iki uç çağrısı) — kök neden sınırında: `arkauc/app/api/kullanim.py:30` ve `:42` (`Depends(gecerli_personel())`) + `arkauc/app/api/kimlik.py:111-112` (`/kimlik/giris` yalnız `son_kullanici`).
- Sorun: `/kullanim/ozet` ve `/kullanim/zaman-serisi` personel rolleriyle sınırlı (`PERSONEL_ROLLERI = ['yonetici','operator','izleyici']`), ancak `onuc`'a giriş yapabilen tek rol `son_kullanici` (`/kimlik/giris` diğer roller için `403`). Dolayısıyla spec §12.1'de `onuc` sayfası olarak listelenen `/kullanim` her zaman "Bu işlem için yetkiniz yok." gösterir.
- Beklenen davranış: son kullanıcı kendi kullanım özetini/zaman serisini görebilmeli (API.md §13, spec §12.1) ya da sayfa `onuc` kapsamından çıkarılmalı.
- Yeniden üretme: `goz.onuc.2@ornek.com` ile `/giris` → `/kullanim` aç → ekranda `Bu işlem için yetkiniz yok.`; ağ: `403 yetki_yok` (bkz. komut 18). Düzeltme yeri modüller arası (arka uç yetkisi veya arayüz kapsamı) — kontrolör kararı gerekir.

### 2) [MINOR] Bazı bağlantılarda görünür odak göstergesi yok

- Yer: `onuc/app/(auth)/giris/page.tsx:104` ("Parolamı unuttum"), `:109` ("Kayıt olun"), `onuc/app/(auth)/kayit/page.tsx:151` ("Giriş yapın"), `onuc/app/(auth)/dogrula/page.tsx:130` ve `onuc/app/(auth)/sifre-sifirla/page.tsx:206` ("Giriş sayfasına dön"); kök neden `onuc/app/globals.css:54` (`*:focus-visible { outline: none; }`) — bu bağlantılarda `focus:border-*` sınıfı yok.
- Sorun: Klavye ile gezinirken bu bağlantılarda hiçbir görsel odak değişimi oluşmuyor (WCAG 2.4.7 Focus Visible ihlali; spec §12.3 "kenarlık-odaklı focus" beklentisi).
- Beklenen davranış: her odaklanabilir öğede görünür kenarlık/çizgi değişimi.
- Yeniden üretme: `Emulation.setFocusEmulationEnabled` ile `/giris` aç, Tab ile "Parolamı unuttum"/"Kayıt olun" bağlantısına gel → odak öncesi/sonrası hesaplanan stil aynı (komut 13).

### 3) [MINOR] Etkin menü bağlantısında odak göstergesi kayboluyor

- Yer: `onuc/components/uygulama-kabugu.tsx:63-73` (etkin bağlantıda `border-neutral-900` zaten sabit, satır 70).
- Sorun: `/kullanim` (veya etkin olan menü) bağlantısı odaklandığında `border` rengi zaten `oklch(0.205 0 none)` olduğu için görünür değişim yok; tek fark 0 genişlikteki `--tw-ring-shadow`.
- Beklenen davranış: odakta etkin durumdan ayırt edilebilir bir gösterge.
- Yeniden üretme: `/kullanim` aç → "Kullanım" bağlantısına Tab ile gel → komut 13 çıktısı.

### 4) [MINOR] `/sifre-sifirla`: geliştirme bağlantısı sessizce dolduruluyor, kullanıcıya yönlendirme yok

- Yer: `onuc/app/(auth)/sifre-sifirla/page.tsx:56-59` (`baglantidanJeton(yanit.gelistirme_baglantisi)` → `setJeton`).
- Sorun: SMTP tanımsızken API `gelistirme_baglantisi` döner; sayfa jetonu gizli alana yazıyor ama ekranda ne "e-posta gönderilmedi" bilgisi ne de "jeton dolduruldu" yönlendirmesi var. `/kayit` sayfası aynı durumu açıkça anlatıyor (`Bu ortamda e-posta gönderimi tanımlı değil; doğrulamayı bağlantıyla tamamlayabilirsiniz.`). Kullanıcı "Jetonla sıfırla" sekmesine geçmediği sürece akış çıkmazda kalıyor.
- Beklenen davranış: kayıt sayfasındaki gibi görünür bilgi veya otomatik sekme geçişi.
- Yeniden üretme: `/sifre-sifirla` → kayıtlı e-posta ile "Sıfırlama bağlantısı gönder" → mesaj jenerik; "Jetonla sıfırla" sekmesine geç → jeton alanı 43 karakterle dolu (komut 20).

---

## Özet

4 bulgu (1 BLOCKER, 0 MAJOR, 3 MINOR).

- BLOCKER: `onuc` `/kullanim` sayfası, `onuc`'a girebilen tek rolle (`son_kullanici`) arka ucun personel zorunluluğu yüzünden hiç veri gösteremiyor (`403 yetki_yok`) — düzeltme modüller arası karar gerektiriyor.
- Dalga 2 kapsamı olarak loglandı: `/sohbet` yer tutucu (sahte sohbet davranışı yok) ve `/sohbet/[id]` rotası henüz yok.

Kanıt dizinleri: `kaynak/testler/betikler/` (betikler), `kaynak/testler/gecici/` (üretim CSS kopyası, build/tsc çıktıları, geçici DB), `kaynak/testler/kanit/mobil-*.png` (ekran görüntüleri).
