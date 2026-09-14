# KutyAI — Helm chart

`dagitim/helm/kutyai`, KutyAI'nin Kubernetes dağıtımıdır (tasarım spec §11).
`dagitim/docker-compose.yml` ile **aynı ortam değişkeni adlarını, portları, sağlık
uçlarını ve kalıcı hacim yollarını** kullanır; Compose'daki üç servis üç
Deployment'a karşılık gelir.

| Compose servisi | Kubernetes kaynakları | Port |
|---|---|---|
| `arka.uc` (FastAPI) | Deployment/Service `kutyai-arka-uc` (+ PVC, HPA, goc Job) | 8000 |
| `onuc` (son kullanıcı) | Deployment/Service `kutyai-onuc` | 3000 |
| `yonetim_paneli` | Deployment/Service `kutyai-panel` | 3001 |

> Kaynak adları `<release>-<chart>` kökünden türer; `helm install kutyai ...`
> ile kurulduğunda yukarıdaki adlar geçerlidir (varsayılan varsayımlar).

## 1. Kurulum

```bash
# Önerilen yol: ad alanını Helm oluşturur (chart Namespace üretmez)
helm install kutyai dagitim/helm/kutyai -n kutyai --create-namespace

# GitOps/Argo senaryosu: ad alanını chart üretsin
helm install kutyai dagitim/helm/kutyai -n kutyai --set namespace.create=true

# Üretim için tipik geçersiz kılmalar
helm upgrade --install kutyai dagitim/helm/kutyai -n kutyai \
  --set ingress.enabled=true --set ingress.className=nginx \
  --set ingress.hosts[0].host=kutyai.example.com \
  --set ingress.hosts[1].host=panel.example.com \
  --set ingress.tls.enabled=true --set ingress.tls.secretName=kutyai-tls \
  --set secrets.values.KUTYAI_SIFRELEME_ANAHTARI="$FERNET_ANAHTARI" \
  --set secrets.values.KUTYAI_VERITABANI_URL="postgresql+asyncpg://kutyai:PAROLA@pg:5432/kutyai" \
  --set arkauc.autoscaling.enabled=true
```

Kurulumdan sonra `helm status kutyai -n kutyai` erişim adreslerini, sır
uyarılarını ve kısıtları yazar (`templates/NOTES.txt`).

## 2. Dosya yapısı

```
Chart.yaml
values.yaml
README.md
.helmignore
templates/
  _helpers.tpl            ad/etiket/seçici/ad alanı/servis adı yardımcıları
  namespace.yaml          Namespace            (namespace.create=true iken)
  serviceaccount.yaml     ServiceAccount       (pod'lar; token bağlanmaz)
  configmap.yaml          ConfigMap            KUTYAI_* sırsız ayarlar
  secret.yaml             Secret               gizli değerler (üretir ya da existingSecret)
  arkauc-deployment.yaml  Deployment           arka.uc
  arkauc-service.yaml     Service              arka.uc (8000)
  arkauc-hpa.yaml         HorizontalPodAutoscaler (autoscaling.enabled=true iken)
  arkauc-pvc.yaml         PersistentVolumeClaim /veri (SQLite + dosyalar)
  arkauc-hf-pvc.yaml      PersistentVolumeClaim hf-onbellek (opsiyonel)
  onuc-deployment.yaml    Deployment + onuc-service.yaml   Service (3000)
  panel-deployment.yaml   Deployment + panel-service.yaml  Service (3001)
  ingress.yaml            Ingress              /api, /, panel alan adı
  migration-job.yaml      Job                  alembic upgrade head (hook)
  NOTES.txt
```

## 3. Compose ↔ Helm eşlemesi

