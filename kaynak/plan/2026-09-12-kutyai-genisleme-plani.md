# KutyAI — Genişleme Uygulama Planı (v2)

> **Ajanlar için:** `kaynak/spec/2026-09-12-kutyai-genisleme-tasarim.md` bağlayıcıdır. Klasör sahipliği ve dondurulmuş dosya kuralları v1 planıyla aynıdır (`kaynak/plan/2026-09-12-kutyai-uygulama-plani.md`).

**Hedef:** v1'de kapsam dışı bırakılan 10 yeteneği eklemek; mevcut 253 testi ve uçları bozmadan.

**Kilit kararlar:** tam çok kiracılılık · adaptör + yerel ödeme sürücüsü + Stripe · OIDC + SAML 2.0 · taşınabilir vektör arama (+ pgvector opsiyonel) · tam i18n (API + arayüz, TR/EN).

---

## Dalga 0 — Kiracılık temeli (seri, controller)

Dondurulur; sonraki hiçbir ajan bu dosyaları değiştirmez.

- [ ] `bdm_veritabani/modeller.py` — `organizasyon`, `uyelik`, `dosya`, `vektor_belgesi`, `vektor_parcasi`, `arac`, `arac_cagrisi`, `plan`, `abonelik`, `fatura`, `sso_saglayici`, `sso_kimlik`, `posta_sablonu` tabloları; 13 tabloya `org_id`; `bdm.gomme_modeli`; `KotaKapsami.organizasyon`
- [ ] `bdm_veritabani/gocler/versions/0002_cok_kiracili.py` — varsayılan organizasyon + üyelik eşleme + `org_id` doldurma (batch alter)
- [ ] `bdm_veritabani/tohum.py` — varsayılan organizasyon + varsayılan `plan` kayıtları + varsayılan posta şablonları (idempotent)
- [ ] `arkauc/app/cekirdek/i18n.py` + `arkauc/ceviriler/{tr,en}.json` — mesaj kataloğu, `Accept-Language` çözümü
- [ ] `arkauc/app/cekirdek/hatalar.py` — yeni kodlar (spec §12) + katalogdan mesaj çözümü
- [ ] `arkauc/app/cekirdek/guvenlik.py` — erişim jetonuna `org` claim'i (`erisim_jetonu_uret(kullanici_id, rol, org_id=None)`)
- [ ] `arkauc/app/cekirdek/bagimliliklar.py` — `aktif_organizasyon`, org-aware `gecerli_personel`, `org_kosulu`
- [ ] `arkauc/app/api/organizasyonlar.py` — spec §2.5 uçları
- [ ] `arkauc/app/api/i18n.py` — `GET /i18n/diller`, `GET /i18n/sozluk/{dil}`
- [ ] `arkauc/app/main.py` — keşif listesine 9 yeni modül
- [ ] `arkauc/testler/conftest.py` — `yardimci.organizasyon()`, otomatik varsayılan üyelik, `org_basliklari`
- [ ] `kaynak/API.md` §15–§22 — yeni sözleşmeler

**Kabul:** `pytest arkauc/testler -q` yeşil (mevcut 253 test org desteğiyle de geçer); göç testi `0001`→`0002` veriyi korur.

---

## Dalga 1 — Yetenekler (5 paralel uygulayıcı + 5 gözlemci)

Her görev kendi klasörüne yazar; ortak dosya değişikliği yok.

| Görev | Dosyalar | Kabul |
|---|---|---|
| **DosyaUcu** | `arkauc/app/api/dosyalar.py`, `arkauc/app/servisler/dosya.py`, `arkauc/testler/test_dosyalar.py` | multipart yükleme, MIME/boyut sınırı, metin çıkarımı (pdf opsiyonel), indirme, silme, org izolasyonu, KVKK maskeleme |
| **AracUcu** | `arkauc/app/api/araclar.py`, `arkauc/app/servisler/arac.py`, `arkauc/testler/test_araclar.py` | CRUD, webhook çalıştırma (imza, zaman aşımı, SSRF), yerleşik araçlar, çağrı logu, org izolasyonu |
| **RagUcu** | `arkauc/app/api/rag.py`, `arkauc/app/servisler/gomme.py`, `arkauc/app/servisler/vektor.py`, `arkauc/testler/test_rag.py` | belge ekle/parçala/göm, arama (taşınabilir + pgvector), silme, `kaynaklar` döndürme |
| **MedyaUcu** | `arkauc/app/api/medya.py`, `arkauc/app/servisler/medya.py`, `arkauc/testler/test_medya.py` | görsel üret, ses üret, ses çöz; yetenek bayrağı yoksa net 400; sonuç `dosya`ya yazılır |
| **SohbetEntegrasyon** | `arkauc/app/api/sohbet.py`, `arkauc/app/servisler/akış.py`, `arkauc/app/servisler/upstream.py`, `arkauc/testler/test_sohbet_ek.py` | `dosya_idleri`, `rag`, `rag_belge_idleri`, `araclar` desteği; yeni SSE olayları `arac_cagrisi`/`arac_sonucu`; araç tur döngüsü; `kaynaklar` |

**Not:** SohbetEntegrasyon diğer dört modülün yardımcı fonksiyonlarını çağırır; bu yüzden arayüzler önceden dondurulur (aşağıda).

