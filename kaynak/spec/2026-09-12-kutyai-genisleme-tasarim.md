# KutyAI — Genişleme Tasarımı (v2 kapsamı)

**Tarih:** 2026-09-12
**Durum:** Onaylandı (kullanıcı kararları: adaptör+yerel sürücü+Stripe · OIDC+SAML · taşınabilir vektör arama + pgvector · tam çok kiracılılık · tam i18n TR/EN)
**Önceki:** `2026-09-12-kutyai-bdm-platformu-tasarim.md` (v1 çekirdek). Bu belge onu **genişletir**, çeliştiği yerde bu belge geçerlidir.

---

## 1. Kapsam

v1'de bilinçli olarak dışarıda bırakılan 10 yetenek ekleniyor. Üç ilke:

1. **Kırıcı değişiklik yok.** Mevcut `/api/v1` uçları ve alan adları korunur; yenileri eklenir.
2. **Tek kod yolu.** SQLite ve Postgres aynı şemayla çalışmaya devam eder; farklar yalnız hızlandırıcı (örn. pgvector) düzeyindedir ve yokluğunda taşınabilir yol kullanılır.
3. **Türkçe varsayılan.** Yeni tüm kullanıcı metinleri TR'dir; EN kataloğu tam çeviri olarak gelir.

## 2. Çok kiracılılık

### 2.1 Model

| Tablo | Alanlar | Not |
|---|---|---|
| `organizasyon` | id, ad, slug (unique), durum (`aktif`\|`askida`), olusturulma, guncellenme | Kiracı kökü |
| `uyelik` | id, organizasyon_id, kullanici_id, rol, durum, olusturulma | `unique(organizasyon_id, kullanici_id)` |

`uyelik.rol`: `sahip` \| `yonetici` \| `operator` \| `izleyici` \| `son_kullanici`.
`kullanici.rol` alanı **korunur** (geriye uyumluluk + kullanıcının varsayılan rolü) ancak **yetki kararı artık üyelik rolünden** verilir.

### 2.2 Aktif organizasyon çözümü (öncelik sırası)

1. `X-Organizasyon: <slug>` istek başlığı
2. Erişim jetonundaki `org` claim'i (`POST /kimlik/organizasyon-sec` ile alınır)
3. Kullanıcının ilk `aktif` üyeliği

Çözümlenen organizasyon `aktif_organizasyon` bağımlılığı ile tüm uçlara verilir. Üyelik yoksa `403 yetki_yok`.

### 2.3 Organizasyona bağlanan tablolar

`bdm`, `konusma`, `api_anahtari`, `islem_kaydi`, `dosya`, `vektor_belgesi`, `vektor_parcasi`, `arac`, `arac_cagrisi`, `abonelik`, `fatura`, `posta_sablonu`, `sso_saglayici` → `org_id` (NOT NULL, FK `organizasyon.id`, RESTRICT).

Global kalanlar: `kullanici`, `oturum`, `dogrulama_jetonu`, `plan`, `maskeleme_kurali`, `ayar`.

`mesaj` org taşımaz; `konusma` üzerinden erişilir.

### 2.4 Göç (v1 → v2)

`0002_cok_kiracili`:
1. `organizasyon` + `uyelik` tabloları oluşturulur.
2. `varsayilan` slug'lı organizasyon eklenir (`ad = ayar.marka_adi`).
3. Her mevcut kullanıcı için üyelik: rolü `kullanici.rol` ile eşlenir (`yonetici`→`sahip`, diğerleri aynı).
4. Org-scoped tablolara `org_id` kolonu eklenir (nullable) → varsayılan organizasyon id'siyle doldurulur → NOT NULL'a çevrilir (SQLite için Alembic `batch_alter_table`).
5. `kullanici.rol` korunur.

Göç **geri dönüşsüzdür**; `alembic downgrade` yalnız kolonları düşürür (veri kaybı). Çalıştırma öncesi yedek zorunlu (`kaynak/ISLETIM.md` §4).

### 2.5 Yeni uçlar

