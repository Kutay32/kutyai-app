# KutyAI — Dağıtım (Docker Compose)

Üç servisi tek komutla ayağa kaldırır: **arka.uc** (FastAPI), **onuc** (son kullanıcı arayüzü),
**yonetim_paneli** (yönetim arayüzü). Varsayılan veritabanı SQLite'tır (adlandırılmış volume);
`postgres` profili ile PostgreSQL'e geçilir.

## 1. Hızlı başlangıç

```powershell
cd dagitim
.\baslat.ps1                      # Windows
```

```bash
cd dagitim
./baslat.sh                       # Linux/macOS
```

Betik sırayla: Docker daemon'ı denetler → `.env` yoksa `.env.ornek`'ten üretir → boş sırları
(`KUTYAI_GIZLI_ANAHTAR`, `KUTYAI_SIFRELEME_ANAHTARI`) üretir → `docker compose up -d --build`
çalıştırır → üç servisin sağlığını bekler → erişim adreslerini yazar.

Elle kurulum (betiksiz):

```bash
cp .env.ornek .env      # KUTYAI_GIZLI_ANAHTAR ve KUTYAI_SIFRELEME_ANAHTARI'ni doldurun
docker compose up -d --build
```

## 2. Dosyalar

| Dosya | Ne yapar |
|---|---|
| `docker-compose.yml` | Servisler, portlar, sağlık kontrolleri, bağımlılık sırası, profiller |
| `Dockerfile.arkauc` | FastAPI imajı: `python:3.13-slim`, UTF-8 yerel ayarı, uvicorn, HEALTHCHECK |
| `Dockerfile.onuc` / `Dockerfile.panel` | Çok aşamalı: `node:22-alpine` derleme + `next start` üretim |
| `*.dockerignore` | Dockerfile'a özel bağlam süzgeci (depo kökü bağlam olarak kullanıldığı için) |
| `.env.ornek` | Tüm `KUTYAI_*` değişkenleri (Türkçe açıklamalı) |
| `baslat.ps1` / `baslat.sh` | Kurulum + derleme + kaldırma + sağlık bekleme |
| `saglik.ps1` / `saglik.sh` | Üç servisin sağlığını yoklar, Türkçe özet verir |
| `nginx.conf` | Opsiyonel tek giriş noktası (`/api/`, `/`, `/panel/`) |

## 3. Komutlar

