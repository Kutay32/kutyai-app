# AGENTS.md

## Hafıza (omp, otomatik)

Sürekli bellek: `obsidian-vault/`. Tüm repoyu okuma.

- Oturum: `00-Ana-Sayfa.md` + `01-Harita.md` + `Hafiza/Gunluk.md`
- Ara: `query_vault.py --root . --q "..."`
- Yaz: `remember.py --root . --baslik "..." --govde "..."`
- Skill: `omp-hafiza` (her konuşma). Vault üret: `to-obsidian`. Aç: `obsidian-vault/AC.bat`

## Ürün

KutyAI — kurumsal BDM: tanımla, hazırla, başlat; sohbet ve API. Kayıt maskeli. Arayüz Türkçe.

## Düzen

- `arkauc/` — FastAPI
- `onuc/` — sohbet (Next.js)
- `yonetim_paneli/` — yönetim
- `bdm_*` — katalog, hazırlama, yönetim, konuşma, veritabanı
- `dagitim/` — Compose
- `kaynak/` — spec

## Komutlar

`uvicorn arkauc.app.main:app --reload --port 8000` · `pytest arkauc/testler -q`
