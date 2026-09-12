# KutyAI — Kurulum Kılavuzu

## 1. Gereksinimler

| Bileşen | Sürüm | Zorunlu mu |
|---|---|---|
| Python | 3.11+ (test edilen: 3.13) | Evet |
| Node.js | 20+ (test edilen: 22) | Arayüzler için |
| Docker | 24+ | Yalnız yerel model konteynerleri için |
| NVIDIA Container Toolkit | — | Yalnız vLLM/TGI (GPU) kullanacaksanız |

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

## 6. Veritabanı göçleri

Şema uygulama açılışında otomatik oluşturulur. Alembic ile yönetmek isterseniz:

```bash
./.venv/Scripts/python -m alembic upgrade head
./.venv/Scripts/python -m alembic revision --autogenerate -m "aciklama"
```

## 7. Yerel model (Ollama) kurulumu

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

## 8. GPU'lu vLLM

```bash
docker run --rm --gpus all vllm/vllm-openai:latest --help   # sürücü kontrolü
```

Panelde `vLLM (yerel)` seçin. GPU çalışma zamanı yoksa panel "Bu model GPU gerektirir" uyarısı verir ve başlatma `503 surucu_yok` ile reddedilir — sessizce CPU'ya düşmez.

## 9. E-posta

`KUTYAI_SMTP_*` tanımlı değilse **konsol sürücüsü** kullanılır: doğrulama ve şifre sıfırlama bağlantıları sunucu günlüğüne yazılır ve API yanıtındaki `gelistirme_baglantisi` alanında döner. Üretimde SMTP tanımlayın.

## 10. Sorun giderme

| Belirti | Çözüm |
|---|---|
| `503 surucu_yok` | Docker çalışmıyor veya GPU yok. `docker info` ile doğrulayın. |
| `502 ust_saglayici_hatasi` | Sağlayıcı adresi/anahtarı hatalı. Panelde **Hazırlama → Doğrula** çalıştırın. |
| Kurulum sihirbazı açılmıyor | `GET /api/v1/saglik/kurulum` yanıtında `kurulum_tamam` true olabilir; `ayar` tablosundaki satırı silin. |
| Doğrulama e-postası gelmiyor | SMTP tanımsız; bağlantı sunucu günlüğünde. |
| Arayüz API'ye ulaşamıyor | `NEXT_PUBLIC_API_URL` ve `KUTYAI_CORS_KAYNAKLAR` değerlerini kontrol edin. |