| Komut | Ne yapar |
|---|---|
| `docker compose up -d --build` | İmajları derler, servisleri arka planda başlatır |
| `docker compose ps` | Servis ve sağlık durumunu listeler |
| `docker compose logs -f arkauc` | Bir servisin günlüğünü izler |
| `docker compose restart onuc` | Tek servisi yeniden başlatır |
| `docker compose build --no-cache arkauc` | İmajı önbelleksiz baştan derler |
| `docker compose down` | Servisleri durdurur ve kaldırır (volume'ler korunur) |
| `docker compose down -v` | **Dikkat:** veri volume'lerini de siler |
| `./saglik.sh` / `.\saglik.ps1` | HTTP sağlık kontrolü + konteyner durumu (bozuksa çıkış kodu 1) |
| `docker compose --profile postgres up -d` | PostgreSQL ile çalıştırır |
| `docker compose --profile nginx up -d` | Tek giriş noktasını da başlatır |

## 4. Portlar ve adresler

| Servis | Adres | Not |
|---|---|---|
| arkauc | http://localhost:8000/api/v1 | Sağlık: `GET /api/v1/saglik`; belge: `/api/docs` |
| onuc | http://localhost:3000 | Son kullanıcı arayüzü |
| yonetim_paneli | http://localhost:3001 | Yönetim paneli; kurulum sihirbazı `/kurulum` |
| nginx (profil `nginx`) | http://localhost:8080 | Tek giriş noktası (aşağıya bakın) |
| postgres (profil `postgres`) | `postgres:5432` (yalnız ağ içinde) | Ana makineye açılmaz |

Arayüzler API'ye **tarayıcıdan görünen** adresle bağlanır: `NEXT_PUBLIC_API_URL`
(varsayılan `http://localhost:8000/api/v1`). Uzak sunucuda `.env` içinde
`KUTYAI_TARAYICI_API_URL=https://alan-adi/api/v1` verin ve derlemeyi yeniden çalıştırın —
bu değer derleme anında istemci paketine gömülür.

## 5. `.env`

Tüm ayarlar kök `.env.ornek` ile aynı adları taşır (`KUTYAI_*`); Docker'a özgü ekler:

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `KUTYAI_VERITABANI_URL` | boş → `sqlite+aiosqlite:////veri/kutyai.db` | Boşsa SQLite (volume) kullanılır |
| `KUTYAI_TARAYICI_API_URL` | `http://localhost:8000/api/v1` | Arayüzlerin gömülü API adresi |
| `KUTYAI_POSTGRES_*` | `kutyai` | Yalnız `postgres` profilinde; `KUTYAI_VERITABANI_URL` ile aynı olmalı |
| `KUTYAI_ORTAM` | `gelistirme` | Üretimde `uretim` yapın; sırlar boşsa uygulama başlamaz |
| `KUTYAI_HF_ONBELLEK` | boş → konteyner içi `bdm_veritabani/hf-onbellek` | Yerel model önbelleği; BDM konteynerine **Docker host** yolundan bağlanır, kalıcılık için host yolunu arkauc'a da bağlayın (`docker-compose.yml` içinde örnek yorumlu) |
| `KUTYAI_DOSYA_DIZINI` | boş → konteyner içi `bdm_veritabani/dosyalar` | Yüklenen dosyaların kökü. Kalıcılık için `/veri/dosyalar` verin; aksi hâlde dosyalar konteyner katmanında kalır ve konteyner yeniden oluşturulunca kaybolur |
| `KUTYAI_STRIPE_GIZLI_ANAHTAR`, `KUTYAI_STRIPE_WEBHOOK_SIRRI` | boş | Yalnız `KUTYAI_ODEME_SAGLAYICI=stripe` iken gerekir; `dagitim/.env` içinde tanımlayın (kök `.env.ornek` açıklamalıdır) |
| `KUTYAI_ARAC_IMZA_ANAHTARI` | boş → jeton sırrından HMAC ile ayrı anahtar türetilir | Webhook `X-Kutyai-Imza` HMAC anahtarı; araç webhook'u kullanıyorsanız bağımsız anahtar tanımlayın |
| `KUTYAI_SSO_YENIDEN_YONLENDIRME` | boş | Doluysa SSO girişi jeton yerine bu adrese `?kod=` ile döner; **tarayıcıdan görünen** arayüz adresi olmalıdır |

Dosya, araç, RAG, ödeme ve SSO değişkenlerinin tamamı (varsayılanlarıyla) kök `.env.ornek`
ve `kaynak/KURULUM.md` §12 içindedir; `docker compose`, `dagitim/.env` dosyasını arkauc
konteynerine `env_file` olarak okur, bu yüzden aynı adlar orada da geçerlidir.

Sır üretimi:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## 6. PostgreSQL profili

```bash
./baslat.sh --profil postgres            # URL'i ve parolayı betik ayarlar
# ya da elle:
docker compose --profile postgres up -d --build
# .env: KUTYAI_VERITABANI_URL=postgresql+asyncpg://kutyai:parola@postgres:5432/kutyai
```

`asyncpg` sürücüsü arkauc imajına kuruludur. Postgres profili etkinken arkauc, `postgres`
servisi **sağlıklı** olana kadar beklemez başlamaz (`depends_on: service_healthy`);
profil kapalıyken bu bağımlılık yok sayılır. Şema açılışta otomatik oluşturulur.

## 7. Tek giriş noktası (nginx, opsiyonel)

```bash
docker compose --profile nginx up -d
# http://localhost:8080  →  /api/ arka.uc · / onuc · /panel/ yonetim_paneli
```

Panel `/panel/` altından servis edildiğinde sayfalar açılır ancak `basePath` ile
derlenmediği için `/_next/...` varlık yolları kökten istenir; **üretimde panel için ayrı
alan adı/port (3001) önerilir**. Ayrıntı ve alternatif `server` bloğu `nginx.conf`
içinde açıklanmıştır. SSE uçları (`/sohbet/akis`, hazırlama ilerlemesi) için tamponlama
kapalıdır.

## 8. Güncelleme

```bash
git pull
docker compose up -d --build                     # imajlar yeniden derlenir, veri korunur
docker compose exec arkauc python -m alembic upgrade head   # şema güncellemesi (gerekirse)
```

Yalnız bir servis değiştiyse: `docker compose up -d --build onuc`.
Veritabanı şeması uygulama açılışında da oluşturulur; Alembic sürüm takibi için yukarıdaki
komut kullanılır. imajlar `kutyai/arkauc:0.1.0`, `kutyai/onuc:0.1.0`,
`kutyai/yonetim-paneli:0.1.0` etiketleriyle üretilir.

## 9. Yedekleme

Ayrıntılı yordam: **`kaynak/ISLETIM.md` §4 (Yedekleme)**. Docker karşılıkları:

```bash
# SQLite (adlandırılmış volume) — tutarlı kopya için önce durdurun
docker compose stop arkauc
docker run --rm -v kutyai_kutyai-veri:/veri -v "$PWD":/yedek alpine \
  tar czf /yedek/kutyai-veri-$(date +%F).tgz -C /veri .
docker compose start arkauc

# PostgreSQL
docker compose exec -T postgres pg_dump -U kutyai kutyai > yedek-$(date +%F).sql
```

Geri yükleme: servisi durdurun, dosyayı/dökümü geri alın,
`docker compose exec arkauc python -m alembic upgrade head` çalıştırın, servisi başlatın.
`.env` dosyasını şifreli kasada saklayın (üretim sırları oradadır).

## 10. Sorun giderme

| Belirti | Çözüm |
|---|---|
| `docker compose config` hata veriyorsa | `.env` içinde sözdizimi hatası; `docker compose config` çıktısı satırı gösterir |
| arkauc `unhealthy` | `docker compose logs arkauc`; `KUTYAI_ORTAM=uretim` iken sırlar boşsa uygulama bilinçli olarak başlamaz |
| Arayüz API'ye ulaşamıyor (CORS / ağ) | `KUTYAI_CORS_KAYNAKLAR` ve `KUTYAI_TARAYICI_API_URL` değerlerini kontrol edin |
| BDM başlatılamıyor, `503 surucu_yok` | `/var/run/docker.sock` bağlı mı: `curl localhost:8000/api/v1/saglik/hazir` → `surucu.docker=true` |
| Postgres profili bağlanamıyor | `KUTYAI_VERITABANI_URL` içindeki kullanıcı/parola `KUTYAI_POSTGRES_*` ile aynı olmalı; `docker compose ps` ile `postgres` sağlığını görün |
| Disk doldu | `docker image prune`, eski volume'leri gözden geçirin; `KUTYAI_SAKLAMA_GUN` değerini kısaltın |
| Kurulum sihirbazı açılmıyor | `GET /api/v1/saglik/kurulum` → `kurulum_tamam`; gerekirse `kutyai` veritabanındaki `ayar` kaydını silin |

## 11. Güvenlik notları

- arkauc imajı, BDM konteynerlerini yönetebilmek için `/var/run/docker.sock` ile bağlanır;
  bu **host üzerinde root yetkisi** anlamına gelir. Güvenilmeyen iş yükü çalıştırmayın ve
  üretimde soketi salt-okunur bir vekil (socket proxy) arkasına almayı değerlendirin.
- `postgres` portu ana makineye açılmaz; yalnız `kutyai-agi` ağından erişilir.
- Üretimde `KUTYAI_ORTAM=uretim` verin, sırları `.env` içinde tanımlayın, `KUTYAI_SMTP_*`
  ayarlarını yapın ve arayüzleri HTTPS sonlandıran bir vekil arkasında çalıştırın.

## 12. Helm (Kubernetes) ile dağıtım

Bu klasördeki Compose dağıtımının Kubernetes karşılığı `helm/kutyai` chart'ıdır; Compose'daki
üç servis üç Deployment'a karşılık gelir ve **aynı** ortam değişkeni adları (`KUTYAI_*`),
portlar (8000/3000/3001), sağlık uçları ve kalıcı hacim yolu (`/veri`) kullanılır.

| Dosya | Ne yapar |
|---|---|
| `helm/kutyai/Chart.yaml` | Chart sürümü `0.1.0`, `kubeVersion: ">=1.25.0-0"` |
| `helm/kutyai/values.yaml` | Tüm değerler; sır varsayılanları **boş** (düz metin sır yok) |
| `helm/kutyai/templates/` | Deployment/Service (arka-uc, onuc, panel), ConfigMap, Secret, PVC, HPA, Ingress, Namespace, ServiceAccount, göç Job'u |
| `helm/kutyai/README.md` | Chart'ın tam belgesi: Compose ↔ Helm eşlemesi, sırlar, üretim notları, doğrulama |
| `helm/kutyai/.helmignore` | Paketleme dışı bırakılanlar |

Kurulum (`kaynak/KURULUM.md` §6, işletim `kaynak/ISLETIM.md` §8):

```bash
helm install kutyai helm/kutyai -n kutyai --create-namespace
helm status kutyai -n kutyai          # erişim adresleri + sır uyarıları
```

Öne çıkan noktalar:

- **Sırlar:** iki mod — `secrets.values` (chart Secret üretir; boş bırakılan
  `KUTYAI_GIZLI_ANAHTAR` ve `KUTYAI_SIFRELEME_ANAHTARI` rastgele üretilir ve yükseltmede
  `lookup` ile korunur) ya da `secrets.existingSecret` (üretimde önerilen). Parola içeren
  `KUTYAI_VERITABANI_URL` `config` yerine `secrets.values` altına yazılır.
- **Göç:** `templates/migration-job.yaml` → `python -m alembic upgrade head`,
  `post-install,pre-upgrade` hook'u (compose'daki `docker compose exec arkauc ...` ile aynı komut).
