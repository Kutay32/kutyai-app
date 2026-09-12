# KutyAI API Sözleşmesi (v1)

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
| 401 | `kimlik_gerekli`, `jeton_gecersiz`, `jeton_suresi_doldu`, `anahtar_gecersiz` |
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
  konteyner: { image?: string; gpu?: boolean; port?: number; bellek_gb?: number } | null;
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
| POST | `/kimlik/panel-giris` | `{eposta, parola}` | aynı (yalnız personel; `son_kullanici` → `403`) |
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

## 7. API anahtarları

| Yöntem | Yol | Yanıt |
|---|---|---|
| GET | `/api-anahtarlari` | `[{id, ad, onek, son_dort, durum, izinli_modeller, gunluk_istek_siniri, olusturulma, son_kullanim}]` |
| POST | `/api-anahtarlari` `{ad, izinli_modeller?, gunluk_istek_siniri?, kullanici_id?}` | `201 {…, tam_anahtar}` — **`tam_anahtar` yalnızca bu yanıtta** |
| POST | `/api-anahtarlari/{id}/iptal` | `{durum:"iptal"}` |

## 8. Model kataloğu

| Yöntem | Yol | Yetki | Yanıt |
|---|---|---|---|
| GET | `/modeller` | kimlikli | `BdmOzet[]` (yalnız `hazir\|calisiyor`, anahtarın izinli listesi süzülür) |
| GET | `/bdm` | personel | `Bdm[]` |
| POST | `/bdm` | yönetici/operatör | `201 Bdm` |
| PATCH | `/bdm/{id}` | yönetici/operatör | `Bdm` |
| POST | `/bdm/{id}/kopyala` | yönetici | `201 Bdm` |
| DELETE | `/bdm/{id}` | yönetici | `204` |

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
{ "bdm_id": 1, "konusma_id": null, "mesaj": "Merhaba", "sistem_istemi": null,
  "sicaklik": null, "maks_token": null }
```
`bdm_id` yerine `bdm_slug` kullanılabilir.

Tek yanıt `200`:
```json
{ "konusma_id": 3, "mesaj_id": 9, "icerik": "...", "token_girdi": 12, "token_cikti": 34, "gecikme_ms": 812 }
```

`GET /sohbet/konusmalar` → `{ toplam, kayitlar: [{ id, baslik, bdm_id, bdm_ad, guncellenme, mesaj_sayisi, token_girdi, token_cikti }] }`
`GET /sohbet/konusmalar/{id}` → `{ id, baslik, bdm_id, olusturulma, mesajlar: [{ id, rol, icerik, token_sayisi, gecikme_ms, olusturulma }] }`

### SSE biçimi (`/sohbet/akis`)

```
event: baslangic
data: {"konusma_id":3,"mesaj_id":9}

event: parca
data: {"icerik":"Mer"}

event: kullanim
data: {"token_girdi":12,"token_cikti":34,"gecikme_ms":812}

event: bitti
data: {}
```
Hata durumunda: `event: hata` + `data:` içinde hata zarfı. `Content-Type: text/event-stream`.

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
| DELETE | `/loglar/konusmalar/{id}` | `204` |
| POST | `/loglar/temizle` `{gun?}` | `{silinen:number}` (yalnız yönetici) |

## 13. Kullanım

| Yöntem | Yol | Yanıt |
|---|---|---|
| GET | `/kullanim/ozet?gun=30` | `{ toplam_istek, toplam_token, basarili, hatali, kota_asimi, ortalama_gecikme_ms }` |
| GET | `/kullanim/zaman-serisi?gun=30&kirilim=bdm\|kullanici` | `{ seri: [{ etiket, istek, token }] }` |

## 14. Ayarlar (yönetici)

| Yöntem | Yol | Gövde |
|---|---|---|
| GET | `/ayarlar` | — → `{ marka_adi, kurulum_tamam, saklama_gun, maskeleme_aktif, kayit_acik, smtp_host, smtp_gonderen, smtp_tanimli, bakim_modu }` |
| PUT | `/ayarlar` | `{ marka_adi?, saklama_gun?, maskeleme_aktif?, kayit_acik?, smtp_host?, smtp_port?, smtp_kullanici?, smtp_sifre?, smtp_gonderen?, smtp_tls?, bakim_modu? }` |
