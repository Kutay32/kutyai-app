/**
 * Posta şablonları sayfası metinleri — spec §9 / API.md §15.
 *
 * Şablon kodları (`dogrulama`, `sifirlama`, `davet`, `kota_uyarisi`, `fatura`,
 * `hosgeldin`) ve iki dil (tr/en) sunucudaki `KODLAR` ve `DILLER` ile aynıdır.
 */
export const trPosta = {
  // --- Sayfa
  "posta.baslik": "Posta Şablonları",
  "posta.aciklama":
    "Doğrulama, sıfırlama ve bildirim e-postalarının konu ve gövdesini organizasyonunuza göre özelleştirin.",
  "posta.ozel.ipucu": "Organizasyona özel kayıt; varsayılan şablonun yerine kullanılır.",
  "posta.varsayilan.ipucu":
    "Bu şablon henüz özelleştirilmemiş; gömülü varsayılan (TR/EN) kullanılıyor.",
  "posta.degisken.ipucu":
    "Şablondaki {{ad}} biçimindeki yer tutucular gönderim anında doldurulur.",

  // --- Şablon kodları
  "posta.kod.dogrulama": "E-posta doğrulama",
  "posta.kod.sifirlama": "Parola sıfırlama",
  "posta.kod.davet": "Davet",
  "posta.kod.kota_uyarisi": "Kota uyarısı",
  "posta.kod.fatura": "Fatura bildirimi",
  "posta.kod.hosgeldin": "Hoş geldin",

  // --- Diller
  "posta.dil.tr": "Türkçe",
  "posta.dil.en": "English",

  // --- Tablo
  "posta.tablo.kod": "Şablon",
  "posta.tablo.dil": "Dil",
  "posta.tablo.konu": "Konu",
  "posta.tablo.kaynak": "Kaynak",
  "posta.tablo.islemler": "İşlemler",
  "posta.etiket.ozel": "Özel",
  "posta.etiket.varsayilan": "Varsayılan",
  "posta.duzenle": "Düzenle",
  "posta.onizle": "Önizle",
  "posta.bos.baslik": "Şablon bulunamadı",
  "posta.bos.aciklama": "Sunucu şablon kataloğunu döndürmedi.",

  // --- Düzenleme (PUT /posta-sablonlari)
  "posta.duzenle.baslik": "{ad} — {dil}",
  "posta.duzenle.aciklama": "Konu ve gövde kaydedildiğinde bu organizasyon için geçerli olur.",
  "posta.duzenle.konu": "Konu",
  "posta.duzenle.govde_metin": "Gövde (düz metin)",
  "posta.duzenle.govde_html": "Gövde (HTML)",
  "posta.duzenle.govde_html.ipucu": "Boş bırakılırsa yalnızca düz metin gönderilir.",
  "posta.duzenle.kaydet": "Kaydet",
  "posta.duzenle.basarili": "Şablon kaydedildi.",
  "posta.duzenle.hata.baslik": "Şablon kaydedilemedi",
  "posta.duzenle.konu.zorunlu": "Konu zorunludur.",
  "posta.duzenle.degisiklik_yok": "Değişiklik yok.",

  // --- Önizleme (POST /posta-sablonlari/{kod}/onizle)
  "posta.onizle.baslik": "{ad} önizleme",
  "posta.onizle.aciklama":
    "Kayıtlı şablon örnek değerlerle doldurulur; doldurduğunuz değişkenler örnek değerleri geçersiz kılar.",
  "posta.onizle.degiskenler": "Değişkenler",
  "posta.onizle.degisken.yok": "Bu şablonda değişken kullanılmamış.",
  "posta.onizle.gonder": "Önizlemeyi yenile",
  "posta.onizle.konu": "Konu",
  "posta.onizle.govde_metin": "Düz metin",
  "posta.onizle.govde_html": "HTML",
  "posta.onizle.hata.baslik": "Önizleme alınamadı",
  "posta.onizle.kayitli.ipucu":
    "Önizleme sunucudaki kayıtlı şablonu kullanır; kaydedilmemiş değişiklikler görünmez.",
  "posta.onizle.bos": "Önizleme verisi boş.",

  // --- Hata kodları (API.md §17)
  "posta.hata.gecersiz_kod": "Geçersiz şablon kodu.",
  "posta.hata.gecersiz_dil": "Geçersiz dil.",
  "posta.hata.bulunamadi": "Posta şablonu bulunamadı.",
  "posta.hata.yetki_yok":
    "Şablonları kaydetmek için bu organizasyonda sahip veya yönetici olmalısınız.",
} as const;

