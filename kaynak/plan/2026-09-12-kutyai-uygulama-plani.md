# KutyAI — Uygulama Planı

> **Ajanlar için:** Bu planı `subagent-driven-development` akışıyla uygula. Her görev kendi klasörüne yazar; çakışma kuralı spec §2'dedir. Adımlar `- [ ]` ile izlenir.

**Hedef:** Kurumsal BDM platformunu uçtan uca çalışır hâle getirmek: kimlik, BDM kataloğu, hazırlama/yönetim uçları, konteyner orkestrasyonu, sohbet akışı + KVKK uyumlu loglama, son kullanıcı ve yönetim arayüzleri, dağıtım.

**Mimari:** Tek FastAPI backend (`arkauc`) + iki Next.js uygulaması (`onuc`, `yonetim_paneli`). BDM yetenekleri kendi klasörlerinde router modülleri olarak yaşar ve `main.py`'deki otomatik keşifle monte edilir — böylece dalga içi paralel geliştirme çakışmaz.

**Yığın:** Python 3.13 · FastAPI · SQLAlchemy 2 async · Alembic · Pydantic v2 · argon2 · PyJWT · cryptography(Fernet) · docker SDK · pytest · Next.js 15 · React 19 · TypeScript · Tailwind v4 · Opensource UI dili.

**Spec:** `kaynak/spec/2026-09-12-kutyai-bdm-platformu-tasarim.md` (tek doğruluk kaynağı)

---

## Dosya yapısı (hedef)

```
E:/kutyai-app
├── pyproject.toml, .gitignore, README.md, .env.ornek
├── bdm_veritabani/
│   ├── __init__.py, modeller.py, oturum.py, tohum.py
│   ├── gocler/env.py, gocler/versions/0001_ilk_sema.py
│   └── kutyai.db                     (SQLite, git'e girmez)
├── bdm_listesi/
│   ├── __init__.py, sema.py, katalog.py, saglayicilar.py, tohum_katalog.json
├── bdm_konusma_gecmisi/
│   ├── __init__.py, yazici.py, maskeleme.py, sorgu.py, disa_aktarim.py, saklama.py
├── bdm_hazırlama_ucu/
│   ├── __init__.py, uc.py, dogrulama.py, cekim.py, manifest.py, on_kontrol.py
├── bdm_yönetim_ucu/
│   ├── __init__.py, uc.py, yasam_dongusu.py, saglik.py, gunlukler.py, surucu_durum.py
├── arkauc/
│   ├── app/main.py
│   ├── app/cekirdek/{ayarlar,hatalar,guvenlik,bagimliliklar,keşif}.py
│   ├── app/servisler/{konteyner,konteyner_docker,konteyner_yerel,upstream,akış,kota,kimlik,posta}.py
│   ├── app/api/{kimlik,kullanicilar,api_anahtarlari,modeller,sohbet,loglar,kullanim,ayarlar,sistem}.py
│   └── testler/{conftest,sahte_ust,sahte_konteyner,test_*}.py
├── onuc/            (Next.js 15)
├── yonetim_paneli/  (Next.js 15)
├── dagitim/{docker-compose.yml,Dockerfile.*,.env.ornek,baslat.ps1,baslat.sh,nginx.conf}
└── kaynak/{spec,plan,testler,*.md}
```

---

## Dalga 0 — Sözleşme (controller tarafından, seri)

Bu dalga **dondurulur**; sonraki hiçbir ajan bu dosyaları değiştirmez.

