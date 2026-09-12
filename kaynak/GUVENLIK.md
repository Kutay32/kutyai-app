# KutyAI — Güvenlik ve KVKK

## 1. Kimlik doğrulama

| Konu | Uygulama |
|---|---|
| Parola saklama | argon2id (`argon2-cffi`), kullanıcı başına rastgele tuz |
| Erişim jetonu | JWT HS256, ömür `KUTYAI_ERISIM_OMRU_DK` (varsayılan 15 dk) |
| Yenileme jetonu | Rastgele 48 bayt; veritabanında yalnız SHA-256 özeti |
| Rotasyon | Her yenilemede eski kayıt `iptal=true`, yeni jeton üretilir |
| Çıkış / şifre sıfırlama | Yenileme jetonu iptal edilir. Erişim jetonu `exp`'e kadar (varsayılan **15 dakika**) geçerli kalır — kısa ömür bilinçli telafi. Anında kesin iptal gerekiyorsa `KUTYAI_ERISIM_OMRU_DK` düşürün. |
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

**Geliştirme bağlantıları:** SMTP tanımlı değilken doğrulama/şifre sıfırlama bağlantısı API yanıtındaki `gelistirme_baglantisi` alanında döner. Bu **yalnız `KUTYAI_ORTAM != uretim`** iken geçerlidir; üretimde bağlantı yalnız sunucu günlüğüne yazılır ve yanıtta asla görünmez. Üretimde SMTP tanımlamak zorunludur.

**Bilinen ve kabul edilen sızıntılar:**
- `POST /kimlik/kayit` kayıtlı e-postada `409`, yeni e-postada `201` döner; e-posta varlığı tek istekle öğrenilebilir. Sözleşme gereği korunur (kullanıcıya "bu e-posta kayıtlı" demek gerekir).
- `/sohbet` yanıtı istemciye ham akıtılır, kayıt maskelenir (API.md §9).

## 5. Ağ ve çalışma zamanı

- **Giden adres doğrulaması:** `bdm.temel_url` yalnız `http`/`https` olabilir; bulut metadata adresleri (`169.254.169.254`, `100.100.100.200`, `metadata.google.internal`) reddedilir. Loopback/özel ağ adresleri **kabul edilir** (yerel Ollama/vLLM bu adreslerde çalışır); bu nedenle `temel_url` ve upstream API anahtarı değişikliği **yalnız yönetici** rolüne açıktır — operatör model tanımını düzenleyebilir ama adresi değiştirip anahtarı başka bir sunucuya yönlendiremez.
- `bdm.upstream_model` konteyner komut satırına girdiği için karakter kümesiyle sınırlanır (`A-Z a-z 0-9 . _ - / :`), `-` ile başlayamaz (bayrak enjeksiyonu engeli).
- CORS yalnız `KUTYAI_CORS_KAYNAKLAR` listesindeki kaynaklara açıktır.
- Oran sınırı: kimlik uçlarında IP başına dakikada 10 deneme (kaba kuvvet), diğer uçlarda istemci başına `KUTYAI_ORAN_SINIRI_ISTEK_DK`. Ters vekil arkasında gerçek istemci IP'si için `KUTYAI_GUVENILIR_VEKIL=true` ayarlayın (yalnız güvenilen vekilde açın; aksi hâlde `X-Forwarded-For` sahtelenebilir).
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
