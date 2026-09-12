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
