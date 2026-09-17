# KutyAI — Kurulum Kılavuzu

## 1. Gereksinimler

| Bileşen | Sürüm | Zorunlu mu |
|---|---|---|
| Python | 3.11+ (test edilen: 3.13) | Evet |
| Node.js | 20+ (test edilen: 22) | Arayüzler için |
| Docker | 24+ | Yalnız yerel model konteynerleri için |
| NVIDIA Container Toolkit | — | Yalnız vLLM/TGI (GPU) kullanacaksanız |
| Kubernetes + Helm | 1.25+ / Helm 3 | Yalnız Helm dağıtımı için (§6) |

## 2. Hızlı kurulum (geliştirme)

```bash
git clone <depo> kutyai-app && cd kutyai-app
python -m venv .venv
./.venv/Scripts/python -m pip install -r requirements-dev.txt     # Windows
# source .venv/bin/activate && pip install -r requirements-dev.txt  # Linux/macOS

cp .env.ornek .env
```

`.env` içinde **üretimde zorunlu** iki değer vardır:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"     # KUTYAI_GIZLI_ANAHTAR
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # KUTYAI_SIFRELEME_ANAHTARI
```

Geliştirmede boş bırakılırsa geçici değerler üretilir ve uyarı loglanır. `KUTYAI_ORTAM=uretim` iken boş bırakmak uygulamayı **başlatmaz**.

## 3. Çalıştırma

```bash
# Backend
./.venv/Scripts/python -m uvicorn arkauc.app.main:app --reload --port 8000

# Son kullanıcı arayüzü
cd onuc && npm install && npm run dev            # http://localhost:3000

# Yönetim paneli
cd yonetim_paneli && npm install && npm run dev  # http://localhost:3001
```

## 4. İlk kurulum (sihirbaz)

1. `http://localhost:3001/kurulum` adresini açın.
2. **Şirket bilgisi:** marka adı.
3. **Yönetici hesabı:** e-posta + parola (en az 8 karakter).
4. **İlk BDM:** sağlayıcıyı seçin.
   - `Ollama (yerel)`: temel adres `http://localhost:11434/v1`, upstream model `llama3`. Önce `ollama pull llama3` çalıştırın.
   - `OpenAI`: API anahtarınızı girin, model `gpt-4o-mini`.
   - `vLLM / TGI`: GPU ve Docker gerekir.
5. **Özet** → Bitir. Kurulum `ayar.kurulum_tamam=true` olarak işaretlenir.

Sonrasında `http://localhost:3000` adresinden son kullanıcı kaydı yapıp sohbete başlayabilirsiniz.

## 5. Docker ile kurulum

```bash
cd dagitim
cp .env.ornek .env      # değerleri düzenleyin
docker compose up -d --build
```

- `arkauc` → http://localhost:8000
- `onuc` → http://localhost:3000
- `yonetim_paneli` → http://localhost:3001

PostgreSQL ile çalıştırmak için:

```bash
docker compose --profile postgres up -d --build
# .env içinde: KUTYAI_VERITABANI_URL=postgresql+asyncpg://kutyai:kutyai@postgres:5432/kutyai
```

## 6. Kubernetes (Helm) ile kurulum

Chart `dagitim/helm/kutyai` (sürüm `0.1.0`), Compose dağıtımının Kubernetes karşılığıdır:
**aynı** ortam değişkeni adları (`KUTYAI_*`), portlar (8000/3000/3001), sağlık uçları ve
kalıcı hacim yolu (`/veri`). Compose ↔ Helm eşlemesinin tamamı chart'ın kendi
belgesindedir: `dagitim/helm/kutyai/README.md` §3.

Ön koşullar: Kubernetes **1.25+** (`Chart.yaml` → `kubeVersion: ">=1.25.0-0"`), Helm 3 ve
imajların derlenmiş olması (`kutyai/arkauc:0.1.0`, `kutyai/onuc:0.1.0`,
`kutyai/yonetim-paneli:0.1.0`; imaj etiketi boş bırakılırsa chart `appVersion` kullanılır).

