/**
 * Konuşma kayıtları (loglar) ve işlem kayıtları (denetim izi) metinleri (spec §10.2).
 *
 * Anahtarlar `alan.alt.anahtar` düzeninde; önek `kayit.` (loglar) ve `islem.`
 * (işlem kayıtları). `{ad}` yer tutucuları `lib/dil.tsx` içindeki `t` ile
 * doldurulur. Cümle içine React bileşeni gömülecekse şablona `{baglanti}` yazılıp
 * `t(...).split("{baglanti}")` ile parçalanır.
 */
export const trKayitlar = {
  // --- Konuşma kayıtları sayfası (app/(panel)/loglar)
  "kayit.loglar.baslik": "Konuşma Kayıtları",
  "kayit.loglar.aciklama":
    "Kayıtlar maskelenmiş olarak saklanır; filtreleyin, indirin ve yönetin.",
  "kayit.loglar.bos.baslik": "Kayıt bulunamadı",
  "kayit.loglar.bos.aciklama":
    "Bu filtrelerle eşleşen konuşma yok. Filtreleri gevşetmeyi deneyin.",
  "kayit.loglar.geri": "Konuşma kayıtları",
  /** Başlığı boş kayıtların yerine gösterilir. */
  "kayit.basliksiz": "Başlıksız konuşma",
  "kayit.gecersiz_no": "Geçersiz kayıt numarası.",

  // --- Kayıt filtresi (components/loglar/filtre-cubugu.tsx)
  "kayit.filtre.aria": "Kayıt filtreleri",
  "kayit.filtre.kullanici": "Kullanıcı",
  "kayit.filtre.tum_kullanicilar": "Tüm kullanıcılar",
  "kayit.filtre.kullanici_kimligi": "Kullanıcı kimliği",
  "kayit.filtre.kullanici_kimligi.ipucu":
    "Kullanıcı listesi yalnız yöneticilere açık; kimlik ile süzün.",
  "kayit.filtre.ornek_kimlik": "ör. 4",
  "kayit.filtre.model": "Model",
  "kayit.filtre.tum_modeller": "Tüm modeller",
  "kayit.filtre.baslangic": "Başlangıç",
  "kayit.filtre.bitis": "Bitiş",
  "kayit.filtre.arama": "Metin arama",
  "kayit.filtre.arama.ipucu": "Başlık veya mesaj içeriği",
  "kayit.filtre.uygula": "Filtrele",
  "kayit.filtre.temizle": "Temizle",

  // --- Kayıt tablosu (components/loglar/tablo.tsx)
  "kayit.tablo.baslik": "Başlık",
  "kayit.tablo.kullanici": "Kullanıcı",
  "kayit.tablo.model": "Model",
  "kayit.tablo.mesaj": "Mesaj",
  "kayit.tablo.token": "Token (giriş/çıkış)",
  "kayit.tablo.tarih": "Tarih",

  // --- Kayıt detayı (app/(panel)/loglar/[id])
  "kayit.detay.bilgileri": "Kayıt Bilgileri",
  "kayit.detay.kullanici": "Kullanıcı",
  "kayit.detay.model": "Model",
  "kayit.detay.olusturulma": "Oluşturulma",
  "kayit.detay.guncellenme": "Son güncelleme",
  "kayit.detay.mesaj_sayisi": "Mesaj sayısı",
  "kayit.detay.token_girdi": "Giriş tokenı",
  "kayit.detay.token_cikti": "Çıkış tokenı",
  "kayit.detay.kaynak": "Kaynak",
  "kayit.detay.kaynak.api": "API anahtarı #{no}",
  "kayit.detay.kaynak.panel": "Panel hesabı",
  "kayit.detay.maskeleme.baslik": "Maskeleme sınırı",
  "kayit.detay.maskeleme.govde":
    "Kayıtlar veritabanına maskelenmiş yazılır (KVKK). Bu sayfa kaydın saklandığı hâli gösterir; kullanıcının kendi oturumunda gördüğü metin farklı olabilir.",
  "kayit.detay.sistem_istemi": "Sistem istemi",
  "kayit.detay.mesajlar": "Mesajlar ({sayi})",
  "kayit.detay.mesajlar.aria": "Mesajlar",
  "kayit.detay.mesaj_yok.baslik": "Mesaj yok",
  "kayit.detay.mesaj_yok.aciklama": "Bu konuşmada kayıtlı mesaj bulunmuyor.",

  // --- Kayıt indirme ve silme
  "kayit.indir": "{bicim} indir",
  "kayit.indir.bildirim": "{bicim} indirmesi tarayıcıya gönderildi.",
  "kayit.sil.dugme": "Sil",
  "kayit.sil.baslik": "Konuşmayı sil",
  "kayit.sil.aciklama":
    "Kayıt ve tüm mesajları kalıcı olarak silinir; bu işlem geri alınamaz.",
  "kayit.sil.soru": "“{baslik}” kaydı silinecek.",
  "kayit.sil.vazgec": "Vazgeç",
  "kayit.sil.onayla": "Kalıcı olarak sil",
  "kayit.sil.hata.baslik": "Silinemedi",
  "kayit.sil.bildirim": "Konuşma kaydı silindi.",

  // --- Mesaj baloncuğu (components/loglar/mesaj-baloncugu.tsx)
  "kayit.rol.kullanici": "Kullanıcı",
  "kayit.rol.asistan": "Asistan",
  "kayit.rol.sistem": "Sistem",
  "kayit.rol.arac": "Araç",
  "kayit.mesaj.token": "{sayi} token",
  "kayit.mesaj.bos_icerik": "(boş içerik)",
  "kayit.mesaj.saglayici_hatasi": "Sağlayıcı hatası",

  // --- Sayfalama (components/loglar/sayfalama.tsx)
  "kayit.sayfalama.ozet": "Toplam {baglanti} kayıt · {sayfa}/{son}. sayfa",
  "kayit.sayfalama.boyut.aria": "Sayfa boyutu",
  "kayit.sayfalama.boyut.secenek": "{sayi} kayıt",
  "kayit.sayfalama.onceki": "Önceki",
  "kayit.sayfalama.sonraki": "Sonraki",

  // --- Uzak veri durumu (components/loglar/veri-durumu.tsx)
  "kayit.veri.hata": "Veri alınamadı",
  "kayit.veri.yenile": "Yeniden dene",

  // --- İşlem kayıtları sayfası (app/(panel)/islem-kayitlari)
  "islem.baslik": "İşlem Kayıtları",
  "islem.aciklama":
    "Giriş, model yaşam döngüsü, kullanıcı/rol, anahtar ve log işlemlerinin denetim izi.",
  "islem.filtre.aria": "İşlem kaydı filtreleri",
  "islem.filtre.eylem": "Eylem",
  "islem.filtre.eylem.ipucu": "Tam eşleşme; ör. kullanici.guncelle",
  "islem.filtre.kullanici": "Kullanıcı",
  "islem.filtre.tum_kullanicilar": "Tüm kullanıcılar",
  "islem.filtre.kullanici_kimligi": "Kullanıcı kimliği",
  "islem.filtre.kullanici_kimligi.ipucu":
    "Kullanıcı listesi yalnız yöneticilere açık; kimlik ile süzün.",
  "islem.filtre.ornek_kimlik": "ör. 4",
  "islem.filtre.baslangic": "Başlangıç",
  "islem.filtre.bitis": "Bitiş",
  "islem.filtre.uygula": "Filtrele",
  "islem.filtre.temizle": "Temizle",
  "islem.tablo.tarih": "Tarih",
  "islem.tablo.eylem": "Eylem",
  "islem.tablo.kullanici": "Kullanıcı",
  "islem.tablo.hedef": "Hedef",
  "islem.tablo.ip": "IP",
  "islem.tablo.ayrinti": "Ayrıntı",
  "islem.goruntule": "Görüntüle",
  "islem.bos.baslik": "İşlem kaydı bulunamadı",
  "islem.bos.aciklama": "Bu filtrelerle eşleşen denetim kaydı yok.",

  // --- İşlem kaydı çekmecesi (app/(panel)/islem-kayitlari/ayrinti-cekmecesi.tsx)
  "islem.kayit": "İşlem kaydı",
  "islem.alan.kayit_no": "Kayıt no",
  "islem.alan.kullanici": "Kullanıcı",
  "islem.alan.hedef": "Hedef",
  "islem.alan.ip": "IP adresi",
  "islem.ayrinti.baslik": "Ayrıntı",
  "islem.ayrinti.bos": "Bu kayıt için ek ayrıntı yazılmamış.",
  "islem.ayrinti.secili_degil": "Kayıt seçilmedi.",

  // --- `ayrinti` alan adlarının okunur karşılıkları (lib/islem-kayitlari.ts)
  "islem.alan.ad": "Ad",
  "islem.alan.anahtarlar": "Değişen ayarlar",
  "islem.alan.api_anahtari_id": "API anahtarı no",
  "islem.alan.baslik": "Başlık",
  "islem.alan.bdm_id": "BDM no",
  "islem.alan.bdm_slug": "BDM slug",
  "islem.alan.durum": "Durum",
  "islem.alan.eposta": "E-posta",
  "islem.alan.gecersiz": "Geçersiz değerler",
  "islem.alan.gun": "Gün",
  "islem.alan.izinli_modeller": "İzinli modeller",
  "islem.alan.konusma_id": "Konuşma no",
  "islem.alan.kullanici_id": "Kullanıcı no",
  "islem.alan.marka_adi": "Marka adı",
  "islem.alan.rol": "Rol",
  "islem.alan.silinen": "Silinen kayıt",
  "islem.alan.slug": "Slug",
  "islem.evet": "Evet",
  "islem.hayir": "Hayır",
} as const;