- [x] `pyproject.toml`, `.gitignore`, `README.md`, `.env.ornek`
- [x] `bdm_veritabani/modeller.py` — spec §4'teki 12 tablonun tamamı
- [x] `bdm_veritabani/oturum.py` — async engine + `oturum_uret()` + `taban_olustur()`
- [x] `bdm_veritabani/tohum.py` — maskeleme kuralları + varsayılan ayarlar + yönetici hesabı
- [x] `arkauc/app/cekirdek/ayarlar.py`, `hatalar.py`, `guvenlik.py`, `bagimliliklar.py`
- [x] `arkauc/app/servisler/konteyner.py` — `KonteynerSurucusu` Protocol + `SahteSurucu` + `SurucuDurumu`/`SaglikDurumu`
- [x] `arkauc/app/api/sistem.py` — `/saglik`, `/saglik/hazir`, `/saglik/kurulum` (Dalga 0'da yazılır; başka ajan dokunmaz)
- [x] `arkauc/app/main.py` — otomatik router keşfi (spec §8)
- [x] `arkauc/testler/conftest.py` — geçici SQLite, `istemci` fikstürü, kimlik yardımcıları
- [x] `kaynak/API.md`, `kaynak/MIMARI.md`, `kaynak/ORKESTRA.md`

**Kabul:** `python -m pytest arkauc/testler -q` → Dalga 0 testleri geçer; `python -c "import bdm_hazırlama_ucu"` çalışır (henüz boş paket).

---

## Dalga 1 — Çekirdek yetenekler (8 paralel uygulayıcı + 8 gözlemci)

Ortak kurallar (her göreve dahil):
- Yalnız kendi dosyalarına yaz. `main.py`, `cekirdek/*`, `bdm_veritabani/*` **dondurulmuş**.
- Testleri `arkauc/testler/` altında `test_<konu>.py` olarak yaz; ayrı test dosyası sahipliği çakışmaz.
- Gözlemci ajan sana ait değildir; testini **bağımsız** yazması için kodu kara kutu kabul et.
- Biçimlendirici/linter çalıştırma; yalnız kendi testini koş.

### T1.1 Kimlik ve kullanıcı uçları
**Dosyalar:** `arkauc/app/servisler/kimlik.py`, `arkauc/app/servisler/posta.py`, `arkauc/app/api/kimlik.py`, `arkauc/app/api/kullanicilar.py`, `arkauc/testler/test_kimlik.py`
**Sözleşme:** spec §7.1, §7.2, §11.
**Gereksinimler:**
- argon2id hash; `kuty_` API anahtarı üretimi/doğrulaması `guvenlik.py`'de hazır.
- `kimlik/kayit` → kullanıcı `beklemede` + doğrulama jetonu üretir; posta sürücüsüne bağlantıyı verir. SMTP yoksa `konsol` sürücüsü loglar ve `ayar.kayit_acik` / `son_dogrulama_baglantisi` alanına yazar (test bunu okur).
- `kimlik/giris` yalnız `son_kullanici`; `kimlik/panel-giris` yalnız personel rolleri. Yanlış rolde `403 yetki_yok`.
- `eposta_dogrulanmadi` ise girişte `403` (mesaj Türkçe).
- Yenilemede refresh rotasyonu: eski `oturum.iptal=True`, yeni jeton.
- `kullanicilar` uçları yalnız `yonetici`; rol/durum değişikliği `islem_kaydi`'na yazılır.
**Test kanıtı:** kayıt → doğrula → giriş → yenile (eski jeton reddedilir) → çıkış; rol yükseltme denemesi `403`; e-posta tekrarı `409`.
**Koşum:** `python -m pytest arkauc/testler/test_kimlik.py -q`

### T1.2 Model kataloğu
**Dosyalar:** `bdm_listesi/sema.py`, `bdm_listesi/katalog.py`, `bdm_listesi/saglayicilar.py`, `bdm_listesi/tohum_katalog.json`, `arkauc/app/api/modeller.py`, `arkauc/testler/test_katalog.py`
**Sözleşme:** spec §4.5, §7.3.
**Gereksinimler:** sağlayıcı yetenek matrisi (`akis`, `yerel`, `gpu_gerekir`, `varsayilan_port`, `varsayilan_temel_url`); `slug` üretimi ve tekilliği (`409 cakisma`); upstream anahtarı yalnız yazılır, okurken `***`; `GET /modeller` yalnız `hazir|calisiyor` ve anahtarın `izinli_modeller` süzgeci.
**Tohum:** 8 kayıt (`ollama-llama3`, `ollama-qwen2.5`, `openai-gpt4o-mini`, `openai-gpt4o`, `openrouter-claude`, `vllm-mistral`, `tgi-llama`, `ozel-uyumlu`).
**Koşum:** `python -m pytest arkauc/testler/test_katalog.py -q`

### T1.3 Hazırlama ucu
**Dosyalar:** `bdm_hazırlama_ucu/{__init__,uc,dogrulama,cekim,manifest,on_kontrol}.py`, `arkauc/testler/test_hazirlama.py`
**Sözleşme:** spec §7.5, §10.
**Gereksinimler:**
- `dogrula`: `temel_url/upstream_model` için `/models` yoklaması (yoksa `/chat/completions` ile 1 tokenlık deneme), gecikme ölçümü, sonucu `bdm.durum`'a yazar (`hazir`/`hata`).
- `cek`: Ollama `POST /api/pull` akışı veya HF `snapshot_download` (opsiyonel bağımlılık yoksa net Türkçe hata); SSE `ilerleme` olayları.
- `manifest`: sağlayıcıya göre konteyner komutu, port, `gpu` bayrağı, `bellek_gb` tahmini (parametre sayısı × 2 / kuantizasyon).
- `on-kontrol`: `SahteSurucu`/gerçek sürücüden Docker+GPU durumu, image önbelleği, disk.
- `vllm|tgi` + GPU yok → `503 surucu_yok` + spec §10 mesajı.
**Koşum:** `python -m pytest arkauc/testler/test_hazirlama.py -q`

### T1.4 Yönetim ucu ve konteyner sürücüleri
**Dosyalar:** `arkauc/app/servisler/konteyner_docker.py`, `konteyner_yerel.py`, `bdm_yönetim_ucu/{__init__,uc,yasam_dongusu,saglik,gunlukler,surucu_durum}.py`, `arkauc/testler/test_yonetim.py`
**Sözleşme:** spec §7.6, §10.
**Gereksinimler:**
- Durum makinesi: `taslak→hazir→calisiyor→durdu`; geçersiz geçiş `409`. Her geçiş `islem_kaydi`'na.
- `DockerSurucusu`: image çek, konteyner oluştur (port, env, `DeviceRequest` GPU), başlat, sağlık sondası (HTTP `/health` veya `/v1/models`), `gunlukler` streaming, durdur/sil.
- `YerelSurucusu`: Ollama REST (`/api/tags`, `/api/ps`, `/api/generate` sağlık).
- Sürücü seçimi: `bdm.yerel_mi` + `saglayici` + `durum.gpu_var`.
- `gunlukler` SSE; `surucu/durum` Docker/nvidia/GPU listesi + image önbelleği.
**Test:** `SahteSurucu` ile tam yaşam döngüsü; gerçek Docker varsa `ollama/ollama` image'ı ile entegrasyon testi (GPU'suz).
**Koşum:** `python -m pytest arkauc/testler/test_yonetim.py -q`

