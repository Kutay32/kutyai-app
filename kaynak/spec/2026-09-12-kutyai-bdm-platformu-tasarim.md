# KutyAI — Kurumsal BDM Platformu · Tasarım Spec'i

**Tarih:** 2026-09-12
**Durum:** Onaylandı (kullanıcı onayı: tasarım sunumu sonrası)
**Kapsam:** v1 — shiplenebilir, uçtan uca çalışan platform

---

## 1. Amaç

Bir şirketin kendi büyük dil modelini (BDM) **tanımlaması, hazırlaması, başlatması, son kullanıcılarına sunması ve tüm konuşmaları kayıt altına alması** için tek kurulumda çalışan platform. Kurulum, yönetim ve kullanım arayüzlerinin tamamı Türkçedir.

### Başarı kriterleri

1. Kurulum sihirbazı ile 10 dakikada çalışır hâle gelir: yönetici hesabı → ilk BDM → doğrulama → sohbet.
2. Son kullanıcı kayıt olur, e-postasını doğrular, giriş yapar, akışlı yanıt alır.
3. Her konuşma ve mesaj maskelenerek veritabanına yazılır; yönetim panelinden filtrelenir, okunur, dışa aktarılır.
4. BDM yaşam döngüsü (doğrula → hazırla → başlat → durdur → log) hem uzak sağlayıcı hem yerel Ollama hem Docker/vLLM konteyneri için çalışır.
5. Kota aşımı, kimlik hatası, upstream hatası kullanıcıya Türkçe ve makine-okunur kodla döner.

---

## 2. Mimari

Tek backend süreci (`arkauc`, FastAPI) + iki bağımsız Next.js uygulaması (`onuc`, `yonetim_paneli`). BDM yetenekleri ayrı süreçler değil, kendi klasörlerinde yaşayan ve `arkauc` içine monte edilen router modülleridir.

```
onuc  ──┐
        ├──► arkauc (FastAPI, /api/v1) ──┬──► bdm_listesi      (katalog)
panel ──┘                                ├──► bdm_hazırlama_ucu (doğrula/çek/manifest)
                                         ├──► bdm_yönetim_ucu   (başlat/durdur/sağlık/log)
                                         ├──► bdm_konusma_gecmisi (yazıcı/maskeleme/dışa aktarım)
                                         └──► bdm_veritabani    (SQLAlchemy + Alembic)
                                                    │
                                    upstream: OpenAI / Azure / OpenRouter
                                              Ollama (yerel REST)
                                              vLLM / TGI (Docker + GPU)
```

### Klasör sözleşmesi

| Klasör | Sorumluluk | Yazma izni |
|---|---|---|
| `bdm_veritabani/` | 12 tablo, async oturum, Alembic göçleri, tohum | yalnız Dalga 0 |
| `bdm_listesi/` | Model kataloğu şeması, CRUD, sağlayıcı yetenek matrisi, tohum JSON | kendi ajanı |
| `bdm_konusma_gecmisi/` | Mesaj/kullanım yazıcısı, maskeleme, sorgu, dışa aktarım, saklama | kendi ajanı |
| `bdm_hazırlama_ucu/` | `uc.py` router: doğrula, çek, manifest, ön kontrol | kendi ajanı |
| `bdm_yönetim_ucu/` | `uc.py` router: başlat/durdur/yeniden başlat, durum, sağlık, log, yönlendirme | kendi ajanı |
| `arkauc/` | `app/cekirdek/*`, `app/api/*`, `app/servisler/*`, `testler/*` | dosya bazlı tek sahip |
| `onuc/` | Son kullanıcı Next.js uygulaması | kendi ajanı |
| `yonetim_paneli/` | Yönetim Next.js uygulaması | kendi ajanı |
| `dagitim/` | Compose, Dockerfile'lar, betikler, .env örneği | kendi ajanı |
| `kaynak/` | Spec, plan, doküman, gözlemci test logları | controller + gözlemciler |

**Çakışma kuralı:** Bir ajan yalnızca kendi klasörüne yazar. Paylaşılan dosya değişikliği gerekiyorsa `hub` üzerinden dosyanın sahibine iletilir. Dalga 0 sonrası `arkauc/app/main.py`, `arkauc/app/cekirdek/*` ve `bdm_veritabani/*` **dondurulmuştur**; değişiklik yalnız controller onayıyla.

---

## 3. Teknoloji