| Yöntem | Yol | Yetki |
|---|---|---|
| GET | `/organizasyonlar` | kimlikli (üye oldukları) |
| POST | `/organizasyonlar` | kimlikli (oluşturan `sahip` olur) |
| GET | `/organizasyonlar/{id}` | üye |
| PATCH | `/organizasyonlar/{id}` | `sahip`/`yonetici` |
| GET | `/organizasyonlar/{id}/uyeler` | üye |
| POST | `/organizasyonlar/{id}/uyeler` | `sahip`/`yonetici` |
| PATCH | `/organizasyonlar/{id}/uyeler/{kullanici_id}` | `sahip`/`yonetici` |
| DELETE | `/organizasyonlar/{id}/uyeler/{kullanici_id}` | `sahip`/`yonetici` |
| POST | `/kimlik/organizasyon-sec` | kimlikli → yeni erişim jetonu |

**Sahiplik kuralları:** son `sahip` düşürülemez/silinemez (`409 gecersiz_gecis`); kendi üyeliğini `sahip` rolünden düşüremez.

## 3. Dosya yükleme

| Tablo | Alanlar |
|---|---|
| `dosya` | id, org_id, kullanici_id, ad, mime, boyut, sha256, yol, metin (çıkarılan), olusturulma |

- Depolama: `KUTYAI_DOSYA_DIZINI` (varsayılan `bdm_veritabani/dosyalar/<org_slug>/<uuid>`).
- Sınırlar: `KUTYAI_DOSYA_MAKS_MB` (varsayılan 25), izinli MIME listesi (`text/*`, `application/pdf`, `image/*`, `application/json`, `text/csv`).
- Metin çıkarımı: `text/*`, `json`, `csv` doğrudan; `pdf` için `pypdf` (kuruluysa); aksi hâlde `metin` boş kalır ve `ayrinti` alanında gerekçe döner — **uydurma metin yok**.
- Uçlar: `POST /dosyalar` (multipart), `GET /dosyalar`, `GET /dosyalar/{id}`, `GET /dosyalar/{id}/icerik` (indirme), `DELETE /dosyalar/{id}`.
- Sohbet eki: `POST /sohbet` gövdesine `dosya_idleri: [int]`; metni çıkarılmış dosyaların içeriği sistem istemine eklenir, boyut sınırı `KUTYAI_DOSYA_BAGLAM_KR` (varsayılan 12k karakter).
- KVKK: dosya içeriği de maskeleme kuralına tabidir (kayıt anında).

## 4. Araç çağırma

| Tablo | Alanlar |
|---|---|
| `arac` | id, org_id, ad, slug, aciklama, json_sema (JSON Schema), tur (`webhook`\|`yerlesik`), uc_noktasi, basliklar (JSON, şifreli sırlar), etkin, olusturulma |
| `arac_cagrisi` | id, org_id, konusma_id, mesaj_id, arac_id, ad, argumanlar (JSON), sonuc (JSON), durum, gecikme_ms, hata, olusturulma |

- Yerleşik araçlar: `hesap_makinesi` (ifade değerlendirme — `ast` ile güvenli), `zaman` (ISO tarih), `web_ara` **yok** (harici anahtar gerektirir, kapsam dışı).
- Akış: upstream isteğine `tools` eklenir → model `tool_calls` dönerse araç çalıştırılır → sonuç `rol=arac` mesajı olarak eklenir → model çağrısı tekrarlanır (en fazla `KUTYAI_ARAC_MAKS_TUR`, varsayılan 4).
- SSE yeni olayları: `arac_cagrisi` (`{ad, argumanlar}`), `arac_sonucu` (`{ad, durum, ozet}`).
- Webhook güvenliği: yalnız `https` (veya `http` + `KUTYAI_ARAC_YEREL_IZIN=true`), hedef adres SSRF denetiminden geçer (v1 `temel_url` kurallarıyla aynı), `X-Kutyai-Imza` HMAC başlığı gönderilir, 10 sn zaman aşımı, yanıt boyutu sınırlı.
- Uçlar: `GET/POST/PATCH/DELETE /araclar`, `POST /araclar/{id}/dene`, `GET /araclar/cagrilar`.

## 5. RAG (bilgi tabanı)

