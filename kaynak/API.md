# KutyAI API Sözleşmesi (v1 + v2)

**Taban adres:** `http://localhost:8000/api/v1`
**Kimlik:** `Authorization: Bearer <erisim_jetonu>` veya `Authorization: Bearer kuty_<32 karakter>`
**Belge:** çalışırken `GET /api/docs` (Swagger), `GET /api/openapi.json`

Bu dosya arayüz ajanları için **bağlayıcı sözleşmedir**. Alan adları değişmez.

---

## 1. Hata zarfı

Her hata gövdesi:

```json
{ "hata": { "kod": "kota_asildi", "mesaj": "Kotanız doldu.", "ayrinti": { "sifirlanma": "2026-09-13T00:00:00Z" } } }
```

| HTTP | `kod` |
|---|---|
| 400 | `gecersiz_istek`, `dogrulama_hatasi` |
| 401 | `kimlik_gerekli`, `jeton_gecersiz`, `jeton_suresi_doldu`, `anahtar_gecersiz`, `gecersiz_kimlik_bilgisi` |
| 403 | `yetki_yok`, `eposta_dogrulanmadi` |
| 404 | `bulunamadi` |
| 409 | `cakisma`, `gecersiz_gecis`, `kurulum_zaten_tamam` |
| 429 | `kota_asildi`, `oran_siniri` |
| 502 | `ust_saglayici_hatasi` |
| 503 | `bdm_hazir_degil`, `surucu_yok`, `veritabani_yok` |
| 500 | `sunucu_hatasi` |

## 2. Ortak tipler

```ts
type Kullanici = {
  id: number; eposta: string; ad_soyad: string;
  rol: "yonetici" | "operator" | "izleyici" | "son_kullanici";
  durum: "aktif" | "beklemede" | "pasif";
  eposta_dogrulandi: boolean; olusturulma: string; son_giris: string | null;
};
type Sayfa<T> = { toplam: number; sayfa: number; boyut: number; kayitlar: T[] };
type Bdm = {
  id: number; slug: string; gorunen_ad: string; aciklama: string;
  saglayici: "openai"|"azure"|"openrouter"|"ollama"|"vllm"|"tgi"|"ozel";
  temel_url: string; upstream_model: string; api_anahtari_maskeli: string;
  baglam_penceresi: number; maks_cikti: number; sicaklik_varsayilan: number;
  sistem_istemi: string;
  yetenekler: { akis: boolean; gorsel: boolean; arac: boolean };
  durum: "taslak"|"hazir"|"calisiyor"|"durdu"|"hata";
  yerel_mi: boolean;
  konteyner: {
    image?: string; gpu?: boolean; port?: number; bellek_gb?: number; konteyner_id?: string;
    yol?: { takma_ad?: string; oncelik?: number };
  } | null;
  olusturulma: string; guncellenme: string;
};
type BdmOzet = Pick<Bdm, "id"|"slug"|"gorunen_ad"|"aciklama"|"saglayici"|"baglam_penceresi"|"yetenekler"|"durum">;
```

---

## 3. Sistem

| Yöntem | Yol | Yetki | Yanıt |
|---|---|---|---|
| GET | `/saglik` | açık | `{ durum: "ayakta", surum, ortam, zaman }` |
| GET | `/saglik/hazir` | açık | `{ durum:"hazir", veritabani:"tamam", surucu:{ad,docker,gpu,mesaj}, surum }` |
| GET | `/saglik/kurulum` | açık | `{ kurulum_tamam: boolean, marka_adi: string, surum }` |

## 4. Kurulum — `POST /kurulum`

Yalnızca `kurulum_tamam=false` iken çalışır; aksi hâlde `409 kurulum_zaten_tamam`.

İstek:
```json
{
  "marka_adi": "Acme AI",
  "yonetici": { "eposta": "admin@acme.com", "ad_soyad": "Ayşe Yılmaz", "parola": "en-az-8-karakter" },
  "bdm": {
    "gorunen_ad": "Yerel Llama 3", "saglayici": "ollama",
    "temel_url": "http://localhost:11434/v1", "upstream_model": "llama3",
    "api_anahtari": "", "yerel_mi": true, "sistem_istemi": ""
  },
  "dogrula": true
}
```
Yanıt `201`: `{ "yonetici": Kullanici, "bdm": Bdm, "dogrulama": { "basarili": bool, "mesaj": string } | null, "kurulum_tamam": true }`

## 5. Kimlik

| Yöntem | Yol | Gövde | Yanıt |
|---|---|---|---|
| POST | `/kimlik/kayit` | `{eposta, ad_soyad, parola}` | `201 {kullanici, dogrulama_gerekli:true, gelistirme_baglantisi?: string}` |
| POST | `/kimlik/dogrula` | `{jeton}` | `{dogrulandi:true}` |
| POST | `/kimlik/giris` | `{eposta, parola}` | `{erisim_jetonu, yenileme_jetonu, kullanici}` |
| POST | `/kimlik/panel-giris` | `{eposta, parola}` | aynı (yalnız personel; personel **üyeliği** olmayan hesap → `403`) |
| POST | `/kimlik/yenile` | `{yenileme_jetonu}` | `{erisim_jetonu, yenileme_jetonu}` |
| POST | `/kimlik/cikis` | `{yenileme_jetonu?}` | `{mesaj}` |
| POST | `/kimlik/sifre-sifirlama-iste` | `{eposta}` | `{mesaj, gelistirme_baglantisi?}` |
| POST | `/kimlik/sifre-sifirla` | `{jeton, yeni_parola}` | `{mesaj}` |
| GET | `/kimlik/ben` | — | `Kullanici` |