| Katman | Seçim | Gerekçe |
|---|---|---|
| Backend | Python 3.13, FastAPI, Uvicorn | LLM ekosistemi, async akış |
| ORM | SQLAlchemy 2.0 async + Alembic | SQLite→Postgres tek şema |
| Doğrulama | Pydantic v2, pydantic-settings | `.env` + tip güvenliği |
| Şifre | `argon2-cffi` | Modern, bellek-sert |
| Jeton | `PyJWT` HS256 | Basit, bağımlılıksız |
| Şifreleme | `cryptography` Fernet | Upstream API anahtarları |
| Konteyner | `docker` SDK | Yaşam döngüsü + GPU device request |
| Arayüzler | Next.js 15 App Router, React 19, TS, Tailwind v4 | Opensource UI hedef yığını |
| Tasarım | Opensource UI dili | Nötr sahne, Instrument Serif + Geist |
| Paketleme | Docker Compose + yerel betikler | Tek komut kurulum |

Bağımlılıklar `pyproject.toml`'da tek yerde; arayüzler `package.json` ile ayrı.

---

## 4. Veri modeli (12 tablo)

Kolon adları Türkçedir. Tüm tablolarda `id` (Integer PK), zaman damgaları UTC.

### 4.1 `kullanici`
`id`, `eposta` (unique, index), `ad_soyad`, `sifre_hash`, `rol` (Enum: `yonetici|operator|izleyici|son_kullanici`), `durum` (Enum: `aktif|beklemede|pasif`), `eposta_dogrulandi` (bool), `olusturulma`, `guncellenme`, `son_giris`.
Panel yalnızca `yonetici|operator|izleyici` rollerini kabul eder (`kimlik/panel-giris`). `son_kullanici` yalnızca `kimlik/giris` kullanır.

### 4.2 `oturum`
`id`, `kullanici_id` FK, `jeton_hash` (unique), `son_kullanma`, `iptal` (bool), `olusturulma`, `user_agent`, `ip`.
Refresh rotasyonu: her yenilemede eski kayıt `iptal=true`, yeni kayıt üretilir.

### 4.3 `dogrulama_jetonu`
`id`, `kullanici_id` FK, `tur` (Enum: `eposta_dogrulama|sifre_sifirlama`), `jeton_hash` (unique), `son_kullanma`, `kullanildi` (bool), `olusturulma`.
Tek kullanımlık; kullanıldığında `kullanildi=true`.

### 4.4 `api_anahtari`
`id`, `ad`, `onek` (index, ilk 12 karakter), `anahtar_hash` (unique, SHA-256), `son_dort`, `kullanici_id` FK (nullable), `durum` (Enum: `aktif|iptal`), `izinli_modeller` (JSON liste, boş=tümü), `gunluk_istek_siniri` (nullable int), `olusturulma`, `son_kullanim`.
Tam anahtar yalnızca oluşturma yanıtında bir kez döner.

### 4.5 `bdm`
`id`, `slug` (unique), `gorunen_ad`, `aciklama`, `saglayici` (Enum: `openai|azure|openrouter|ollama|vllm|tgi|ozel`), `temel_url`, `upstream_model`, `api_anahtari_sifreli` (Fernet, nullable), `baglam_penceresi`, `maks_cikti`, `sicaklik_varsayilan`, `sistem_istemi`, `yetenekler` (JSON: `{"akis": true, "gorsel": false, "arac": false}`), `durum` (Enum: `taslak|hazir|calisiyor|durdu|hata`), `yerel_mi` (bool), `konteyner` (JSON: `{"image","gpu","port","bellek_gb","argumanlar":[],"konteyner_id"}`, nullable), `olusturulma`, `guncellenme`.

### 4.6 `konusma`
`id`, `kullanici_id` FK (nullable), `api_anahtari_id` FK (nullable), `bdm_id` FK, `baslik`, `sistem_istemi`, `token_girdi`, `token_cikti`, `arsivlendi` (bool), `olusturulma`, `guncellenme`.

### 4.7 `mesaj`
`id`, `konusma_id` FK (index), `rol` (Enum: `kullanici|asistan|sistem|arac`), `icerik` (Text), `token_sayisi`, `gecikme_ms`, `model`, `hata` (Text nullable), `olusturulma`.

### 4.8 `kullanim_kaydi`
`id`, `kullanici_id` FK, `api_anahtari_id` FK, `bdm_id` FK, `konusma_id` FK (nullable), `girdi_token`, `cikti_token`, `gecikme_ms`, `durum` (Enum: `basarili|hata|kota_asildi`), `olusturulma`.