| Tablo | Alanlar |
|---|---|
| `vektor_belgesi` | id, org_id, ad, kaynak (`metin`\|`dosya`\|`url`), dosya_id, meta (JSON), parca_sayisi, olusturulma |
| `vektor_parcasi` | id, org_id, belge_id, sira, icerik, vektor (JSON `list[float]`), token_sayisi, olusturulma |

- Gömme: upstream `POST {temel_url}/embeddings`, model `bdm.gomme_modeli` (yeni alan, varsayılan `text-embedding-3-small`).
- Parçalama: ~800 karakter, 120 karakter örtüşme, cümle sınırına saygılı.
- Arama: kosinüs benzerliği; taşınabilir yol Python'da, `pgvector` uzantısı varsa `vektor_pg` kolonu + `<=>` operatörü ile SQL'de (otomatik seçim, `ayrinti.yol` ile bildirilir).
- Uçlar: `GET/POST /rag/belgeler`, `GET/DELETE /rag/belgeler/{id}`, `POST /rag/ara`, `POST /rag/belgeler/{id}/yeniden-gom`.
- Sohbet entegrasyonu: `POST /sohbet` gövdesine `rag: true` ve opsiyonel `rag_belge_idleri`; en iyi `KUTYAI_RAG_UST_K` (varsayılan 4) parça sistem istemine eklenir; kullanılan parçalar yanıtta `kaynaklar` olarak döner.
- Ölçek sınırı: taşınabilir yol için 200.000 parça (belgelenir); üstünde pgvector önerilir.

## 6. Ödeme, abonelik, faturalama

| Tablo | Alanlar |
|---|---|
| `plan` | id, ad, slug, aylik_fiyat_kurus, para (`TRY`\|`USD`), dahil_istek, dahil_token, ozellikler (JSON), etkin | global |
| `abonelik` | id, org_id, plan_id, durum (`deneme`\|`aktif`\|`gecikmis`\|`iptal`), donem_basi, donem_sonu, saglayici, dis_id | org |
| `fatura` | id, org_id, abonelik_id, tutar_kurus, para, durum (`taslak`\|`odendi`\|`basarisiz`\|`iade`), kalemler (JSON), dis_id, olusturulma, odeme_tarihi | org |

Adaptör (`OdemeSaglayici` Protocol):

| Sürücü | Davranış |
|---|---|
| `yerel` | Manuel tahsilat: fatura üretir; `POST /faturalama/faturalar/{id}/odendi` ile işaretlenir. Offline tam çalışır. |
| `stripe` | `POST /faturalama/odeme-oturumu` → Stripe Checkout oturumu; `POST /faturalama/webhook/stripe` → imza doğrulaması (`Stripe-Signature`, HMAC-SHA256, zaman toleransı) → abonelik/fatura durumu güncellenir. |

- Plan limitleri organizasyon kotasına yansır: `POST /faturalama/abonelik` plan seçildiğinde org kotası (`kota` kapsamı `organizasyon`) plan limitleriyle güncellenir.
- Kota kapsamı yeni değer: `organizasyon`.
- Uçlar: `GET /faturalama/planlar`, `GET /faturalama/abonelik`, `POST /faturalama/abonelik`, `POST /faturalama/abonelik/iptal`, `GET /faturalama/faturalar`, `POST /faturalama/faturalar/{id}/odendi` (yalnız `yerel` sürücü + `sahip`), `POST /faturalama/odeme-oturumu`, `POST /faturalama/webhook/stripe` (açık uç, imza doğrulamalı).
- Kota aşım davranışı: `gecikmis` abonelikte sohbet `402` + kod `abonelik_gecikmis` (yeni hata kodu); `deneme`/`aktif` normal.

## 7. SSO

| Tablo | Alanlar |
|---|---|
| `sso_saglayici` | id, org_id, tur (`oidc`\|`saml`), ad, slug, etkin, ayarlar (JSON), olusturulma |
| `sso_kimlik` | id, kullanici_id, saglayici_id, dis_id, eposta, olusturulma; `unique(saglayici_id, dis_id)` |