`gelistirme_baglantisi` yalnız SMTP tanımlı değilken döner (test/kurulum kolaylığı).

## 6. Kullanıcı yönetimi (yönetici)

| Yöntem | Yol | Gövde |
|---|---|---|
| GET | `/kullanicilar?rol=&durum=&arama=&sayfa=&boyut=` | — → `Sayfa<Kullanici>` |
| POST | `/kullanicilar` | `{eposta, ad_soyad, parola, rol}` → `201 Kullanici` |
| PATCH | `/kullanicilar/{id}` | `{rol?, durum?, ad_soyad?}` → `Kullanici` |
| DELETE | `/kullanicilar/{id}` | — → `204` (pasifleştirir) |

Uçlar **aktif organizasyon kapsamlıdır**: liste yalnız o organizasyonun üyelerini döner
(`rol`/`durum` süzgeçleri `kullanici` alanlarına uygulanır); hedef kullanıcı aktif
organizasyonun üyesi değilse `404 bulunamadi`. `POST /kullanicilar` ile oluşturulan
kullanıcı aktif organizasyona üye yazılır (üyelik rolü `ROL_ESLEME` ile `rol` alanından
türetilir). Denetim kayıtları (`kullanici.olustur`, `kullanici.guncelle`,
`kullanici.pasiflestir`) aktif organizasyonun `org_id`'si ile yazılır.

## 7. API anahtarları (yönetici/operatör; `izleyici` → `403`)

| Yöntem | Yol | Yanıt |
|---|---|---|
| GET | `/api-anahtarlari` | `[{id, ad, onek, son_dort, durum, izinli_modeller, gunluk_istek_siniri, olusturulma, son_kullanim}]` |
| POST | `/api-anahtarlari` `{ad, izinli_modeller?, gunluk_istek_siniri?, kullanici_id?}` | `201 {…, tam_anahtar}` — **`tam_anahtar` yalnızca bu yanıtta** |
| POST | `/api-anahtarlari/{id}/iptal` | `{durum:"iptal"}` |

`kullanici_id` verilirse kullanıcı **aktif organizasyonun üyesi** olmalıdır; değilse `400 gecersiz_istek`.

## 8. Model kataloğu

| Yöntem | Yol | Yetki | Yanıt |
|---|---|---|---|
| GET | `/modeller` | kimlikli | `BdmOzet[]` (yalnız `hazir\|calisiyor`, anahtarın izinli listesi süzülür) |
| GET | `/saglayicilar` | **açık** | `[{ad, gorunen_ad, yerel, gpu_gerekir, akis_destegi, api_anahtari_gerekir, varsayilan_temel_url, varsayilan_port, konteyner_image, aciklama}]` — kurulum sihirbazı kimlik doğrulamadan önce çağırır |
| GET | `/bdm` | personel | `Bdm[]`; isteğe bağlı `?arama=` (görünen ad ve slug üzerinde, büyük/küçük harf duyarsız) |
| POST | `/bdm` | yönetici/operatör | `201 Bdm` |
| PATCH | `/bdm/{id}` | yönetici/operatör | `Bdm` |
| POST | `/bdm/{id}/kopyala` | yönetici | `201 Bdm` |
| DELETE | `/bdm/{id}` | yönetici | `204`; `durum=calisiyor` ise veya bağlı konuşma/kullanım kaydı varsa `409 gecersiz_gecis` |

`POST /bdm` gövdesi:
```json
{ "gorunen_ad":"...", "slug":"opsiyonel", "aciklama":"", "saglayici":"openai",
  "temel_url":"https://api.openai.com/v1", "upstream_model":"gpt-4o-mini",
  "api_anahtari":"sk-...", "baglam_penceresi":128000, "maks_cikti":4096,
  "sicaklik_varsayilan":0.7, "sistem_istemi":"", "yerel_mi":false }
```

## 9. Sohbet

| Yöntem | Yol | Yetki |
|---|---|---|
| POST | `/sohbet` | `gecerli_istemci` (JWT veya API anahtarı) |
| POST | `/sohbet/akis` | aynı, `text/event-stream` |
| GET | `/sohbet/konusmalar` | aynı |
| GET | `/sohbet/konusmalar/{id}` | aynı |
| PATCH | `/sohbet/konusmalar/{id}` `{baslik}` | aynı |
| DELETE | `/sohbet/konusmalar/{id}` | aynı |

İstek gövdesi:
```json
{ "bdm_id": 1, "bdm_slug": null, "konusma_id": null, "mesaj": "Merhaba", "sistem_istemi": null,
  "sicaklik": null, "maks_token": null,
  "dosya_idleri": null, "rag": false, "rag_belge_idleri": null, "rag_ust_k": null,
  "arac_sluglari": null }
```
`bdm_id` yerine `bdm_slug` kullanılabilir.

Ek bağlam alanları (v2, hepsi opsiyonel):