### 4.9 `kota`
`id`, `kapsam` (Enum: `kullanici|api_anahtari`), `kapsam_id`, `gunluk_istek` (nullable), `aylik_token` (nullable), `kullanilan_gunluk`, `kullanilan_aylik`, `gun_sifirlanma`, `ay_sifirlanma`.
`kosul`: (`kapsam`, `kapsam_id`) unique.

### 4.10 `islem_kaydi`
`id`, `kullanici_id` FK (nullable), `eylem`, `hedef_tur`, `hedef_id`, `ayrinti` (JSON), `ip`, `olusturulma`.

### 4.11 `ayar`
`anahtar` (PK, String), `deger` (JSON), `guncellenme`.
Kullanılan anahtarlar: `kurulum_tamam`, `marka_adi`, `varsayilan_bdm_slug`, `saklama_gun`, `maskeleme_aktif`, `kayit_acik`, `smtp_*`, `bakim_modu`.

### 4.12 `maskeleme_kurali`
`id`, `ad`, `desen` (regex), `etkin` (bool), `sira`.
Tohum: TCKN, e-posta, telefon (TR), IBAN, kredi kartı.

---

## 5. Ayarlar (`arkauc/app/cekirdek/ayarlar.py`, ön ek `KUTYAI_`)

| Anahtar | Varsayılan | Not |
|---|---|---|
| `VERITABANI_URL` | `sqlite+aiosqlite:///<kök>/bdm_veritabani/kutyai.db` | Postgres: `postgresql+asyncpg://...` |
| `GIZLI_ANAHTAR` | geliştirmede üretilir + uyarı loglanır | JWT imzası |
| `SIFRELEME_ANAHTARI` | geliştirmede üretilir + uyarı | Fernet |
| `ERISIM_OMRU_DK` | 15 | |
| `YENILEME_OMRU_GUN` | 30 | |
| `CORS_KAYNAKLAR` | `http://localhost:3000,http://localhost:3001` | |
| `ONUC_URL` / `PANEL_URL` | `http://localhost:3000` / `:3001` | e-posta bağlantıları |
| `SAKLAMA_GUN` | 90 | log saklama |
| `MASKELEME_AKTIF` | true | |
| `SMTP_HOST/PORT/KULLANICI/SIFRE/GONDEREN/TLS` | boş | boşsa `konsol` posta sürücüsü |
| `ORTAM` | `gelistirme` | `uretim`'de üretilmiş sır zorunlu |
| `DOCKER_SOKETI` | boş (otomatik) | |
| `IMAGE_ONBELLEK` | `vllm/vllm-openai:latest,ollama/ollama:latest` | |
| `ORAN_SINIRI_ISTEK/DK` | 60 | kullanıcı başına |

`uretim` ortamında `GIZLI_ANAHTAR` veya `SIFRELEME_ANAHTARI` boşsa uygulama **başlamaz** (açık hata).

---

## 6. Hata zarfı

Tüm hatalar gövdesi:

```json
{ "hata": { "kod": "kota_asildi", "mesaj": "Günlük istek kotanız doldu.", "ayrinti": { "sifirlanma": "..." } } }
```

| HTTP | `kod` örnekleri |
|---|---|
| 400 | `gecersiz_istek`, `dogrulama_hatasi` |
| 401 | `kimlik_gerekli`, `jeton_gecersiz`, `jeton_suresi_doldu`, `anahtar_gecersiz` |
| 403 | `yetki_yok`, `eposta_dogrulanmadi` |
| 404 | `bulunamadi` |
| 409 | `cakisma` (eposta/slug tekrarı) |
| 429 | `kota_asildi`, `oran_siniri` |
| 502 | `ust_saglayici_hatasi` |
| 503 | `bdm_hazir_degil`, `surucu_yok` |

Sunucu tarafı ayrıntı (traceback, upstream gövdesi) yalnızca log + `islem_kaydi`'na yazılır. SSE sırasında hata `event: hata` çerçevesi olarak akıtılır.

---

## 7. API yüzeyi

Taban: `/api/v1`. Kimlik: `Authorization: Bearer <jwt>` veya `Authorization: Bearer kuty_<...>`.

