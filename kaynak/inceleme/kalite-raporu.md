# Kod kalitesi ve güvenlik incelemesi raporu — 2026-09-12

Kapsam: `arkauc/`, `bdm_hazırlama_ucu/`, `bdm_yönetim_ucu/`, `bdm_listesi/`, `bdm_konusma_gecmisi/`, `bdm_veritabani/`
(HEAD = `62e8838`; Dalga 1 + düzeltme turu). `onuc/`, `yonetim_paneli/`, `dagitim/` kapsam dışıdır.

## Yöntem

- Diff kaynakları: `git show 789ceef`, `git show 62e8838`, `git diff c314801..HEAD`. Kapsamdaki tüm ürün
  dosyaları ve test dosyaları satır satır okundu; **hiçbir ürün dosyası değiştirilmedi**.
- Test kalitesi taraması: `arkauc/testler/` altındaki 185 test fonksiyonu (193 parametrik vaka) yardımcı bir
  okuma ajanıyla tarandı; yalnız kanıtlanabilir bulgular rapora alındı.
- Sır sızması taraması: tüm `logger.*` çağrıları `sifre|parola|token|api_anahtar|secret|gizli` deseniyle tarandı.
- Doğrulama koşuları: depo kökündeki `.venv` (FastAPI 0.141.1, SQLAlchemy 2.0.52) ile, depo dışında üretilen
  geçici SQLite dosyasına karşı yazılan izole deney betikleri. Depo içindeki hiçbir dosya yazılmadı.
  1. İki eşzamanlı oturumda `kota_kontrol` + `kota_kullan` (kota sayacı yarışı)
  2. İki eşzamanlı `POST /kurulum` (6 koşu)
  3. `_kilit` enjekte edilerek kilit devre dışı bırakılmış kurulum (10 koşu)
  4. `KUTYAI_MASKELEME_AKTIF=false` iken `PUT /ayarlar {"maskeleme_aktif": true}` + `POST /sohbet`
  5. İki eşzamanlı `POST /bdm/yonetim/{id}/baslat` (`SahteSurucu` ile)
  6. Durdurulmuş akış iptalinde oturum/görev sahipliği (GC denemesi)

## Bulgular

- **[BLOCKER]** `arkauc/app/api/ayarlar.py:54-55` — Panelden verilen `maskeleme_aktif` değeri `ayar` tablosuna
  yazılıyor ve `GET /ayarlar` bu değeri "etkin ayar" olarak raporluyor; ancak maskelemeyi gerçekten uygulayan tek
  tüketici `bdm_konusma_gecmisi/maskeleme.py:42` ortam değerini (`ayarlar.maskeleme_aktif`) okuyor, veritabanı
  anahtarını hiç okumuyor. **Beklenen:** diğer tüm anahtarlarda olduğu gibi (`saklama_gun`, `kayit_acik`,
  `bakim_modu`, `smtp_*`) etkin değerin `ayar` tablosundan okunması ve panel anahtarının maskelemeyi gerçekten
  açıp kapatması (API.md §14; spec §4.11 `ayar` anahtarları; `bdm_veritabani/tohum.py:20` varsayılanı `True`).
  **Kanıt:** deney 4 — `KUTYAI_MASKELEME_AKTIF=false`, `PUT /ayarlar {"maskeleme_aktif": true}` → 200,
  `GET /ayarlar` → `"maskeleme_aktif": true`, ardından gönderilen sohbet mesajı veritabanına
  `"Bana ayse@acme.com adresinden yazin"` olarak **maskesiz** yazıldı. Yani yönetici panelde maskelemeyi
  açtığını görürken e-posta/telefon/TCKN/IBAN içeren mesajlar düz metin olarak saklanıyor (KVKK kontrolü
  etkisiz). Tersi yönde de (ortam `true`, panel `false`) panel tercihi yok sayılır.

- **[MAJOR]** `arkauc/app/servisler/kota.py:178-179` — Kota sayaçları Python tarafında oku-değiştir-yaz ile
  artırılıyor (`kayit.kullanilan_gunluk += 1`, `kayit.kullanilan_aylik += ...`); SQLAlchemy mutlak değeri yazan
  bir `UPDATE` üretir. `kota_kontrol` (satır 128-156) ile `kota_kullan` arasında satır kilidi yoktur ve bu iki
  adım tek bir kritik bölge değildir: `/sohbet` akışında araya saniyeler süren upstream çağrısı girer
  (`arkauc/app/api/sohbet.py:180-190, 253-276`). **Beklenen:** sayacın atomik artırımı
  (`UPDATE kota SET kullanilan_gunluk = kullanilan_gunluk + 1`) ve kontrol+artırımın aynı kritik bölgede
  yapılması; proje bu deseni zaten kullanıyor (`oturumu_yenile` ve `dogrulama_jetonu_tuket` koşullu UPDATE +
  `rowcount` denetimi, `arkauc/app/servisler/kimlik.py:289-300, 383-404`). **Kanıt:** `dagitim/docker-compose.yml:132-149`
  PostgreSQL profilini sunuyor; `READ COMMITTED` altında iki eşzamanlı istek aynı sayacı okuyup son yazan kazanır
  (kayıp güncelleme) → günlük/aylık kota altında sayılır ve sınır aşılabilir [INFERENCE]. Varsayılan SQLite
  profilinde ise deney 1'de iki eşzamanlı oturumda `B kontrol` adımı `sqlite3.OperationalError: database is locked`
  ile bitti (30 sn sonra) — yani aynı istek çifti 500 ile düşer, 429/200 üretmez.

