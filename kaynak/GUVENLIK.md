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

**v2 yüzeyleri (KVKK):**

- Yüklenen dosyanın **baytları** diskte ham saklanır (kullanıcının kendi dosyası, indirmede
  aynen döner); yalnız *çıkarılan metin* maskelenip `dosya.metin`'e yazılır. Sohbete eklenen
  dosya/RAG bağlamı bu maskeli metindir.
- Araç çağrıları `arac_cagrisi` tablosuna yazılırken `argumanlar` ve `sonuc` **ham** saklanır
  (modele/webhook'a giden yapısal veri; kişisel veri içerebilir). Konuşmaya düşen araç mesajı ise
  `mesaj_ekle` üzerinden maskelenir. `arac_cagrisi` kayıtları konuşma silinince **silinmez**
  (`ON DELETE SET NULL` ile referanslar boşalır) ve `POST /loglar/temizle` bu tabloyu kapsamaz —
  gerekiyorsa ayrı temizlik/zamanlanmış iş tanımlayın.
- Dosya kayıtları ve diskteki kopyalar da `POST /loglar/temizle` kapsamında değildir
  (`DELETE /dosyalar/{id}` ile veya dizin düzeyinde temizlenir).

## 5. Ağ ve çalışma zamanı

- **Giden adres doğrulaması:** `bdm.temel_url` yalnız `http`/`https` olabilir; bulut metadata adresleri (`169.254.169.254`, `100.100.100.200`, `metadata.google.internal`) reddedilir. Loopback/özel ağ adresleri **kabul edilir** (yerel Ollama/vLLM bu adreslerde çalışır); bu nedenle `temel_url` ve upstream API anahtarı değişikliği **yalnız yönetici** üyelik rolüne açıktır (`sahip`/`yonetici`; global `kullanici.rol` yetmez, §9) — operatör model tanımını düzenleyebilir ama adresi değiştirip anahtarı başka bir sunucuya yönlendiremez.
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
- [ ] SSO sağlayıcıları ve `KUTYAI_SSO_OTOMATIK_UYELIK` kurum politikasına göre ayarlandı (§7)
- [ ] `KUTYAI_SSO_YEREL_IZIN=false`; IdP adresleri (`issuer`, `idp_sso_url`) `https` ve genel adres (§7)
- [ ] `KUTYAI_STRIPE_WEBHOOK_SIRRI` tanımlı; webhook ucu yalnız HTTPS sonlandıran vekil arkasında (§8)
- [ ] Helm kullanılıyorsa sırlar `secrets.existingSecret` ya da kasada; `values.yaml` içinde düz metin sır yok (§10)
- [ ] Yükleme dizini (`KUTYAI_DOSYA_DIZINI`) kalıcı hacimde, yedek kapsamında ve izinleri dardır (§11)
- [ ] `KUTYAI_ARAC_YEREL_IZIN=false`; webhook adresleri `https` ve `KUTYAI_ARAC_IMZA_ANAHTARI` tanımlı (§12)
- [ ] SAML kullanılıyorsa `signxml` kurulu, IdP sertifikaları ve sunucu saati izleniyor (§7)

## 7. SSO (OIDC / SAML)

SSO sağlayıcıları **organizasyon kapsamlıdır** (`sso_saglayici.org_id`). İstemci sırrı ve
IdP sertifikası Fernet ile şifrelenmiş saklanır; API hiçbir zaman çözülmüş değeri döndürmez
(yanıtta yalnız `sir_tanimli` boolean'ı; `ayarlar` içinde anahtar adında `secret`/`sifre`
geçen alanlar süzülür). Sağlayıcı yönetimi organizasyon yönetim rollerine (`sahip`/`yonetici`)
açıktır.

**OIDC** (`arkauc/app/servisler/sso_oidc.py`)

| Denetim | Uygulama |
|---|---|
| Akış | Authorization Code + **PKCE** (`code_challenge_method=S256`) |
| `state` | `KUTYAI_GIZLI_ANAHTAR` ile HS256 imzalı, **10 dakika** ömürlü; sağlayıcı kimliği, `nonce`, `code_verifier` ve dönüş adresini taşır (sunucu tarafı oturum gerektirmez). `jti` süreç belleğindeki tek kullanım kümesinde tutulur; `/donus` (ve `/saml/acs`) state'i tüketir, aynı state ikinci kez `401 oidc_durum_gecersiz` alır. Küme çok replikada paylaşılmaz (varsayılan dağıtım tek süreçtir) |
| IdP adresi | `issuer` **`https`** olmalı ve keşif belgesindeki `issuer` alanıyla birebir eşleşmeli; adres SSRF denetiminden geçer (`KUTYAI_SSO_YEREL_IZIN=true` iken `http` ve yerel ağ istisnası) |
| E-posta eşleşmesi | IdP `email_verified=false` bildirdiyse e-posta ile mevcut hesaba bağlanılmaz; eşleşme ayrıca kullanıcının sağlayıcı organizasyonunda aktif üye olmasını gerektirir |
| `id_token` imzası | JWKS üzerinden doğrulanır; izinli algoritmalar RS256/RS384/RS512/ES256/ES384 |
| Beyanlar | `iss`, `aud`, `exp`, `iat` zorunlu; ayrıca `nonce` karşılaştırılır |
| Hatalar | `401 oidc_durum_gecersiz`, `401 sso_dogrulanamadi` (teknik ayrıntı yanıta konmaz) |

**SAML** (`arkauc/app/servisler/sso_saml.py`)

- XML-DSig `signxml` ile doğrulanır; **IdP sertifikası zorunludur** (`ayarlar.idp_imza_sertifikasi`),
  imzasız yanıt kabul edilmez.
- XML ayrıştırma XXE savunmalıdır (varlık genişletme ve ağ erişimi kapalı, DTD yok).
- Denetimler: `Audience` (`sp_entity_id`, varsayılan ACS adresi), `Destination` ve
  `SubjectConfirmationData@Recipient`, `NotBefore` / `NotOnOrAfter` (±120 sn tolerans).
- Tekrar oynatma: aynı `Assertion ID` **600 sn** içinde reddedilir (`409 saml_tekrar_oynatma`).
  Küme süreç belleğindedir ve yalnız doğrulanmış Assertion kimliğini taşır; çok replikada
  paylaşılmaz (varsayılan dağıtım tek süreçtir).
- `InResponseTo`: `/saml/acs`, `RelayState` içindeki imzalı `state`ten başlatılan `AuthnRequest`
  kimliğini çözer ve doğrulamaya verir. `RelayState` **zorunludur**: yoksa `400 oidc_durum_gecersiz`,
  çözülemez/başka sağlayıcıya aitse ya da tekrar kullanılmışsa `401 oidc_durum_gecersiz`; IdP
  başlatmalı akış desteklenmez. Doğrulamada yanıttaki **tüm** `InResponseTo` değerleri
  (`Response`, `Assertion` ve `SubjectConfirmationData`) beklenen kimliğe eşit olmalıdır;
  hiçbiri yoksa da yanıt reddedilir → `401 saml_yanit_gecersiz`.
- Zorunlu alanlar (yokluğu `401 saml_yanit_gecersiz`): `Conditions@NotOnOrAfter`,
  `SubjectConfirmationData@NotOnOrAfter`, `SubjectConfirmationData@Recipient = ACS` ve `Audience`.
  `Destination` yalnız **imzalı** düğümden okunur ve Response imzalıysa zorunludur; yalnız
  Assertion imzalıysa ACS bağlaması `Recipient` ile kurulur (imzasız Response'un `Destination`
  alanı güvenilmez sayılır, bu yüzden hiç okunmaz).
- `idp_sso_url` **`https`** olmalıdır; adres SSRF denetiminden geçer (`KUTYAI_SSO_YEREL_IZIN=true`
  iken `http` ve yerel ağ istisnası).
- `AuthnRequest` isteğe bağlı `sp_imza_anahtari` (PEM RSA özel anahtar) ile `RSA-SHA256`
  imzalanır; anahtar tanımlı değilse istek imzasız gider ve sunucu uyarı loglar.

**JIT kullanıcı ve üyelik**

- Eşleşme sırası: `sso_kimlik` (sağlayıcı + dış kimlik) → e-posta → yeni kullanıcı.
- E-posta ile mevcut kullanıcıya bağlanma **yalnız** o kullanıcı sağlayıcının organizasyonunda
  aktif üyeyse yapılır; başka bir organizasyonun üyesiyle eşleşme `403 yetki_yok` ile reddedilir
  ve jeton verilmez. Böylece kendi IdP'sini tanımlayan bir organizasyon yöneticisi, kurbanın
  e-postasına assertion ürettirip başka kiracının hesabını devralamaz. OIDC'te IdP
  `email_verified=false` bildirdiyse e-posta adımı hiç denenmez (`401 sso_dogrulanamadi`).
- SSO'dan gelen yeni kullanıcı `eposta_dogrulandi=true` ve rastgele parola özetiyle oluşturulur;
  pasif kullanıcı `403` ile reddedilir.
- Üyelik yoksa `KUTYAI_SSO_OTOMATIK_UYELIK=true` ise `son_kullanici` rolüyle eklenir, değilse
  `403 yetki_yok`.
- Yönlendirme akışında `KUTYAI_SSO_YENIDEN_YONLENDIRME` adresine **60 sn** ömürlü imzalı bir
  `kod` eklenir; jetonlar `POST /sso/kod-degistir` ile alınır. Kod durumsuz bir jetondur:
  **sunucu tarafı tek-kullanım denetimi yoktur**, aynı kod 60 sn içinde yeniden kullanılabilir.
- Denetim izi: `kimlik.sso_giris` ve `sso.saglayici_*` olayları organizasyon ve IP ile yazılır.

**Doğrulama durumu:** OIDC/SAML akışları bu depoda sahte IdP ile koşulur (OIDC:
`httpx.MockTransport`; SAML: gerçekten imzalanmış yanıt) ve negatif testler vardır: imza,
`audience`, `Destination`, süre penceresi, tekrar oynatma, XSW, XXE, `nonce`, `state`.
`InResponseTo` hem doğrulama biriminde hem `/saml/acs` ucunda (`RelayState` → `AuthnRequest`
kimliği bağlanarak) sınanır; `sp_imza_anahtari` ile imzalı `AuthnRequest` ve `/saml/baslat`
yolu da test kapsamındadır. Ayrıca `RelayState`'siz ACS (`400`), başka sağlayıcının state'i
(`401`), aynı `state`in ikinci kullanımı, `email_verified=false`, başka organizasyon üyesinin
e-postası (`403`), `http` `issuer`/`idp_sso_url`, bulut metadata adresi ve süre alanları
eksik SAML yanıtı negatif testlerle sınanır. Gerçek bir IdP veya SAML sunucusuna karşı
çalıştırma kanıtı görülmedi.

## 8. Ödeme ve webhook güvenliği

- Sağlayıcı seçimi `KUTYAI_ODEME_SAGLAYICI` (`yerel` varsayılan, `stripe`).
- **Stripe webhook'u kimlik doğrulaması kullanmaz**; tek doğrulama `Stripe-Signature` başlığıdır:
  - biçim `t=<zaman>,v1=<imza>`; HMAC-SHA256 girdisi `{t}.{ham gövde}`,
  - `KUTYAI_STRIPE_WEBHOOK_SIRRI` ile hesaplanır ve `hmac.compare_digest` (sabit zamanlı) ile karşılaştırılır,
  - zaman toleransı **300 sn**; aşılırsa imza geçersiz sayılır,
  - sır tanımsız ya da imza hatalı → `502 webhook_imzasi_gecersiz`; sağlayıcı `stripe` değilse uç
    `400 odeme_saglayici_yok` döner.
- Stripe API anahtarı `KUTYAI_STRIPE_GIZLI_ANAHTAR`. İki değer de ortam değişkenidir ve Helm'de
  **Secret** altında tutulur (§10). İmza doğrulanmadan abonelik/fatura üzerinde hiçbir yazma yapılmaz.
- **Ödeme onayı:** abonelik checkout oturumu `client_reference_id` + `metadata[abonelik_id]`/
  `metadata[fatura_id]` ile etiketlenir; abonelik `dis_id` (Stripe abonelik kimliği, yoksa oturum
  kimliği) ve fatura `dis_id` (oturum kimliği) bu kimliklerle saklanır. Ödeme onayı webhook'la
  gelene kadar abonelik `deneme`, fatura `taslak` kalır ve **plan kotası yazılmaz**; onay
  (`checkout.session.completed` / `invoice.paid`) geldiğinde abonelik `aktif` olur, kota uygulanır ve
  gerçek `sub_…` kimliği aboneliğe yazılır. Webhook olayı `metadata` ve `dis_id` üzerinden eşlenir;
  hiçbir kayda oturmayan olay `uygulandi: false` döner ve günlüğe yazılır (durum değişmez), böylece
  yabancı/gecikmiş bir olay başka kiracının aboneliğini etkilemez.
- `yerel` sağlayıcıda manuel tahsilat (`POST /faturalama/faturalar/{id}/odendi`) yalnız organizasyon
  yönetim rollerine (`sahip`/`yonetici`) açıktır ve yalnız `yerel` sürücüde çalışır.
- Abonelik ve faturalar `org_id` ile ayrılır; başka organizasyonun faturası `404` döner.
- **Durum:** `402 abonelik_gecikmis` kodu tanımlıdır ve abonelik durumu `erisim` alanında
  raporlanır; ancak uçlarda **erişim kapısı olarak zorlanmaz** — sohbet yalnız kota denetler
  (plan kotası dahil, `KotaKapsami.organizasyon`).

## 9. Çok kiracılılık ve organizasyon izolasyonu

- Kiracı = **organizasyon**. Kiracıya bağlı kayıtlar `org_id` taşır; hangi tabloların zorunlu
  olduğu `bdm_veritabani/modeller.py` → `ORG_ZORUNLU_TABLOLAR` içindedir. **RLS yoktur**;
  izolasyon uygulama sorgularındaki `org_id` süzgeciyle sağlanır.
- Aktif organizasyon `X-Organizasyon` başlığı → jeton `org` claim'i → API anahtarının
  organizasyonu → kullanıcının ilk aktif üyeliği sırasıyla çözülür (`kaynak/API.md` §15).
- Hiçbiri yoksa kullanıcı **varsayılan organizasyona** eklenir (tek kiracılı kurulum ve ilk
  kullanıcı kolaylığı); bu ekleme bir üyelik satırı oluşturur, mevcut bir organizasyona
  gizlice erişim sağlamaz.
- Yetki kararı `kullanici.rol` değil **üyelik rolü** üzerinden verilir; `sahip` her zaman
  yetkilidir. Son `sahip` düşürülemez/silinemez (`409 gecersiz_gecis`) ve `sahip` rolüne yükseltme
  yalnız mevcut aktif `sahip` tarafından yapılabilir (`sahip`/`yonetici` uçlarında `403 yetki_yok`).
- Askıya alınmış organizasyon (`durum=askida`) erişimi her çözüm yolunda (başlık, jeton `org`
  claim'i, API anahtarı, ilk üyelik) `403 yetki_yok` ile keser; başlıkla eşleşen API anahtarı da
  bu denetimden muaf değildir.
- Başlıkla başka organizasyon istenirse: API anahtarının organizasyonu uyuşmuyorsa
  `403 org_erisim_yok`, kullanıcının üyeliği yoksa `403 yetki_yok`.
- Başka organizasyonun kaydı, kayıt yokmuş gibi `404` döner (varlık sızdırılmaz).
- Kotalar organizasyon kapsamında da tutulur (`kota.kapsam=organizasyon`,
  `kapsam_id=org_id`); plan limitleri bu satıra yazılır ve kullanıcı/anahtar kotasından önce
  denetlenir.
- Denetim izi (`islem_kaydi`) kayıtlarında `org_id` bulunur; organizasyon silinirse
  `ON DELETE SET NULL` ile null'lanır (kayıt korunur).

## 10. Sırların saklanması ve dağıtımı

| Ortam | Sırların yeri | Not |
|---|---|---|
| Yerel/geliştirme | kök `.env` (`KUTYAI_*`) | `KUTYAI_ORTAM=gelistirme` iken eksik sırlar geçici üretilir ve uyarı loglanır |
| Docker Compose | `dagitim/.env` | `KUTYAI_GIZLI_ANAHTAR`, `KUTYAI_SIFRELEME_ANAHTARI`, `KUTYAI_SMTP_SIFRE`, `KUTYAI_STRIPE_*`, `KUTYAI_ARAC_IMZA_ANAHTARI` burada; dosyayı şifreli kasada saklayın |
| Kubernetes (Helm) | `secrets.values` → Secret ya da `secrets.existingSecret` | `config` (ConfigMap) **sırsız** ayarlar içindir; ConfigMap küme içinde okunabilir |

Helm tarafının işletim kuralları:

- `values.yaml` içinde hiçbir sır düz metin tutulmaz; parola içeren `KUTYAI_VERITABANI_URL`
  `config` yerine `secrets.values` altına yazılır.
- Boş bırakılan `KUTYAI_GIZLI_ANAHTAR` (64 karakter) ve `KUTYAI_SIFRELEME_ANAHTARI` (Fernet)
  rastgele üretilir ve yükseltmede `lookup` ile korunur; üretilen değeri hemen kasadaki kopyasına
  alın. Üretimde kendi değerlerinizi vermek ya da `secrets.existingSecret` kullanmak önerilir.
- Sırlar değişince pod'lar `checksum/sirlar` ek açıklamasıyla kendiliğinden yenilenir.
- `KUTYAI_GIZLI_ANAHTAR` değişirse tüm erişim/yenileme jetonları geçersizleşir;
  **Fernet anahtarı kaybolursa** şifreli upstream API anahtarları ve SSO sırları açılamaz.
- Kubernetes `Secret` yalnız base64'tür: etcd şifreleme-at-rest, sıkı RBAC ve/veya harici sır
  yöneticisi (SOPS, SealedSecrets, Vault CSI, External Secrets) önerilir. Bu iki önlem chart'ın
  kapsamı dışındadır ve varsayılan olarak **kapalıdır** — kümede ayrıca yapılandırılmalıdır.

## 11. Dosya yükleme güvenliği

`arkauc/app/api/dosyalar.py` + `arkauc/app/servisler/dosya.py`.

| Denetim | Uygulama |
|---|---|
| Tür | `mime_coz`: istemcinin bildirdiği MIME `application/octet-stream`/boşsa **uzantıdan** türetilir; sonuç izinli listede değilse `400 dosya_tur_desteklenmiyor`. İzinli: `text/*`, `image/*`, `application/pdf`, `application/json` |
| Boyut | `KUTYAI_DOSYA_MAKS_MB` (varsayılan 25 MB). Gövde **blok blok** (64 KB) okunur; sınır aşıldığı anda istek `413 dosya_cok_buyuk` ile reddedilir ve **diske hiçbir şey yazılmaz** — tek istekle disk doldurulamaz |
| Yol | Dosya adından yol üretilmez: hedef `uuid4`'tür (`<kök>/<org_slug>/<uuid4>`); disk yolları istemci girdisinden bağımsızdır (path traversal yok) |
| İndirme başlığı | `Content-Disposition` ASCII yedek adı CR/LF ve tırnaktan süzülür; asıl ad RFC 5987 `filename*` ile yüzde kodlanır (başlık enjeksiyonu engeli) |
| Metin çıkarımı | `pypdf` ile PDF, `text/*` ve `application/json` doğrudan; bozuk/taranmış PDF'te metin boş kalır (uydurma yok) ve gerekçe döner. Çıkarılan metin maskelenir |
| Kapsam | Tüm dosya uçları personeldir ve aktif organizasyona süzülür; başka organizasyonun dosyası `404` döner (indirme ve medya çözümleme dahil) |

Operasyonel notlar: dosya dizininin izinlerini yalnız uygulama kullanıcısına verin; yedekleri
şifreli kasada tutun (içerik ham kişisel veri olabilir) ve `KUTYAI_DOSYA_DIZINI`'ni
yükleme/saklama politikasına dahil edin (`kaynak/ISLETIM.md` §12).

## 12. Araç çağrısı ve webhook güvenliği

`arkauc/app/servisler/arac.py`.

- **SSRF:** Webhook adresi v1 `temel_url` denetiminden geçer (`_adres_dogrula`: yalnız `http`/
  `https`) ve **`https` zorunludur**; `KUTYAI_ARAC_YEREL_IZIN=true` iken yerel ağa `http` kabul
  edilir (üretimde kapalı tutun). Denetim kara liste değildir: konak küçük harfe indirilip
  sondaki noktalar kırpılır (`metadata.google.internal.` de yakalanır), literal IP'ler — eski
  sayısal yazımlar (`2852039166`, `0xA9FEA9FE`, `0177.0.0.1`) dahil — `ipaddress` aralıklarıyla
  denetlenir ve alan adları `getaddrinfo` ile **çözümlenip** dönen tüm adresler aynı kurallarla
  sınanır. Link-local (`169.254.0.0/16`, `fe80::/10`), multicast, tanımsız ve metadata adresleri
  (`169.254.169.254`, `100.100.100.200`, `metadata.google.internal`) ile `::ffff:` eşlemeleri her
  koşulda reddedilir; loopback/özel/ULA adresler ve çözümlenemeyen konaklar yalnız yerel izin
  kipinde kabul edilir. Yönlendirmeler **izlenmez** (`follow_redirects=False`; 3xx yanıt hata
  sayılır) — böylece denetim sonrası başka bir adrese sıçrama (redirect tabanlı SSRF) engellenir.
  Yerel izin kipinde bile çağrı anında adres yeniden denetlenir.
- **BDM `temel_url`:** Operatör yapılandırması olduğu için yerel ağa izin verilir (yerel model
  sunucuları loopback/özel ağda çalışır); link-local ve metadata adresleri burada da reddedilir.
- **İmza:** Her webhook isteği `X-Kutyai-Imza: sha256=<hmac>` başlığıyla imzalanır; HMAC-SHA256,
  gövde üzerinden. Anahtar `KUTYAI_ARAC_IMZA_ANAHTARI`; **tanımsızsa** oturum jetonlarını imzalayan
  `KUTYAI_GIZLI_ANAHTAR` doğrudan kullanılmaz, ondan HMAC-SHA256 ile ayrı bir anahtar türetilir
  (`hmac(gizli_anahtar, "arac-imza")`) — böylece webhook alıcısı jeton imzalama sırrını ele
  geçirmez; üretimde yine de bağımsız bir `KUTYAI_ARAC_IMZA_ANAHTARI` tanımlayın. Alıcı taraf
  imzayı sabit zamanlı karşılaştırmayla doğrulamalı ve zaman damgası/tekrar saldırısına karşı
  kendi önlemini almalıdır (uygulama nonce göndermez).
- **Sırlar:** Araç başlıkları (`Authorization` vb.) Fernet ile şifrelenerek saklanır; API
  yanıtlarında değerler **maskelenir** (`basliklari_maskele`). Çözülemeyen şifreli başlık kaydı
  `400 arac_basliklar_gecersiz` üretir (sessizce imzasız istek gönderilmez).
- **Kaynak sınırları:** 10 sn zaman aşımı, 64 KB yanıt sınırı (aşılırsa `arac_yanit_cok_buyuk`)
  ve araç döngüsü için `KUTYAI_ARAC_MAKS_TUR` tur sınırı (aşılırsa `400 arac_tur_siniri`);
  argümanlar JSON Schema ile doğrulanır (şema dışı alan/eksik zorunlu alan reddedilir).
- **Yetki:** Araç tanımlama/düzenleme yalnız organizasyon yöneticilerine (`sahip`/`yonetici`)
  açıktır; çağrı günlüğü personel tarafından okunabilir. Araçlar organizasyon kapsamlıdır,
  `slug` organizasyon içinde tekildir.
- **Yerleşik araçlar:** `hesap_makinesi` `ast` ile ayrıştırılır ve yalnız izinli işleçler
  değerlendirilir (ifade 200 karakter, üs 64, taban 10⁹ sınırı); `eval`/`exec` yoktur.