### 7.1 Kimlik — `arkauc/app/api/kimlik.py`
| Yöntem | Yol | Yetki |
|---|---|---|
| POST | `/kimlik/kayit` | açık (ayar `kayit_acik`) |
| POST | `/kimlik/dogrula` | açık (jeton gövdede) |
| POST | `/kimlik/giris` | açık — `son_kullanici` |
| POST | `/kimlik/panel-giris` | açık — personel rolleri |
| POST | `/kimlik/yenile` | açık (refresh jetonu) |
| POST | `/kimlik/cikis` | kimlikli |
| POST | `/kimlik/sifre-sifirlama-iste` | açık |
| POST | `/kimlik/sifre-sifirla` | açık (jeton gövdede) |
| GET | `/kimlik/ben` | kimlikli |

### 7.2 Kullanıcılar — `arkauc/app/api/kullanicilar.py`
`GET /kullanicilar` (filtre: rol, durum, arama, sayfa) · `PATCH /kullanicilar/{id}` (rol/durum) · `DELETE` (pasifleştir) · `POST /kullanicilar` (personel daveti) — hepsi `yonetici`.

### 7.3 Model kataloğu — `arkauc/app/api/modeller.py`
`GET /modeller` (kimlikli; yalnız `hazir|calisiyor` + anahtarın izinlisi) · `GET/POST/PATCH/DELETE /bdm` (yönetici/operatör; DELETE yalnız yönetici) · `POST /bdm/{id}/kopyala`.

### 7.4 Sohbet — `arkauc/app/api/sohbet.py`
`POST /sohbet` (tek yanıt) · `POST /sohbet/akis` (SSE) · `GET /sohbet/konusmalar` · `GET /sohbet/konusmalar/{id}` · `PATCH` (başlık) · `DELETE`.
Gövde: `{ "bdm_id"|"bdm_slug", "konusma_id"?, "mesaj", "sistem_istemi"?, "sicaklik"?, "maks_token"? }`.
Yanıt: `{ "konusma_id", "mesaj_id", "icerik", "token_girdi", "token_cikti", "gecikme_ms" }`.
SSE olayları: `baslangic`, `parca` (`{"icerik": "..."}`), `kullanim`, `hata`, `bitti`.

### 7.5 Hazırlama — `bdm_hazırlama_ucu/uc.py` → `/api/v1/bdm/hazirlama`
`POST /{bdm_id}/dogrula` (upstream erişim + model listesi + gecikme) · `POST /{bdm_id}/cek` (SSE ilerleme; Ollama pull / HF snapshot) · `POST /{bdm_id}/manifest` (konteyner komutu + GPU tahmini) · `GET /{bdm_id}/on-kontrol` (Docker, GPU, disk, image).

### 7.6 Yönetim — `bdm_yönetim_ucu/uc.py` → `/api/v1/bdm/yonetim`
`POST /{bdm_id}/baslat` · `/durdur` · `/yeniden-baslat` · `GET /{bdm_id}/durum` · `GET /{bdm_id}/saglik` · `GET /{bdm_id}/gunlukler` (SSE, `?satir=200`) · `PATCH /{bdm_id}/yol` (alias/öncelik) · `GET /surucu/durum`.

### 7.7 Loglar ve kullanım — `arkauc/app/api/loglar.py`, `kullanim.py`
`GET /loglar/konusmalar` (kullanıcı, bdm, tarih aralığı, metin arama, sayfalama) · `GET /loglar/konusmalar/{id}` · `GET /loglar/konusmalar/{id}/disa-aktar?bicim=json|md|csv` · `DELETE /loglar/konusmalar/{id}` · `POST /loglar/temizle` (yönetici; saklama politikası) · `GET /kullanim/ozet` · `GET /kullanim/zaman-serisi?gun=30&kirilim=bdm|kullanici`.

### 7.8 Sistem — `arkauc/app/api/sistem.py`
`GET /saglik` (canlılık) · `GET /saglik/hazir` (DB + sürücü) · `GET /saglik/kurulum` (`kurulum_tamam`) · `GET/PUT /ayarlar` (yönetici).
`arkauc/app/api/api_anahtarlari.py`: `GET/POST /api-anahtarlari`, `POST /api-anahtarlari/{id}/iptal`.

---

## 8. Router keşfi sözleşmesi (dondurulmuş)

`arkauc/app/main.py` aşağıdaki modülleri `importlib` ile yükler, `router` özniteliğini verilen ön ek ile monte eder; modül yoksa **uyarı loglar ve atlar** (dalga içi paralel geliştirmeyi mümkün kılar).

