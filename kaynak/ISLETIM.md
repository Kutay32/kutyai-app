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

## 8. Kubernetes (Helm) işletimi

Chart `dagitim/helm/kutyai`; kurulum `kaynak/KURULUM.md` §6, değerlerin tamamı
`dagitim/helm/kutyai/values.yaml` ve chart README §4. Tüm ayarlar Compose ile **aynı**
`KUTYAI_*` adlarını taşır; sırsızlar `config:` (ConfigMap), gizliler `secrets.values:`
(Secret) altına yazılır.

### 8.1 Günlük değerler

| İhtiyaç | Değer yolu |
|---|---|
| Replika sayısı | `<arka-uc\|onuc\|panel>.replicaCount` |
| İmaj deposu/etiketi | `<bileşen>.image.repository/tag`, `migration.image.*` |
| CPU/bellek | `<bileşen>.resources.requests/limits` |
| Otomatik ölçekleme | `arkauc.autoscaling.{enabled,minReplicas,maxReplicas,targetCPUUtilizationPercentage,behavior}` |
| Kalıcı veri (`/veri`) | `arkauc.persistence.data.{enabled,size,storageClassName,accessModes,existingClaim}` |
| HF model önbelleği | `arkauc.persistence.hfCache.*` (etkinse `KUTYAI_HF_ONBELLEK=/veri/hf-onbellek`) |
| BDM konteynerleri | `arkauc.dockerSocket.enabled` (varsayılan **kapalı**) |
| Ortam değişkeni | `config`, `secrets.values`, `<bileşen>.extraEnv` |
| Ingress | `ingress.{enabled,className,hosts,tls,annotations}` |
| Sağlık sondaları | `<bileşen>.livenessProbe/readinessProbe` |
| Yerleşim/güvenlik bağlamı | `<bileşen>.nodeSelector/tolerations/affinity`, `<bileşen>.securityContext`, `imagePullSecrets` |

Varsayılan olarak `config.KUTYAI_ORTAM=uretim` gelir (Compose örneğinde `gelistirme`);
`config.KUTYAI_VERITABANI_URL` SQLite'tır ve `/veri` hacmini kullanır.

### 8.2 Alembic göçü (Job)

- `templates/migration-job.yaml` arkauc imajıyla `python -m alembic upgrade head` çalıştırır
  (Compose karşılığı: `docker compose exec arkauc python -m alembic upgrade head`).
- Hook: **`post-install,pre-upgrade`**, `hook-weight: -5`. Yükseltmede yeni sürüm
  açılmadan önce koşar ve başarısız olursa yükseltmeyi durdurur. İlk kurulumda
  `pre-install` bilinçli olarak kullanılmaz: chart'ın PVC'si henüz yokken Job pod'u
  Pending kalırdı.
- Göç tekrar çalıştırılabilir: uygulama şemayı açılışta da kurar
  (`bdm_veritabani/oturum.py` → `Taban.metadata.create_all`) ve göçler
  `create_all(checkfirst=True)` kullanır.
- SQLite'ta göç pod'una `/veri` hacmi bağlanır (`migration.mountDataVolume: true`);
  harici PostgreSQL'de `false` yapın. Kapatmak için `migration.enabled=false`.
- Dayanıklılık: `backoffLimit: 3`, `activeDeadlineSeconds: 600`.
- **Göç geri dönüşsüzdür**; yükseltmeden önce §4'teki yedeği alın.

İzleme ve elle çalıştırma (`helm install kutyai ...` ile kaynak kökü `kutyai` olur):

```bash
kubectl get job -n kutyai
kubectl logs -n kutyai job/kutyai-goc                 # Job adı: <kök>-goc
helm upgrade kutyai dagitim/helm/kutyai -n kutyai     # pre-upgrade göçünü tetikler
```

### 8.3 HPA ve ölçekleme