| Compose (`.env.ornek`, `docker-compose.yml`) | Helm karşılığı |
|---|---|
| `.env` → `env_file: arkauc` | `config:` (sırsız, ConfigMap) + `secrets.values:` (gizli, Secret) |
| `KUTYAI_VERITABANI_URL=sqlite+aiosqlite:////veri/kutyai.db` | `config.KUTYAI_VERITABANI_URL`; dosya `arkauc-pvc.yaml` hacminde |
| `volumes: kutyai-veri:/veri` | `arkauc.persistence.data` (PVC `kutyai-veri`, `arkauc.dataPath: /veri`) |
| `KUTYAI_DOSYA_DIZINI` (`.env.ornek`'te boş → `bdm_veritabani/dosyalar`) | `config.KUTYAI_DOSYA_DIZINI=/veri/dosyalar` (**kalıcı**: aynı PVC). Compose'da yükleme dizini imaj kökünde kalır ve konteyner yeniden oluşturulunca kaybolur; burada bilinçli olarak kalıcı hacme alındı. İmaj kökündeki `bdm_veritabani/` paket dizini gölgelenmez |
| `KUTYAI_HF_ONBELLEK` + yorumlu host bağlaması | `arkauc.persistence.hfCache.enabled` → PVC `kutyai-hf-onbellek`, `KUTYAI_HF_ONBELLEK=/veri/hf-onbellek` |
| `/var/run/docker.sock:/var/run/docker.sock` | `arkauc.dockerSocket.enabled` (hostPath; **varsayılan kapalı**) |
| `healthcheck` arkauc `GET /api/v1/saglik` | `arkauc.livenessProbe` + `arkauc.readinessProbe` (aynı yol) |
| `healthcheck` onuc/panel `GET /` | `onuc/panel.*Probe` (yol `/`) |
| `ports: 8000:8000 / 3000:3000 / 3001:3001` | Service portları + Ingress (küme içi erişim `ClusterIP`) |
| `NEXT_PUBLIC_API_URL` (build arg + runtime env) | `browserApiUrl` (ve `onuc/panel.browserApiUrl`) → `NEXT_PUBLIC_API_URL`; imaj derleme zamanı notu §6 |
| `depends_on: service_healthy` | Kubernetes'te yok; `readinessProbe` + göç Job'u sırayı sağlar (arayüzler API'ye istek anında bağlanır) |
| `profiles: ["postgres"]` (`postgres` servisi) | **Kapsam dışı** (spec şablon listesi) — harici PostgreSQL: `secrets.values.KUTYAI_VERITABANI_URL` |
| `profiles: ["nginx"]` (`nginx.conf`) | `ingress.hosts` (yol düzeni aynı: `/api`, `/`, panel ayrı alan adı) |
| `docker compose exec arkauc python -m alembic upgrade head` | Job `kutyai-goc` → `python -m alembic upgrade head` (post-install/pre-upgrade hook; §7) |
| `baslat.sh/ps1` sır üretimi | `secret.yaml` boş sırları üretir (aşağıya bakın) |
| `saglik.sh` / `saglik.ps1` | `kubectl get pods`, `kubectl describe`, probe durumları |
| `KUTYAI_ORTAM=uretim` + zorunlu sırlar | `config.KUTYAI_ORTAM` (varsayılan `uretim`); sırlar her hâlükârda sağlanır |

Ortam değişkeni **adları** birebir aynıdır (`KUTYAI_*`); liste
`dagitim/.env.ornek` / kök `.env.ornek` ile karşılaştırılarak doldurulmuştur.
Yeni bir değişken eklemek için `values.yaml → config:` altına yazmak yeterlidir.

## 4. Özelleştirme (değerler)

| Ne | Değer yolu |
|---|---|
| İmaj deposu/etiketi | `arkauc.image.repository/tag`, `onuc.image.*`, `panel.image.*`, `migration.image.*` |
| Replika sayısı | `arkauc.replicaCount`, `onuc.replicaCount`, `panel.replicaCount` |
| Kaynak istek/limit | `<bileşen>.resources.requests/limits` |
| HPA eşikleri | `arkauc.autoscaling.{enabled,minReplicas,maxReplicas,targetCPUUtilizationPercentage,behavior}` |
| Ingress host/TLS | `ingress.{enabled,className,annotations,hosts,tls}` |
| PVC boyutu/sınıfı | `arkauc.persistence.data.{size,storageClassName,accessModes,existingClaim}`, `arkauc.persistence.hfCache.*` |
| Ortam değişkenleri | `config` (sırsız), `secrets.values` (gizli), `<bileşen>.extraEnv` |
| Sağlık sondaları | `<bileşen>.livenessProbe/readinessProbe` |
| Güvenlik bağlamı | `<bileşen>.securityContext` |
| Yerleşim | `<bileşen>.nodeSelector/tolerations/affinity`, `imagePullSecrets` |
| Göç Job'u | `migration.{enabled,image,backoffLimit,activeDeadlineSeconds,mountDataVolume,resources}` |

## 5. Sırlar

İki mod vardır (ikisi birden yoksa şablon açık bir hatayla durur):

1. **`secrets.existingSecret`** — üretimde önerilen. Chart Secret üretmez; tüm
   anahtarları kendi aracınız (SealedSecrets, SOPS, Vault CSI, External Secrets)
   yönetir. Pod'lar `envFrom.secretRef` ile bu Secret'ı okur.
2. **`secrets.create` (varsayılan `true`)** — `secrets.values` altındaki
   `KUTYAI_*` anahtarları Secret'a yazılır. **Boş** bırakılan anahtarlar Secret'a
   yazılmaz; iki istisna rastgele **üretilir**:
   - `KUTYAI_GIZLI_ANAHTAR` (64 karakter),
   - `KUTYAI_SIFRELEME_ANAHTARI` (Fernet: 32 bayt urlsafe base64 —
     `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`).

   Üretilen değerler yükseltmede `lookup` ile **korunur** (Fernet anahtarı
   değişirse kayıtlı şifreli veriler açılamaz). `helm template`/`--dry-run`
   çalışırken `lookup` boş döner, o nedenle bu komutlar her seferinde yeni değer
   üretir — yalnızca yerel doğrulamayı etkiler, kümeye yazılmaz.

Değerler `values.yaml` içinde **düz metin tutulmaz**: varsayılanlar boştur.
Parola içeren bağlantı adresleri (`KUTYAI_VERITABANI_URL`) ConfigMap yerine
`secrets.values` altına yazılmalıdır; aynı anahtar iki kaynakta varsa pod'lar
sırlar (secretRef) kazanır.

Sırsız anahtarlar `config` altında **ConfigMap** olarak dağıtılır (küme içinde
okunabilir olduğundan oraya sır koymayın).

`KUTYAI_GIZLI_ANAHTAR`/`KUTYAI_SIFRELEME_ANAHTARI` değişirse pod'lar
`checksum/sirlar` ek açıklaması sayesinde kendiliğinden yenilenir.

## 6. Üretim notları ve kısıtlar

- **Veritabanı / ölçekleme.** Varsayılan Compose ile aynıdır: SQLite
  (`sqlite+aiosqlite:////veri/kutyai.db`) + ReadWriteOnce hacim → `arka.uc`
  **tek replika**. Çok replika ve HPA için harici PostgreSQL verin
  (`secrets.values.KUTYAI_VERITABANI_URL`); yüklenen dosyalar aynı hacmi
  paylaştığı için ek olarak pod'lar arası paylaşılabilir bir hacim gerekir
  (`--set arkauc.persistence.data.accessModes[0]=ReadWriteMany`, ör. NFS/CephFS),
  sonra `arkauc.autoscaling.enabled=true` ve `arkauc.replicaCount>=2`. HPA açıkken
  Deployment `replicas` alanını yazmaz (sahibi HPA olur). HPA CPU yüzdesi
  `arkauc.resources.requests.cpu` üzerinden hesaplanır; o alan boşaltılırsa
  ölçekleme çalışmaz.
- **Tarayıcı API adresi.** `NEXT_PUBLIC_API_URL` imaj **derlenirken** istemci
  paketine gömülür (`dagitim/Dockerfile.onuc`, `Dockerfile.panel`). Çalışma
  zamanında `browserApiUrl` verilmesi sunucu tarafını etkiler ama tarayıcı
  paketini değiştirmez: üretim imajlarını gerçek alan adıyla derleyin
  (`--build-arg NEXT_PUBLIC_API_URL=https://kutyai.example.com/api/v1`),
  `KUTYAI_TARAYICI_API_URL` notu için `dagitim/OKUBENI.md` §4.
- **Gerçek istemci IP'si.** Ingress arkasında `config.KUTYAI_GUVENILIR_VEKIL`
  varsayılanı `true`'dur (bu chart'taki Ingress güvenilir kabul edilir). Ingress
  kullanmıyorsanız ya da başka bir vekil varsa `false` yapın.
- **BDM konteynerleri (/var/run/docker.sock).** Compose soketi olduğu gibi
  bağlar. Kubernetes'te varsayılan **kapalıdır**; açmak düğüm üzerinde root
  yetkisi demektir ve non-root pod ile soket grubu izinleri uyumlu olmayabilir
  (`securityContext.runAsUser/fsGroup`). Model önbelleği (`hfCache`) ayrıca
  **Docker host** yolu olarak çözülür: çok düğümlü kümede model önbelleği için
  ayrı bir çözüm (node-local dizin ya da ağ hacmi) gerekir. Üretimde soketi
  salt-okunur bir vekil (socket proxy) arkasına alın — `dagitim/OKUBENI.md` §11,
  `kaynak/ISLETIM.md`.
- **Non-root.** `arka.uc` ve göç Job'u non-root (`10001`) çalışır; kalıcı hacim
  `fsGroup` ile devredilir, böylece PVC'ye yazabilir. Node imajları root
  çalıştığı ve `next start` kendi `.next/cache` dizinine yazabildiği için
  `onuc`/`panel` varsayılan olarak imaj kullanıcısındadır; bunları da non-root
  yapmak `Dockerfile.onuc`/`Dockerfile.panel` içinde `USER` + chown gerektirir
  (bu chart'ın kapsamı dışında). Tüm konteynerlerde
  `allowPrivilegeEscalation: false`, tüm Linux yetenekleri düşürülür ve
  `seccompProfile: RuntimeDefault` uygulanır.
- **Kalıcı hacimler.** `kutyai-veri` ve `kutyai-hf-onbellek` PVC'lerinde
  `helm.sh/resource-policy: keep` vardır: `helm uninstall` veriyi silmez.
- **Panel yolu.** Panel imajı `basePath` ile derlenmediği için `/panel` öneki
  statik varlıkları kırar (`dagitim/nginx.conf` aynı notu taşır); varsayılan
  Ingress bu nedenle panel için ayrı alan adı (`panel.kutyai.local`) kullanır.

## 7. Göç (Alembic) Job'u

`templates/migration-job.yaml`, arkauc imajını kullanarak
`python -m alembic upgrade head` çalıştırır (compose'daki
`docker compose exec arkauc python -m alembic upgrade head` ile aynı komut).
Hook: **`post-install,pre-upgrade`**, `hook-weight: -5`.

- **Yükseltmede** `pre-upgrade` ile yeni sürüm açılmadan önce koşar; başarısız
  olursa yükseltme durur (`helm.sh/hook-delete-policy` başarılı job'u siler).
- **İlk kurulumda** `pre-install` KULLANILMAZ: chart'ın PVC'si (`kutyai-veri`)
  o aşamada henüz oluşturulmadığı için Job pod'u Pending kalır ve kurulum
  `activeDeadlineSeconds` sonunda başarısız olur. Bu yüzden göç, kaynaklar
  oluşturulduktan sonra koşar. Bu güvenlidir çünkü uygulama şemayı açılışta da
  kurar (`bdm_veritabani/oturum.py` → `Taban.metadata.create_all`) ve göçler
  `create_all(checkfirst=True)` kullanır — göç tekrar çalıştırılabilir.
- SQLite'ta göç pod'una `/veri` hacmi bağlanır (`migration.mountDataVolume`);
  harici PostgreSQL'de bunu `false` yapın.
- Kapatmak için `--set migration.enabled=false`. Göç geri dönüşsüz olduğundan
  üretimde önce `kaynak/ISLETIM.md` §4 yedeğini alın.

## 8. Doğrulama

```bash
helm lint dagitim/helm/kutyai
helm template kutyai dagitim/helm/kutyai -n kutyai > /tmp/kutyai-helm.yaml
helm template kutyai dagitim/helm/kutyai -n kutyai \
  --set namespace.create=true --set arkauc.autoscaling.enabled=true \
  --set arkauc.persistence.hfCache.enabled=true --set arkauc.dockerSocket.enabled=true \
  --set ingress.tls.enabled=true
```

Bu depoda koşulan doğrulama (helm 3.16.3, kubeconform 0.6.7, Kubernetes 1.29
şemaları) ve sonuçları:

- `helm lint` → `1 chart(s) linted, 0 chart(s) failed`
- `helm template` (varsayılan) → 12 kaynak, hata yok
- `helm template` (varyant) → 15 kaynak (Namespace, HPA, ikinci PVC dahil), hata yok
- `kubeconform -strict` → 12/12 ve 15/15 geçerli, 0 hatalı
- `kubectl apply --dry-run=client` → **gerçek küme yok**; istemci doğrulaması
  OpenAPI şemasını kümeden indirmeye çalıştığı için çalıştırılamadı
  (`dial tcp 127.0.0.1:8080: connection refused`). Bunun yerine kubeconform'un
  çevrimdışı şemaları ve zorunlu alan denetimi kullanıldı.
- `secrets.create=false` + `secrets.existingSecret` boş → açık hata
  (yanlış yapılandırma sessizce geçmez).