```python
YONLENDIRICILER = (
    ("arkauc.app.api.kimlik",            "/api/v1", ""),
    ("arkauc.app.api.kullanicilar",      "/api/v1", ""),
    ("arkauc.app.api.api_anahtarlari",   "/api/v1", ""),
    ("arkauc.app.api.modeller",          "/api/v1", ""),
    ("arkauc.app.api.kurulum",           "/api/v1", ""),
    ("arkauc.app.api.sohbet",            "/api/v1", ""),
    ("arkauc.app.api.loglar",            "/api/v1", ""),
    ("arkauc.app.api.kullanim",          "/api/v1", ""),
    ("arkauc.app.api.ayarlar",           "/api/v1", ""),
    ("arkauc.app.api.sistem",            "/api/v1", ""),
    ("bdm_hazırlama_ucu.uc",             "/api/v1/bdm/hazirlama", "hazirlama"),
    ("bdm_yönetim_ucu.uc",               "/api/v1/bdm/yonetim",    "yonetim"),
)
```

**Hiçbir ajan `main.py`'yi değiştirmez.**

---

## 9. Çekirdek bağımlılıklar (`arkauc/app/cekirdek/bagimliliklar.py`)

| Ad | Döner | Kural |
|---|---|---|
| `veritabani_oturumu` | `AsyncSession` | istek başına |
| `gecerli_kullanici` | `Kullanici` | JWT; süre/iptal kontrolü |
| `gecerli_personel(roller)` | `Kullanici` | rol kümesi kontrolü |
| `gecerli_istemci` | `IstemciKimligi` | JWT **veya** `kuty_` anahtarı |
| `kota_kontrol(kapsam)` | — | 429 fırlatır, kullanımı artırır |

`IstemciKimligi`: `{ "tur": "kullanici"|"anahtar", "kullanici": Kullanici|None, "anahtar": ApiAnahtari|None }`.

---

## 10. Konteyner orkestrasyonu

`sürücü` arayüzü (`arkauc/app/servisler/konteyner.py`):

```python
class KonteynerSurucusu(Protocol):
    async def durum(self) -> SurucuDurumu: ...          # docker var mı, gpu var mı, image'lar
    async def baslat(self, bdm: dict, manifest: dict) -> str: ...   # konteyner_id
    async def durdur(self, konteyner_id: str) -> None: ...
    async def sil(self, konteyner_id: str) -> None: ...
    async def saglik(self, konteyner_id: str) -> SaglikDurumu: ...
    async def gunlukler(self, konteyner_id: str, satir: int) -> AsyncIterator[str]: ...
```

Uygulamalar: `DockerSurucusu` (docker SDK, `DeviceRequest(capabilities=[["gpu"]])`, port eşleme, sağlık sondası) · `YerelSurucusu` (Ollama REST) · `SahteSurucu` (test; bellekte durum tutar).

**GPU yoksa:** `baslat` sessizce CPU'ya düşmez. `SurucuDurumu.gpu_var == False` ve sağlayıcı `vllm|tgi` ise **503 `surucu_yok`** ve Türkçe yönlendirme mesajı ("Bu model GPU gerektirir; Ollama gibi CPU uyumlu bir sağlayıcı seçin veya GPU çalışma zamanını kurun."). Panelde uyarı kartı gösterilir.

---

## 11. Güvenlik ve KVKK

- Şifre: argon2id. E-posta karşılaştırması küçük harfe normalize edilir.
- API anahtarı biçimi `kuty_` + 32 bayt base62. Saklanan: SHA-256 + `onek` + `son_dort`.
- Upstream anahtarları Fernet ile şifreli; API hiçbir zaman çözülmüş anahtarı döndürmez (`***` maskesi).
- JWT: HS256, `sub`=kullanıcı id, `rol`, `jti`, `exp`. Refresh rotasyonu + iptal listesi.
- Oran sınırı: kullanıcı/anahtar/IP başına dakikalık istek; bellek içi kayan pencere.
- Maskeleme kayıt anında uygulanır (geri dönüşü yok). `maskeleme_kurali` tablosundan desen okunur, `[MASKELENDI:ad]` ile değiştirilir.
- Saklama: `saklama_gun` sonrası `POST /loglar/temizle` ve günlük zamanlanmış görev siler.
- Denetim izi: giriş, BDM yaşam döngüsü, kullanıcı/rol değişikliği, anahtar işlemleri, log silme.
- CORS: yalnız `CORS_KAYNAKLAR`.
- E-posta: SMTP yoksa `konsol` sürücüsü bağlantıyı loglar + `ayar` tablosuna yazar; panel kurulum adımında bu durum açıkça gösterilir. (Geliştirme/test edilebilirliği için bilinçli karar.)

