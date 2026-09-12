# Spec uyum raporu — 2026-09-12

Kapsam: backend (`arkauc/`, `bdm_*`). Bağlayıcı sözleşme: `kaynak/API.md` §1–§14;
tasarım referansı: `kaynak/spec/2026-09-12-kutyai-bdm-platformu-tasarim.md`.
`onuc/`, `yonetim_paneli/`, `dagitim/` bu raporun dışındadır.

## Yöntem

1. Uygulama gerçekten oluşturuldu ve rotalar OpenAPI'den döküldü:
   `./.venv/Scripts/python.exe -c "from arkauc.app.main import app; app.openapi()"`.
   Sonuç: 46 yol / 56 operasyon; `docs`, `openapi.json`, `oauth2-redirect` dışında
   **56 ürün operasyonu**. API.md §1–§14'te tanımlı operasyon sayısı **55**
   (§3:3, §4:1, §5:9, §6:4, §7:3, §8:7, §9:6, §10:4, §11:8, §12:5, §13:3, §14:2).
2. Her ucun yanıt alan adları, gövde modelleri ve durum kodları kodla birebir
   karşılaştırıldı (serileştiriciler: `bdm_sozlugu`, `bdm_ozeti`, `kullanici_sozlugu`,
   `_sozluk`, `saglayici_listesi`, `_etkin_ayarlar`).
3. Her ucun `Depends(...)` satırı okunarak yetki matrisi çıkarıldı.
4. API.md §1 hata tablosundaki 20 kod repo genelinde tarandı; ters yönde
   (tabloda olmayan kod) tarama da yapıldı.
5. Spec §7.4 (SSE sırası), §7.5, §10 (GPU), §11 (güvenlik/KVKK) maddeleri kodda
   karşılığıyla eşleştirildi.
6. Gözlem loglarındaki (`kaynak/testler/*-log.md`) tüm BLOCKER/MAJOR bulgular
   ilgili kod satırları okunarak kapanış denetiminden geçirildi.

## Bulgular

### BLOCKER

- [BLOCKER] `arkauc/app/cekirdek/hatalar.py:124-127` (+ `arkauc/app/cekirdek/ayarlar.py:47`,
  `arkauc/app/main.py:82-88`) — **Oran sınırı hiç uygulanmıyor; `oran_siniri` kodu
  üretilemez.** — Beklenen: spec §11 "Oran sınırı: kullanıcı/anahtar/IP başına
  dakikalık istek; bellek içi kayan pencere" ve spec §5 `ORAN_SINIRI_ISTEK/DK=60`;
  API.md §1 429 satırında `oran_siniri` bağlayıcı sözleşme kodudur.
  — Kanıt: `OranSiniri` sınıfı yalnız tanımlı ve `_HTTP_KODLARI` (`hatalar.py:154-162`)
  eşlemesinde geçiyor; repo genelinde bu sınıfı `raise` eden, `import` eden ya da
  okuyan **tek bir çağrı yok**. `main.py:82-88` yalnız `CORSMiddleware` kuruyor;
  `/sohbet` (`sohbet.py:235-247`) ve `/sohbet/akis` (`sohbet.py:311-323`) zincirinde
  limit adımı yok (yalnız `_bakim_denetimi` → `_bdm_coz` → `_kota_denetle`).
  `oran_siniri_istek_dk` ayarı hiçbir yerde okunmuyor. Sonuç: `/kimlik/giris`
  üzerinde sınırsız parola denemesi ve `/sohbet` üzerinde sınırsız istek mümkün;
  API.md'nin 429 `oran_siniri` kodu erişilemez durumda — tek erişilebilir 429
  günlük/aylık kotadır (`servisler/kota.py:135-158`), o da kayan pencere değildir.

### MAJOR