```bash
# Önerilen yol: ad alanını Helm oluşturur
helm install kutyai dagitim/helm/kutyai -n kutyai --create-namespace

# GitOps/Argo senaryosu: ad alanını chart üretsin
helm install kutyai dagitim/helm/kutyai -n kutyai --set namespace.create=true

# Üretim için tipik geçersiz kılmalar
helm upgrade --install kutyai dagitim/helm/kutyai -n kutyai \
  --set ingress.enabled=true --set ingress.className=nginx \
  --set ingress.hosts[0].host=kutyai.example.com \
  --set ingress.hosts[1].host=panel.example.com \
  --set ingress.tls.enabled=true --set ingress.tls.secretName=kutyai-tls \
  --set secrets.values.KUTYAI_SIFRELEME_ANAHTARI="$FERNET_ANAHTARI" \
  --set secrets.values.KUTYAI_VERITABANI_URL="postgresql+asyncpg://kutyai:PAROLA@pg:5432/kutyai" \
  --set arkauc.autoscaling.enabled=true
```

Kurulumdan sonra `helm status kutyai -n kutyai`; erişim adreslerini, sır uyarılarını ve
kısıtları yazar (`templates/NOTES.txt`).

### 6.1 Varsayılanlar

| Ayar | Varsayılan | Not |
|---|---|---|
| `config.KUTYAI_ORTAM` | `uretim` | Compose örneğinde `gelistirme`; chart üretimi varsayar. `KUTYAI_GIZLI_ANAHTAR`/`KUTYAI_SIFRELEME_ANAHTARI` `secrets.create` modunda her koşulda sağlanır/üretilir; `existingSecret` modunda kendi Secret'ınızda bulunmalıdır |
| `secrets.create` | `true` | `secrets.values` altındaki `KUTYAI_*` anahtarları Secret'a yazılır; boş bırakılan iki sır rastgele üretilir |
| `secrets.existingSecret` | `""` | Doluysa chart Secret üretmez; tüm anahtarları kendi aracınız (SOPS/Vault/SealedSecrets) yönetir |
| `arkauc.replicaCount` | `1` | Varsayılan SQLite + `ReadWriteOnce` hacim tek replika gerektirir |
| `arkauc.autoscaling.enabled` | `false` | Açmak için harici PostgreSQL + pod'lar arası paylaşılabilir hacim gerekir |
| `config.KUTYAI_VERITABANI_URL` | `sqlite+aiosqlite:////veri/kutyai.db` | Parola içeren PostgreSQL adresi `config` yerine `secrets.values` altına yazılmalıdır |
| `arkauc.persistence.data` | `5Gi` PVC, `/veri` | `helm.sh/resource-policy: keep` → `helm uninstall` veriyi silmez |
| `arkauc.dockerSocket.enabled` | `false` | Soket düğümde root yetkisi demektir; **kapalıyken BDM (Ollama/vLLM/TGI) konteynerleri başlatılamaz** |
| `ingress.enabled` | `true` | `kutyai.local` (`/api` → arkauc, `/` → onuc) ve `panel.kutyai.local` |
| `migration.enabled` | `true` | Alembic göçü `post-install,pre-upgrade` hook'u olarak koşar (§7) |

### 6.2 Kurulumdan sonra

1. `kubectl get pods,svc,pvc -n kutyai` — üç Deployment/Service, PVC'ler ve `-goc` Job'u.
2. Sağlık uçları Compose ile aynı sözleşmedir: `GET /api/v1/saglik` (canlılık),
   `GET /api/v1/saglik/hazir` (veritabanı + sürücü).
3. Ingress kapalıysa yerelden erişim:
   `kubectl port-forward -n kutyai svc/kutyai-onuc 3000:3000` (kaynak adları
   `<release>-kutyai` kökünden türer; release adı `kutyai` içeriyorsa yalnız `<release>`).
4. İlk kurulum sihirbazı panel adresinden açılır (§4).

### 6.3 Bilinen sınırlar (doğrulanmadı)

- Chart **gerçek bir Kubernetes kümesine kurulmadı**. Doğrulanan: `helm lint` temiz;
  `helm template` varsayılanda **12**, chart README §8'deki varyantta **15** kaynak;
  `kubeconform -strict -kubernetes-version 1.29.0` ile 12/12 ve 15/15 geçerli (helm 3.16.3).
  `kubectl apply --dry-run=client` küme olmadığı için çalıştırılamadı.