- **[MAJOR]** `bdm_yönetim_ucu/yasam_dongusu.py:155-158` — `baslat`, durum geçişini kilitsiz oku-denetle-yaz ile
  yapıyor: `gecis_dogrula(bdm, calisiyor)` sonrası `_calistir` içinde konteyner başlatılıyor, `bdm.konteyner`
  sonra yazılıyor. İki eşzamanlı istek de geçiş denetimini geçer ve sürücü iki kez çağrılır. **Beklenen:** geçişin
  koşullu UPDATE + `rowcount` ile tek istekte kilitlenmesi (`kimlik.py` deseni); yalnız geçişi kazanan istek
  konteyner başlatmalı. **Kanıt:** deney 5 — iki eşzamanlı `POST /bdm/yonetim/{id}/baslat` ikisi de 200 döndü,
  sürücüde **iki** konteyner oluştu (`sahte-vllm-1-1`, `sahte-vllm-1-2`), ama `bdm.konteyner.konteyner_id`
  yalnız `sahte-vllm-1-2` oldu. Kayıt dışı kalan konteyner platformdan durdurulamaz/silinemez (GPU/bellek sızıntısı);
  gerçek Docker sürücüsünde aynı ad (`kutyai-{slug}`, `konteyner_docker.py:266-270`) nedeniyle ikinci `run`
  çakışma yoluna girip ilk konteyneri kaldırır (`konteyner_docker.py:169-175`), bu durumda kayıtlı kimlik de geçersiz
  kalır.

- **[MINOR]** `arkauc/app/servisler/konteyner_docker.py:148,174,195,208` ve `arkauc/app/servisler/konteyner_yerel.py:134`
  — Sürücü istisna metni doğrudan istemciye dönen `mesaj` alanına konuyor
  (`f"'{image}' imajı çekilemedi: {hata}"`, `f"Konteyner başlatılamadı: {hata}"`, `f"... boşaltılamadı: {hata}"`).
  Bu metinler Docker API adresi, soket yolu, imaj kayıt defteri yanıtı ya da yerel servis adresi gibi iç
  ayrıntıları personel oturumuna taşır. **Beklenen:** projenin kendi politikası — `upstream.py:78-100`
  düzeltme turunda tam gövdeyi ve taşıma istisnasını yalnız günlüğe yazıp istemciye sabit Türkçe mesaj ve
  `{durum, saglayici}` ayrıntısı döndürüyor; sürücülerin de aynı sözleşmeye uyması. **Kanıt:** kod okuması;
  `SurucuYok`/`UstSaglayiciHatasi` doğrudan hata zarfına (`hatalar.py:160-162`) dönüşüyor.

- **[MINOR]** `arkauc/app/api/kurulum.py:97-110` — `_upstream_dogrula`, `inspect.signature` ile üç olası imzayı
  yoklayıp dallanıyor; teslim edilen kodda tek sağlayıcı `bdm_hazırlama_ucu/dogrulama.py:dogrula(bdm, *, oturum=None,
  ...)` ve ilk dal (`{"oturum", "bdm"} <= adlar`) her zaman kazanıyor, diğer iki dal ve `except ImportError`
  koruması ölü. **Beklenen:** doğrudan `await dogrula(oturum=oturum, bdm=bdm)` çağrısı; paralel geliştirme
  dönemine ait imza uyarlaması teslim edilen kodda bakım yükü ve yanlış dallanma riski. **Kanıt:** kod okuması +
  `arkauc/app/main.py:33-35` (yönlendirici listesi modülü kalıcı olarak yüklüyor).

- **[MINOR]** `arkauc/testler/test_kota.py:132` — Test, `kota_kontrol(..., bdm_id=7)` çağrısında kendi verdiği
  değeri doğruluyor (`assert yakalanan.value.ayrinti["bdm_id"] == 7`); hiçbir davranışı kanıtlamaz, yalnız anahtarın
  varlığını gösterir. **Beklenen:** kanıtlayan satırlar korunup bu satırın kaldırılması (hata zarfının `bdm_id`
  taşıdığı zaten 129-131. satırlardaki `kapsam`/`sifirlanma` denetimleriyle birlikte okunur). **Kanıt:** aynı dosya,
  aynı test; değer testin kendisinden geliyor.

