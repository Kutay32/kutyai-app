# KutyAI — Güvenlik ve KVKK

## 1. Kimlik doğrulama

| Konu | Uygulama |
|---|---|
| Parola saklama | argon2id (`argon2-cffi`), kullanıcı başına rastgele tuz |
| Erişim jetonu | JWT HS256, ömür `KUTYAI_ERISIM_OMRU_DK` (varsayılan 15 dk) |
| Yenileme jetonu | Rastgele 48 bayt; veritabanında yalnız SHA-256 özeti |
| Rotasyon | Her yenilemede eski kayıt `iptal=true`, yeni jeton üretilir |
| İptal | Çıkış, şifre sıfırlama ve hesap pasifleştirmede tüm oturumlar iptal edilir |
| Roller | `yonetici`, `operator`, `izleyici`, `son_kullanici` |
| E-posta doğrulama | Tek kullanımlık, 24 saat ömürlü jeton; doğrulanmadan sohbet engellenir |

## 2. API anahtarları

- Biçim: `kuty_` + 32 karakter (base62).
- Veritabanında saklanan: SHA-256 özeti + `onek` (ilk 12) + `son_dort`. Tam anahtar **yalnızca oluşturma yanıtında** bir kez gösterilir.
- `izinli_modeller` ile model kısıtı, `gunluk_istek_siniri` ile anahtar bazlı kota.
- İptal anında `durum=iptal`; doğrulama reddedilir.

## 3. Upstream sağlayıcı anahtarları

- `KUTYAI_SIFRELEME_ANAHTARI` (Fernet) ile şifrelenerek saklanır.
- API hiçbir zaman çözülmüş anahtarı döndürmez; yalnız `api_anahtari_maskeli` (`sk-1***cdef`).
- `uretim` ortamında anahtar tanımlı değilse uygulama başlamaz.

## 4. KVKK uyumu

| Gereksinim | Uygulama |
|---|---|
| Veri minimizasyonu | Kayıt anında maskeleme; ham kişisel veri veritabanına yazılmaz |
| Maskeleme desenleri | TCKN, e-posta, telefon, IBAN, kredi kartı (`maskeleme_kurali` tablosu, panelden yönetilebilir) |
| Saklama süresi | `ayar.saklama_gun` (varsayılan 90); süre sonunda temizlik |
| Silme hakkı | `DELETE /api/v1/loglar/konusmalar/{id}` |
| Veri taşınabilirliği | `GET /api/v1/loglar/konusmalar/{id}/disa-aktar?bicim=json\|md\|csv` |
| Denetim izi | `islem_kaydi` tablosu: giriş, BDM yaşam döngüsü, kullanıcı/rol, anahtar işlemleri, log silme |
| Bilgi sızdırmama | Şifre sıfırlama isteği, e-posta var olsa da olmasa da aynı yanıtı döner |

**Not:** Maskeleme geri döndürülemez. Kayıt anında uygulanır; bu bilinçli bir tasarım kararıdır (spec §11).

## 5. Ağ ve çalışma zamanı

- CORS yalnız `KUTYAI_CORS_KAYNAKLAR` listesindeki kaynaklara açıktır.
- Oran sınırı kullanıcı/anahtar/IP başına dakikalık istek sayısıyla sınırlanır (`KUTYAI_ORAN_SINIRI_ISTEK_DK`).
- Konteynerler yalnız gerekli portu yayınlar; model servisleri varsayılan olarak `localhost` üzerinde dinler.
- Hata yanıtları teknik ayrıntı içermez; traceback ve upstream gövdesi sunucu günlüğüne ve denetim izine gider.

## 6. Üretim kontrol listesi

- [ ] `KUTYAI_ORTAM=uretim`
- [ ] `KUTYAI_GIZLI_ANAHTAR` ve `KUTYAI_SIFRELEME_ANAHTARI` tanımlı ve yedekli
- [ ] `KUTYAI_CORS_KAYNAKLAR` gerçek alan adlarıyla sınırlı
- [ ] SMTP yapılandırıldı (konsol sürücüsü kapalı)
- [ ] `KUTYAI_VERITABANI_URL` PostgreSQL'e işaret ediyor ve düzenli yedekleniyor
- [ ] HTTPS sonlandırması ters vekil üzerinde
- [ ] `saklama_gun` kurum politikasına uygun
- [ ] Denetim izi düzenli olarak gözden geçiriliyor
- [ ] İlk yönetici hesabının parolası değiştirildi
