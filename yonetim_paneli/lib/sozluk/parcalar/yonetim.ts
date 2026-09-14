/**
 * Kullanıcılar, API anahtarları ve kullanım sayfalarının metinleri (spec §10.2).
 *
 * Anahtarlar `alan.alt.anahtar` düzeninde; `{eposta}`, `{sayi}`, `{gun}`,
 * `{uzunluk}`, `{kirilim}`, `{olcu}` yer tutucuları `t(...)` ile doldurulur.
 * Cümle içine React bileşeni gömülecekse şablona `{baglanti}` yazılıp
 * `t(...).split("{baglanti}")` ile parçalanır.
 */
export const trYonetim = {
  // --- Kullanıcılar: sayfa başlığı ve ortak alan adları
  "kullanicilar.baslik": "Kullanıcılar",
  "kullanicilar.aciklama": "Personel ve son kullanıcı hesapları; rol ve durum yönetimi.",
  "kullanicilar.yeni": "Yeni personel",
  "kullanicilar.siz": "Siz",
  "kullanicilar.eposta": "E-posta",
  "kullanicilar.ad_soyad": "Ad soyad",
  "kullanicilar.rol": "Rol",
  "kullanicilar.durum": "Durum",
  "kullanicilar.gecici_parola": "Geçici parola",
  "kullanicilar.duzenle": "Düzenle",
  "kullanicilar.pasiflestir": "Pasifleştir",
  "kullanicilar.kaydet": "Kaydet",
  "kullanicilar.vazgec": "Vazgeç",
  "kullanicilar.evet": "Evet",
  "kullanicilar.hayir": "Hayır",

  // --- Kullanıcılar: filtre çubuğu
  "kullanicilar.filtre.aria": "Kullanıcı filtreleri",
  "kullanicilar.filtre.rol.tumu": "Tüm roller",
  "kullanicilar.filtre.durum.tumu": "Tüm durumlar",
  "kullanicilar.filtre.arama": "Arama",
  "kullanicilar.filtre.arama.yer_tutucu": "E-posta veya ad soyad",
  "kullanicilar.filtre.uygula": "Filtrele",
  "kullanicilar.filtre.temizle": "Temizle",

  // --- Kullanıcılar: tablo ve boş durum
  "kullanicilar.tablo.dogrulandi": "Doğrulandı",
  "kullanicilar.tablo.son_giris": "Son giriş",
  "kullanicilar.tablo.islemler": "İşlemler",
  "kullanicilar.bos.baslik": "Kullanıcı bulunamadı",
  "kullanicilar.bos.aciklama": "Bu filtrelerle eşleşen hesap yok.",

  // --- Kullanıcılar: personel ekleme
  "kullanicilar.ekle.baslik": "Yeni personel",
  "kullanicilar.ekle.aciklama": "Kullanıcı hemen aktif ve e-posta doğrulanmış olarak açılır.",
  "kullanicilar.ekle.gonder": "Personel ekle",
  "kullanicilar.ekle.hata.baslik": "Personel eklenemedi",
  "kullanicilar.ekle.basarili.baslik": "Personel eklendi",
  "kullanicilar.ekle.basarili.aciklama": "Geçici parolayı kullanıcıya iletin.",
  "kullanicilar.ekle.anladim": "Anladım, kapat",
  "kullanicilar.ekle.parola.uyari.baslik": "Bu parola bir daha gösterilmez",
  "kullanicilar.ekle.parola.uyari.metin":
    "Parolayı şimdi kopyalayıp kullanıcıya iletin; bu pencere kapandıktan sonra yeniden görüntülenemez.",
  "kullanicilar.ekle.parola.ipucu":
    "En az 8 karakter; kullanıcı ilk girişten sonra değiştirebilir.",
  "kullanicilar.ekle.parola.uret": "Üret",

  // --- Kullanıcılar: düzenleme
  "kullanicilar.duzenle.baslik": "Kullanıcıyı düzenle",
  "kullanicilar.duzenle.hata.baslik": "Güncellenemedi",
  "kullanicilar.duzenle.degisiklik_yok": "Değişiklik yok.",
  "kullanicilar.duzenle.basarili": "Kullanıcı güncellendi.",

  // --- Kullanıcılar: pasifleştirme
  "kullanicilar.pasiflestir.baslik": "Kullanıcıyı pasifleştir",
  "kullanicilar.pasiflestir.aciklama": "Kayıt silinmez; açık oturumlar iptal edilir.",
  "kullanicilar.pasiflestir.metin":
    "{baglanti} hesabı pasifleştirilecek ve mevcut oturumları kapatılacak.",
  "kullanicilar.pasiflestir.basarili": "{eposta} pasifleştirildi.",
  "kullanicilar.pasiflestir.hata.baslik": "Pasifleştirilemedi",

  // --- API anahtarları: sayfa
  "anahtar.baslik": "API Anahtarları",
  "anahtar.aciklama":
    "Sohbet uçlarına programatik erişim; tam anahtar yalnızca oluşturmada görünür.",
  "anahtar.yeni": "Yeni anahtar",
  "anahtar.izinli_modeller": "İzinli modeller",
  "anahtar.tum_modeller": "Tüm modeller",
  "anahtar.vazgec": "Vazgeç",
  "anahtar.tablo.ad": "Ad",
  "anahtar.tablo.anahtar": "Anahtar",
  "anahtar.tablo.durum": "Durum",
  "anahtar.tablo.son_kullanim": "Son kullanım",
  "anahtar.tablo.olusturulma": "Oluşturulma",
  "anahtar.tablo.islem": "İşlem",
  "anahtar.bos.baslik": "Henüz anahtar yok",
  "anahtar.bos.aciklama": "Entegrasyonlar için ilk API anahtarını oluşturun.",

  // --- API anahtarları: oluşturma
  "anahtar.olustur.baslik": "Yeni API anahtarı",
  "anahtar.olustur.aciklama": "Anahtar yalnızca oluşturma yanıtında tam olarak gösterilir.",
  "anahtar.olustur.gonder": "Anahtar oluştur",
  "anahtar.olustur.hata.baslik": "Anahtar oluşturulamadı",
  "anahtar.olustur.ad": "Anahtar adı",
  "anahtar.olustur.ad.zorunlu": "Anahtar adı zorunludur.",
  "anahtar.olustur.ad.kisa": "Anahtar adı en az {uzunluk} karakter olmalıdır.",
  "anahtar.olustur.ad.yer_tutucu": "ör. Muhasebe entegrasyonu",
  "anahtar.olustur.secili": "{sayi} model seçildi.",
  "anahtar.olustur.tum_modeller.ipucu":
    "Hiçbiri seçilmezse anahtar tüm modellere erişebilir.",
  "anahtar.olustur.katalog_bos":
    "Katalogda model yok; anahtar tüm modellere erişecek şekilde oluşturulacak.",

  // --- API anahtarları: durum ve iptal
  "anahtar.durum.iptal": "İptal edildi",
  "anahtar.iptal": "İptal et",
  "anahtar.iptal.baslik": "Anahtarı iptal et",
  "anahtar.iptal.aciklama":
    "İptal edilen anahtar kimlik doğrulamada reddedilir; bu işlem geri alınamaz.",
  "anahtar.iptal.metin":
    "{baglanti} anahtarı iptal edilecek ve kullanan entegrasyonlar erişimini kaybedecek.",
  "anahtar.iptal.basarili": "{ad} anahtarı iptal edildi.",
  "anahtar.iptal.hata.baslik": "İptal edilemedi",

  // --- API anahtarları: oluşturma sonucu (kapatılamaz katman)
  "anahtar.sonuc.baslik": "API anahtarı oluşturuldu",
  "anahtar.sonuc.uyari.baslik": "Bu anahtar bir daha gösterilmeyecek",
  "anahtar.sonuc.uyari.metin":
    "Sunucu tam anahtarı yalnızca bu yanıtta döndürür. Şimdi kopyalayıp güvenli bir yere kaydedin; bu pencere kapandıktan sonra anahtarı yeniden görüntülemenin bir yolu yoktur.",
  "anahtar.sonuc.kopyala": "Kopyala",
  "anahtar.sonuc.kopyalandi": "Kopyalandı",
  "anahtar.sonuc.kopyalama_hatasi":
    "Kopyalanamadı; anahtarı elle seçip kopyalayın.",
  "anahtar.sonuc.kaydettim": "Kaydettim, kapat",

  // --- Kullanım: sayfa ve özet
  "kullanim.baslik": "Kullanım",
  "kullanim.aciklama":
    "İstek, token ve gecikme değerleri; model veya kullanıcı kırılımında.",
  "kullanim.gun": "{gun} gün",
  "kullanim.ozet.baslik": "Özet",
  "kullanim.ozet.aria": "Kullanım özeti",
  "kullanim.ozet.toplam_istek": "Toplam istek",
  "kullanim.ozet.toplam_token": "Toplam token",
  "kullanim.ozet.ortalama_gecikme": "Ortalama gecikme",
  "kullanim.ozet.basarili": "Başarılı",
  "kullanim.ozet.hatali": "Hatalı",
  "kullanim.ozet.kota_asimi": "Kota aşımı",

  // --- Kullanım: kırılım ve ölçü
  "kullanim.kirilim.baslik": "Kırılım",
  "kullanim.kirilim.aria": "Kırılım grafiği",
  "kullanim.kirilim.bdm": "Modele göre",
  "kullanim.kirilim.kullanici": "Kullanıcıya göre",
  "kullanim.olcu.istek": "İstek",
  "kullanim.olcu.token": "Token",
  "kullanim.olcu.aria": "Ölçü",
  "kullanim.grafik.baslik": "{kirilim} kullanım",
  "kullanim.grafik.aciklama": "Son {gun} günün {olcu} toplamı.",
  "kullanim.bos.baslik": "Bu aralıkta kullanım yok",
  "kullanim.bos.aciklama": "Seçilen gün aralığında kayıtlı istek bulunmuyor.",
} as const;