- Varsayılanlarla `arka.uc` **tek replikadır**; `onuc`/`panel` imajları root çalışır
  (non-root için `Dockerfile.onuc`/`Dockerfile.panel` içinde `USER` + chown gerekir).
- `NEXT_PUBLIC_API_URL` imaj **derlenirken** istemci paketine gömülür; üretim imajını
  gerçek alan adıyla derleyin (`--build-arg NEXT_PUBLIC_API_URL=https://.../api/v1`).
- Panel imajı `basePath` ile derlenmediği için varsayılan Ingress panel için ayrı alan adı
  kullanır.

## 7. Veritabanı göçleri

Şema uygulama açılışında otomatik oluşturulur. Alembic ile yönetmek isterseniz:

```bash
./.venv/Scripts/python -m alembic upgrade head
./.venv/Scripts/python -m alembic revision --autogenerate -m "aciklama"
```

## 8. Yerel model (Ollama) kurulumu

```bash
docker run -d --name kutyai-ollama -p 11434:11434 -v kutyai-ollama:/root/.ollama ollama/ollama:latest
docker exec -it kutyai-ollama ollama pull llama3
```

Panelde `Ollama (yerel)` sağlayıcısıyla BDM ekleyin; **Hazırlama → Doğrula** başarılı olduğunda model `hazir` durumuna geçer.

### Model ön indirme (Hazırlama → Modeli indir)

| Sağlayıcı | Yol | Not |
|---|---|---|
| `ollama` | Ollama `POST /api/pull` | SSE ilerleme; model Ollama deposuna iner |
| `vllm`, `tgi` | HuggingFace `snapshot_download` | `KUTYAI_HF_ONBELLEK` dizinine iner (varsayılan `bdm_veritabani/hf-onbellek`) ve konteynere `/root/.cache/huggingface` olarak bağlanır — indirme bir kez yapılır |
| `openai`, `azure`, `openrouter` | Desteklenmez | Modeller sağlayıcı tarafında çalışır; `400` + Türkçe gerekçe döner |

`vllm`/`tgi` için HF deposuna erişim gerekir; özel/gated modellerde `HF_TOKEN` ortam değişkenini tanımlayın.

## 9. GPU'lu vLLM

```bash
docker run --rm --gpus all vllm/vllm-openai:latest --help   # sürücü kontrolü
```

Panelde `vLLM (yerel)` seçin. GPU çalışma zamanı yoksa panel "Bu model GPU gerektirir" uyarısı verir ve başlatma `503 surucu_yok` ile reddedilir — sessizce CPU'ya düşmez.

## 10. E-posta

`KUTYAI_SMTP_*` tanımlı değilse **konsol sürücüsü** kullanılır: doğrulama ve şifre sıfırlama bağlantıları sunucu günlüğüne yazılır ve API yanıtındaki `gelistirme_baglantisi` alanında döner. Üretimde SMTP tanımlayın.

## 11. Sorun giderme