- HPA **varsayılan kapalıdır** (`arkauc.autoscaling.enabled: false`): varsayılan veritabanı
  SQLite ve `/veri` hacmi `ReadWriteOnce`'tur, SQLite çok pod ile paylaşılamaz; yüklenen
  dosyalar (`/veri/dosyalar`) da pod'lar arasında paylaşılmalıdır.
- Çok replika/otomatik ölçekleme için üçü birlikte gerekir: harici PostgreSQL
  (`secrets.values.KUTYAI_VERITABANI_URL`), pod'lar arası paylaşılabilir hacim
  (`arkauc.persistence.data.accessModes[0]=ReadWriteMany`, ör. NFS/CephFS) ve
  `arkauc.autoscaling.enabled=true` + `arkauc.replicaCount>=2`.
- HPA etkinken Deployment `spec.replicas` alanını yazmaz (sahibi HPA olur).
- Hedef CPU, `arkauc.resources.requests.cpu` üzerinden yüzde olarak hesaplanır; bu istek
  boşaltılırsa ölçekleme çalışmaz. Varsayılanlar: min 2, max 6, %70 (`autoscaling/v2`).

### 8.4 Sır yönetimi

İki mod vardır; ikisi birden yoksa şablon açık hatayla durur:

1. **`secrets.existingSecret`** — üretimde önerilen. Chart Secret üretmez; anahtarları
   SealedSecrets/SOPS/Vault CSI/External Secrets yönetir; pod'lar `envFrom.secretRef` ile okur.
2. **`secrets.create` (varsayılan `true`)** — `secrets.values` altındaki dolu anahtarlar
   Secret'a yazılır. Boş bırakılan iki anahtar **rastgele üretilir**:
   `KUTYAI_GIZLI_ANAHTAR` (64 karakter) ve `KUTYAI_SIFRELEME_ANAHTARI` (Fernet,
   32 bayt urlsafe base64). Üretilen değerler yükseltmede `lookup` ile **korunur**;
   `helm template`/`--dry-run` her çalıştırmada yeni değer üretir (yalnız yerel doğrulama).

İşletim kuralları:

- `values.yaml` içinde sır **düz metin tutulmaz**; parola içeren `KUTYAI_VERITABANI_URL`
  `config` yerine `secrets.values` altına yazılır (ConfigMap küme içinde okunabilir).
- `KUTYAI_GIZLI_ANAHTAR`/`KUTYAI_SIFRELEME_ANAHTARI` değişirse pod'lar
  `checksum/sirlar` ek açıklamasıyla kendiliğinden yenilenir.
- Üretilen değerleri okuyup kasada saklayın; **Fernet anahtarı yedeksiz kaybolursa**
  şifreli upstream anahtarları/SSO sırları açılamaz:

```bash
kubectl get secret kutyai -n kutyai \
  -o jsonpath='{.data.KUTYAI_SIFRELEME_ANAHTARI}' | base64 -d
```

### 8.5 Günlük kontroller (Kubernetes karşılıkları)

| Kontrol (§1) | Kubernetes |
|---|---|
| Servis ayakta mı | `kubectl get pods -n kutyai`; pod `Running/Ready` + probe durumu |
| Sağlık uçları | `kubectl port-forward -n kutyai svc/kutyai-arka-uc 8000:8000` → `curl localhost:8000/api/v1/saglik` |
| Günlük | `kubectl logs -n kutyai deploy/kutyai-arka-uc -f` |
| Olay/başlatma hatası | `kubectl describe pod -n kutyai <pod>` (probe, PVC, imaj çekme) |
| Sürücü/BDM durumu | Aynı API uçları; `arkauc.dockerSocket.enabled=false` ise BDM başlatılamaz |

### 8.6 Bilinen sınırlar (doğrulanmadı)

- Chart **gerçek bir kümeye kurulmadı**; doğrulama `helm lint` + `helm template` +
  `kubeconform -strict -kubernetes-version 1.29.0` ile sınırlıdır (`kaynak/KURULUM.md` §6.3).