### T1.5 Sohbet, upstream ve kota
**Dosyalar:** `arkauc/app/servisler/upstream.py`, `akış.py`, `kota.py`, `arkauc/app/api/sohbet.py`, `arkauc/app/api/kullanim.py`, `arkauc/testler/sahte_ust.py`, `arkauc/testler/test_sohbet.py`, `arkauc/testler/test_kota.py`
**Sözleşme:** spec §7.4, §7.7 (kullanım), §6.
**Gereksinimler:**
- `upstream.py`: OpenAI-uyumlu `/chat/completions` (stream + non-stream), sağlayıcıya göre başlık/URL farkları; `SahteUstSaglayici` enjekte edilebilir olmalı (ayarlardan veya bağımlılık enjeksiyonundan).
- `akış.py`: SSE çerçeveleme (`baslangic`, `parca`, `kullanim`, `hata`, `bitti`), istemci kopmasında upstream iptali.
- Kota: istek öncesi kontrol (`429 kota_asildi` + `ayrinti.sifirlanma`), sonrası `kullanim_kaydi` yazımı.
- Her mesaj `bdm_konusma_gecmisi.yazici` ile **maskelenerek** yazılır; `konusma.token_girdi/cikti` güncellenir; ilk mesajda başlık türetilir (ilk 60 karakter).
- `GET /kullanim/ozet`, `/kullanim/zaman-serisi` (spec §7.7).
**Koşum:** `python -m pytest arkauc/testler/test_sohbet.py arkauc/testler/test_kota.py -q`