### Dalga 1 arayüz sözleşmesi (dondurulmuş imzalar)

```python
# arkauc/app/servisler/dosya.py
async def dosya_kaydet(oturum, *, org_id, kullanici_id, ad, mime, icerik: bytes) -> Dosya
async def dosya_getir(oturum, org_id: int, dosya_id: int) -> Dosya
async def metin_cikar(dosya: Dosya) -> tuple[str, str | None]   # (metin, gerekce)
async def baglam_metni(oturum, org_id, dosya_idleri: list[int], *, sinir: int) -> str

# arkauc/app/servisler/gomme.py
async def gomme_uret(bdm, metinler: list[str]) -> list[list[float]]

# arkauc/app/servisler/vektor.py
def parcala(metin: str, *, boyut: int = 800, ortusme: int = 120) -> list[str]
def kosinus(a: list[float], b: list[float]) -> float
async def parcalari_yaz(oturum, *, org_id, belge_id, parcalar, vektorler) -> int

# arkauc/app/servisler/arac.py
async def araclari_getir(oturum, org_id: int, idler: list[int] | None) -> list[Arac]
def arac_tanimi(arac: Arac) -> dict          # OpenAI tools formatı
async def arac_calistir(oturum, *, org_id, arac: Arac, argumanlar: dict) -> dict
def yerlesik_mi(arac: Arac) -> bool

# arkauc/app/servisler/medya.py
async def gorsel_uret(bdm, istem: str, *, boyut: str = "1024x1024", adet: int = 1) -> list[bytes]
async def ses_uret(bdm, metin: str, *, ses: str = "alloy", bicim: str = "mp3") -> bytes
async def ses_coz(bdm, dosya_adi: str, icerik: bytes) -> str
```

## Dalga 2 — Ticari ve kurumsal (5 paralel + 5 gözlemci)

| Görev | Dosyalar | Kabul |
|---|---|---|
| **OdemeAdaptor** | `arkauc/app/servisler/odeme.py`, `odeme_yerel.py`, `odeme_stripe.py`, `arkauc/app/api/faturalama.py`, testler | adaptör sözleşmesi, plan/abonelik/fatura CRUD, plan→org kotası, Stripe webhook imza doğrulaması, `402 abonelik_gecikmis` |
| **OidcSso** | `arkauc/app/servisler/sso_oidc.py`, `arkauc/app/api/sso.py`, testler | discovery, PKCE, JWKS imza, nonce/state, kullanıcı eşleme, otomatik üyelik |
| **SamlSso** | `arkauc/app/servisler/sso_saml.py`, testler | imzalı AuthnRequest, `signxml` ile Response+Assertion doğrulaması, Audience/Recipient/süre/InResponseTo, replay kümesi, XSW denemeleri |
| **PanelSayfalari** | `yonetim_paneli/app/(panel)/{organizasyonlar,dosyalar,bilgi-tabani,araclar,faturalama,posta-sablonlari,sso}/**` + `lib/*.ts` + `components/*` | gerçek veriyle çalışan sayfalar, org değiştirici |
| **OnucYetenekleri** | `onuc/app/{dosyalar,medya}/**`, `onuc/components/sohbet/**` (ekler), `onuc/lib/*.ts` | dosya eki yükleme, RAG anahtarı, araç sonuç kartı, görsel/ses üretim sayfaları |

## Dalga 3 — i18n ve Helm (4 paralel + gözlemciler)

| Görev | Kapsam | Kabul |
|---|---|---|
| **I18nApi** | `arkauc/ceviriler/*.json`, `arkauc/app/cekirdek/i18n.py` (tamamlama), tüm API modüllerindeki sabit mesajların kataloğa taşınması | `Accept-Language: en` ile tüm hata/mesaj yanıtları EN; eksik anahtar tarayıcısı temiz |
| **I18nOnuc** | `onuc/lib/sozluk/*`, tüm `onuc/app/**`, `onuc/components/**` metinleri | TR/EN dil değiştirme, `<html lang>`, eksik anahtar yok |
| **I18nPanel** | `yonetim_paneli/lib/sozluk/*`, tüm `yonetim_paneli/app/**`, `components/**` | aynı |
| **HelmChart** | `dagitim/helm/kutyai/**` | `helm template` geçerli; değerlerle özelleştirilebilir |

## Dalga 4 — Bütünleşik doğrulama ve kapanış

- [ ] `pytest arkauc/testler -q` yeşil (hedef: 400+ test)
- [ ] `onuc` + `yonetim_paneli`: `tsc --noEmit` + `build` + birim testleri yeşil
- [ ] Uçtan uca duman: iki organizasyon → izolasyon kanıtı; dosya yükle → RAG belgesi → RAG'li sohbet; araç çağrısı; plan seç → kota; dil değiştir
- [ ] Gerçek tarayıcı kanıtları `kaynak/testler/kanit/` altına
- [ ] Bağımsız gözlemci logları `kaynak/testler/` altına
- [ ] İki aşamalı inceleme (spec + kalite) ve güvenlik incelemesi (SAML/SSO/ödeme odaklı)
- [ ] Dokümanlar: `API.md`, `KURULUM.md`, `ISLETIM.md`, `GUVENLIK.md`, `MIMARI.md` güncel