- [MAJOR] `bdm_konusma_gecmisi/maskeleme.py:42-43` (+ `arkauc/app/api/ayarlar.py:31,54-56`,
  `bdm_veritabani/tohum.py:20`) — **`maskeleme_aktif` ayarı iki farklı kaynaktan
  okunuyor; panelin yönettiği anahtar etkisiz.** — `PUT /ayarlar` `{maskeleme_aktif}`
  değerini `ayar` tablosuna yazıyor (`ayarlar.py:31`) ve `GET /ayarlar` bu DB değerini
  raporluyor (`ayarlar.py:54-56`), ancak maskeleme motoru DB'ye bakmıyor:
  `maskeleme.py:42-43` `if not ayarlar.maskeleme_aktif: return metin` — ortam
  değişkenini (`KUTYAI_MASKELEME_AKTIF`) okuyor. Beklenen: API.md §14'te tanımlı
  ayarın davranışı belirlemesi.
  — Kanıt: `KUTYAI_MASKELEME_AKTIF=false` iken DB'de `maskeleme_aktif=true` kalır
  (varsayılan, `tohum.py:20`); panel "maskeleme aktif" gösterirken kullanıcı mesajı
  `yazici.py:74` erken dönen `maskele_metin` yüzünden hem veritabanına hem sağlayıcıya
  **ham** gider — API.md §9'daki maskeleme sınırı ve spec §11 "maskeleme kayıt anında
  uygulanır" maddesi ihlal edilir. Ters yönde (env açık, panelden kapatma) ayar yine
  etkisizdir: panelde kapatılan maskeleme kapanmaz.

- [MAJOR] `arkauc/app/main.py:60-73` (+ `bdm_konusma_gecmisi/saklama.py:14-27`) —
  **Günlük zamanlanmış saklama görevi yok.** — Beklenen: spec §11 "Saklama:
  `saklama_gun` sonrası `POST /loglar/temizle` **ve günlük zamanlanmış görev** siler".
  — Kanıt: `_yasam_dongusu` yalnız `ayarlar.dogrula()`, `tablolari_olustur()`,
  `tohumla()` çağırıyor; `arkauc/`, `bdm_*` ve `requirements.txt` genelinde
  `apscheduler|scheduler|create_task|gecelik` araması **sıfır** sonuç veriyor.
  `eski_konusmalari_sil` tek çağrı yeri `arkauc/app/api/loglar.py:205` (elle
  `POST /loglar/temizle`). Sonuç: saklama süresi yalnız yönetici elle çalıştırırsa
  uygulanır; aksi halde konuşma kayıtları (maskeli de olsa KVKK kapsamındaki veri)
  süresiz birikir.