- `dockerSocket` varsayılan kapalıdır; açmak düğümde root yetkisi demektir ve non-root pod
  ile soket grubu izinleri uyumlu olmayabilir. Model önbelleği Docker host yolu olarak
  çözülür; çok düğümlü kümede ayrı çözüm gerekir.
- `kutyai-veri` ve `kutyai-hf-onbellek` PVC'lerinde `helm.sh/resource-policy: keep` vardır:
  `helm uninstall` veriyi silmez.
- Panel `/panel` önekiyle servis edilemez (statik varlık yolları kökten istenir); panel için
  ayrı alan adı kullanın.

## 9. Dil ve çerez davranışı

Uygulama Türkçe (varsayılan) ve İngilizce destekler; desteklenen diller `tr`, `en`.

**Sunucu (arkauc).**

- İstek dili `Accept-Language` başlığından çözülür (`dil_coz`): etiketin kökü desteklenen bir
  dille eşleşmezse **Türkçe** döner (`tr-TR` → `tr`, `de-DE` → `tr`).
- Hata ve bilgi mesajları o dilde döner; `kod` alanı her zaman dilden bağımsız ve makine
  okunurdur. Mesaj bulunamazsa Türkçe kataloğa, o da yoksa anahtarın kendisine düşülür.
- Açık uçlar: `GET /api/v1/i18n/diller`, `GET /api/v1/i18n/sozluk/{dil}` (kimlik gerektirmez).
- Katalog dosyaları `arkauc/ceviriler/tr.json`, `en.json`.

**Arayüzler (onuc, yonetim_paneli).**

- Dil tercihi `kutyai.dil` çerezinde (`path=/`, `max-age=31536000`, `SameSite=Lax`) **ve**
  `localStorage`'da tutulur; ikisi çakışırsa istemci tercihi kazanır.
- `<html lang>` sunucuda çerezden okunur (sunucu bileşenleri) ve dil değişiminde güncellenir;
  katalog çevirisi istemci tarafında yapılır, arayüzler `/i18n/sozluk` ucunu çağırmaz.
- Dil seçici: onuc → `/hesap`, panel → üst çubuk.
- Arayüzler API'ye her istekte `Accept-Language` gönderir (hataların seçilen dilde dönmesi için).

**İşletim notları.**

- Ters vekil/CDN `Accept-Language` başlığını **silmeyin**; aynı URL farklı dillerde içerik
  döndürdüğü için HTML önbelleğini dil ekseninde ayırın (ör. `Vary` ya da çerez bazlı anahtar).
- Çerez adı değişirse (`kutyai.dil`) sunucu varsayılan dile (`tr`) döner; ham çerez değeri
  desteklenen bir dil değilse de varsayılan kullanılır.

## 10. Organizasyon yönetimi

Kiracı birimi **organizasyondur**; panel üst çubuğundaki seçici aktif organizasyonu belirler
(`yonetim_paneli/lib/aktif-organizasyon.ts`), her API isteğine `X-Organizasyon: <slug>` başlığı
eklenir ve organizasyon değişimi `POST /kimlik/organizasyon-sec` ile jetonu tazeler.

| İşlem | Panel | API |
|---|---|---|
| Organizasyon oluştur | Organizasyonlar → Yeni | `POST /organizasyonlar` `{ad, slug?}` — oluşturan `sahip` olur |
| Üye ekle | Organizasyonlar → Üyeler | `POST /organizasyonlar/{id}/uyeler` `{eposta?\|kullanici_id?, rol}` |
| Rol/durum değiştir | Üye satırı | `PATCH /organizasyonlar/{id}/uyeler/{kullanici_id}` `{rol?, durum?}` |
| Üyeliği kaldır | Üye satırı | `DELETE /organizasyonlar/{id}/uyeler/{kullanici_id}` (`204`) |
| Organizasyonu askıya al | Organizasyon ayarı | `PATCH /organizasyonlar/{id}` `{ad?, durum?}` (`durum=askida`) |

