# KutyAI — İşletim Kılavuzu

## 1. Günlük kontroller

| Kontrol | Nasıl |
|---|---|
| Servis ayakta mı | `GET /api/v1/saglik` → `durum: "ayakta"` |
| Veritabanı + sürücü | `GET /api/v1/saglik/hazir` |
| Sürücü ve GPU | Panel → Kontrol Paneli → sürücü kartı; `GET /api/v1/bdm/yonetim/surucu/durum` |
| BDM durumları | Panel → BDM'ler; `hata` durumundaki kayıtları inceleyin |
| Kota ve kullanım | Panel → Kullanım; `GET /api/v1/kullanim/ozet?gun=1` |

## 2. BDM yaşam döngüsü

```
taslak ──doğrula──► hazir ──başlat──► calisiyor ──durdur──► durdu
   │                   │                  │                  │
   └───────────────────┴──── hata ◄───────┴──────────────────┘
```

| Adım | Nereden | Not |
|---|---|---|
| Doğrula | Panel → BDM → Hazırlama | Upstream erişimi + gecikme ölçümü; başarısızsa `hata` |
| Çek | Panel → BDM → Hazırlama | Yalnız Ollama; ilerleme akışı gösterilir |
| Manifest | Panel → BDM → Hazırlama | Konteyner komutu, port, GPU, bellek tahmini |
| Ön kontrol | Panel → BDM → Hazırlama | Docker, GPU, disk, image önbelleği |
| Başlat / Durdur | Panel → BDM → Çalışma | Her geçiş denetim izine yazılır |

GPU'suz sunucuda `vllm`/`tgi` başlatılamaz; panel açık uyarı gösterir. CPU'da çalıştırmak için `ollama` sağlayıcısını kullanın.

## 3. Kaynak boyutlandırma (kaba)

| Model boyutu | GPU belleği | Not |
|---|---|---|
| 7B (4-bit) | ~6 GB | Ollama CPU'da da çalışır (yavaş) |
| 7B (16-bit) | ~16 GB | vLLM önerilir |
| 13B (16-bit) | ~28 GB | vLLM, tensor paralel gerekebilir |
| 70B (4-bit) | ~40 GB | Çoklu GPU |

## 4. Yedekleme

| Veri | Yöntem | Sıklık |
|---|---|---|
| SQLite (`bdm_veritabani/kutyai.db`) | Dosya kopyası (servis durdurulmuşken) | Günlük |
| PostgreSQL | `pg_dump kutyai > yedek-$(date +%F).sql` | Günlük |
| `.env` | Şifreli kasa | Değişiklikte |
| Model ağırlıkları | Yeniden indirilebilir; yedeklemeye gerek yok | — |

Geri yükleme: servisi durdurun, dosyayı/dökümü geri alın, `alembic upgrade head` çalıştırın, servisi başlatın.

## 5. Saklama ve temizlik

- `ayar.saklama_gun` değerinden eski konuşmalar `POST /api/v1/loglar/temizle` ile silinir (yalnız yönetici).
- Günlük otomatik temizlik için zamanlanmış görev:

```bash
# Linux/macOS — her gece 03:00
0 3 * * * curl -s -X POST http://localhost:8000/api/v1/loglar/temizle \
  -H "Authorization: Bearer $KUTYAI_YONETICI_JETONU"
```

```powershell
# Windows — Görev Zamanlayıcı
schtasks /create /tn "KutyAI log temizligi" /sc daily /st 03:00 ^
  /tr "powershell -c \"Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/v1/loglar/temizle -Headers @{Authorization='Bearer JETON'}\""
```

## 6. Sık karşılaşılan durumlar

| Durum | Müdahale |
|---|---|
| Upstream sağlayıcı kesintisi | Panelde BDM'i doğrulayın; alternatif modele yönlendirin (`PATCH /bdm/yonetim/{id}/yol`) |
| Kota aşımı şikâyeti | Panel → Kullanıcılar / API Anahtarları; kotayı güncelleyin |
| Konteyner takılı kaldı | `GET /bdm/yonetim/{id}/gunlukler` ile logu okuyun; `durdur` → `yeniden-baslat` |
| Disk doldu | Eski image'ları temizleyin (`docker image prune`); saklama süresini kısaltın |
| Yanlış maskeleme | `maskeleme_kurali` tablosundaki deseni düzeltin; yeni kayıtlar yeni desenle maskelenir |
| Şüpheli erişim | İşlem Kayıtları sayfasını inceleyin; ilgili API anahtarını iptal edin, oturumları kapatın |

## 7. Güncelleme

```bash
git pull
./.venv/Scripts/python -m pip install -r requirements.txt
./.venv/Scripts/python -m alembic upgrade head
# servisleri yeniden başlatın
```

Arayüzler için `cd onuc && npm install && npm run build` (ve `yonetim_paneli` için aynısı).
