"""loglar-log.md üretimi — ham kanıtlardan (bkz. goz_log_uret.py)."""

from __future__ import annotations

import pathlib

from goz_log_uret import HEDEF, KANIT, bolumleri_ayir, kopyala

P = "E:/kutyai-app/.venv/Scripts/python.exe"

BASLIK = """# loglar gözlem logu — 2026-09-12

## Kapsam

- Ölçülen uçlar: `arkauc/app/api/loglar.py` (API.md §12), `api_anahtarlari.py` (§7),
  `ayarlar.py` (§14), `kurulum.py` (§4). Yan ürün olarak §3 `/saglik/kurulum`, §5 giriş,
  §8 `/modeller`, §9 `/sohbet` uçları da yoklandı.
- Yöntem: canlı backend (uvicorn, port 8106) + HTTP istemcisi (httpx) + **bağımsız SQL**
  sorguları (sqlite3, sunucu dışı ayrı bağlantı). Uygulayıcının kendi test dosyası
  (`arkauc/testler/test_loglar.py`) hiç çalıştırılmadı; tüm kanıt ham HTTP/SQL çıktısıdır.
- Ham çıktı dosyaları: `kaynak/testler/kanit/loglar/*.txt` (komut bazlı, kırpılmamış).
- Betikler: `kaynak/testler/betikler/goz_*.py` (yeniden üretilebilirlik için).

## Ortam

- Depo: `E:/kutyai-app`, Python: `E:/kutyai-app/.venv/Scripts/python.exe` (3.13.3).
- Geçici veritabanı: `kaynak/testler/gecici/goz_loglar.db` (SQLite, her senaryodan önce
  silinip yeniden oluşturuldu).
- Sunucu: `hub op:start` → `python -m uvicorn arkauc.app.main:app --port 8106`.
- Kurulum sihirbazı testleri taze DB ile başlatıldı (`kurulum_tamam=false`).

## Koşulan komutlar
"""

KOMUTLAR: list[tuple[str, str, str, str, str]] = [
    (
        "0) Sunucu başlatma ve sağlık yoklaması",
        "hub op:start (uvicorn, port 8106) + curl /saglik, /saglik/kurulum",
        "Sunucu ayakta; `kurulum_tamam=false` başlangıç durumu.",
        "00-ortam",
        "GEÇTİ",
    ),
    (
        "1) Tohum: log uçları için doğrudan SQL verisi",
        f"{P} goz_tohum.py",
        "4 konuşma + 6 mesaj eklenir (biri Türkçe karakterli başlık, biri eski tarihli).",
        "tohum",
        "GEÇTİ",
    ),
    (
        "2) Kurulum yarış durumu — farklı e-posta",
        f"{P} goz_01_kurulum_yaris.py",
        "İki eşzamanlı `POST /kurulum`: birincisi 201, ikincisi 409 `kurulum_zaten_tamam`; "
        "tek yönetici + tek BDM.",
        "01",
        "KALDI",
    ),
    (
        "3) Kurulum yarış durumu — aynı e-posta (taze DB)",
        f"{P} goz_01_kurulum_yaris.py ayni_eposta",
        "Birincisi 201, ikincisi 409 `cakisma`/`kurulum_zaten_tamam`; 500 olmamalı.",
        "01b",
        "KALDI",
    ),
    (
        "4) API anahtarları — sızma, iptal, izinli_modeller (§7)",
        f"{P} goz_02_anahtarlar.py",
        "Tam anahtar yalnız oluşturmada; listede `kuty_` geçmez; iptal sonrası 401 "
        "`anahtar_gecersiz`; bilinmeyen slug 400 `gecersiz_istek`.",
        "02",
        "GEÇTİ",
    ),
    (
        "5) Loglar — filtre, sayfalama, dışa aktarım, silme (§12)",
        f"{P} goz_03_loglar.py",
        "Filtreler doğru; `boyut` 200 ile sınırlı; silme personel, temizle yalnız yönetici; "
        "dışa aktarım üç biçimde doğru.",
        "03",
        "KALDI",
    ),
    (
        "6) Ayarlar — SMTP şifresi, sınır değerler, bakım modu (§14)",
        f"{P} goz_04_ayarlar.py",
        "`smtp_sifre` DB'de şifreli ve hiçbir yanıtta yok; `saklama_gun` 0/3651 → 400; "
        "operator/izleyici 403; bakım modu sohbeti kısıtlar.",
        "04",
        "KALDI",
    ),
    (
        "7) Denetim izi — kullanıcı/rol değişiklikleri (§10, GUVENLIK §4)",
        f"{P} goz_05_denetim.py",
        "`kullanici.guncelle` ve `kullanici.pasiflestir` `islem_kaydi`'na yazılır.",
        "05",
        "GEÇTİ",
    ),
    (
        "8) Dışa aktarım uç durumları — boş konuşma, CSV kaçışlama",
        f"{P} goz_06_disa_aktarim.py",
        "Mesajsız konuşma geçerli dosya üretir; CSV RFC 4180 kaçışlaması doğru; formül "
        "enjeksiyonu etkisizleştirilir.",
        "06",
        "GEÇTİ",
    ),
    (
        "9) İzleyici rolünün anahtar yetkisi (§7)",
        f"{P} goz_07_rol_anahtar.py",
        "Salt-okunur `izleyici` rolü anahtar üretemez/iptal edemez (ya da sözleşme bu "
        "yetkiyi açıkça tanımlar).",
        "07",
        "KALDI",
    ),
]


