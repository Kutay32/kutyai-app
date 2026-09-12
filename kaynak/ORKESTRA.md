# KutyAI — Orkestra Sözleşmesi

Bu belge, platformun **nasıl geliştirildiğini** ve şirketin kendi ekibinin aynı düzeni nasıl sürdüreceğini tanımlar.

## 1. İlke

Her özellik için **iki ajan** çalışır:

| Rol | Görev | Yazma izni |
|---|---|---|
| **Uygulayıcı** | Özelliği kodlar, kendi testini yazar, commit eder | yalnız kendi klasörü |
| **Gözlemci** | Kodu kara kutu kabul eder, bağımsız test koşar, kanıtı loglar | yalnız `kaynak/testler/` |

Gözlemci uygulayıcının testini **tekrar etmez**; sözleşmeyi (spec + `API.md`) okuyup kendi senaryolarını yazar.

## 2. Döngü

```
1. Spec dondurulur (kaynak/spec/)
2. Uygulayıcı ve gözlemci eşzamanlı başlar
3. Gözlemci test betiğini spec'ten yazar, kodu bekler
4. Uygulayıcı biter → derler, kendi testini koşar
5. Gözlemci koşar → kaynak/testler/<modul>-log.md
6. Controller logu uygulayıcıya iletir → düzeltme ister
7. Uygulayıcı düzeltir → gözlemci yeniden koşar (log aynı dosyaya güncelleme olarak yazılır)
8. Spec uyumu incelemesi → kod kalitesi incelemesi → kapanış
```

**Kapanış koşulu:** gözlemci logunda BLOCKER kalmaması + iki aşamalı incelemenin onayı.

## 3. Gözlemci log biçimi (zorunlu)

```markdown
# <modül> gözlem logu — YYYY-MM-DD
## Kapsam (spec/API maddeleri)
- §7.4 sohbet akışı
## Koşulan komutlar
### 1) python -m pytest arkauc/testler/test_sohbet.py -q
- Beklenen: 6 test geçer
- Gerçek çıktı:
```
.....
```
- Sonuç: GEÇTİ
## Bulgular
- [BLOCKER] arkauc/app/api/sohbet.py:88 — istemci koptuğunda upstream iptal edilmiyor — beklenen: iptal — yeniden üretme: 200 tokenlık yanıtı yarıda kes
- [MINOR] mesaj başlığı 60 karakterde kesilmiyor
## Özet
2 bulgu (1 BLOCKER, 1 MINOR)
```

Ağırlık: `BLOCKER` (çalışmıyor/veri kaybı/güvenlik) · `MAJOR` (sözleşme ihlali) · `MINOR` (kalite).

## 4. Klasör sahipliği

Bir ajan **yalnızca** kendi klasörüne yazar. Paylaşılan dosya değişikliği gerekiyorsa sahibine iletilir. Dondurulmuş dosyalar:

```
arkauc/app/main.py
arkauc/app/cekirdek/**
arkauc/testler/conftest.py
bdm_veritabani/**
```

Değişiklik gerekiyorsa: controller onayı + tüm dalgaların haberdar edilmesi.

## 5. Dalga düzeni

| Dalga | İçerik | Paralellik |
|---|---|---|
| 0 | Sözleşme: şema, çekirdek, keşif, fikstürler, doküman | seri |
| 1 | Çekirdek yetenekler: kimlik, katalog, hazırlama, yönetim, sohbet, loglar, iki arayüz iskeleti | 8 uygulayıcı + 8 gözlemci |
| 1′ | Gözlemci logları → düzeltme turu | 8 uygulayıcı |
| 2 | Arayüzler ve dağıtım | 4 uygulayıcı + gözlemciler |
| 3 | Uçtan uca doğrulama, iki aşamalı inceleme, kapanış | seri |

## 6. İnceleme sırası

1. **Spec uyumu:** kod `kaynak/spec` ve `kaynak/API.md` ile birebir mi? Eksik ve **fazla** özellik aranır.
2. **Kod kalitesi:** hata yolları, sızıntı, gereksiz soyutlama, test kalitesi, Türkçe metin tutarlılığı.
3. Bulgu varsa uygulayıcı düzeltir, inceleme yeniden koşar. **İnceleme onaylanmadan görev kapanmaz.**

## 7. Şirket içi kullanım

Aynı düzeni kendi özellikleriniz için uygulayın:

1. `kaynak/spec/` altına özellik spec'i yazın (kabul kriterleri ölçülebilir olsun).
2. Uygulayıcı + gözlemci ajanı ayrı klasörlerle görevlendirin.
3. Gözlem logunu `kaynak/testler/` altında saklayın; sürüm kontrolüne alın.
4. Logdaki BLOCKER kapanmadan özelliği yayına almayın.