İşletim kuralları:

- Yetki **üyelik rolü** üzerinden verilir (`sahip` > `yonetici` > `operator` > `izleyici` >
  `son_kullanici`); `sahip` her zaman yetkilidir.
- Son `sahip` düşürülemez/silinemez ve kişi kendi `sahip` rolünü düşüremez → `409 gecersiz_gecis`.
- `durum=askida` organizasyonda erişim `403 yetki_yok` ile kesilir; kullanıcı panelden çıkış yapıp
  başka organizasyon seçebilir.
- Her organizasyonun BDM, konuşma, API anahtarı, dosya, RAG belgesi, araç, SSO sağlayıcısı,
  abonelik/fatura ve posta şablonu kayıtları **ayrıdır**; başka organizasyonun kaydı `404` döner.
- Organizasyon değişimi jetonu tazeler: panel `POST /kimlik/organizasyon-sec` çağırır ve yeni
  erişim jetonu alır. Başlık göndermeyen istemcilerde sıra jetonun `org` claim'i → API
  anahtarının organizasyonu → ilk aktif üyeliktir (`kaynak/API.md` §15).
- **Yetki sınırı:** `son_kullanici` üyeler yalnız sohbet, kendi konuşma geçmişi ve kişisel
  kullanım uçlarını kullanır; dosya, RAG, araç, medya, faturalama, SSO ve posta şablonu uçları
  **personeldir** ve `son_kullanici` üyeliğinde `403 yetki_yok` döner. Arayüzler bu yetenekleri
  yalnız personel oturumlarında gösterir.

## 11. Plan, abonelik ve kota

Planlar globaldir (tohum verisiyle gelir); abonelik ve faturalar organizasyon kapsamlıdır.

1. **Plan seç:** `GET /faturalama/planlar` (panel → Faturalama) etkin planları fiyata göre sıralar.
2. **Abonelik başlat:** `POST /faturalama/abonelik` `{plan_id, donem_gun?}`. Uç, plan limitlerini
   organizasyon kotasına yazar (`dahil_istek`, `dahil_token`) ve **sayaçları sıfırlar**, ilk faturayı
   `taslak` üretir; yanıttaki `odeme_url` ödeme adresidir (`yerel` sürücüde `null`).
3. **Kota davranışı:** kota organizasyon kapsamında tutulur ve tanımlıysa diğer kapsamlardan
   (kullanıcı/anahtar) **önce** denetlenir; aşımda sohbet `429 kota_asildi` döner. Uç, plan
   limitlerini yazarken `kullanilan_gunluk`/`kullanilan_aylik` sayaçlarını **sıfırlar** ve
   sıfırlama tarihlerini yeniden kurar (gün: +1 gün, ay: +30 gün) — yani plan değişimi/dönem
   yenileme mevcut dönemin kullanımını affeder.
4. **Tahsilat:**
   - `yerel` sürücü (varsayılan): `POST /faturalama/faturalar/{id}/odendi` (yalnız `sahip`/`yonetici`)
     faturayı `odendi` yapar; abonelik `gecikmis` ise `aktif`e döner.
   - `stripe`: ödeme oturumu URL'si kullanıcıya iletilir; Stripe Dashboard'da webhook ucu
     `POST /api/v1/faturalama/webhook/stripe` ve olaylar `checkout.session.completed`,
     `invoice.paid`, `invoice.payment_failed`, `customer.subscription.deleted` tanımlanır.
     İmza sırrı `KUTYAI_STRIPE_WEBHOOK_SIRRI` ile aynı olmalıdır; imza doğrulanmadan hiçbir
     abonelik/fatura yazımı yapılmaz.
5. **Durum izleme:** `GET /faturalama/abonelik` (`durum`, `donem_sonu`, `erisim`) ve
   `GET /faturalama/faturalar?sayfa=&boyut=`. Abonelik `gecikmis`/`iptal` iken `erisim: false`
   raporlanır — sohbet bu alanı kapı olarak **zorlamaz**, yalnız kota denetler; kurum politikası
   gerekiyorsa BDM'leri `durdu`/`pasif` duruma alın.
