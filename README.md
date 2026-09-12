# KutyAI — Kurumsal BDM Platformu

Şirketinizin büyük dil modelini (BDM) tanımlayın, hazırlayın, başlatın; son kullanıcılarınıza sohbet arayüzü ve API sunun. Tüm konuşmalar KVKK uyumlu biçimde maskelenerek kayıt altına alınır. Arayüzlerin tamamı Türkçedir.

## Ne içerir

| Bileşen | Açıklama |
|---|---|
| `arkauc/` | FastAPI backend: kimlik, sohbet, model yönetimi, loglar, kullanım |
| `onuc/` | Son kullanıcı sohbet arayüzü (Next.js) |
| `yonetim_paneli/` | Yönetim paneli: kurulum sihirbazı, BDM yönetimi, loglar (Next.js) |
| `bdm_listesi/` | Model kataloğu ve sağlayıcı yetenek matrisi |
| `bdm_hazırlama_ucu/` | Erişim doğrulama, model çekme, konteyner manifesti |
| `bdm_yönetim_ucu/` | Başlat/durdur/sağlık/log — konteyner yaşam döngüsü |
| `bdm_konusma_gecmisi/` | Konuşma kaydı, maskeleme, dışa aktarım, saklama |
| `bdm_veritabani/` | 12 tablolu şema + Alembic göçleri |
| `dagitim/` | Docker Compose ve kurulum betikleri |
| `kaynak/` | Spec, plan, API sözleşmesi, orkestra düzeni |

## Hızlı başlangıç (yerel)

```bash
python -m venv .venv
./.venv/Scripts/python -m pip install -r requirements-dev.txt     # Windows
# source .venv/bin/activate && pip install -r requirements-dev.txt  # Linux/macOS

cp .env.ornek .env
./.venv/Scripts/python -m uvicorn arkauc.app.main:app --reload --port 8000
```

- API belgesi: http://localhost:8000/api/docs
- Kurulum sihirbazı için paneli açın, `/kurulum` adresine gidin.

## Testler

```bash
./.venv/Scripts/python -m pytest arkauc/testler -q
```

## Dokümanlar

- `kaynak/spec/2026-09-12-kutyai-bdm-platformu-tasarim.md` — tasarım sözleşmesi
- `kaynak/API.md` — HTTP sözleşmesi (arayüz ajanları için bağlayıcı)
- `kaynak/MIMARI.md` — katmanlar ve kararlar
- `kaynak/ORKESTRA.md` — geliştirme düzeni (uygulayıcı + gözlemci döngüsü)
- `kaynak/KURULUM.md` — üretim kurulumu
- `kaynak/ISLETIM.md` — günlük işletim ve yedekleme
- `kaynak/GUVENLIK.md` — güvenlik ve KVKK

## Lisans

Şirket içi kullanım.