| Alan | Etki |
|---|---|
| `dosya_idleri` | Ekli dosyaların çıkarılmış **maskeli** metni sistem istemine eklenir; toplam `KUTYAI_DOSYA_BAGLAM_KR` karakterde kesilir. Organizasyona ait olmayan/bulunmayan id → `404 bulunamadi` |
| `rag` + `rag_belge_idleri` | Bilgi tabanından sorguya en yakın `rag_ust_k` (verilmezse `KUTYAI_RAG_UST_K`) parça sistem istemine eklenir; kullanılan parçalar yanıtta `kaynaklar` olarak döner. Org dışı belge id'si → `404 belge_bulunamadi` |
| `arac_sluglari` | Yalnız verilen araçlar modele sunulur; alan hiç verilmezse BDM'nin `arac` yeteneği açıkken organizasyonun tüm etkin araçları sunulur. Bilinmeyen slug → `404 arac_bulunamadi` |

Araç turu sınırı (`KUTYAI_ARAC_MAKS_TUR`) aşılırsa `400 arac_tur_siniri`.

Tek yanıt `200`:
```json
{ "konusma_id": 3, "mesaj_id": 9, "icerik": "...", "token_girdi": 12, "token_cikti": 34, "gecikme_ms": 812,
  "kaynaklar": [{ "belge_id": 2, "belge_ad": "El Kitabı", "sira": 0, "skor": 0.8312 }],
  "arac_cagrilari": [{ "ad": "hesap_makinesi", "durum": "basarili" }] }
```
`kaynaklar` yalnız `rag: true` ve sonuç bulunduysa, `arac_cagrilari` yalnız araç çalıştırıldıysa eklenir.

`GET /sohbet/konusmalar` → `{ toplam, kayitlar: [{ id, baslik, bdm_id, bdm_ad, guncellenme, mesaj_sayisi, token_girdi, token_cikti }] }`
`GET /sohbet/konusmalar/{id}` → `{ id, baslik, bdm_id, olusturulma, mesajlar: [{ id, rol, icerik, token_sayisi, gecikme_ms, olusturulma }] }`

### SSE biçimi (`/sohbet/akis`)

```
event: baslangic
data: {"konusma_id":3,"mesaj_id":9}

event: arac_cagrisi
data: {"ad":"hesap_makinesi","argumanlar":{"ifade":"(2+3)*4"}}

event: arac_sonucu
data: {"ad":"hesap_makinesi","durum":"basarili","ozet":"20"}

event: parca
data: {"icerik":"Mer"}

event: kullanim
data: {"token_girdi":12,"token_cikti":34,"gecikme_ms":812}

event: bitti
data: {"kaynaklar":[{"belge_id":2,"belge_ad":"El Kitabı","sira":0,"skor":0.8312}],
       "arac_cagrilari":[{"ad":"hesap_makinesi","durum":"basarili"}]}
```
Olay sırası: `baslangic` → (`arac_cagrisi` → `arac_sonucu`)\* → `parca`\* → `kullanim` → `bitti`.
`arac_cagrisi`/`arac_sonucu` yalnız araç kullanıldığında, `bitti` gövdesindeki `kaynaklar`/`arac_cagrilari`
alanları yalnız RAG/araç sonucu varsa gelir (yoksa `data: {}`). `durum` değerleri: `basarili` | `hata`.
Hata durumunda: `event: hata` + `data:` içinde hata zarfı, **ardından her zaman `event: bitti`**. `Content-Type: text/event-stream`.

**Maskeleme sınırı (bilinçli karar):** Kullanıcı mesajı hem veritabanına hem sağlayıcıya **maskelenmiş** olarak gider. Modelin ürettiği yanıt veritabanına **maskelenmiş** kaydedilir; istemciye ise ham akıtılır (kendi oturumunun verisi). Bu nedenle paneldeki kayıt ile istemcideki metin farklı olabilir — kayıt tarafı KVKK'ya uygun, gösterim tarafı kullanıcının kendi verisidir.

**Bakım modu:** `ayar.bakim_modu=true` iken `/sohbet` ve `/sohbet/akis` → `503 bdm_hazir_degil` (mesaj: "Sistem bakımda.").

## 10. BDM hazırlama — `/bdm/hazirlama` (personel)

| Yöntem | Yol | Yanıt |
|---|---|---|
| POST | `/{id}/dogrula` | `{ basarili, gecikme_ms, modeller: string[], mesaj }` |
| POST | `/{id}/cek` | SSE: `event: ilerleme` + `data: {"yuzde":42,"mesaj":"..."}`, son `event: bitti` |
| POST | `/{id}/manifest` | `{ image, komut: string[], port, gpu, bellek_gb, ortam: Record<string,string> }` |
| GET | `/{id}/on-kontrol` | `{ docker, gpu, disk_gb, image_var, uygun, uyarilar: string[] }` |

GPU gerektiren sağlayıcıda (`vllm`, `tgi`) GPU yoksa `503 surucu_yok`.

## 11. BDM yönetimi — `/bdm/yonetim` (personel)