export const enPosta: Record<keyof typeof trPosta, string> = {
  // --- Page
  "posta.baslik": "E-mail Templates",
  "posta.aciklama":
    "Customize the subject and body of verification, reset and notification e-mails for your organization.",
  "posta.ozel.ipucu": "Organization-specific record; it replaces the default template.",
  "posta.varsayilan.ipucu":
    "This template has not been customized yet; the embedded default (TR/EN) is used.",
  "posta.degisken.ipucu":
    "Placeholders in the {{ad}} form are filled in when the e-mail is sent.",

  // --- Template codes
  "posta.kod.dogrulama": "E-mail verification",
  "posta.kod.sifirlama": "Password reset",
  "posta.kod.davet": "Invitation",
  "posta.kod.kota_uyarisi": "Quota warning",
  "posta.kod.fatura": "Invoice notification",
  "posta.kod.hosgeldin": "Welcome",

  // --- Languages
  "posta.dil.tr": "Turkish",
  "posta.dil.en": "English",

  // --- Table
  "posta.tablo.kod": "Template",
  "posta.tablo.dil": "Language",
  "posta.tablo.konu": "Subject",
  "posta.tablo.kaynak": "Source",
  "posta.tablo.islemler": "Actions",
  "posta.etiket.ozel": "Custom",
  "posta.etiket.varsayilan": "Default",
  "posta.duzenle": "Edit",
  "posta.onizle": "Preview",
  "posta.bos.baslik": "No templates found",
  "posta.bos.aciklama": "The server did not return the template catalog.",

  // --- Editing (PUT /posta-sablonlari)
  "posta.duzenle.baslik": "{ad} — {dil}",
  "posta.duzenle.aciklama":
    "Once saved, the subject and body apply to this organization.",
  "posta.duzenle.konu": "Subject",
  "posta.duzenle.govde_metin": "Body (plain text)",
  "posta.duzenle.govde_html": "Body (HTML)",
  "posta.duzenle.govde_html.ipucu": "If left blank, only the plain text is sent.",
  "posta.duzenle.kaydet": "Save",
  "posta.duzenle.basarili": "Template saved.",
  "posta.duzenle.hata.baslik": "Could not save the template",
  "posta.duzenle.konu.zorunlu": "The subject is required.",
  "posta.duzenle.degisiklik_yok": "No changes.",

  // --- Preview (POST /posta-sablonlari/{kod}/onizle)
  "posta.onizle.baslik": "{ad} preview",
  "posta.onizle.aciklama":
    "The saved template is rendered with sample values; values you fill in override the samples.",
  "posta.onizle.degiskenler": "Variables",
  "posta.onizle.degisken.yok": "This template does not use any variables.",
  "posta.onizle.gonder": "Refresh preview",
  "posta.onizle.konu": "Subject",
  "posta.onizle.govde_metin": "Plain text",
  "posta.onizle.govde_html": "HTML",
  "posta.onizle.hata.baslik": "Could not load the preview",
  "posta.onizle.kayitli.ipucu":
    "The preview uses the template saved on the server; unsaved changes are not shown.",
  "posta.onizle.bos": "The preview is empty.",

  // --- Error codes (API.md §17)
  "posta.hata.gecersiz_kod": "Invalid template code.",
  "posta.hata.gecersiz_dil": "Invalid language.",
  "posta.hata.bulunamadi": "E-mail template not found.",
  "posta.hata.yetki_yok":
    "You must be an owner or administrator in this organization to save templates.",
};