### T1.6 Loglar, ayarlar, API anahtarları
**Dosyalar:** `arkauc/app/api/loglar.py`, `ayarlar.py`, `api_anahtarlari.py`, `arkauc/testler/test_loglar.py`
**Sözleşme:** spec §7.7, §7.8, §4.4.
**Gereksinimler:** filtre (kullanıcı, bdm, tarih aralığı, metin arama), sayfalama zarfı `{ "toplam", "sayfa", "boyut", "kayitlar" }`; `disa-aktar` json/md/csv; silme + maskelemenin geri döndürülemezliği; `temizle` saklama günü; API anahtarı oluşturma yalnız bir kez tam anahtar döner, sonra `onek`/`son_dort`.
**Koşum:** `python -m pytest arkauc/testler/test_loglar.py -q`

### T1.7 `onuc` iskeleti ve kimlik sayfaları
**Klasör:** `onuc/` (tamamı kendisine ait)
**Gereksinimler:** Next.js 15 App Router + TS + Tailwind v4; `lib/cn.ts` (`clsx`+`tailwind-merge`); `lib/api.ts` (fetch sarmalayıcı, 401'de tek yenileme denemesi, hata zarfı çözümleme); Instrument Serif + Geist (`next/font`); sayfalar `/giris`, `/kayit`, `/dogrula`, `/sifre-sifirla`; korumalı rota sarmalayıcı; Türkçe metinler; Opensource UI bileşenleri GitHub'dan uyarlanır (Login/Signup/ForgotPassword formları, Toast, Spin Loader). `npm run build` ve `npx tsc --noEmit` yeşil.
**Koşum:** `cd onuc && npm run build`

### T1.8 `yonetim_paneli` iskeleti ve kurulum sihirbazı
**Klasör:** `yonetim_paneli/` (tamamı kendisine ait)
**Gereksinimler:** aynı yığın; `/giris` (panel-giris), `/kurulum` 4 adım (şirket bilgisi → yönetici hesabı → ilk BDM → özet) — `saglik/kurulum` durumuna göre yönlendirme; panel kabuğu (sol menü, üst bar, kullanıcı menüsü, BDM seçici); `lib/api.ts`; `components/ui/*` ortak bileşenleri **tam** (Dalga 2 ajanları bunlara dokunmaz); Dashboard `/` iskeleti. `npm run build` yeşil.
**Koşum:** `cd yonetim_paneli && npm run build`

---

## Dalga 1-gözlem (8 paralel gözlemci ajanı)

Her gözlemci: spec maddelerini okur, **kendi** test betiğini yazar, uygulayıcının kodunu kara kutu çalıştırır, kanıtı `kaynak/testler/dalga1-<modul>-log.md`'ye yazar.

Log biçimi (zorunlu):
```
# <modül> gözlem logu — <tarih>
## Kapsam (spec maddeleri)
## Koşulan komutlar
### 1) <komut>
- Beklenen: ...
- Gerçek çıktı: ```...```
- Sonuç: GEÇTİ | KALDI
## Bulgular
- [BLOCKER|MAJOR|MINOR] dosya:satır — sorun — beklenen davranış — yeniden üretme adımı
```

## Dalga 1-düzeltme
Controller, log dosyalarını ilgili uygulayıcı ajana `hub send` ile iletir ve düzeltme ister. Uygulayıcı düzeltir, testini yeniden koşar, gözlemci yeniden koşar. Ancak sonra kapanır.

---

## Dalga 2 — Arayüzler ve dağıtım (4 paralel uygulayıcı + gözlemciler)

### T2.1 `onuc` sohbet arayüzü
**Sahip:** yalnız `onuc/app/sohbet/**`, `onuc/components/sohbet/**`, `onuc/lib/sohbet.ts`. Kabuk/`components/ui` dosyaları T1.7 sahibinindir; değişiklik gerekirse controller'a bildir.
**Gereksinimler:** SSE akışı (fetch + `ReadableStream`), mesaj balonları, markdown + kod bloğu kopyalama, model seçici, konuşma listesi + arama, otomatik kaydırma, "durdur"/"yeniden üret", boş durum, mobil çekmece, `prefers-reduced-motion`.

### T2.2 Panel BDM sayfaları
**Sahip:** yalnız `yonetim_paneli/app/bdm/**`, `yonetim_paneli/components/bdm/**`.
**Gereksinimler:** liste + filtre, yeni/düzenle formu (sağlayıcıya göre alanlar), detay sekmeleri (Genel · Hazırlama: doğrula/çek/ön-kontrol · Çalışma: başlat/durdur/sağlık · Günlükler: SSE terminal · Yönlendirme), durum rozetleri, GPU yok uyarısı.

### T2.3 Panel log, kullanım, kullanıcı ve ayar sayfaları
**Sahip:** yalnız `yonetim_paneli/app/loglar/**`, `app/kullanim/**`, `app/kullanicilar/**`, `app/api-anahtarlari/**`, `app/ayarlar/**`, `app/islem-kayitlari/**`, `yonetim_paneli/components/loglar/**`.
**Gereksinimler:** konuşma tablosu + filtre + detay çekmecesi + dışa aktarma indirmesi; kullanım grafikleri (bağımlılıksız SVG/CSS — grafik kütüphanesi ekleme); kullanıcı rol/durum yönetimi; API anahtarı oluşturma (tam anahtarı bir kez göster + kopyala) ve iptal; ayarlar (marka, SMTP, saklama, maskeleme, tehlikeli bölge); denetim izi tablosu.

### T2.4 `dagitim`
**Dosyalar:** `dagitim/docker-compose.yml`, `Dockerfile.arkauc`, `Dockerfile.onuc`, `Dockerfile.panel`, `.env.ornek`, `baslat.ps1`, `baslat.sh`, `saglik.ps1`, `saglik.sh`, `nginx.conf`.
**Gereksinimler:** üç servis + Postgres profili (`--profile postgres`); healthcheck'ler; `KUTYAI_VERITABANI_URL` ile Postgres'e geçiş; Windows (`baslat.ps1`) ve Linux/macOS (`baslat.sh`) tek komut kurulum; `.env` yoksa örnekten üretir; UTF-8 klasör adları için Docker bağlamı doğrulanır.

---

## Dalga 3 — Doğrulama ve kapanış

- [ ] `python -m pytest arkauc/testler -q` → tümü geçer
- [ ] `cd onuc && npm run build && npx tsc --noEmit` → yeşil
- [ ] `cd yonetim_paneli && npm run build && npx tsc --noEmit` → yeşil
- [ ] Uçtan uca duman testi (gerçek tarayıcı): kurulum → kayıt → doğrula → giriş → sohbet → panelde log ve kullanım görünürlüğü → ekran görüntüsü
- [ ] Docker yaşam döngüsü: `ollama/ollama` konteyneri ile başlat/durdur/log
- [ ] Spec uyumu incelemesi (reviewer) + kod kalitesi incelemesi (reviewer) → bulgular kapatılır
- [ ] `kaynak/KURULUM.md`, `API.md`, `ISLETIM.md`, `GUVENLIK.md` güncel ve Türkçe
- [ ] `finishing-a-development-branch` akışı: özet + birleştirme kararı

---

## Kabul kriterleri (spec §1 ile birebir)

1. Kurulum sihirbazı 4 adımda tamamlanır ve `ayar.kurulum_tamam=true` yazılır.
2. Son kullanıcı kaydolur, doğrular, giriş yapar, **akışlı** yanıt alır.
3. Konuşma + mesajlar maskelenmiş olarak yazılır; panelden filtrelenir, okunur, json/md/csv indirilir.
4. BDM doğrula → hazırla → başlat → durdur akışı hem uzak sağlayıcıda hem Docker/Ollama yolunda çalışır; GPU yokluğu sessizce yutulmaz.
5. Kota aşımı `429 kota_asildi`, kimlik hatası `401`, upstream hatası `502 ust_saglayici_hatasi` — hepsi Türkçe mesajlı.