export const enKayitlar: Record<keyof typeof trKayitlar, string> = {
  // --- Conversation logs page (app/(panel)/loglar)
  "kayit.loglar.baslik": "Conversation Logs",
  "kayit.loglar.aciklama":
    "Records are stored masked; filter, download and manage them.",
  "kayit.loglar.bos.baslik": "No records found",
  "kayit.loglar.bos.aciklama":
    "No conversation matches these filters. Try loosening the filters.",
  "kayit.loglar.geri": "Conversation logs",
  "kayit.basliksiz": "Untitled conversation",
  "kayit.gecersiz_no": "Invalid record number.",

  // --- Record filter (components/loglar/filtre-cubugu.tsx)
  "kayit.filtre.aria": "Record filters",
  "kayit.filtre.kullanici": "User",
  "kayit.filtre.tum_kullanicilar": "All users",
  "kayit.filtre.kullanici_kimligi": "User ID",
  "kayit.filtre.kullanici_kimligi.ipucu":
    "The user list is available to administrators only; filter by ID.",
  "kayit.filtre.ornek_kimlik": "e.g. 4",
  "kayit.filtre.model": "Model",
  "kayit.filtre.tum_modeller": "All models",
  "kayit.filtre.baslangic": "Start",
  "kayit.filtre.bitis": "End",
  "kayit.filtre.arama": "Text search",
  "kayit.filtre.arama.ipucu": "Title or message content",
  "kayit.filtre.uygula": "Filter",
  "kayit.filtre.temizle": "Clear",

  // --- Record table (components/loglar/tablo.tsx)
  "kayit.tablo.baslik": "Title",
  "kayit.tablo.kullanici": "User",
  "kayit.tablo.model": "Model",
  "kayit.tablo.mesaj": "Messages",
  "kayit.tablo.token": "Tokens (in/out)",
  "kayit.tablo.tarih": "Date",

  // --- Record detail (app/(panel)/loglar/[id])
  "kayit.detay.bilgileri": "Record Details",
  "kayit.detay.kullanici": "User",
  "kayit.detay.model": "Model",
  "kayit.detay.olusturulma": "Created",
  "kayit.detay.guncellenme": "Last updated",
  "kayit.detay.mesaj_sayisi": "Message count",
  "kayit.detay.token_girdi": "Input tokens",
  "kayit.detay.token_cikti": "Output tokens",
  "kayit.detay.kaynak": "Source",
  "kayit.detay.kaynak.api": "API key #{no}",
  "kayit.detay.kaynak.panel": "Panel account",
  "kayit.detay.maskeleme.baslik": "Masking limit",
  "kayit.detay.maskeleme.govde":
    "Records are written to the database masked (KVKK). This page shows the record as stored; the text the user sees in their own session may differ.",
  "kayit.detay.sistem_istemi": "System prompt",
  "kayit.detay.mesajlar": "Messages ({sayi})",
  "kayit.detay.mesajlar.aria": "Messages",
  "kayit.detay.mesaj_yok.baslik": "No messages",
  "kayit.detay.mesaj_yok.aciklama": "There are no recorded messages in this conversation.",

  // --- Record download and delete
  "kayit.indir": "Download {bicim}",
  "kayit.indir.bildirim": "The {bicim} download was sent to your browser.",
  "kayit.sil.dugme": "Delete",
  "kayit.sil.baslik": "Delete conversation",
  "kayit.sil.aciklama":
    "The record and all of its messages will be permanently deleted; this cannot be undone.",
  "kayit.sil.soru": "The record “{baslik}” will be deleted.",
  "kayit.sil.vazgec": "Cancel",
  "kayit.sil.onayla": "Delete permanently",
  "kayit.sil.hata.baslik": "Could not delete",
  "kayit.sil.bildirim": "Conversation record deleted.",

  // --- Message bubble (components/loglar/mesaj-baloncugu.tsx)
  "kayit.rol.kullanici": "User",
  "kayit.rol.asistan": "Assistant",
  "kayit.rol.sistem": "System",
  "kayit.rol.arac": "Tool",
  "kayit.mesaj.token": "{sayi} tokens",
  "kayit.mesaj.bos_icerik": "(empty content)",
  "kayit.mesaj.saglayici_hatasi": "Provider error",

  // --- Pagination (components/loglar/sayfalama.tsx)
  "kayit.sayfalama.ozet": "{baglanti} records in total · page {sayfa}/{son}",
  "kayit.sayfalama.boyut.aria": "Page size",
  "kayit.sayfalama.boyut.secenek": "{sayi} records",
  "kayit.sayfalama.onceki": "Previous",
  "kayit.sayfalama.sonraki": "Next",

  // --- Remote data state (components/loglar/veri-durumu.tsx)
  "kayit.veri.hata": "Could not load data",
  "kayit.veri.yenile": "Try again",

  // --- Audit records page (app/(panel)/islem-kayitlari)
  "islem.baslik": "Audit Logs",
  "islem.aciklama":
    "Audit trail of sign-in, model lifecycle, user/role, key and log operations.",
  "islem.filtre.aria": "Audit record filters",
  "islem.filtre.eylem": "Action",
  "islem.filtre.eylem.ipucu": "Exact match; e.g. kullanici.guncelle",
  "islem.filtre.kullanici": "User",
  "islem.filtre.tum_kullanicilar": "All users",
  "islem.filtre.kullanici_kimligi": "User ID",
  "islem.filtre.kullanici_kimligi.ipucu":
    "The user list is available to administrators only; filter by ID.",
  "islem.filtre.ornek_kimlik": "e.g. 4",
  "islem.filtre.baslangic": "Start",
  "islem.filtre.bitis": "End",
  "islem.filtre.uygula": "Filter",
  "islem.filtre.temizle": "Clear",
  "islem.tablo.tarih": "Date",
  "islem.tablo.eylem": "Action",
  "islem.tablo.kullanici": "User",
  "islem.tablo.hedef": "Target",
  "islem.tablo.ip": "IP",
  "islem.tablo.ayrinti": "Details",
  "islem.goruntule": "View",
  "islem.bos.baslik": "No audit records found",
  "islem.bos.aciklama": "No audit record matches these filters.",

  // --- Audit record drawer (app/(panel)/islem-kayitlari/ayrinti-cekmecesi.tsx)
  "islem.kayit": "Audit record",
  "islem.alan.kayit_no": "Record no",
  "islem.alan.kullanici": "User",
  "islem.alan.hedef": "Target",
  "islem.alan.ip": "IP address",
  "islem.ayrinti.baslik": "Details",
  "islem.ayrinti.bos": "No extra details were recorded for this entry.",
  "islem.ayrinti.secili_degil": "No record selected.",

  // --- Readable labels for `ayrinti` field names (lib/islem-kayitlari.ts)
  "islem.alan.ad": "Name",
  "islem.alan.anahtarlar": "Changed settings",
  "islem.alan.api_anahtari_id": "API key no",
  "islem.alan.baslik": "Title",
  "islem.alan.bdm_id": "BDM no",
  "islem.alan.bdm_slug": "BDM slug",
  "islem.alan.durum": "Status",
  "islem.alan.eposta": "E-mail",
  "islem.alan.gecersiz": "Invalid values",
  "islem.alan.gun": "Days",
  "islem.alan.izinli_modeller": "Allowed models",
  "islem.alan.konusma_id": "Conversation no",
  "islem.alan.kullanici_id": "User no",
  "islem.alan.marka_adi": "Brand name",
  "islem.alan.rol": "Role",
  "islem.alan.silinen": "Deleted records",
  "islem.alan.slug": "Slug",
  "islem.evet": "Yes",
  "islem.hayir": "No",
};