**OIDC** (`ayarlar`: issuer, client_id, client_secret_sifreli, kapsamlar, eposta_claim, ad_claim):
`GET /sso/{org_slug}/{saglayici_slug}/baslat` → `state`+`nonce` (imzalı, tek kullanımlık, 10 dk) ile yetkilendirme yönlendirmesi;
`GET /sso/{org_slug}/{saglayici_slug}/donus?code&state` → kod değişimi (PKCE `S256`), `id_token` doğrulama (**imza JWKS ile, `iss`, `aud`, `exp`, `nonce`**), kullanıcı eşleme (önce `sso_kimlik`, sonra e-posta), üyelik yoksa `KUTYAI_SSO_OTOMATIK_UYELIK` açıksa `son_kullanici` üyeliği oluşturulur → erişim/yenileme jetonu.

**SAML 2.0** (`ayarlar`: idp_metadata_xml, sp_entity_id, acs_url, idp_imza_sertifikasi, eposta_ozniteligi):
`GET /sso/{org_slug}/{saglayici_slug}/saml/baslat` → imzalı `AuthnRequest` (yönlendirme bağlaması, `RelayState` = state);
`POST /sso/{org_slug}/{saglayici_slug}/saml/acs` → `SAMLResponse` doğrulaması:
- XML-DSig imzası `signxml` ile **hem Response hem Assertion** üzerinde,
- `Audience` = SP entity id, `Recipient` = ACS URL,
- `NotBefore`/`NotOnOrAfter` penceresi (izin: ±2 dk),
- `InResponseTo` = başlatılan istek kimliği,
- **tekrar oynatma önleme:** kullanılan `Assertion ID` 10 dk boyunca reddedilir (bellek içi küme),
- yalnız `RSA-SHA256`/`RSA-SHA1` kabul; `Destination` denetimi.
Sonra OIDC ile aynı kullanıcı eşleme/üyelik yolu.

**Güvenlik notu:** XML imza doğrulaması elle yazılmaz; `signxml` kullanılır ve yalnız doğrulanmış ağaç üzerinde `lxml` XPath sorguları çalıştırılır (XSW saldırılarına karşı imzalanan düğüm referansı doğrulanır).

## 8. Görsel ve ses üretimi

`arkauc/app/servisler/medya.py`:
- `gorsel_uret(bdm, istem, boyut, adet)` → `POST {temel_url}/images/generations` → `{gorseller: [base64|url], boyut}`
- `ses_uret(bdm, metin, ses, bicim)` → `POST {temel_url}/audio/speech` → ikili akış
- `ses_coz(bdm, dosya_id)` → `POST {temel_url}/audio/transcriptions` (multipart) → `{metin}`

`bdm.yetenekler` bayrakları: `akis`, `gorsel`, `ses`, `arac`. Yetenek yoksa `400 gecersiz_istek` + Türkçe gerekçe.
Uçlar: `POST /medya/gorsel`, `POST /medya/ses`, `POST /medya/coz`. Üretilenler `dosya` tablosuna yazılır, `kullanim_kaydi`'na işlenir.

## 9. E-posta şablonları

`posta_sablonu`: id, org_id, kod (`dogrulama`\|`sifirlama`\|`davet`\|`kota_uyarisi`\|`fatura`\|`hosgeldin`), dil (`tr`\|`en`), konu, govde_metin, govde_html, guncellenme; `unique(org_id, kod, dil)`.
Motor: `{{degisken}}` yerine koyma + `{{#if}}` yok (YAGNI). Şablon yoksa gömülü varsayılan (TR/EN) kullanılır.
Uçlar: `GET/PUT /posta-sablonlari` (yönetici), `POST /posta-sablonlari/{kod}/onizle`.

## 10. i18n

### 10.1 API

- Mesaj katalogları: `arkauc/ceviriler/tr.json`, `arkauc/ceviriler/en.json`; anahtar = hata `kod`u veya mesaj kimliği.
- `KutyaiHatasi` mesajı istek anında çözülür: `Accept-Language` → dil; `az`/`en*` → `en`, aksi hâlde `tr`.
- `ayrinti.kod` her zaman döner (makine-okunur); `mesaj` seçilen dilde.
- Yeni uç: `GET /i18n/diller`, `GET /i18n/sozluk/{dil}` (arayüzün ihtiyaç duyduğu katalog).

### 10.2 Arayüz