- [MAJOR] `bdm_hazırlama_ucu/cekim.py:76-81` (+ `bdm_hazırlama_ucu/uc.py:118-127`) —
  **`POST /{id}/cek` yalnız Ollama yolunu destekliyor; vllm/tgi için HF snapshot yolu yok.**
  — Beklenen: spec §7.5 "`POST /{bdm_id}/cek` (SSE ilerleme; **Ollama pull / HF snapshot**)".
  — Kanıt: `cek_destegi_denetle` (`cekim.py:76-81`) Ollama dışındaki her sağlayıcıda
  `GecersizIstek` fırlatıyor (`DESTEKLENMEYEN_MESAJ = "Bu sağlayıcı için model indirme
  desteklenmiyor."`); `cek_akisi` yalnız `{temel}/api/pull` (Ollama) NDJSON akışını
  çeviriyor. GPU'lu makinede vllm BDM'i için `/cek` → 400 `gecersiz_istek`
  (GPU'suzda önce 503 `surucu_yok`). Panelin "Hazırlama" sekmesi bu iki sağlayıcıda
  model indiremiyor. `hazirlama-log.md` MINOR-5 olarak kayıtlıydı ve **kapatılmamış**.

### MINOR

- [MINOR] `arkauc/app/cekirdek/hatalar.py:154-162` + `:182-184` — **Tabloda olmayan
  hata kodları üretiliyor.** — `_HTTP_KODLARI` 405 için `yontem_izinli_degil`, eşlemede
  olmayan durum kodları için `http_hatasi` üretiyor; API.md §1 tablosunda 405 satırı yok
  ve bu iki kod hiçbir satırda geçmiyor. — Kanıt: `GET /api/v1/kimlik/giris` →
  `405 {"hata":{"kod":"yontem_izinli_degil",...}}`. Tablo dışı kod, sözleşmeye göre
  istemci hata eşlemesini bozar (istemciler kod-odaklı dallanıyor).

- [MINOR] `arkauc/app/api/loglar.py:92-93` — **Sözleşmede tanımsız uç:
  `GET /api/v1/islem-kayitlari`.** — API.md §1–§14'te bu uç yok; 55 sözleşme
  operasyonunun tamamı mevcutken 56. operasyon budur. — Kanıt: OpenAPI dökümü
  `GET /api/v1/islem-kayitlari` döndürüyor; spec §12.2 panel sayfası olarak
  `/islem-kayitlari` listeliyor, yani uç bilinçli eklenmiş ama bağlayıcı sözleşmeye
  (API.md) yazılmamış — alan/uç envanterinin API.md'de eksiksiz olması gerekir.

- [MINOR] `bdm_listesi/sema.py:25,47` (+ `bdm_listesi/katalog.py:161-166`) —
  **`yetenekler` kısmi sözlükle yazılabiliyor; yanıt tipi sözleşmeyi ihlal edebiliyor.**
  — `BdmOlustur`/`BdmGuncelle` `yetenekler: dict[str, bool] | None` kabul ediyor;
  `bdm_guncelle` gelen sözlüğü doğrulamadan `setattr` ediyor (`katalog.py:166`).
  `PATCH /bdm/{id}` `{"yetenekler": {"akis": false}}` gövdesinden sonra
  `Bdm.yetenekler` yalnız `{akis:false}` olur ve `katalog.py:80` bunu olduğu gibi
  döndürür. — Beklenen: API.md §2 `yetenekler: { akis: boolean; gorsel: boolean;
  arac: boolean }`; tip tanımlı istemcide `yetenekler.gorsel` `undefined` olur.

- [MINOR] `bdm_yönetim_ucu/uc.py:130-137` (+ `bdm_yönetim_ucu/yasam_dongusu.py:84-93`) —
  **`PATCH /{id}/yol` alanları yazılıyor ve döndürülüyor ama hiçbir tüketici okumuyor.**
  — `takma_ad`/`oncelik` `bdm.konteyner["yol"]` altına yazılıyor (API.md §2'deki
  `yol?: { takma_ad?, oncelik? }` biçimiyle uyumlu) ve `baslat`/`yeniden-baslat`
  sonrasında korunuyor; ancak repo genelinde `yol`/`takma_ad`/`oncelik` okuyan başka
  bir kod yok — `sohbet.py:103-109` modeli yalnız `bdm_id`/`bdm_slug` ile çözüyor,
  `servisler/upstream.py:44-45` adresi `bdm.temel_url`'den kuruyor. — Spec §7.6 bu ucu
  "alias/öncelik" olarak tanımladığı için alan bir alias yönlendirmesi beklenir; şu
  haliyle uç yalnız veri saklar (uç nokta ve alan adları sözleşmeye uygundur).

## Yetki matrisi

Kaynak: her ucun `Depends(...)` satırı + `PERSONEL_ROLLERI = (yonetici, operator, izleyici)`
(`bdm_veritabani/modeller.py:39`); yazma uçlarında `izleyici` → 403 `yetki_yok`.

| Uç | API.md yetki | Koddaki bağımlılık | Durum |
|---|---|---|---|
| `GET /saglik`, `/saglik/hazir`, `/saglik/kurulum` | açık | yok | ✅ |
| `POST /kurulum` | açık (`kurulum_tamam=false`) | yok + kilit/ayar denetimi (`kurulum.py:128-134`) | ✅ |
| `POST /kimlik/kayit` | açık | yok (+`kayit_acik`, `kimlik.py:150`) | ✅ |
| `POST /kimlik/dogrula`, `/giris`, `/panel-giris`, `/yenile`, `/sifre-sifirlama-iste`, `/sifre-sifirla` | açık | yok | ✅ |
| `POST /kimlik/cikis`, `GET /kimlik/ben` | kimlikli (spec §7.1) | `gecerli_kullanici` | ✅ |
| `/kullanicilar*` | yönetici | `gecerli_personel((yonetici,))` | ✅ |
| `/api-anahtarlari*` | yönetici/operatör | `gecerli_personel((yonetici, operator))` | ✅ |
| `GET /modeller` | kimlikli | `gecerli_istemci` | ✅ |
| `GET /saglayicilar` | açık | yok | ✅ |
| `GET /bdm` | personel | `gecerli_personel()` | ✅ |
| `POST/PATCH /bdm` | yönetici/operatör | `gecerli_personel((yonetici, operator))` | ✅ |
| `POST /bdm/{id}/kopyala`, `DELETE /bdm/{id}` | yönetici | `gecerli_personel((yonetici,))` | ✅ |
| `/sohbet`, `/sohbet/akis`, `/sohbet/konusmalar*` | `gecerli_istemci` | `gecerli_istemci` | ✅ |
| `/bdm/hazirlama/*` (4) | personel | `gecerli_personel()` (`uc.py:92,116,133,147`) | ✅ |
| `/bdm/yonetim/*` (8) | personel | `gecerli_personel()` (`uc.py:35,46,58,70,83,94,106,126`) | ✅ |
| `GET /loglar/konusmalar`, `/loglar/konusmalar/{id}`, `/disa-aktar` | personel | `gecerli_personel()` (`loglar.py:76,101,153,165`) | ✅ |
| `DELETE /loglar/konusmalar/{id}` | yönetici/operatör | `gecerli_personel(YAZMA_ROLLERI)` (`loglar.py:182`) | ✅ |
| `POST /loglar/temizle` | yönetici | `gecerli_personel((yonetici,))` (`loglar.py:202`) | ✅ |
| `GET /kullanim/ozet`, `/zaman-serisi` | personel | `gecerli_personel()` | ✅ |
| `GET /kullanim/benim` | `gecerli_istemci` | `gecerli_istemci` (`kullanim.py:75-80`) | ✅ |
| `GET/PUT /ayarlar` | yönetici | `gecerli_personel((yonetici,))` | ✅ |
| `GET /islem-kayitlari` | (sözleşmede yok) | `gecerli_personel()` | — |

Ek: `gecerli_istemci` API anahtarında `izinli_modeller` süzgecini uygular
(`sohbet.py:114-116`, `katalog.py:262-270`); `son_kullanici` + `eposta_dogrulanmadi` →
403 (`bagimliliklar.py:133-135`); `durum=pasif` kullanıcı → 403 (`bagimliliklar.py:76-77`).

## Hata kodları (API.md §1)

- Tablodaki 20 koddan **19'u üretiliyor**: `gecersiz_istek`, `dogrulama_hatasi`,
  `kimlik_gerekli`, `jeton_gecersiz`, `jeton_suresi_doldu`, `anahtar_gecersiz`,
  `gecersiz_kimlik_bilgisi` (`servisler/kimlik.py:57-62`), `yetki_yok`,
  `eposta_dogrulanmadi`, `bulunamadi`, `cakisma`, `gecersiz_gecis`,
  `kurulum_zaten_tamam` (`api/kurulum.py:128-134`), `kota_asildi`
  (`servisler/kota.py:147,152`), `ust_saglayici_hatasi` (`servisler/upstream.py:107-122`),
  `bdm_hazir_degil`, `surucu_yok`, `veritabani_yok` (`api/sistem.py:39-41`),
  `sunucu_hatasi`.
- **Üretilmeyen tek kod: `oran_siniri`** (bkz. BLOCKER).
- Tabloda olmayan üretilen kodlar: `yontem_izinli_degil` (405) ve `http_hatasi`
  (eşleme dışı `HTTPException` durumları).
- Zarf biçimi birebir: `hatalar.py:48-49` `{"hata": {"kod", "mesaj", "ayrinti"}}`;
  `RequestValidationError` → 400 `dogrulama_hatasi` (`hatalar.py:172-177`); 500
  `sunucu_hatasi` gövdesi traceback sızdırmıyor (yalnız `logger.exception`).

## Spec maddeleri

**§7.4 SSE sırası — ✅** `servisler/akış.py:71-77,100-103,134`: `baslangic` → `parca`*
→ `kullanim` → `bitti`; hata yollarında (`except KutyaiHatasi` :85-94,
`except Exception` :95-105, kayıt arızası :118-126) `event: hata` + zarf ve **ardından
her koşulda** `event: bitti`. `media_type="text/event-stream"` (`sohbet.py:348`).
`baslangic` gövdesi `{konusma_id, mesaj_id}`, `parca` `{icerik}`, `kullanim`
`{token_girdi, token_cikti, gecikme_ms}` — API.md §9 ile birebir.
Maskeleme sınırı: `mesaj_ekle` kayıt anında maskeler (`yazici.py:74`), upstream
listesi DB'den okunur (`yazici.py:129-147`), istemciye akan `parca` hamdır (`akış.py:79`).
Bakım modu: `sohbet.py:84-87` → 503 `bdm_hazir_degil`, mesaj "Sistem bakımda." ✅

**§10 GPU yönlendirmesi — ✅** İki bağımsız kapı, sessiz CPU düşüşü yok:
`bdm_hazırlama_ucu/uc.py:35-51` (`/cek`, `/manifest`) ve
`bdm_yönetim_ucu/yasam_dongusu.py:117-119` (`baslat`, `yeniden-baslat`) —
`saglayici_bilgisi(...).gpu_gerekir and not durum.gpu_var` → 503 `surucu_yok`,
Türkçe mesaj spec §10 ile birebir (`yasam_dongusu.py:25-28`). `vllm|tgi`
`gpu_gerekir=True` (`saglayicilar.py:85,99`) ve bu sağlayıcılar `DockerSurucusu`'na
gider (`konteyner.py:141-146`); Docker tarafı GPU isteğini yalnız manifest `gpu=true`
ise ekler (`konteyner_docker.py:165-168`). `GET /{id}/on-kontrol` GPU'suzda 200 +
`uygun=false` + `uyarilar[GPU_UYARI_MESAJI]` döndürür — spec §10'un "panelde uyarı
kartı gösterilir" maddesi bunu gerektirir (503 değil).

**§11 güvenlik — çoğu ✅, iki boşluk (yukarıdaki BLOCKER/MAJOR):** argon2id
`PasswordHasher` (`guvenlik.py:19,25-35`), yeniden-hash kontrolü
(`servisler/kimlik.py:100-105`); e-posta normalizasyonu tek noktada
(`servisler/kimlik.py:70-72`) ve tüm karşılaştırmalarda; API anahtarı `kuty_`+32 base62,
SHA-256 + `onek`(12) + `son_dort`(4) (`guvenlik.py:107-116`); upstream anahtarı
Fernet ile şifreli ve yanıtlarda daima maskeli (`katalog.py:55-63` — `tam_anahtar=True`
çağrısı yok); JWT HS256 `sub/rol/jti/exp` (`guvenlik.py:50-62`); refresh rotasyonu
**atomik** (`servisler/kimlik.py:296-309`: `UPDATE ... WHERE iptal=0` + `rowcount != 1`
→ 401); maskeleme `[MASKELENDI:ad]` kural tablosundan (`maskeleme.py:15-35`);
denetime izi beş kategoride de yazılı (giriş `kimlik.py:122-131`, BDM yaşam döngüsü
`yasam_dongusu.py:135-146`, rol/durum `kullanicilar.py:114-122,141-149`, anahtar
`api_anahtarlari.py:117-125,141-149`, log silme `loglar.py:188-195,207-213`);
CORS yalnız `CORS_KAYNAKLAR` (`main.py:82-88`, `"*"` yok).

**§11 not:** erişim jetonu iptal listesi denetlenmiyor — `jti` yalnız üretiliyor,
`gecerli_kullanici` (`bagimliliklar.py:79-86`) `Oturum.iptal`'e bakmıyor; `iptal`
listesi yalnız yenileme akışında okunuyor (`servisler/kimlik.py:296-309`).
`/kimlik/cikis` sonrası erişim jetonu `exp`'e kadar (varsayılan 15 dk) geçerli kalır;
hesap pasifleştirmesi ise `bagimliliklar.py:76-77` ile anında engellenir. Spec §11
"Refresh rotasyonu + iptal listesi" ifadesi yenileme jetonları için karşılanmıştır;
erişim jetonu için kısa ömür + durum denetimi tercih edilmiştir.

## Gözlem logu kapanış denetimi

`kaynak/testler/*-log.md` içindeki tüm BLOCKER/MAJOR bulguların (23 adet: kimlik 7,
sohbet 3, loglar 3, hazırlama 3, modeller 1, yönetim 4, panel 2) karşılığı kodda okundu.

| Log bulgusu | Düzeltmenin kanıtı | Durum |
|---|---|---|
| kimlik BLOCKER-1 (yenileme yarışı) | `servisler/kimlik.py:296-309` atomik `UPDATE ... iptal=0` + `rowcount` denetimi | ✅ KAPALI |
| kimlik MAJOR-1 (kayıt yarışı 500) | `servisler/kimlik.py:122-135` `IntegrityError` → `Cakisma` | ✅ KAPALI |
| kimlik MAJOR-2/3 (jeton tek kullanım) | `servisler/kimlik.py:355-380` koşullu `UPDATE kullanildi=0` + `rowcount` | ✅ KAPALI |
| kimlik MAJOR-4 (zamanlama sızıntısı) | `servisler/kimlik.py:45-54` sabit maliyetli `zamanlama_dogrulamasi()`; `api/kimlik.py:295-301` her iki dalda | ✅ KAPALI |
| kimlik MAJOR-5 (kendini pasifleştirme/rol düşürme) | `api/kullanicilar.py:99-108` `GecersizGecis` (PATCH), `:131-132` (DELETE) | ✅ KAPALI |
| kimlik MAJOR-6 (`gecersiz_kimlik_bilgisi` tabloda yok) | `kaynak/API.md:22` 401 satırına eklendi (sözleşme güncellendi) | ✅ KAPALI |
| sohbet BLOCKER (upstream rol adları) | `bdm_konusma_gecmisi/yazici.py:22-26,139` `UST_ROL_ADLARI` → `user/assistant` | ✅ KAPALI |
| sohbet MAJOR (`sistem_istemi` maskesiz) | `api/sohbet.py:94-99,130-132,218` | ✅ KAPALI |
| sohbet MAJOR (zarf `ayrinti.govde` sızıntısı) | `servisler/upstream.py:96-122` `ayrinti` yalnız `durum`/`saglayici`; gövde sadece loga | ✅ KAPALI |
| loglar BLOCKER (kurulum TOCTOU) | `api/kurulum.py:131-176` `asyncio.Lock` + kilit içinde taze okuma ve commit | ✅ KAPALI |
| loglar MAJOR (aynı e-posta 500) | `api/kurulum.py:173-179` `IntegrityError` → 409 `cakisma` | ✅ KAPALI |
| loglar MAJOR (izleyici siliyor) | `api/loglar.py:182` `gecerli_personel(YAZMA_ROLLERI)`; API.md §12 satırı da güncellendi | ✅ KAPALI |
| hazırlama BLOCKER-1 (`/cek` gövdesiz kopma) | `bdm_hazırlama_ucu/uc.py:60-73` `_sse` tüm istisnaları zarfa çevirip her durumda `bitti` | ✅ KAPALI |
| hazırlama BLOCKER-2 (`/dogrula` durum makinesini atlıyor) | `bdm_hazırlama_ucu/dogrulama.py:88-95` `calisiyor` durumuna dokunmuyor | ✅ KAPALI |
| hazırlama MAJOR-3 (`InvalidURL` → 500) | `dogrulama.py:29-35,109-116` `ADRES_HATALARI` → Türkçe "adres geçersiz" sonucu | ✅ KAPALI |
| modeller BLOCKER (yetim konuşma) | `katalog.py:205-234` `bdm_sil` konuşma/kullanım sayımı → 409; `oturum.py:41-56` SQLite `PRAGMA foreign_keys=ON` | ✅ KAPALI |
| modeller MINOR (`?arama=`) | `kaynak/API.md:127` `?arama=` belgelendi | ✅ KAPALI |
| yönetim BLOCKER (yerel `durdur` no-op) | `servisler/konteyner.py:158-172` sürücü örnek önbelleği; `konteyner_yerel.py:113-131` `keep_alive=0` boşaltma | ✅ KAPALI |
| yönetim MAJOR (`saglik`/`gunlukler` varsayılan adres) | `konteyner_yerel.py:48-62` kayıtlı `temel` adresi, `adres_kaynagi` ile bildirilir | ⚠️ KISMİ (süreç yeniden başlarsa `varsayilan`) |
| yönetim MAJOR (`/gunlukler` başlık sonrası kopma) | `bdm_yönetim_ucu/gunlukler.py:60-90` ilk satır ön-alımı; sürücü hatası akış başlamadan 503 | ✅ KAPALI |
| yönetim MAJOR (manifest `saglik_url` yok) | `bdm_hazırlama_ucu/manifest.py:94-102,120` üretiliyor, Docker etiketi/sondasında kullanılıyor | ✅ KAPALI |
| panel BLOCKER (yenileme tekilleştirme) | `yonetim_paneli/lib/api.ts` (çalışma ağacında, commit dışı) — **bu raporun kapsamı dışı** | ➖ kapsam dışı |
| panel MAJOR (`dogrulama` okunmuyor) | `yonetim_paneli/app/kurulum/page.tsx` (çalışma ağacında) — **kapsam dışı** | ➖ kapsam dışı |
| onuc BLOCKER (`/kullanim` 403) | Backend tarafı: `api/kullanim.py:75-127` `GET /kullanim/benim` (`gecerli_istemci`) + API.md §13; istemci `onuc/lib/kullanim.ts:17` bu ucu çağırıyor | ✅ KAPALI |

Kapanmamış BLOCKER **yok**. Tek kısmi kapanış yönetim MAJOR-2'dir: sürücü kaydı
bellekte tutulduğu için süreç yeniden başladığında `temel_url` kaybolur ve varsayılan
adrese düşülür; durum `ayrinti.adres_kaynagi="varsayilan"` ile açıkça bildirildiği için
sessiz bir yanlış cevap değildir. Ayrıca `hazirlama-log.md` MINOR-5 (HF snapshot)
**kapanmamıştır** — yukarıda MAJOR olarak raporlandı.

## Onaylanan noktalar

- **Uç envanteri:** API.md §1–§14'teki 55 operasyonun tamamı mevcut; eksik uç yok.
  Tek fazladan uç `GET /islem-kayitlari` (MINOR).
- **Alan adları birebir:** `erisim_jetonu`/`yenileme_jetonu` (`api/kimlik.py:133-137,252`),
  `tam_anahtar` yalnız `POST /api-anahtarlari` yanıtında (`api_anahtarlari.py:125`),
  `api_anahtari_maskeli`, `guncellenme`, `son_giris` (null olabilir), `Sayfa<T>`
  (`toplam/sayfa/boyut/kayitlar`), `BdmOzet` 8 alanı, `saglayicilar` 10 alanı,
  `/kullanim/benim` iç içe `kota` nesnesi ve `seri`, `/loglar/konusmalar` 8 sözleşme
  alanı, `/bdm/hazirlama` ve `/bdm/yonetim` yanıt anahtarları — hepsi sözleşmedeki
  Türkçe adlarla üretiliyor; İngilizce veya farklı adlı alan yok.
- **Durum kodları:** kurulum 201 (`kurulum.py:127`), kayıt/kullanıcı/BDM/anahtar
  oluşturma 201, silme uçları 204 (`modeller.py:146`, `kullanicilar.py:127`,
  `loglar.py:176`, `sohbet.py:412`), `PATCH`/iptal 200.
- **Geçersiz durum geçişi** → 409 `gecersiz_gecis` (`yasam_dongusu.py:33-48`);
  BDM silme `calisiyor` veya bağlı kayıt varsa 409 (`modeller.py:150-155`,
  `katalog.py:205-234`).
- **BDM listeleri:** `GET /bdm?arama=` görünen ad + slug üzerinde `ilike`
  (`katalog.py:190-200`); `GET /modeller` yalnız `hazir|calisiyor` + anahtarın izinli
  listesi (`katalog.py:262-270`).
- **`/loglar/konusmalar` sayfalama sınırları** `Query(ge=1, le=200)` ile 400
  `dogrulama_hatasi`; `baslangic > bitis` → 400 `gecersiz_istek` (`loglar.py:43-51,63-93`).
- **Dışa aktarım** json/md/csv + `Content-Disposition` (`loglar.py:160-174`,
  `disa_aktarim.py:78-95`); desteklenmeyen biçim 400 `gecersiz_istek`; CSV formül
  enjeksiyonu etkisizleştirilmiş (`disa_aktarim.py:50-58`).
- **`/kullanim/benim` yalnız çağıranın kayıtları:** `_kapsam_kosulu` (`kullanim.py:31-39`)
  anahtar/kullanıcı kapsamına göre filtreler.
- **Ayar güvenliği:** `GET/PUT /ayarlar` yanıtı `smtp_sifre` içermiyor; parola Fernet
  ile şifrelenerek saklanıyor (`ayarlar.py:88-91`).
- **Üretim sırları:** `ORTAM=uretim` ve sır eksikse `ayarlar.dogrula()` uygulamayı
  başlatmıyor (`ayarlar.py:105-111`, `main.py:61`).
- **Ek alanlar (sözleşmeyi bozmaz, bilinçli):** `/manifest` yanıtına `saglik_url`
  (`manifest.py:120`) — Docker sağlık sondası için gerekli ve `yonetim-log.md`
  MAJOR'unun kapanışı; `/sohbet/konusmalar` ve `/loglar/konusmalar` ek alanlar;
  `/gunlukler` SSE `: nabız` yorumu (`gunlukler.py:26`). Hepsi eklemeli (additive),
  mevcut alanları değiştirmiyor.

## Özet

8 bulgu (1 BLOCKER, 3 MAJOR, 4 MINOR).

BLOCKER: Oran sınırı hiç uygulanmamış — `OranSiniri`/`oran_siniri_istek_dk` ölü kod,
API.md §1'in `oran_siniri` kodu hiçbir akışta üretilemiyor ve `/kimlik/giris`
(brute-force) ile `/sohbet` (kaynak tüketimi) sınırsız.
MAJOR: (1) `maskeleme_aktif` ayarı panelde yönetilirken maskeleme motoru ortam
değişkenini okuduğu için ayar etkisiz; (2) günlük zamanlanmış saklama görevi yok;
(3) `/cek` yalnız Ollama yolunu destekliyor, vllm/tgi için HF snapshot yolu yok.
MINOR: sözleşmede tanımsız `GET /islem-kayitlari` ucu; tablo dışı hata kodları
(`yontem_izinli_degil`, `http_hatasi`); `yetenekler` kısmi yazılabiliyor; `/yol`
alanları hiçbir tüketici tarafından okunmuyor.
Gözlem loglarındaki 23 BLOCKER/MAJOR bulgunun tamamı (2'si kapsam dışı istemci
bulgusu) kapalı; kapanmamış BLOCKER yok.