---

## 12. Arayüzler

### 12.1 `onuc` (son kullanıcı)
Sayfalar: `/giris`, `/kayit`, `/dogrula`, `/sifre-sifirla`, `/sohbet`, `/sohbet/[id]`, `/kullanim`, `/hesap`.
Özellikler: akışlı yanıt (SSE), model seçici, konuşma listesi + arama, otomatik başlık, markdown + kod bloğu kopyalama, üretimi durdurma, yeniden üretme, mobil uyum, oturum yenileme (401'de tek deneme).

### 12.2 `yonetim_paneli`
Sayfalar: `/kurulum` (4 adım: şirket → yönetici → ilk BDM → özet), `/giris`, `/` kontrol paneli, `/bdm`, `/bdm/yeni`, `/bdm/[id]` (sekmeler: Genel · Hazırlama · Çalışma · Günlükler · Yönlendirme), `/loglar`, `/loglar/[id]`, `/kullanim`, `/kullanicilar`, `/api-anahtarlari`, `/ayarlar`, `/islem-kayitlari`.

### 12.3 Tasarım dili (Opensource UI)
Nötr sahne (beyaz/kırık beyaz, `neutral-*`), Instrument Serif yalnız marka başlıkları, Geist gövde/UI, `rounded-md` (buton) / `rounded-lg` (alan, küçük kart) / `rounded-2xl` (büyük yüzey), `p-4` iç boşluk, kenarlık-odaklı focus (`focus:border-neutral-900 focus:ring-0`), hata için rose, `md:` breakpoint (asla `sm:`), düz yüzeyler, gradyan/glow/glassmorphism/purple yasak. Bileşenler GitHub kaynağından (`bidyut10/opensourceui`) uyarlanır, metinler Türkçeleştirilir.

---

## 13. Doğrulama stratejisi

1. **Birim/entegrasyon (pytest):** geçici SQLite; `SahteUstSaglayici` (SSE taklidi, hata enjeksiyonu) ve `SahteSurucu`. Kapsam: kimlik akışı ve jeton rotasyonu, rol yetkisi, kota aşımı, sohbet akışı + log yazımı, maskeleme, hazırlama doğrulama, yaşam döngüsü geçişleri, dışa aktarım biçimleri.
2. **Arayüz:** `npm run build` + `tsc --noEmit` yeşil; gerçek tarayıcıda uçtan uca duman testi (kayıt → doğrula → giriş → sohbet → panelde log görünür).
3. **Docker:** gerçek `ollama/ollama` konteyneri ile başlat/durdur/log kanıtı (GPU gerektirmez).
4. Her dalgada gözlemci ajan kanıtı `kaynak/testler/` altında; spec uyumu + kod kalitesi incelemesi geçmeden özellik kapanmaz.

---

## 14. Kapsam dışı (v1)

Ödeme/abonelik/faturalama · çok kiracılılık ve organizasyon izolasyonu · RAG/vektör veritabanı · dosya yükleme · araç çağırma · görsel/ses üretimi · SSO/SAML/OIDC · Kubernetes/Helm · i18n altyapısı (tek dil: Türkçe) · e-posta şablon motoru (düz metin/HTML gömülü).

---

## 15. Riskler ve karşılıklar

| Risk | Karşılık |
|---|---|
| GPU bulunamaması | Net 503 + Türkçe yönlendirme; CPU uyumlu Ollama yolu test edilir |
| Upstream sağlayıcı kesintisi | 502 sadeleştirilmiş mesaj + denetim kaydı; sağlık ucu sağlayıcı durumunu gösterir |
| Unicode klasör adları (`bdm_hazırlama_ucu`) | Import edilebilirliği doğrulandı; Docker'da UTF-8 yol; CI'da içe aktarma testi |
| Uzun model indirme | SSE ilerleme + iptal; disk ön kontrolü |
| E-posta gönderimi yok | `konsol` sürücüsü + panelde açık uyarı (test edilebilirlik) |
| Paralel ajan çakışması | Klasör sahipliği + dondurulmuş çekirdek + otomatik router keşfi |