| Belirti | Çözüm |
|---|---|
| `503 surucu_yok` | Docker çalışmıyor veya GPU yok. `docker info` ile doğrulayın. |
| `502 ust_saglayici_hatasi` | Sağlayıcı adresi/anahtarı hatalı. Panelde **Hazırlama → Doğrula** çalıştırın. |
| Kurulum sihirbazı açılmıyor | `GET /api/v1/saglik/kurulum` yanıtında `kurulum_tamam` true olabilir; `ayar` tablosundaki satırı silin. |
| Doğrulama e-postası gelmiyor | SMTP tanımsız; bağlantı sunucu günlüğünde. |
| Arayüz API'ye ulaşamıyor | `NEXT_PUBLIC_API_URL` ve `KUTYAI_CORS_KAYNAKLAR` değerlerini kontrol edin. |
| `400 sso_yapilandirilmamis` | Sağlayıcı pasif ya da zorunlu `ayarlar` eksik (`issuer`/`client_id`, SAML'de `idp_sso_url`/`idp_imza_sertifikasi`). |
| `401 saml_yanit_gecersiz` | IdP sertifikası yanlış/süresi geçmiş ya da sunucu saati IdP'den ±2 dakikadan fazla sapıyor. |
| `413 dosya_cok_buyuk` | `KUTYAI_DOSYA_MAKS_MB` sınırını yükseltin. |
| `400 gomme_modeli_yok` | RAG için BDM kaydındaki `gomme_modeli` alanı boş; değeri tanımlayın. |

## 12. v2 yetenekleri: bağımlılıklar ve ortam değişkenleri

SAML doğrulaması **`signxml`** (XML-DSig) ile yapılır; paket `requirements.txt` içindedir ve
`lxml` bağımlılığıyla birlikte kurulur. Kurulum/güncelleme aynı komuttur:

```bash
./.venv/Scripts/python -m pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt  # Linux/macOS
```

- Docker dağıtımında yeni bağımlılık imaj katmanını geçersiz kılar: `docker compose build arkauc`
  (veya `up -d --build`) ile imajı yeniden derleyin; `Dockerfile.arkauc` bağımlılıkları
  `requirements.txt`'ten kurar, pip önbelleği katman içinde kalır.
- `signxml`, `arkauc/app/servisler/sso_saml.py` içinde **üst düzeyde** içe aktarılır; eksikse
  yönlendirici keşfi hatayı yükseltir ve uygulama başlamaz (keşif yalnız modül dosyası yokken
  uyarıp atlar). Güncellemeden sonra bağımlılıkları mutlaka kurun. Geliştirme ortamında
  (Windows, Python 3.13) `signxml` ve `lxml` tekerlek olarak kurulur; ek sistem paketi gerekmez.
  Docker imajı da bağımlılıkları aynı `requirements.txt` ile kurar — imajı yeniden derlemek
  yeterlidir.

v2 yeteneklerinin ortam değişkenleri (tamamı `.env.ornek` içinde açıklamalıdır; Helm chart
bunları `config` ve `secrets.values` altında taşır):

| Değişken | Varsayılan | Ne yapar |
|---|---|---|
| `KUTYAI_DOSYA_MAKS_MB` | `25` | Yükleme boyut sınırı; aşılırsa `413 dosya_cok_buyuk` |
| `KUTYAI_DOSYA_DIZINI` | boş → `bdm_veritabani/dosyalar` | Yüklenen dosyaların kök dizini (`<dizin>/<org_slug>/<uuid>`); kalıcı hacme verin |
| `KUTYAI_DOSYA_BAGLAM_KR` | `12000` | Sohbete eklenen dosya metninin toplam karakter sınırı |
| `KUTYAI_ARAC_IMZA_ANAHTARI` | boş → jeton sırrından HMAC ile türetilir | Webhook `X-Kutyai-Imza` HMAC anahtarı (bağımsız anahtar tanımlamanız önerilir) |
| `KUTYAI_ARAC_YEREL_IZIN` | `false` | `true` iken yerel ağa `http` webhook kabul edilir (üretimde kapalı tutun) |
| `KUTYAI_ARAC_MAKS_TUR` | `4` | Araç çağırma turu üst sınırı |
| `KUTYAI_RAG_UST_K` | `4` | Sohbete eklenen en iyi parça sayısı |
| `KUTYAI_ODEME_SAGLAYICI` | `yerel` | `yerel` (manuel tahsilat) ya da `stripe` |
| `KUTYAI_STRIPE_GIZLI_ANAHTAR` | boş | Stripe API anahtarı; `stripe` sürücüsünde zorunlu |
| `KUTYAI_STRIPE_WEBHOOK_SIRRI` | boş | Stripe webhook imza sırrı; boşsa webhook `400 odeme_saglayici_yok` döner |
| `KUTYAI_SSO_OTOMATIK_UYELIK` | `true` | SSO ile gelen kullanıcı üyesiz ise `son_kullanici` üyeliği otomatik açılır |
| `KUTYAI_SSO_YENIDEN_YONLENDIRME` | boş | Doluysa SSO girişi jeton gövdesi yerine bu adrese `?kod=` ekleyerek `302` yönlendirir |
| `KUTYAI_SSO_YEREL_IZIN` | `false` | `true` iken IdP adreslerinde (`issuer`, `idp_sso_url`) `http` ve yerel ağ adresleri kabul edilir (üretimde kapalı tutun) |

Yerel geliştirmede varsayılanlar yeterlidir: `yerel` ödeme sürücüsü ve kapalı Stripe sırlarıyla
faturalama tamamen offline çalışır; SSO yalnız sağlayıcı tanımlandığında devreye girer.