- **Ölçekleme:** HPA varsayılan kapalı; açmak için harici PostgreSQL ve pod'lar arası
  paylaşılabilir hacim gerekir (varsayılan SQLite + `ReadWriteOnce`).
- **BDM konteynerleri:** `arkauc.dockerSocket.enabled` varsayılan **kapalı**; açmak düğümde root
  yetkisi demektir (bkz. §11).
- **Kalıcı hacimler:** `kutyai-veri` / `kutyai-hf-onbellek` PVC'lerinde
  `helm.sh/resource-policy: keep` vardır; `helm uninstall` veriyi silmez.
- **v2 değişkenleri:** chart, dosya (`KUTYAI_DOSYA_MAKS_MB`, `KUTYAI_DOSYA_DIZINI=/veri/dosyalar`,
  `KUTYAI_DOSYA_BAGLAM_KR`), araç (`KUTYAI_ARAC_YEREL_IZIN`, `KUTYAI_ARAC_MAKS_TUR`), RAG
  (`KUTYAI_RAG_UST_K`), ödeme (`KUTYAI_ODEME_SAGLAYICI`) ve SSO (`KUTYAI_SSO_*`) anahtarlarını
  `config` altında taşır; gizliler (`KUTYAI_STRIPE_*`, `KUTYAI_ARAC_IMZA_ANAHTARI`) `secrets.values`
  altındadır ve `existingSecret` modunda kendi Secret'ınızda bulunmalıdır. Tam liste:
  `dagitim/helm/kutyai/values.yaml`.

**Doğrulama ve sınır:** `helm lint` temiz; `helm template` varsayılanda 12, chart README §8'deki
varyantta 15 kaynak; `kubeconform -strict -kubernetes-version 1.29.0` ile 12/12 ve 15/15 geçerli
(helm 3.16.3). Chart **gerçek bir kümeye kurulmadı**; `kubectl apply --dry-run=client` küme
olmadığı için çalıştırılamadı.