- `onuc/lib/sozluk/tr.ts`, `en.ts`; `yonetim_paneli/lib/sozluk/tr.ts`, `en.ts`.
- `DilSaglayici` (React context) + `t(anahtar, degiskenler)`; dil `localStorage` + çerez, `<html lang>` güncellenir.
- Dil seçici: onuc `/hesap`, panel üst bar.
- **Kapsam:** her iki uygulamadaki tüm kullanıcıya görünen metinler katalogdan gelir. Sunucu bileşenlerinde `Accept-Language` çerezi okunur.
- Eksik anahtar → TR metne düşer + `console.warn` (üretimde sessiz).

## 11. Kubernetes / Helm

`dagitim/helm/kutyai/`: `Chart.yaml`, `values.yaml`, `templates/` (namespace, secret, configmap, arkauc Deployment/Service/HPA/PVC, onuc Deployment/Service, panel Deployment/Service, Ingress, migration Job, ServiceAccount), `README.md`, `NOTES.txt`.
Doğrulama: `helm template` (helm varsa) + `kubectl --dry-run=client` yoksa YAML şema denetimi (`python -c yaml.safe_load` + alan kontrolü). Gerçek küme yoksa bu açıkça raporlanır.

## 12. Yeni hata kodları

| Kod | HTTP | Anlam |
|---|---|---|
| `organizasyon_gerekli` | 400 | Aktif organizasyon çözülemedi |
| `org_erisim_yok` | 403 | Kayıt başka organizasyona ait |
| `abonelik_gecikmis` | 402 | Abonelik ödemesi gecikmiş |
| `sso_yapilandirilmamis` | 400 | Sağlayıcı pasif/eksik |
| `sso_dogrulanamadi` | 401 | OIDC/SAML doğrulaması başarısız |
| `arac_hatasi` | 502 | Araç webhook'u başarısız |
| `rag_gomme_hatasi` | 502 | Gömme üretilemedi |
| `medya_desteklenmiyor` | 400 | Model görsel/ses desteklemiyor |
| `dosya_cok_buyuk` | 413 | Boyut sınırı aşıldı |

## 13. Doğrulama stratejisi (ek)

| Alan | Yöntem |
|---|---|
| Kiracılık izolasyonu | Her modül için "A org B org'un kaydını göremez" testi (uç + DB) |
| Göç | `0001` şemasından `0002`'ye yükseltme testi: veri korunur, `org_id` dolar |
| Dosya | Gerçek multipart yükleme + metin çıkarımı + KVKK maskeleme |
| Araç | Sahte webhook sunucusu; imza başlığı, zaman aşımı, hata yolu, tur sınırı |
| RAG | Sahte `/v1/embeddings`; benzerlik sıralaması, `kaynaklar` dönüşü, pgvector yolu ayrı test |
| Ödeme | Adaptör sözleşme testi; Stripe webhook imzası (geçerli/geçersiz/zaman aşımı) gerçek HMAC ile |
| SAML | Sahte IdP: imzalı Response üretir; imza, Audience, süre, replay, XSW denemeleri |
| OIDC | Sahte sağlayıcı: discovery + JWKS + kod değişimi + nonce/state denetimi |
| i18n | `Accept-Language: en` → EN mesaj; eksik anahtar taraması (katalogda olmayan metin) |
| Helm | `helm template` + zorunlu alan denetimi |
| Arayüz | Gerçek tarayıcı: org değiştirme, dosya eki, araç kartı, görsel/ses, dil değiştirme |

## 14. Riskler

| Risk | Karşılık |
|---|---|
| Şema göçü geri dönüşsüz | Yedek zorunlu + göç testi + idempotent tohum |
| SAML imza açığı | `signxml`, yalnız doğrulanmış ağaç, replay kümesi, bağımsız güvenlik incelemesi |
| i18n hacmi (binlerce metin) | Katalog dışı metin tarayıcısı; kademeli dosya bazlı dönüşüm |
| Kota/plan karışıklığı | Tek kritik bölge: `kota_kullan` atomik; plan limitleri org kapsamına yazılır |
| pgvector yokluğu | Taşınabilir yol varsayılan; `ayrinti.yol` ile şeffaf |
| Ajan çakışması | Klasör sahipliği + dondurulmuş çekirdek + otomatik router keşfi (v1 kuralı) |
