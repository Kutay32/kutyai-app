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
| `arkauc/app/servisler` | upstream istemci, akış, kota, kimlik, posta, konteyner | çekirdek |
| `arkauc/app/cekirdek` | ayarlar, hata zarfı, güvenlik, bağımlılıklar, denetim, router keşfi | `bdm_veritabani` |
| `bdm_listesi` | BDM kaydı şeması + CRUD + sağlayıcı matrisi | `bdm_veritabani` |
| `bdm_hazırlama_ucu` | erişim doğrulama, model çekme, konteyner manifesti, ön kontrol | `bdm_listesi`, konteyner sözleşmesi |
| `bdm_yönetim_ucu` | yaşam döngüsü durum makinesi, sağlık, log akışı, sürücü durumu | konteyner sürücüleri |
| `bdm_konusma_gecmisi` | mesaj/kullanım yazımı, maskeleme, sorgu, dışa aktarım, saklama | `bdm_veritabani` |
| `bdm_veritabani` | 12 tablo, async oturum, Alembic | — |

## Router keşfi

`arkauc/app/main.py` içindeki `YONLENDIRICILER` listesi dondurulmuştur. Modül yoksa uyarı loglanır ve atlanır; bu, klasör sahipliğiyle paralel geliştirmeyi mümkün kılar. Yeni uç eklemek için ilgili klasörde `router` tanımlayan bir modül oluşturmak yeterlidir.

## Sohbet akışı (veri yolu)

1. İstemci `POST /sohbet/akis` → `gecerli_istemci` (JWT veya `kuty_` anahtarı)
2. BDM kaydı çözülür; `hazir|calisiyor` değilse `503`
3. Kota kontrolü → aşımda `429`
4. Kullanıcı mesajı **maskelenerek** yazılır
5. Upstream'e istek; parçalar SSE ile akıtılır
6. Yanıt tamamlanınca asistan mesajı, token kullanımı ve `kullanim_kaydi` yazılır
7. İstemci koparsa upstream isteği iptal edilir; kısmi yanıt kaydedilmez

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