6. `faturalama.*` eylemleri işlem kayıtlarına (`/islem-kayitlari`) yazılır; iptal
   `POST /faturalama/abonelik/iptal` ile yapılır.

## 12. Dosya dizini yedeği

- Yükleme kökü `KUTYAI_DOSYA_DIZINI` (boşsa `bdm_veritabani/dosyalar`); dosyalar
  `<kök>/<org_slug>/<uuid4>` altında, meta veri ise `dosya` tablosunda (`yol` **mutlak** yol,
  `sha256`, `boyut`, `mime`) durur.
- **Yedek:** veritabanı ve dosya dizini **birlikte** alınmalıdır — tablodaki mutlak yol yoksa
  yükleme kaydı kalır ama içerik okunamaz (indirme/çözümleme `404`, ayrıntı
  `icerik_diskte_yok`).
- Docker/Helm: kalıcılık için dizini bir hacme verin (`KUTYAI_DOSYA_DIZINI=/veri/dosyalar`);
  varsayılan bırakılırsa dosyalar konteyner katmanında kalır ve konteyner yeniden
  oluşturulduğunda kaybolur. Helm chart bu değeri `config` içinde hazır taşır.
- **Geri yükleme:** servisi durdurun → DB yedeğini + dosya dizinini aynı yollara koyun →
  `alembic upgrade head` → servisi başlatın.
- **Silme:** `DELETE /dosyalar/{id}` kaydı ve diskteki kopyayı birlikte siler; `saklama_gun`
  temizliği dosyaları **kapsamaz**, gerekiyorsa disk kullanımını ayrıca izleyin.

```bash
# Linux/macOS — dizin yedeği (DB yedeğiyle aynı gün alın)
tar czf kutyai-dosyalar-$(date +%F).tgz -C "$KUTYAI_DOSYA_DIZINI" .
```

```powershell
# Windows
Compress-Archive -Path "$env:KUTYAI_DOSYA_DIZINI\*" -DestinationPath "kutyai-dosyalar-$(Get-Date -f yyyy-MM-dd).zip"
```

## 13. RAG yeniden gömme

- Gömme modeli BDM kaydındaki **`gomme_modeli`** alanıdır; sağlayıcı/model değiştirildiğinde
  mevcut parçaların vektörleri eski modelle üretilmiş kalır.
- Yeniden gömme: `POST /rag/belgeler/{id}/yeniden-gom` (yönetici/operatör). Gövde opsiyoneldir:
  `bdm_id` verilirse o model, verilmezse organizasyonun ilk `hazir|calisiyor` modeli kullanılır;
  tüm parçalar yeniden gömülür (idempotent).
- Tüm belgeler için sırayla çağırın (`GET /rag/belgeler` → her kayıt için yeniden-gom); büyük
  kurulumda bunu bakım penceresinde yapın, gömme sağlayıcı kotasını izleyin.
- Belgede parça yoksa `400 belge_parcasi_yok`; model hazır değilse `503 bdm_hazir_degil`; gömme
  üretilemezse `502 rag_gomme_hatasi` (sağlayıcı adresi/anahtarı ve `gomme_modeli` denetlenir;
  alan boşsa `400 gomme_modeli_yok`).
- Arama yolu `POST /rag/ara` yanıtındaki `ayrinti.yol` ile izlenir: Postgres'te `pgvector`
  uzantısı ve `vektor_pg` kolonu varsa `pgvector`, aksi hâlde `python` (taşınabilir kosinüs,
  belgelenen sınır 200.000 parça). Yol değişimini görmek için göç sonrası ilk aramayı kontrol edin.

## 14. SSO sağlayıcı kurulumu