| Yöntem | Yol | Yanıt |
|---|---|---|
| POST | `/{id}/baslat` | `{ durum, konteyner_id }` |
| POST | `/{id}/durdur` | `{ durum }` |
| POST | `/{id}/yeniden-baslat` | `{ durum, konteyner_id }` |
| GET | `/{id}/durum` | `{ durum, konteyner_id, saglik: {calisiyor, hazir, mesaj} }` |
| GET | `/{id}/saglik` | `{ calisiyor, hazir, mesaj, ayrinti }` |
| GET | `/{id}/gunlukler?satir=200` | SSE: `event: satir` + `data: {"metin":"..."}` |
| PATCH | `/{id}/yol` `{oncelik?, takma_ad?}` | `Bdm` |
| GET | `/surucu/durum` | `{ surucu, docker, gpu, gpu_listesi: string[], image_onbellek: string[], mesaj }` |

Geçersiz durum geçişi `409 gecersiz_gecis`.

## 12. Loglar (personel)

| Yöntem | Yol | Not |
|---|---|---|
| GET | `/loglar/konusmalar?kullanici_id=&bdm_id=&baslangic=&bitis=&arama=&sayfa=&boyut=` | `Sayfa<{id,baslik,kullanici_eposta,bdm_ad,mesaj_sayisi,token_girdi,token_cikti,olusturulma}>` |
| GET | `/loglar/konusmalar/{id}` | mesajlarla birlikte |
| GET | `/loglar/konusmalar/{id}/disa-aktar?bicim=json\|md\|csv` | dosya indirme |
| GET | `/islem-kayitlari?eylem=&kullanici_id=&baslangic=&bitis=&sayfa=&boyut=` | Denetim izi: `Sayfa<{id, kullanici_id, kullanici_eposta, eylem, hedef_tur, hedef_id, ayrinti, ip, olusturulma}>` (personel; en yeni önce) |
| DELETE | `/loglar/konusmalar/{id}` | `204` — yönetici/operatör (`izleyici` → `403`) |
| POST | `/loglar/temizle` `{gun?}` | `{silinen:number}` (yalnız yönetici) |

Sayfalama sınırları: `sayfa >= 1`, `1 <= boyut <= 200`; aralık dışı değer `400 dogrulama_hatasi`.
`baslangic > bitis` ise `400 gecersiz_istek`.

## 13. Kullanım

| Yöntem | Yol | Yetki | Yanıt |
|---|---|---|---|
| GET | `/kullanim/ozet?gun=30` | personel | `{ toplam_istek, toplam_token, basarili, hatali, kota_asimi, ortalama_gecikme_ms }` |
| GET | `/kullanim/zaman-serisi?gun=30&kirilim=bdm\|kullanici` | personel | `{ seri: [{ etiket, istek, token }] }` |
| GET | `/kullanim/benim?gun=30` | `gecerli_istemci` | Kişisel kullanım: `{ gun, toplam_istek, toplam_token, girdi_token, cikti_token, ortalama_gecikme_ms, kota: {gunluk_istek, kullanilan_gunluk, aylik_token, kullanilan_aylik, gun_sifirlanma, ay_sifirlanma} \| null, seri: [{ tarih, token }] }` — yalnız çağıran kullanıcının/anahtarın kayıtları |

## 14. Ayarlar (yönetici)

| Yöntem | Yol | Gövde |
|---|---|---|
| GET | `/ayarlar` | — → `{ marka_adi, kurulum_tamam, saklama_gun, maskeleme_aktif, kayit_acik, smtp_host, smtp_gonderen, smtp_tanimli, bakim_modu }` |
| PUT | `/ayarlar` | `{ marka_adi?, saklama_gun?, maskeleme_aktif?, kayit_acik?, smtp_host?, smtp_port?, smtp_kullanici?, smtp_sifre?, smtp_gonderen?, smtp_tls?, bakim_modu? }` |

---

## 15. Çok kiracılılık (v2)

**Aktif organizasyon** şu öncelikle çözülür: `X-Organizasyon: <slug>` başlığı → erişim jetonundaki `org` claim'i → API anahtarının organizasyonu → kullanıcının ilk aktif üyeliği. Hiçbiri yoksa kullanıcı **varsayılan organizasyona** eklenir (`varsayilan`).

Yetki kararı `kullanici.rol` değil **üyelik rolü** üzerinden verilir: `sahip` (her zaman yetkili) · `yonetici` · `operator` · `izleyici` · `son_kullanici`.

| Yöntem | Yol | Yetki | Not |
|---|---|---|---|
| GET | `/organizasyonlar` | kimlikli | Üye olduğu organizasyonlar: `[{id, ad, slug, durum, rol, olusturulma}]` |
| POST | `/organizasyonlar` | kimlikli | `{ad, slug?}` → `201`; oluşturan `sahip` olur |
| GET | `/organizasyonlar/{id}` | üye | |
| PATCH | `/organizasyonlar/{id}` | `sahip`/`yonetici` | `{ad?, durum?}` |
| GET | `/organizasyonlar/{id}/uyeler` | üye | `[{kullanici_id, eposta, ad_soyad, rol, durum, olusturulma}]` |
| POST | `/organizasyonlar/{id}/uyeler` | `sahip`/`yonetici` | `{eposta?\|kullanici_id?, rol}` → `201` |
| PATCH | `/organizasyonlar/{id}/uyeler/{kullanici_id}` | `sahip`/`yonetici` | `{rol?, durum?}` |
| DELETE | `/organizasyonlar/{id}/uyeler/{kullanici_id}` | `sahip`/`yonetici` | `204` |
| POST | `/kimlik/organizasyon-sec` | kimlikli | `{organizasyon_id}` → `{erisim_jetonu, organizasyon}` |