export const enYonetim: Record<keyof typeof trYonetim, string> = {
  // --- Users: page title and shared field labels
  "kullanicilar.baslik": "Users",
  "kullanicilar.aciklama": "Staff and end-user accounts; role and status management.",
  "kullanicilar.yeni": "New staff",
  "kullanicilar.siz": "You",
  "kullanicilar.eposta": "E-mail",
  "kullanicilar.ad_soyad": "Full name",
  "kullanicilar.rol": "Role",
  "kullanicilar.durum": "Status",
  "kullanicilar.gecici_parola": "Temporary password",
  "kullanicilar.duzenle": "Edit",
  "kullanicilar.pasiflestir": "Deactivate",
  "kullanicilar.kaydet": "Save",
  "kullanicilar.vazgec": "Cancel",
  "kullanicilar.evet": "Yes",
  "kullanicilar.hayir": "No",

  // --- Users: filter bar
  "kullanicilar.filtre.aria": "User filters",
  "kullanicilar.filtre.rol.tumu": "All roles",
  "kullanicilar.filtre.durum.tumu": "All statuses",
  "kullanicilar.filtre.arama": "Search",
  "kullanicilar.filtre.arama.yer_tutucu": "E-mail or full name",
  "kullanicilar.filtre.uygula": "Filter",
  "kullanicilar.filtre.temizle": "Clear",

  // --- Users: table and empty state
  "kullanicilar.tablo.dogrulandi": "Verified",
  "kullanicilar.tablo.son_giris": "Last sign-in",
  "kullanicilar.tablo.islemler": "Actions",
  "kullanicilar.bos.baslik": "No users found",
  "kullanicilar.bos.aciklama": "No account matches these filters.",

  // --- Users: adding staff
  "kullanicilar.ekle.baslik": "New staff",
  "kullanicilar.ekle.aciklama": "The user starts active with a verified e-mail address.",
  "kullanicilar.ekle.gonder": "Add staff",
  "kullanicilar.ekle.hata.baslik": "Staff could not be added",
  "kullanicilar.ekle.basarili.baslik": "Staff added",
  "kullanicilar.ekle.basarili.aciklama": "Share the temporary password with the user.",
  "kullanicilar.ekle.anladim": "Got it, close",
  "kullanicilar.ekle.parola.uyari.baslik": "This password will not be shown again",
  "kullanicilar.ekle.parola.uyari.metin":
    "Copy the password now and share it with the user; it cannot be shown again once this window closes.",
  "kullanicilar.ekle.parola.ipucu":
    "At least 8 characters; the user can change it after the first sign-in.",
  "kullanicilar.ekle.parola.uret": "Generate",

  // --- Users: editing
  "kullanicilar.duzenle.baslik": "Edit user",
  "kullanicilar.duzenle.hata.baslik": "Could not update",
  "kullanicilar.duzenle.degisiklik_yok": "No changes.",
  "kullanicilar.duzenle.basarili": "User updated.",

  // --- Users: deactivation
  "kullanicilar.pasiflestir.baslik": "Deactivate user",
  "kullanicilar.pasiflestir.aciklama": "The record is kept; active sessions are revoked.",
  "kullanicilar.pasiflestir.metin":
    "{baglanti} will be deactivated and their active sessions closed.",
  "kullanicilar.pasiflestir.basarili": "{eposta} was deactivated.",
  "kullanicilar.pasiflestir.hata.baslik": "Could not deactivate",

  // --- API keys: page
  "anahtar.baslik": "API Keys",
  "anahtar.aciklama":
    "Programmatic access to the chat endpoints; the full key is shown only on creation.",
  "anahtar.yeni": "New key",
  "anahtar.izinli_modeller": "Allowed models",
  "anahtar.tum_modeller": "All models",
  "anahtar.vazgec": "Cancel",
  "anahtar.tablo.ad": "Name",
  "anahtar.tablo.anahtar": "Key",
  "anahtar.tablo.durum": "Status",
  "anahtar.tablo.son_kullanim": "Last used",
  "anahtar.tablo.olusturulma": "Created",
  "anahtar.tablo.islem": "Action",
  "anahtar.bos.baslik": "No keys yet",
  "anahtar.bos.aciklama": "Create the first API key for your integrations.",

  // --- API keys: creation
  "anahtar.olustur.baslik": "New API key",
  "anahtar.olustur.aciklama": "The key is shown in full only in the creation response.",
  "anahtar.olustur.gonder": "Create key",
  "anahtar.olustur.hata.baslik": "Key could not be created",
  "anahtar.olustur.ad": "Key name",
  "anahtar.olustur.ad.zorunlu": "Key name is required.",
  "anahtar.olustur.ad.kisa": "Key name must be at least {uzunluk} characters.",
  "anahtar.olustur.ad.yer_tutucu": "e.g. Accounting integration",
  "anahtar.olustur.secili": "{sayi} models selected.",
  "anahtar.olustur.tum_modeller.ipucu":
    "If none is selected, the key can access all models.",
  "anahtar.olustur.katalog_bos":
    "No models in the catalog; the key will be created with access to all models.",

  // --- API keys: status and revocation
  "anahtar.durum.iptal": "Revoked",
  "anahtar.iptal": "Revoke",
  "anahtar.iptal.baslik": "Revoke key",
  "anahtar.iptal.aciklama":
    "A revoked key is rejected during authentication; this action cannot be undone.",
  "anahtar.iptal.metin":
    "The {baglanti} key will be revoked and integrations using it will lose access.",
  "anahtar.iptal.basarili": "{ad} key was revoked.",
  "anahtar.iptal.hata.baslik": "Could not revoke",

  // --- API keys: creation result (non-dismissible layer)
  "anahtar.sonuc.baslik": "API key created",
  "anahtar.sonuc.uyari.baslik": "This key will not be shown again",
  "anahtar.sonuc.uyari.metin":
    "The server returns the full key only in this response. Copy it now and store it somewhere safe; there is no way to view the key again after this window closes.",
  "anahtar.sonuc.kopyala": "Copy",
  "anahtar.sonuc.kopyalandi": "Copied",
  "anahtar.sonuc.kopyalama_hatasi": "Could not copy; select the key and copy it manually.",
  "anahtar.sonuc.kaydettim": "I saved it, close",

  // --- Usage: page and summary
  "kullanim.baslik": "Usage",
  "kullanim.aciklama":
    "Request, token and latency figures; broken down by model or user.",
  "kullanim.gun": "{gun} days",
  "kullanim.ozet.baslik": "Summary",
  "kullanim.ozet.aria": "Usage summary",
  "kullanim.ozet.toplam_istek": "Total requests",
  "kullanim.ozet.toplam_token": "Total tokens",
  "kullanim.ozet.ortalama_gecikme": "Average latency",
  "kullanim.ozet.basarili": "Successful",
  "kullanim.ozet.hatali": "Failed",
  "kullanim.ozet.kota_asimi": "Quota exceeded",

  // --- Usage: breakdown and metric
  "kullanim.kirilim.baslik": "Breakdown",
  "kullanim.kirilim.aria": "Breakdown chart",
  "kullanim.kirilim.bdm": "By model",
  "kullanim.kirilim.kullanici": "By user",
  "kullanim.olcu.istek": "Requests",
  "kullanim.olcu.token": "Tokens",
  "kullanim.olcu.aria": "Metric",
  "kullanim.grafik.baslik": "{kirilim} usage",
  "kullanim.grafik.aciklama": "Total {olcu} over the last {gun} days.",
  "kullanim.bos.baslik": "No usage in this range",
  "kullanim.bos.aciklama": "No requests were recorded in the selected day range.",
};