def ham(anahtar: str, sinir: int = 2600) -> str:
    satirlar = bolumleri_ayir((KANIT / f"{anahtar}.txt").read_text(encoding="utf-8"))
    cikti: list[str] = []
    blok: list[str] = []
    baslik = ""

    def kapat() -> None:
        govde = "\n".join(blok).strip("\n")
        if not govde:
            return
        if len(govde) > sinir:
            govde = govde[:sinir] + f"\n... (kırpıldı; tam kayıt: kanit/loglar/{anahtar}.txt)"
        cikti.append(govde)

    for satir in satirlar:
        if satir.startswith("=== ") and satir.endswith(" ==="):
            kapat()
            baslik = satir[4:-4]
            blok = [satir]
        else:
            blok.append(satir)
    kapat()
    return "\n\n".join(cikti)


BULGULAR = """
## Bulgular

- [BLOCKER] `arkauc/app/api/kurulum.py:102-127` — **`POST /kurulum` yarış durumu (TOCTOU)**.
  `kurulum_tamam` denetimi ile yazımı arasında kilit yok (`veritabani_oturumu` commit'i
  istek sonunda, `bdm_veritabani/oturum.py:52`). İki eşzamanlı istek (farklı yönetici
  e-postası) → **ikisi de 201**, iki `yonetici` kaydı (id=1,2), iki BDM, `marka_adi` ve
  `varsayilan_bdm_slug` son bitirenin değeriyle ezildi (kayıp güncelleme). Beklenen:
  tek istek 201, diğeri 409 `kurulum_zaten_tamam` (API.md §4). Yeniden üretme:
  taze DB → `goz_01_kurulum_yaris.py` (kanit/loglar/01.txt).
- [MAJOR] `arkauc/app/api/kurulum.py:106-115` — **aynı e-posta ile eşzamanlı kurulum
  500 döndürüyor.** İki istek de `mevcut is None` görüyor; ikincisi `kullanici.eposta`
  tekil kısıtına çarpıp yakalanmayan `IntegrityError` → `{"kod":"sunucu_hatasi"}`.
  Beklenen: 409 `cakisma` (API.md §1, §4). Kök neden BLOCKER ile aynı; yeniden üretme:
  kanit/loglar/01b.txt.
- [MAJOR] `arkauc/app/api/loglar.py:94-98` — **`DELETE /loglar/konusmalar/{id}` tüm
  personel rollerine açık; `izleyici` (salt-okunur) bile kalıcı siliyor (204).**
  API.md §12 silme için yetki belirtmiyor, yalnız `POST /loglar/temizle` için "yalnız
  yönetici" diyor; GUVENLIK.md §4 `DELETE .../loglar/konusmalar/{id}`'i "silme hakkı"
  olarak listeliyor. Değerlendirme: geri döndürülemez veri kaybı üreten bu uç
  `yonetici`/`operator` ile sınırlanmalı (ya da sözleşmede açıkça yazılmalı); izleyiciye
  açık bırakılması yetki modeliyle çelişiyor. Kanıt: kanit/loglar/03.txt.
- [MINOR] `arkauc/app/api/ayarlar.py:39,63` — **`bakim_modu` hiçbir yerde uygulanmıyor.**
  `bakim_modu=true` iken `POST /sohbet` normal işlendi ve konuşma loglara yazıldı
  (upstream olmadığı için 502 döndü), `/modeller` ve `/loglar/konusmalar` 200 döndü.
  Beklenen (gözlemci hipotezi): 503. API.md §14 davranışı tanımlamıyor → sözleşme
  boşluğu; ayar yalnız depolanıp raporlanıyor, operasyonel etkisi yok.
  Kanıt: kanit/loglar/04.txt.
- [MINOR] `arkauc/app/api/api_anahtarlari.py:70,87,127` — **anahtar oluşturma/iptal
  `izleyici` rolüne de açık.** Salt-okunur `izleyici` hesabı anahtar üretti (201),
  ürettiği anahtarla `GET /modeller` 200 ve `POST /sohbet` 502 (kimlik kabul edildi,
  upstream yok) aldı, ayrıca `POST /api-anahtarlari/{id}/iptal` ile anahtar iptal etti
  (200 `{"durum":"iptal"}`). Anahtar `izinli_modeller=[]` ile **tüm hazır modellere**
  açık. API.md §7'de yetki sütunu yok → belirsizlik; salt-okunur rolden sohbet kimliği
  üretilebilmesi ayrıcalık yükseltme yüzeyi. Sözleşmede yetki netleştirilmeli.
  Kanıt: kanit/loglar/02.txt, kanit/loglar/07.txt.
- [MINOR] `bdm_konusma_gecmisi/disa_aktarim.py:53-70` — **CSV dışa aktarımında formül
  enjeksiyonu.** `=HYPERLINK("http://kotu.example","tıkla")` içeren mesaj CSV'ye
  olduğu gibi yazıldı; Excel/Sheets dosyayı açınca formül çalışır. Beklenen: hücre
  `'` öneki ya da sekme ile etkisizleştirilmeli; en azından "formül başlatan
  karakterler" kaçışlanmalı. Kanıt: kanit/loglar/06.txt.
- [MINOR] `arkauc/app/api/loglar.py:44-49`, `bdm_konusma_gecmisi/sorgu.py:19-25` —
  **sayfalama sınır davranışı tutarsız/doğrulanmıyor.** `baslangic > bitis` sessizce
  `{toplam:0}` döndürüyor (400 beklenirdi), `boyut=-5` "1"e kırpılıyor (varsayılan 25
  beklenirdi), `boyut=10000` 200'e kırpılıyor (kaynak tüketimi açısından doğru).
  Aynı parametreler için üç farklı politika; sözleşmede tanımsız. Kanıt:
  kanit/loglar/03.txt.

## Kapsam dışı gözlemler (diğer modüller)

- `arkauc/app/api/kimlik.py` — `POST /kimlik/giris` personel hesaplarını 403
  `yetki_yok` ("Bu giriş kapısı yalnızca son kullanıcılar içindir") ile reddediyor;
  API.md §5 `giris` için böyle bir kısıt yazmıyor (panel için `/kimlik/panel-giris`
  ayrıca tanımlı). Gözlem sırasında personel oturumu bu yüzden panel-giris ile alındı.
- `arkauc/app/api/kimlik.py` — hatalı girişte dönen `401` kodu `gecersiz_kimlik_bilgisi`,
  API.md §1 tablosunda yok (`kimlik_gerekli`, `jeton_gecersiz`, `jeton_suresi_doldu`,
  `anahtar_gecersiz` listeleniyor).

## Özet

7 bulgu (1 BLOCKER, 2 MAJOR, 4 MINOR).
- BLOCKER: `POST /kurulum` yarış durumu — eşzamanlı iki istek iki yönetici ve iki BDM
  oluşturuyor; `marka_adi`/`varsayilan_bdm_slug` son bitirenin değeriyle eziliyor.
"""


def main() -> None:
    kopyala()
    parcalar = [BASLIK]
    for baslik, komut, beklenen, kanit, sonuc in KOMUTLAR:
        parcalar.append(
            f"\n### {baslik}\n\n```\n{komut}\n```\n\n"
            f"- Beklenen: {beklenen}\n"
            f"- Gerçek çıktı:\n\n```\n{ham(kanit)}\n```\n\n"
            f"- Sonuç: {sonuc}\n"
        )
    parcalar.append(BULGULAR)
    HEDEF.write_text("".join(parcalar), encoding="utf-8")
    print("yazıldı:", HEDEF, HEDEF.stat().st_size, "bayt")


if __name__ == "__main__":
    main()