Panel → **SSO** sayfasından sağlayıcı eklenir (`tur`: `oidc` ya da `saml`, `ad`, `slug`, `etkin`).
Sağlayıcı yönetimi `sahip`/`yonetici` rollerindedir; sır ve sertifika Fernet ile şifreli saklanır,
API yalnız `sir_tanimli` boolean'ını döner.

**OIDC (Authorization Code + PKCE):**

| Ayar | Örnek / not |
|---|---|
| `issuer` | `https://idp.example.com/realms/kurum` (keşif: `/.well-known/openid-configuration`) |
| `client_id` + sır | IdP'de **gizli istemci** olarak tanımlayın; sır panelde `sir` alanına |
| `kapsamlar` | Varsayılan `openid email profile` |
| `eposta_claim` / `ad_claim` | Varsayılan `email` / `name` |
| Dönüş adresi | `https://<api>/api/v1/sso/<org_slug>/<saglayici_slug>/donus` |

**SAML 2.0 (HTTP-Redirect + HTTP-POST):**

| Ayar | Örnek / not |
|---|---|
| `idp_sso_url` | IdP giriş adresi (AuthnRequest buraya yönlendirilir) |
| `sp_entity_id` | Varsayılan ACS adresidir; IdP'de Entity ID olarak bunu verin |
| `idp_imza_sertifikasi` | IdP imza sertifikası (PEM ya da çıplak base64) — **zorunlu** |
| `eposta_ozniteligi` / `ad_ozniteligi` | IdP'nin gönderdiği öznitelik adları (boşsa `NameID` e-postası kullanılır) |
| `sp_imza_anahtari` | Opsiyonel PEM RSA özel anahtarı; varsa `AuthnRequest` `RSA-SHA256` ile imzalanır |
| ACS adresi | `https://<api>/api/v1/sso/<org_slug>/<saglayici_slug>/saml/acs` |
| Başlatma | `GET /api/v1/sso/<org_slug>/<saglayici_slug>/baslat` (SAML için `/saml/baslat` da vardır) |

İşletim notları:

- İlk girişte kullanıcı otomatik oluşturulur (`son_kullanici`, `eposta_dogrulandi=true`);
  eşleşme önce `sso_kimlik` kaydı, sonra e-posta iledir. E-posta eşleşmesi **yalnız sağlayıcının
  organizasyonunda zaten aktif üyeliği olan** kullanıcıyla birleştirilir (aksi hâlde `403
  yetki_yok`); IdP `email_verified=false` bildirirse e-posta adımı hiç denenmez. Yeni kullanıcıda
  üyelik yoksa `KUTYAI_SSO_OTOMATIK_UYELIK=true` iken `son_kullanici` üyeliği açılır, değilse giriş `403`.
- Kurumsal uygulamaya yönlendirme gerekiyorsa `KUTYAI_SSO_YENIDEN_YONLENDIRME` verin; giriş,
  **60 sn** ömürlü `?kod=` ile bu adrese döner ve arayüz `POST /sso/kod-degistir` ile jetonları alır.
- SAML'de sertifika geçerliliğini ve sunucu saatini izleyin (izin ±120 sn); aynı `Assertion ID`
  10 dakika içinde yeniden sunulursa `409 saml_tekrar_oynatma` alınır.
- Denetim: `kimlik.sso_giris`, `sso.saglayici_olusturuldu`/`_guncellendi`/`_silindi` kayıtları
  organizasyon ve IP ile işlem kayıtlarına düşer; giriş sorunlarında önce buraya bakın.
- Sağlayıcıyı devre dışı bırakmak için `etkin=false` (silmeden); silmek `DELETE
  /sso/saglayicilar/{id}` ile yapılır ve sağlayıcıya bağlı `sso_kimlik` eşleşmeleri de silinir
  (FK `ON DELETE CASCADE`; SQLite'ta `PRAGMA foreign_keys=ON`). Bu kullanıcılar bir sonraki
  girişte yeniden eşlenir — hesapları silinmez.