## Onaylanan noktalar

- **Yenileme ve doğrulama jetonları atomik:** `oturumu_yenile` (`kimlik.py:289-300`) ve `dogrulama_jetonu_tuket`
  (`kimlik.py:383-404`) koşullu UPDATE + `rowcount` ile tek kullanımlığı garanti ediyor; eşzamanlılık testleri
  (`test_kimlik.py`) gerçek davranışı sınıyor.
- **Kurulum yarışı gerçekten kapatılmış:** `asyncio.Lock` + kilit içinde taze okuma + kilit içinde commit
  (`kurulum.py:122-176`). Deney 2: iki eşzamanlı `POST /kurulum`, 6/6 koşuda `[201, 409]` ve tek yönetici/tek BDM.
  Deney 3: `_kilit` devre dışı bırakıldığında 10/10 koşuda `[201, 409 cakisma]` — `IntegrityError` güvenlik ağı çalışıyor.
- **SSE kaynak temizliği:** sohbet akışında istemci koptuğunda upstream üreteci `finally: await akis.aclose()` ile
  kapatılıyor ve kısmi yanıt yazılmıyor (`akış.py:110-113`, `test_sohbet.py:434-470`); günlük akışında bekleyen okuma
  `_kapat` ile iptal edilip kaynak akışı kapatılıyor (`gunlukler.py:37-49, 100-103`). Çekim akışı `httpx.AsyncClient`
  bağlamını üreteç iptalinde kapatıyor (`cekim.py:127-147`). Deney 6: üreteç hiç tüketilmezse görev GC ile
  toplanıyor, sürücü akışı kapanıyor, kalıcı görev/thread sızıntısı yok (yalnız "Task was destroyed but it is
  pending!" uyarısı).
- **Hata zarfı ve iç ayrıntı:** upstream hata gövdesi ve taşıma istisnası metni istemciye dönmüyor, yalnız günlüğe
  yazılıyor (`upstream.py:78-125`, `test_sohbet.py:497-524`); hata kodları HTTP kodlarına doğru eşleniyor
  (`hatalar.py:160-200`).
- **Sır yönetimi:** upstream anahtarları ve `smtp_sifre` Fernet ile şifreli saklanıyor, yanıtlarda yalnız maskeli
  gösterim var (`katalog.py:57-70`, `ayarlar.py:72-84`); üretimde üretilmiş geçici sırla başlatma engelli
  (`ayarlar.py:103-108`); `logger` çağrılarında sır/parola/jeton değeri geçmiyor (tarama temiz).
- **Test kalitesi:** 185 test fonksiyonunun tamamı tarandı; davranışı kanıtlamayan tek satır yukarıdaki MINOR
  bulgudur, geri kalanı HTTP/SSE/veritabanı sözleşmesini ya da sağlayıcı tel formatını ölçüyor
  (ör. `test_sohbet.py:107-131` SSE olay sırası, `test_yonetim.py:461-486` günlük akışı çerçevelemesi).
  Uygulama ayrıntısını sabitleyen sınırlı sayıda satır (ör. `test_yonetim.py:327` sürücü çağrı dizisi,
  `test_butunluk.py:32-35` `PRAGMA foreign_keys`) ilgili davranışı başka testler de ölçtüğü için ayrı bulgu sayılmadı.

## Özet

6 bulgu (1 BLOCKER, 2 MAJOR, 3 MINOR). Öncelik sırası: `maskeleme_aktif` anahtarının etkisizliği (KVKK),
kota sayacının atomik olmaması, eşzamanlı `baslat` ile konteyner sızıntısı; ardından sürücü hata mesajlarında iç
ayrıntı, `kurulum._upstream_dogrula` ölü dallanması ve kanıtlamayan test satırı.

## Not: inceleme sırasındaki eşzamanlı çalışma

Bulgular incelenen revizyona (`62e8838`) göredir; tüm deneyler o revizyonun koduyla koşuldu. İnceleme
sürerken başka ajanlar çalışma kopyasında `arkauc/app/api/loglar.py`, `arkauc/app/cekirdek/ayarlar.py`,
`arkauc/app/main.py`, `arkauc/app/servisler/konteyner_docker.py`, `bdm_hazırlama_ucu/*`,
`bdm_konusma_gecmisi/maskeleme.py` gibi dosyaları değiştirdi (yeni `arkauc/app/cekirdek/oran_siniri.py`
dahil). Bu değişiklikler bu raporun kanıtı değildir. BLOCKER bulgunun hedefi olan `maskeleme.py:42` çalışma
kopyasında `maskeleme_etkin()` ile veritabanı öncelikli hâle getirilmiş görünüyor; bu, bulgunun bağımsız
olarak doğrulandığını gösterir (incelenen revizyonda hata mevcuttu).