**Kurallar:** son `sahip` düşürülemez/silinemez ve kişi kendi `sahip` rolünü düşüremez → `409 gecersiz_gecis`. `sahip` rolüne **yükseltme** (`POST`/`PATCH .../uyeler`) yalnız mevcut aktif `sahip` tarafından yapılabilir; `yonetici` kendisi ya da başkası için `rol: "sahip"` gönderirse `403 yetki_yok`. Askıya alınmış organizasyon (`durum=askida`) hangi çözüm yoluyla (başlık, jeton `org` claim'i, API anahtarı, ilk üyelik) bulunursa bulunsun erişim `403 yetki_yok` ile kesilir. Organizasyon kapsamlı tüm kayıtlar (`bdm`, `konusma`, `api_anahtari`, `loglar`, `kullanim`, `dosya`, `rag`, `araclar`, `faturalama`, `sso`, `posta-sablonlari`) yalnız aktif organizasyona görünür; başka organizasyonun kaydı `404` döner.

## 16. Dil (i18n)

- İstek dili `Accept-Language` başlığından çözülür (`tr` varsayılan, `en` desteklenir); hata ve bilgi mesajları o dilde döner.
- `kod` alanı her zaman dilden bağımsızdır ve mesaj seçimi için tek referanstır.
- Yanıt başlığı `Content-Language: tr|en` döner.

| Yöntem | Yol | Yetki | Yanıt |
|---|---|---|---|
| GET | `/i18n/diller` | açık | `[{kod, ad, varsayilan}]` |
| GET | `/i18n/sozluk/{dil}` | açık | `{ anahtar: mesaj }` (arayüz kataloğu) |

## 17. Yeni hata kodları (v2)

| HTTP | `kod` |
|---|---|
| 400 | `organizasyon_gerekli`, `sso_yapilandirilmamis`, `medya_desteklenmiyor`, `arac_tur_siniri`, `arac_uc_noktasi_zorunlu`, `arac_uc_noktasi_gecersiz`, `arac_https_zorunlu`, `arac_yerlesik_bilinmiyor`, `arac_basliklar_gecersiz`, `dosya_tur_desteklenmiyor`, `dosya_metni_cikarilamadi`, `belge_kaynak_gerekli`, `belge_metni_bos`, `belge_parcasi_yok`, `gomme_modeli_yok`, `odeme_saglayici_yok` |
| 401 | `sso_dogrulanamadi`, `oidc_durum_gecersiz`, `saml_yanit_gecersiz` |
| 402 | `abonelik_gecikmis` |
| 403 | `org_erisim_yok` |
| 404 | `plan_bulunamadi`, `abonelik_yok`, `fatura_bulunamadi`, `arac_bulunamadi`, `belge_bulunamadi` |
| 409 | `saml_tekrar_oynatma`, `arac_slug_kullaniliyor` |
| 413 | `dosya_cok_buyuk` |
| 502 | `arac_hatasi`, `rag_gomme_hatasi`, `webhook_imzasi_gecersiz` |

Araç argümanları şemaya uymazsa `400 arac_arguman_*` (`tur`, `enum`, `minimum`, `maksimum`, `zorunlu`, `fazla`) döner. Ayrıca §1'deki ortak kodlar geçerlidir (`bulunamadi`, `yetki_yok`, `gecersiz_istek`, `cakisma`, `gecersiz_gecis`, `dogrulama_hatasi`).

---

## 18. Dosyalar (`/dosyalar`, personel)

| Yöntem | Yol | Not |
|---|---|---|
| POST | `/dosyalar` | multipart: `dosya` (zorunlu), `ad?` → `201 {id, ad, mime, boyut, sha256, metin_uzunluk, olusturulma}` |
| GET | `/dosyalar?arama=&sayfa=&boyut=` | `Sayfa<{id, ad, mime, boyut, olusturulma}>` (en yeni önce) |
| GET | `/dosyalar/{id}` | meta (metin maskeli) |
| GET | `/dosyalar/{id}/icerik` | ham baytlar, `Content-Disposition: attachment` + RFC 5987 `filename*` |
| DELETE | `/dosyalar/{id}` | `204`, diskten de siler |

Sınırlar: `KUTYAI_DOSYA_MAKS_MB` (413 `dosya_cok_buyuk`), izinli MIME listesi (400 `dosya_tur_desteklenmiyor`). Çıkarılan metin `dosya.metin`'e **maskelenmiş** yazılır. PDF çıkarımı `pypdf` ile.

## 19. Araçlar (`/araclar`)

| Yöntem | Yol | Yetki |
|---|---|---|
| GET | `/araclar?etkin=` | personel (izleyici okur) |
| POST | `/araclar` | yönetici/operatör |
| PATCH | `/araclar/{id}` | yönetici/operatör |
| DELETE | `/araclar/{id}` | yönetici/operatör → `204` |
| POST | `/araclar/{id}/dene` | yönetici/operatör → `{durum, sonuc, gecikme_ms}` |
| GET | `/araclar/cagrilar?arac_id=&durum=&sayfa=&boyut=` | `Sayfa<{id, ad, argumanlar, sonuc, durum, gecikme_ms, hata, olusturulma}>` |

`POST /araclar` gövdesi: `{ad, slug?, aciklama?, json_sema?, tur: "webhook"|"yerlesik", uc_noktasi?, basliklar?, etkin?}`. Yerleşik türler: `hesap_makinesi`, `zaman`. Webhook: HTTPS zorunlu (`KUTYAI_ARAC_YEREL_IZIN=true` ile yerel HTTP), `X-Kutyai-Imza: sha256=<hmac>` başlığı (`KUTYAI_ARAC_IMZA_ANAHTARI` boşsa jeton sırrından ayrı anahtar türetilir), 10 sn zaman aşımı, 64 KB yanıt sınırı; hedef adres SSRF denetiminden geçer — loopback/özel/link-local adresler ile bulut metadata adresleri (`169.254.169.254`, `100.100.100.200`, `metadata.google.internal`) reddedilir, yerel kabul yalnız `KUTYAI_ARAC_YEREL_IZIN=true` iken geçerlidir.

Sohbette kullanım: `arac_sluglari` alanı; SSE olayları `arac_cagrisi` / `arac_sonucu`; yanıtta `arac_cagrilari`.

## 20. Bilgi tabanı / RAG (`/rag`)

| Yöntem | Yol | Yetki | Not |
|---|---|---|---|
| GET | `/rag/belgeler` | personel | `[{id, ad, kaynak, parca_sayisi, olusturulma}]` |
| POST | `/rag/belgeler` | yönetici/operatör | `{ad, bdm_id, metin? \| dosya_id?, meta?}` → `201` |
| GET | `/rag/belgeler/{id}` | personel | parçalarla birlikte |
| DELETE | `/rag/belgeler/{id}` | yönetici/operatör | `204` |
| POST | `/rag/ara` | personel | `{sorgu, bdm_id?, ust_k?, belge_idleri?}` → `{sonuclar: [{belge_id, belge_ad, sira, icerik, skor}], ayrinti: {yol, ust_k}}` |
| POST | `/rag/belgeler/{id}/yeniden-gom` | yönetici/operatör | parçaları yeni gömme modeliyle tazeler |

Gömme: `POST {bdm.temel_url}/embeddings`, model `bdm.gomme_modeli`. Arama taşınabilir (Python kosinüs); Postgres + `pgvector` varsa SQL yolu, `ayrinti.yol` bunu bildirir. Sohbette `rag: true` + `rag_belge_idleri`; yanıtta `kaynaklar`.

## 21. Medya (`/medya`)

| Yöntem | Yol | Gövde | Yetki |
|---|---|---|---|
| POST | `/medya/gorsel` | `{bdm_id, istem, boyut?, adet?}` | yönetici/operatör → `[{dosya_id, ad, mime, boyut}]` |
| POST | `/medya/ses` | `{bdm_id, metin, ses?, bicim?}` | yönetici/operatör → `{dosya_id}` |
| POST | `/medya/coz` | `{bdm_id, dosya_id}` | yönetici/operatör → `{metin}` |

Model yeteneği kapalıysa `400 medya_desteklenmiyor`. Üretilenler `dosya` tablosuna yazılır, `kullanim_kaydi` işlenir.

---

## 22. SSO (`/sso`, organizasyon kapsamlı)

Sağlayıcı yönetimi organizasyon yönetim rollerine (`sahip`/`yonetici`) açıktır; giriş akışı uçları **kimlik istemez** (tarayıcı yönlendirmesi olarak çalışır).

| Yöntem | Yol | Yetki | Not |
|---|---|---|---|
| GET | `/sso/saglayicilar` | personel | `[{id, tur, ad, slug, etkin, ayarlar, sir_tanimli, giris_yolu, olusturulma}]` |
| POST | `/sso/saglayicilar` | `sahip`/`yonetici` | `{tur: "oidc"\|"saml", ad, slug?, etkin?, ayarlar?, sir?}` → `201` (sağlayıcı gövdesi); slug çakışması `409 cakisma` |
| PATCH | `/sso/saglayicilar/{id}` | `sahip`/`yonetici` | `{ad?, etkin?, ayarlar?, sir?}`; `ayarlar` mevcut anahtarlarla **birleştirilir** |
| DELETE | `/sso/saglayicilar/{id}` | `sahip`/`yonetici` | `204` |
| GET | `/sso/{org_slug}/{saglayici_slug}/baslat` | açık | `302` → türe göre OIDC yetkilendirme ya da SAML IdP yönlendirmesi |
| GET | `/sso/{org_slug}/{saglayici_slug}/saml/baslat` | açık | SAML için başlatma kapısı (`302`); sağlayıcı OIDC ise `400 sso_yapilandirilmamis` |
| GET | `/sso/{org_slug}/{saglayici_slug}/donus?code=&state=` | açık | OIDC dönüşü (SAML sağlayıcıda `400 sso_yapilandirilmamis`): `state` zorunlu ve **tek kullanımlık** (10 dk); kod değişimi + `id_token` doğrulaması → jeton gövdesi ya da `KUTYAI_SSO_YENIDEN_YONLENDIRME` adresine `302` (`?kod=`) |
| POST | `/sso/{org_slug}/{saglayici_slug}/saml/acs` | açık | `application/x-www-form-urlencoded`: `SAMLResponse` (zorunlu), `RelayState` (**zorunlu**; imzalı state: yoksa `400 oidc_durum_gecersiz`, çözülemez/başka sağlayıcıya aitse `401 oidc_durum_gecersiz`) |
| POST | `/sso/kod-degistir` | açık | `{kod}` → jeton gövdesi; yönlendirme akışının **60 sn** ömürlü imzalı kodu (durumsuzdur: sunucu tarafı tek-kullanım kaydı yoktur) |

Sağlayıcı gövdesinde `sir` yazılabilir ama **okunmaz**: yanıtta yalnız `sir_tanimli: boolean` döner, `ayarlar` içinde adında `secret`/`sifre` geçen anahtarlar süzülür. `giris_yolu` = `/api/v1/sso/{org}/{slug}/baslat`.

`ayarlar` anahtarları:

| `tur` | Anahtarlar |
|---|---|
| `oidc` | `issuer` (zorunlu; `.well-known/openid-configuration` kökü, **`https`** ve keşif belgesindeki `issuer` ile birebir aynı olmalı), `client_id` (zorunlu), `kapsamlar?` (varsayılan `openid email profile`), `eposta_claim?` (varsayılan `email`), `ad_claim?` (varsayılan `name`) — istemci sırrı `sir` alanında |
| `saml` | `idp_sso_url` (zorunlu, **`https`**), `sp_entity_id?` (varsayılan ACS adresi), `idp_imza_sertifikasi` (zorunlu; PEM ya da çıplak base64), `eposta_ozniteligi?`, `ad_ozniteligi?`, `sp_imza_anahtari?` (PEM RSA özel anahtar; varsa `AuthnRequest` `RSA-SHA256` ile imzalanır) |

`issuer`/`idp_sso_url` adresleri SSRF denetiminden geçer: `https` zorunludur ve bulut metadata,
loopback, özel/link-local adresler reddedilir (`400 sso_yapilandirilmamis`). Şirket içi/yerel IdP
için `KUTYAI_SSO_YEREL_IZIN=true` ayarlanır; bu durumda `http` ve yerel ağ adresleri kabul edilir
(üretimde kapalı tutun).

Jeton gövdesi (`/donus`, `/saml/acs` ve `/sso/kod-degistir` ortak): `{ erisim_jetonu, yenileme_jetonu, kullanici: {id, eposta, ad_soyad, rol, durum, eposta_dogrulandi}, organizasyon: {id, ad, slug} | null }`. `KUTYAI_SSO_YENIDEN_YONLENDIRME` doluysa gövde yerine `302` + `?kod=` döner.

Kullanıcı eşleme sırası: `sso_kimlik` (sağlayıcı + dış kimlik) → e-posta → **yeni kullanıcı** (`son_kullanici`, `eposta_dogrulandi=true`). E-posta adımı **yalnız kullanıcı sağlayıcının organizasyonunda aktif üyeyse** birleştirir; aksi halde giriş `403 yetki_yok` ile reddedilir ve jeton verilmez. OIDC'te IdP `email_verified=false` bildirdiyse e-posta adımı hiç denenmez (`401 sso_dogrulanamadi`). Üyelik yoksa `KUTYAI_SSO_OTOMATIK_UYELIK=true` iken `son_kullanici` üyeliği eklenir.

Hatalar: `400 sso_yapilandirilmamis` (sağlayıcı yok/pasif, zorunlu ayar eksik, IdP adresi güvenli değil ya da keşif `issuer`'ı uyuşmuyor), `400 oidc_durum_gecersiz` (`/saml/acs`'te `RelayState` yok), `401 sso_dogrulanamadi` (id_token doğrulanamadı, `email_verified=false` ile mevcut hesap çakışması), `401 oidc_durum_gecersiz` (state yok/çözülemez/başka sağlayıcıya ait/tekrar kullanılmış), `401 saml_yanit_gecersiz` (imza, `Audience`, `Destination`, `Recipient`, süre alanları, `InResponseTo`), `409 saml_tekrar_oynatma` (aynı `Assertion ID` 10 dk içinde yeniden kullanılırsa), `403 yetki_yok` (kullanıcı pasif, e-posta başka organizasyona ait ya da otomatik üyelik kapalıyken üyelik yok).

## 23. Faturalama (`/faturalama`)

Planlar **global**, abonelik ve faturalar organizasyon kapsamlıdır.

| Yöntem | Yol | Yetki | Not |
|---|---|---|---|
| GET | `/faturalama/planlar` | personel | Etkin planlar (fiyata göre artan): `[{id, ad, slug, aylik_fiyat_kurus, aylik_fiyat, para, dahil_istek, dahil_token, ozellikler, etkin}]` |
| GET | `/faturalama/abonelik` | personel | Abonelik gövdesi ya da `null`: `{id, durum: "deneme"\|"aktif"\|"gecikmis"\|"iptal", plan, donem_basi, donem_sonu, saglayici, dis_id, erisim}` |
| POST | `/faturalama/abonelik` | `sahip`/`yonetici` | `{plan_id, donem_gun?}` (`1..3650`, varsayılan 30) → `201 {abonelik, fatura, odeme_url}` |
| POST | `/faturalama/abonelik/iptal` | `sahip`/`yonetici` | Aboneliği `iptal` işaretler → abonelik gövdesi; abonelik yoksa `404 abonelik_yok` |
| GET | `/faturalama/faturalar?sayfa=&boyut=` | personel | `{toplam, sayfa, boyut, kayitlar}`; varsayılan 25, en çok 200 (`400 gecersiz_istek`) |
| POST | `/faturalama/faturalar/{id}/odendi` | `sahip`/`yonetici` | **Yalnız `yerel` sürücü**: faturayı `odendi` yapar; `gecikmis` abonelik `aktif`e döner. Başka sürücüde ya da fatura zaten ödenmişse `400 gecersiz_istek` |
| POST | `/faturalama/odeme-oturumu` | `sahip`/`yonetici` | `{fatura_id}` → `{dis_id, url, saglayici}` (sağlayıcı ödeme oturumu; `yerel` sürücüde `url: null`) |
| POST | `/faturalama/webhook/stripe` | **açık** | Ham Stripe olayı; `KUTYAI_ODEME_SAGLAYICI=stripe` değilse `400 odeme_saglayici_yok`, imza geçersizse `502 webhook_imzasi_gecersiz` → `{alindi: true, tur, uygulandi}` |

`POST /faturalama/abonelik` ilk faturayı `taslak` üretir. Ödeme onayı sağlayıcıda bekleniyorsa (`stripe`: `odeme_url` döner) abonelik **`deneme`** kalır ve plan kotası **yazılmaz**; kota, ödeme onayı geldiğinde (webhook) yazılır. `yerel` sürücüde tahsilat manuel olduğu için abonelik hemen `aktif` olur, plan limitleri organizasyon kotasına yazılır (`dahil_istek`, `dahil_token`; sayaçlar sıfırlanır).

Fatura gövdesi: `{id, tutar_kurus, tutar, para, durum: "taslak"\|"odendi"\|"basarisiz"\|"iade", kalemler, dis_id, olusturulma, odeme_tarihi}`.

Stripe eşlemesi: abonelik checkout oturumu `client_reference_id` (organizasyon) + `metadata[abonelik_id]`/`metadata[fatura_id]` ile etiketlenir; `abonelik.dis_id` Stripe abonelik kimliğini (oturum yanıtında yoksa oturum kimliğini), `fatura.dis_id` checkout oturum kimliğini taşır. Webhook olayı önce `metadata`, sonra `dis_id` (checkout oturumu/abonelik) üzerinden aboneliğe ve faturaya eşlenir; `checkout.session.completed`/`invoice.paid` → fatura `odendi` + abonelik `aktif` + kota uygulanır (gerçek `sub_…` kimliği aboneliğe yazılır), `invoice.payment_failed` → fatura `basarisiz` + abonelik `gecikmis`, `customer.subscription.deleted` → abonelik `iptal`. Hiçbir kayda oturmayan olay ya da durum güncellemeyen diğer olaylar `uygulandi: false` ile yanıtlanır (durum değişmez, olay günlüğe yazılır).

Hatalar: `404 plan_bulunamadi`, `404 abonelik_yok`, `404 fatura_bulunamadi`, `400 odeme_saglayici_yok`, `502 webhook_imzasi_gecersiz`. Aboneliği `gecikmis`/`iptal` olan organizasyonda `POST /sohbet` ve `POST /sohbet/akis` **`402 abonelik_gecikmis`** döner (spec §6); abonelik durumu ayrıca `GET /faturalama/abonelik` yanıtındaki `erisim` alanıyla bildirilir.

## 24. Posta şablonları (`/posta-sablonlari`, organizasyon kapsamlı)

Şablonlar `(org, kod, dil)` ile saklanır; organizasyon kaydı yoksa gömülü varsayılan (TR/EN) kullanılır.

| Yöntem | Yol | Yetki | Not |
|---|---|---|---|
| GET | `/posta-sablonlari` | personel | 6 kod × 2 dil: `[{kod, dil, konu, govde_metin, govde_html, ozel}]` (`ozel=false` → gömülü varsayılan) |
| PUT | `/posta-sablonlari` | `sahip`/`yonetici` | `{kod, dil?, konu, govde_metin?, govde_html?}` → `{kod, dil, konu, govde_metin, govde_html, ozel: true}`; geçersiz kod/dil `400 gecersiz_istek` (ayrıntıda geçerli listeler) |
| POST | `/posta-sablonlari/{kod}/onizle` | personel | `{degiskenler?, dil?}` → `{kod, dil, konu, govde_metin, govde_html}`; bilinmeyen `kod` → `404 bulunamadi`, bilinmeyen dil `tr`ye düşer |

Kodlar: `dogrulama`, `sifirlama`, `davet`, `kota_uyarisi`, `fatura`, `hosgeldin`. Diller: `tr` (varsayılan), `en`.

Yerine koyma `{{degisken}}` biçimindedir (koşullu blok yok); bilinmeyen değişken metinde aynen kalır. Önizleme örnek değerlerle doldurur (`marka`, `ad`, `organizasyon`, `baglanti`, `davet_eden`, `yuzde`, `donem`, `tutar`, `fatura_no`) ve `degiskenler` ile bunlar ezilebilir.
