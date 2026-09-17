# KutyAI — Mimari

```
İstemciler              Sunucu                      Modeller
──────────              ──────                      ────────
onuc (Next.js)  ──┐
                  ├──► arkauc (FastAPI, /api/v1) ──┬──► bdm_listesi        (katalog)
yonetim_paneli ───┘                                ├──► bdm_hazırlama_ucu  (doğrula/çek/manifest)
   (Next.js)                                       ├──► bdm_yönetim_ucu    (başlat/durdur/log)
                                                   ├──► bdm_konusma_gecmisi(yazıcı/maskeleme/dışa aktarım)
                                                   └──► bdm_veritabani     (SQLAlchemy + Alembic)
                                                              │
                                            upstream: OpenAI · Azure · OpenRouter
                                                      Ollama (yerel REST)
                                                      vLLM / TGI (Docker + GPU)
```

## Katmanlar

| Katman | Sorumluluk | Bağımlı olduğu |
|---|---|---|
| `arkauc/app/api` | HTTP uçları, doğrulama, yetki | çekirdek, modüller |
| `arkauc/app/servisler` | upstream istemci, akış, kota, kimlik, posta, konteyner, dosya, araç, RAG/gömme, medya, ödeme, SSO | çekirdek |
| `arkauc/app/cekirdek` | ayarlar, hata zarfı, güvenlik, bağımlılıklar, denetim, router keşfi, dil katalogları (i18n), organizasyon çözümü | `bdm_veritabani` |
| `bdm_listesi` | BDM kaydı şeması + CRUD + sağlayıcı matrisi | `bdm_veritabani` |
| `bdm_hazırlama_ucu` | erişim doğrulama, model çekme, konteyner manifesti, ön kontrol | `bdm_listesi`, konteyner sözleşmesi |
| `bdm_yönetim_ucu` | yaşam döngüsü durum makinesi, sağlık, log akışı, sürücü durumu | konteyner sürücüleri |
| `bdm_konusma_gecmisi` | mesaj/kullanım yazımı, maskeleme, sorgu, dışa aktarım, saklama | `bdm_veritabani` |
| `bdm_veritabani` | 25 tablo (v1'de 12; v2 organizasyon, üyelik, plan/abonelik/fatura, dosya, RAG vektörü, araç ve SSO tablolarını ekledi), async oturum, Alembic | — |

Kiracıya bağlı tablolar `org_id` taşır; zorunlu listesi `bdm_veritabani/modeller.py` →
`ORG_ZORUNLU_TABLOLAR` içindedir.

## Dil (i18n) katmanı

Sunucu ve arayüzler dili birbirinden bağımsız çözer; ikisi de aynı düşme zincirini kullanır:
desteklenen dil → Türkçe → anahtarın kendisi. Desteklenen diller `tr` (varsayılan) ve `en`.

| Katman | Dosya | Davranış |
|---|---|---|
| Sunucu katalogları | `arkauc/ceviriler/{tr,en}.json` | Anahtar → mesaj; `cekirdek/i18n.py` önbellekle okur |
| Sunucu dili çözme | `arkauc/app/cekirdek/i18n.py` | `dil_coz(Accept-Language)` etiket kökünü eşler (`en-US` → `en`); bilinmeyen → `tr` |
| Hata zarfı | `arkauc/app/cekirdek/hatalar.py` | `istek_dili` başlıktan dili seçer; `hata.mesaj` o dilde, `hata.kod` dilden bağımsız |
| Dil uçları | `arkauc/app/api/i18n.py` | `GET /i18n/diller`, `GET /i18n/sozluk/{dil}` — kimlik gerektirmez |
| Arayüz katalogları | `onuc/lib/sozluk/`, `yonetim_paneli/lib/sozluk/` | `tr` kaynak katalog; `en` `Record<keyof typeof tr, string>` ile derleme zamanında tamlık denetimi |
| Arayüz bağlamı | `lib/dil.tsx` | `DilSaglayici` + `useDil` + `t(anahtar, değişkenler)`; `{ad}` yer tutucuları |
| Sunucu bileşeni dili | `lib/sunucu-dil.ts` | `dilOku()` `kutyai.dil` çerezini okur; `<html lang>` sunucuda çerezden gelir |
| React dışı çözüm | `onuc/lib/tarayici-dil.ts`, `yonetim_paneli/lib/sozluk/index.ts` → `aktifDil()` | `localStorage` → çerez → varsayılan |

- Arayüzler dil tercihini `localStorage` **ve** `kutyai.dil` çerezinde tutar (`path=/`, bir yıl,
  `SameSite=Lax`); sunucu bileşenleri çerezi, tarayıcı modülleri `localStorage`'ı tercih eder.
  Dil değişiminde hem çerez hem `<html lang>` güncellenir.
- Arayüzler her API isteğinde `Accept-Language` gönderir, böylece hata mesajları arayüzde
  seçilen dille aynı olur.
- Arayüz katalogları yereldir; arayüzler `/i18n/sozluk` ucunu çağırmaz (uç, arayüz dışı
  istemciler için vardır).

## Çok kiracılılık

Kapsam (kiracı) **organizasyon**tur. Kiracıya bağlı kayıtlar `org_id` ile ayrılır; zorunlu
tablolar `bdm_veritabani/modeller.py` → `ORG_ZORUNLU_TABLOLAR` içinde listelenir (`bdm`,
`konusma`, `api_anahtari`, `dosya`, `vektor_belgesi`, `vektor_parcasi`, `arac`, `abonelik`,
`fatura`, `posta_sablonu`, `sso_saglayici`).

**Aktif organizasyon** tek yardımcıda (`cekirdek/organizasyon.py` → `organizasyon_coz`) şu
öncelikle çözülür:

1. `X-Organizasyon: <slug>` başlığı (`ORG_BASLIGI = "x-organizasyon"`),
2. erişim jetonundaki `org` claim'i,
3. API anahtarının bağlı olduğu organizasyon (`api_anahtari.org_id`),
4. kullanıcının ilk aktif üyeliği.

Hiçbiri yoksa kullanıcı **varsayılan organizasyona** eklenir; bu, tek kiracılı kurulumların
ve ilk kullanıcının çalışması içindir. Sıra `kaynak/API.md` §15'te sözleşmedir.

| Konu | Uygulama |
|---|---|
| Bağımlılıklar | `aktif_organizasyon` (panel/JWT uçları), `istemci_organizasyonu` (JWT **veya** `kuty_` anahtarı; sohbet uçları) |
| Yetki | Karar `uyelik.rol` üzerinden verilir (`gecerli_personel`), `kullanici.rol` üzerinden değil; `sahip` her zaman yetkilidir |
| Askıya alınmış org | `durum=askida` → `403 yetki_yok` |
| Başlık uyuşmazlığı | API anahtarının org'u başlıkla uyuşmuyorsa `403 org_erisim_yok`; üyelik yoksa `403 yetki_yok` |
| Çapraz org okuma | Başka organizasyonun kaydı kayıt bulunamıyormuş gibi `404` döner |
| Varsayılan atama | ORM'e doğrudan eklenen nesnede `org_id` boşsa `bdm_veritabani/oturum.py`'deki `before_flush` kancası varsayılan organizasyonu yazar (test/tohum kolaylığı) |
| Arayüz tarafı | Panel seçimi `yonetim_paneli/lib/aktif-organizasyon.ts` içinde saklanır, her isteğe `X-Organizasyon` başlığı eklenir; değişim `POST /kimlik/organizasyon-sec` ile jetonu tazeler |

## Dosya deposu (spec §3)

`arkauc/app/servisler/dosya.py` + `arkauc/app/api/dosyalar.py`. Dosyalar
`<KUTYAI_DOSYA_DIZINI ya da bdm_veritabani/dosyalar>/<org_slug>/<uuid4>` altında tutulur;
`dosya.yol` mutlak yolu, `sha256`/`boyut`/`mime` ise meta veriyi taşır. Uçlar personeldir ve
aktif organizasyona kapsanır; başka organizasyonun kaydı `404` döner.

| Konu | Uygulama |
|---|---|
| MIME çözümü | `mime_coz`: `application/octet-stream`/boş tür uzantıdan türetilir (`UZANTI_MIME`); izinli listeler `text/*`, `image/*`, `application/pdf`, `application/json` — değilse `400 dosya_tur_desteklenmiyor` |
| Boyut | `KUTYAI_DOSYA_MAKS_MB`; yükleme blok blok okunur ve sınır aşılırsa diske yazılmadan `413 dosya_cok_buyuk` |
| Metin çıkarımı | `text/*` ve `application/json` doğrudan; `application/pdf` için `pypdf`; çıkarılamazsa `metin` boş kalır ve gerekçe `dosya_metni_cikarilamadi` olur (**uydurma metin yok**) |
| KVKK | Çıkarılan metin maskeleme kuralından geçirilip `dosya.metin`'e yazılır; sohbete giden bağlam da bu maskeli metindir |
| Sohbet eki | `baglam_metni` dosyaları `--- <ad> ---` başlığıyla birleştirir ve `KUTYAI_DOSYA_BAGLAM_KR` karakterde keser |
| İndirme | `Content-Disposition: attachment` + RFC 5987 `filename*` (başlık enjeksiyonuna karşı ASCII yedek ad süzülür) |

## Araç çağırma döngüsü (spec §4)

`arkauc/app/servisler/arac.py` (tanım, doğrulama, çalıştırma) + `arkauc/app/servisler/akış.py`
(döngü). Araçlar organizasyon kapsamlıdır; `slug` organizasyon içinde tekildir.

- **Türler:** `webhook` (dış HTTP) ve `yerlesik` (`hesap_makinesi` — `ast` ile güvenli ifade
  değerlendirme, sınırlı işleç/üs/uzunluk; `zaman` — ISO damga). Yerleşik slug listesi
  `YERLESIK_SLUGLAR`, varsayılan JSON şemaları `YERLESIK_SEMALAR`.
- **Döngü:** modele OpenAI `tools` biçiminde tanıtılır (`arac_tanimi`) → yanıt `tool_calls`
  içerirse argümanlar JSON Schema'ya göre doğrulanır (`argumanlari_dogrula`) → araç çalışır →
  sonuç `rol=tool` mesajı olarak eklenir → model yeniden çağrılır. Tur sınırı
  `KUTYAI_ARAC_MAKS_TUR`; aşılırsa `400 arac_tur_siniri`.
- **Kayıt:** her çağrı `arac_cagrisi` tablosuna yazılır (`argumanlar`, `sonuc`, `durum`,
  `gecikme_ms`, `hata`) ve konuşmaya `rol=arac` mesajı eklenir.
- **Hata siyaseti:** çalıştırma hataları istisna olarak yükselmez; `{"hata": ...}` gövdesiyle
  modele döner ki model hata metnini görebilsin. Yalnız şema ihlalleri `400` olur.
- **Webhook:** HTTPS zorunlu (`KUTYAI_ARAC_YEREL_IZIN=true` ile yerel HTTP), v1 `temel_url`
  SSRF denetimi yeniden kullanılır (`_adres_dogrula`: konak normalizasyonu + `ipaddress`
  aralıkları + çözümlenen adresler; loopback/özel/link-local/metadata reddedilir),
  `X-Kutyai-Imza: sha256=<hmac>` (anahtar `KUTYAI_ARAC_IMZA_ANAHTARI`; boşsa jeton sırrından
  HMAC ile AYRI anahtar türetilir), 10 sn zaman aşımı, 64 KB yanıt sınırı. Başlıklar Fernet ile
  şifreli saklanır, yanıtlarda maskelenir.
- **SSE:** `arac_cagrisi {ad, argumanlar}` ve `arac_sonucu {ad, durum, ozet}`; araç turu
  bitmeden içerik parçaları yayınlanmaz (sıra korunur).

## Bilgi tabanı / RAG (spec §5)

`arkauc/app/servisler/gomme.py` (gömme üretimi) + `arkauc/app/servisler/vektor.py` (parçalama,
yazım, arama) + `arkauc/app/api/rag.py`.

- **Gömme:** upstream `POST {bdm.temel_url}/embeddings`, model `bdm.gomme_modeli`; alan boşsa
  `400 gomme_modeli_yok`, sağlayıcı hatası `502 rag_gomme_hatasi`.
- **Parçalama:** ~800 karakter, 120 karakter örtüşme, cümle/kelime sınırına saygılı
  (`PARCA_BOYUT`, `ORTUSME`, `MIN_PARCA`).
- **Depolama:** `vektor_belgesi` + `vektor_parcasi` (`vektor` JSON `list[float]`, isteğe bağlı
  `vektor_pg`); kaynak `metin | dosya`.
- **Arama iki yollu:** `pgvector` uzantısı ve `vektor_pg` kolonu varsa `<=>` operatörüyle SQL,
  yoksa Python kosinüs. Seçim `arama_yolu()` ile yapılır ve yanıttaki `ayrinti.yol` bunu
  bildirir. Taşınabilir yol için belgelenen ölçek sınırı 200.000 parçadır; üstünde pgvector
  önerilir.
- **Sohbet:** `rag: true` + opsiyonel `rag_belge_idleri`; en iyi `KUTYAI_RAG_UST_K` parça
  sistem istemine `--- Bilgi tabanı ---` başlığıyla eklenir, kullanılan parçalar `kaynaklar`
  olarak döner. Yeniden gömme: `POST /rag/belgeler/{id}/yeniden-gom`.

## Medya üretimi (spec §8)

`arkauc/app/servisler/medya.py` + `arkauc/app/api/medya.py`.

| Yetenek | Upstream | Bayrak | Yanıt |
|---|---|---|---|
| Görsel | `POST {temel_url}/images/generations` | `bdm.yetenekler.gorsel` | `[{dosya_id, ad, mime, boyut}]` |
| Ses | `POST {temel_url}/audio/speech` | `bdm.yetenekler.ses` | `{dosya_id}` |
| Ses çözümü | `POST {temel_url}/audio/transcriptions` (multipart) | `bdm.yetenekler.ses` | `{metin}` |

Yetenek kapalıysa `400 medya_desteklenmiyor`. Yazma rolleri `sahip`/`yonetici`/`operator`;
üretilenler `dosya` tablosuna yazılır ve her deneme (başarılı/hatalı) `kullanim_kaydi` işlenir.

## Ödeme adaptörü (spec §6)

`arkauc/app/servisler/odeme.py` içindeki `OdemeSaglayici` Protocol'ü üç uçtan oluşur:
`abonelik_baslat`, `odeme_oturumu`, `webhook_isle` (dönüşler `{dis_id, url|None, saglayici}`).
Sürücü `KUTYAI_ODEME_SAGLAYICI` ile seçilir:

| Sürücü | Davranış |
|---|---|
| `yerel` | Sağlayıcı çağrısı yok; fatura `POST /faturalama/faturalar/{id}/odendi` ile elle işaretlenir. Offline tam çalışır |
| `stripe` | Checkout oturumları + `Stripe-Signature` HMAC-SHA256 doğrulamalı webhook (`webhook_isle`) |

`POST /faturalama/abonelik` plan limitlerini organizasyon kotasına yazar
(`plan_kotasini_uygula`: `dahil_istek`, `dahil_token`, sayaç sıfırlama); abonelik durumu
`erisim_var_mi` ile `erisim` alanında raporlanır (`gecikmis`/`iptal` → false).

## SSO (spec §7)

Sağlayıcılar organizasyon kapsamlı (`sso_saglayici`), kimlikler `sso_kimlik`
(`unique(saglayici_id, dis_id)`). İki akış da aynı giriş tamamlama yolunu kullanır:
kullanıcı eşleme → üyelik → denetim → jeton (yönlendirme kipinde 60 sn ömürlü imzalı `kod`).

| Bileşen | Dosya | Özet |
|---|---|---|
| OIDC | `arkauc/app/servisler/sso_oidc.py` | Keşif (`.well-known/openid-configuration`), PKCE `S256`, HS256 imzalı `state` (10 dk; sağlayıcı, `nonce`, `code_verifier`, dönüş adresi), `id_token` JWKS doğrulaması + `iss`/`aud`/`exp`/`iat` ve `nonce` denetimi |
| SAML | `arkauc/app/servisler/sso_saml.py` | HTTP-Redirect bağlamalı `AuthnRequest` (`RelayState` = state; opsiyonel `RSA-SHA256` imzası), `POST .../saml/acs` `SAMLResponse` doğrulaması: `signxml` XML-DSig, XSW savunması, Audience/Recipient/Destination, zaman penceresi (±120 sn), `Assertion ID` tekrar oynatma (10 dk bellek kümesi) |
| Ortak | `arkauc/app/api/sso.py` | Sağlayıcı CRUD, `/baslat` kapısı, JIT kullanıcı/üyelik, `POST /sso/kod-degistir` |

## Helm dağıtımı (spec §11)

`dagitim/helm/kutyai/` chart'ı Compose dağıtımının Kubernetes karşılığıdır: aynı `KUTYAI_*`
adları, aynı portlar ve sağlık uçları. Sırsız değerler ConfigMap'e (`config`), gizliler
Secret'a (`secrets.values` ya da `secrets.existingSecret`) gider; boş bırakılan
`KUTYAI_GIZLI_ANAHTAR`/`KUTYAI_SIFRELEME_ANAHTARI` rastgele üretilir ve yükseltmede `lookup`
ile korunur. Şablonlar: Deployment/Service (arka-uc, onuc, panel), ConfigMap, Secret, PVC,
HPA, Ingress, Namespace, ServiceAccount ve `post-install,pre-upgrade` hook'lu Alembic göç
Job'u. Ayrıntı: `dagitim/helm/kutyai/README.md`, işletim `kaynak/ISLETIM.md` §8.

## Router keşfi

`arkauc/app/main.py` içindeki `YONLENDIRICILER` listesi dondurulmuştur. Modül yoksa uyarı loglanır ve atlanır; bu, klasör sahipliğiyle paralel geliştirmeyi mümkün kılar. Yeni uç eklemek için ilgili klasörde `router` tanımlayan bir modül oluşturmak yeterlidir.

## Sohbet akışı (veri yolu)

1. İstemci `POST /sohbet/akis` → `gecerli_istemci` (JWT veya `kuty_` anahtarı) + `istemci_organizasyonu` (aktif organizasyon)
2. BDM kaydı çözülür; kayıt aktif organizasyona ait değilse `404`, `hazir|calisiyor` değilse `503`
3. Kota kontrolü → aşımda `429`
4. Ek bağlam çözülür (org kapsamlı): `dosya_idleri` → maskeli çıkarılmış metin, `rag` → en yakın parçalar + `kaynaklar`, `arac_sluglari` ya da BDM `arac` yeteneği → araç tanımları
5. Kullanıcı mesajı **maskelenerek** yazılır; sistem istemi temel istem + ek bağlam olarak kurulur
6. Upstream'e istek; model `tool_calls` dönerse araçlar çalıştırılır ve döngü en fazla `KUTYAI_ARAC_MAKS_TUR` tur sürer
7. Parçalar SSE ile akıtılır (`arac_cagrisi`/`arac_sonucu`, `parca`), ardından `kullanim` ve `bitti` (varsa `kaynaklar`/`arac_cagrilari`)
8. Yanıt tamamlanınca asistan mesajı, token kullanımı ve `kullanim_kaydi` yazılır
9. İstemci koparsa upstream isteği iptal edilir; kısmi yanıt kaydedilmez

## Kararlar

| Karar | Gerekçe |
|---|---|
| Tek backend süreci, klasör başına router | Mikroservis karmaşası olmadan net sınırlar |
| Enum'lar VARCHAR (`native_enum=False`) | Aynı şema SQLite + Postgres |
| Motor tembel + SQLite'ta NullPool | Testler arası olay döngüsü izolasyonu |
| Hata zarfı Türkçe mesaj + makine kodu | Arayüz doğrudan gösterir, log ayrıştırılabilir |
| Konteyner sürücüsü Protocol + Sahte | GPU'suz geliştirme ve deterministik test |
| Konuşma kaydı yazma anında maskeleme | Geri dönüşü olmayan KVKK uyumu |
| SMTP yokken konsol sürücüsü | Posta sunucusu olmadan uçtan uca test edilebilirlik |
| Aktif organizasyon tek yardımcıda, 4 kademeli çözüm | Her uç aynı kuralı uygular; sorgular `org_id` süzgecini açıkça taşır (RLS yok) |
| Dil katalogları sunucuda ve arayüzde ayrı dosyalar | Arayüz derlemesi API'ye bağlı kalmasın; sunucu hata mesajları ile arayüz metinleri bağımsız evrilsin |
| RAG'da arama yolu otomatik seçilir (`pgvector` → Python) ve `ayrinti.yol` ile bildirilir | Kurulum tek veritabanı sürücüsüne bağlı kalmasın; performans yolu varsa sessizce kullanılsın |
| Araç çalıştırma hataları modele metin olarak döner, yalnız şema ihlali `400` olur | Model hatayı görüp turu düzeltebilsin; istemci akışı kesilmesin |
| Dosya metni de kayıt anında maskelenir ve sohbete maskeli bağlam gider | KVKK sınırı tek noktada kalsın; ek yetenekler onu aşmasın |
| SSO akışı durumsuz `state`/`kod` ile çalışır (sunucu tarafı oturum yok) | Çok süreçli dağıtımda ek depolama gerekmesin; PKCE ve sağlayıcı kod tek kullanımlığı korumayı taşısın |
| Ödeme sağlayıcısı Protocol + iki sürücü (`yerel`, `stripe`) | Offline kurulum tam çalışsın, Stripe opsiyonel kalsın |
