/**
 * BDM (Bağlı Dil Modeli) metinleri: liste, form, sekmeler, satır işlemleri ve
 * `lib/bdm.ts` veri katmanının hata mesajları.
 *
 * Anahtarlar `bdm.*` düzeninde; `{ad}`, `{sayi}` gibi yer tutucular `t` ile
 * doldurulur. Cümle içine React bileşeni gömülecekse şablona `{ad}`/`{kod}`
 * yazılıp çağıran tarafta `t(...).split("{ad}")` ile parçalanır.
 */
export const trBdm = {
  // --- Liste sayfası
  "bdm.baslik": "BDM'ler",
  "bdm.aciklama": "Bağlı dil modellerini yönetin, hazırlayın ve çalıştırın.",
  "bdm.yeni": "Yeni BDM",
  "bdm.yeni.aciklama": "Kayıt taslak durumunda oluşturulur; bağlantıyı doğrulayınca hazır olur.",
  "bdm.listeye_don": "Listeye dön",
  "bdm.ara.etiket": "BDM ara",
  "bdm.ara.ipucu": "Görünen ad veya slug ara…",
  "bdm.suzgec.saglayici": "Sağlayıcı süzgeci",
  "bdm.suzgec.tum_saglayicilar": "Tüm sağlayıcılar",
  "bdm.suzgec.durum": "Durum süzgeci",
  "bdm.suzgec.tum_durumlar": "Tüm durumlar",
  "bdm.suzgec.temizle": "Süzgeçleri temizle",
  "bdm.liste.alinamadi": "BDM listesi alınamadı",
  "bdm.yeniden_dene": "Yeniden dene",
  "bdm.bos.suzgec.baslik": "Süzgeçle eşleşen BDM yok.",
  "bdm.bos.suzgec.aciklama": "Arama metnini veya süzgeçleri değiştirip yeniden deneyin.",
  "bdm.bos.baslik": "Henüz BDM eklenmedi.",
  "bdm.bos.aciklama": "İlk modelinizi ekleyip bağlantısını doğrulayın.",
  "bdm.kayit.sayisi": "{sayi} kayıt gösteriliyor.",

  // --- Ayrıntı sayfası ve sekmeler
  "bdm.sekme.genel": "Genel",
  "bdm.sekme.hazirlama": "Hazırlama",
  "bdm.sekme.calisma": "Çalışma",
  "bdm.sekme.gunlukler": "Günlükler",
  "bdm.sekme.yonlendirme": "Yönlendirme",
  "bdm.gecersiz.baslik": "Geçersiz kayıt",
  "bdm.gecersiz.aciklama": "Adresteki BDM kimliği geçersiz.",
  "bdm.yuklenemedi": "BDM yüklenemedi",
  "bdm.yerel": "Yerel",
  "bdm.uzak": "Uzak",
  "bdm.adres_tanimsiz": "adres tanımsız",
  "bdm.model_tanimsiz": "model tanımsız",
  "bdm.tanimsiz": "tanımsız",

  // --- Tablo ve satır işlemleri
  "bdm.alan.gorunen_ad": "Görünen ad",
  "bdm.alan.saglayici": "Sağlayıcı",
  "bdm.alan.model": "Model",
  "bdm.alan.durum": "Durum",
  "bdm.alan.yer": "Yer",
  "bdm.alan.guncellenme": "Güncellenme",
  "bdm.alan.islemler": "İşlemler",
  "bdm.alan.yeni_gorunen_ad": "Yeni görünen ad",
  "bdm.alan.yeni_ad": "Yeni ad",
  "bdm.eylem.duzenle": "Düzenle",
  "bdm.eylem.kopyala": "Kopyala",
  "bdm.eylem.calistir": "Çalıştır",
  "bdm.eylem.baslat": "Başlat",
  "bdm.eylem.durdur": "Durdur",
  "bdm.eylem.yeniden_baslat": "Yeniden başlat",
  "bdm.eylem.sil": "Sil",
  "bdm.vazgec": "Vazgeç",
  "bdm.kaydet": "Kaydet",
  "bdm.bildirim.baslatildi": "{ad} başlatıldı.",
  "bdm.bildirim.durduruldu": "{ad} durduruldu.",
  "bdm.bildirim.kopyalandi": "{ad} kopyalandı.",
  "bdm.bildirim.silindi": "{ad} silindi.",
  "bdm.bildirim.islem_tamam": "İşlem tamamlandı.",
  "bdm.hata.islem": "İşlem tamamlanamadı.",
  "bdm.hata.kopyalama": "Kopyalama tamamlanamadı.",
  "bdm.hata.silme": "Silme tamamlanamadı.",

  // --- Kopyalama ve silme diyalogları
  "bdm.kopyala.baslik": "BDM'yi kopyala",
  "bdm.kopyala.aciklama": "{ad} ayarları yeni bir taslak kayıt olarak çoğaltılır.",
  "bdm.kopyala.varsayilan_ad": "{ad} kopya",
  "bdm.sil.baslik": "BDM'yi sil",
  "bdm.sil.aciklama": "Bu işlem geri alınamaz.",
  "bdm.sil.kalicilik": "Kalıcı olarak sil",
  "bdm.sil.uyari":
    "{ad} kaydı ve konteyner kaydı silinir. Bağlı konuşma veya kullanım kaydı varsa silme reddedilir.",
  "bdm.sil.kart.aciklama":
    "Kayıt kalıcı olarak silinir. Bağlı konuşma veya kullanım kaydı varsa silme reddedilir ve gerekçe gösterilir.",
  "bdm.sil.onay.baslik": "Silmeyi onayla",
  "bdm.sil.onay.uyari": "{ad} ({slug}) kaydı silinecek.",

  // --- Satır menüsü gerekçeleri
  "bdm.menu.etiket": "{ad} işlemleri",
  "bdm.menu.zaten_calisiyor": "Bu model zaten çalışıyor.",
  "bdm.menu.once_dogrula": "Önce Hazırlama sekmesinden bağlantıyı doğrulayın.",
  "bdm.menu.once_durdur": "Hata durumundaki model önce durdurulmalıdır.",
  "bdm.menu.calismiyor": "Bu model çalışmıyor.",
  "bdm.menu.kopyala_yetki": "Kopyalama yalnız yönetici rolünde yapılabilir.",
  "bdm.menu.sil_yetki": "Silme yalnız yönetici rolünde yapılabilir.",
  "bdm.menu.sil_calisiyor": "Çalışan model silinemez; önce durdurun.",

  // --- GPU şeridi ve ilerleme çubuğu
  "bdm.gpu.okunamadi": "Çalışma zamanı durumu okunamadı",
  "bdm.gpu.surucu_yok": "Sürücü bilgisi alınamadı.",
  "bdm.gpu.bulunamadi": "GPU bulunamadı",
  "bdm.gpu.mesaj":
    "Bu ortamda GPU çalışma zamanı bulunamadı; GPU gerektiren modeller başlatılamaz.",
  "bdm.gpu.devredisi":
    "vLLM ve TGI için başlatma düğmeleri devre dışı. GPU gerektirmeyen Ollama sağlayıcısını kullanabilirsiniz.",
  "bdm.ilerleme.etiket": "Model indirme ilerlemesi",
  "bdm.ilerleme.yuzde": "%{yuzde}",
  "bdm.ilerleme.satir": "%{yuzde} · {mesaj}",

  // --- BDM formu
  "bdm.form.model.baslik": "Model bilgileri",
  "bdm.form.model.aciklama":
    "Görünen ad müşteriye gösterilir; slug boş bırakılırsa addan üretilir.",
  "bdm.form.parametreler.baslik": "Üretim parametreleri",
  "bdm.form.parametreler.aciklama":
    "Varsayılanlar sohbet isteklerinde kullanılır; istek başına geçersiz kılınabilir.",
  "bdm.form.yukleniyor": "Sağlayıcı listesi yükleniyor…",
  "bdm.form.saglayicilar.alinamadi": "Sağlayıcı listesi alınamadı",
  "bdm.form.gpu.baslik": "GPU gerektiren sağlayıcı",
  "bdm.form.gpu.aciklama":
    "{ad} GPU üzerinde çalışır. GPU çalışma zamanı yoksa hazırlama ve başlatma uçları {kod} döner.",
  "bdm.form.seciniz": "Seçiniz…",
  "bdm.form.gorunen_ad.ipucu": "Yerel Llama 3",
  "bdm.form.gorunen_ad.kisa": "Görünen ad en az 2 karakter olmalıdır.",
  "bdm.form.slug.ipucu.duzenle": "Slug oluşturulduktan sonra değiştirilemez.",
  "bdm.form.slug.ipucu.yeni": "Boş bırakılırsa görünen addan üretilir.",
  "bdm.form.saglayici.zorunlu": "Sağlayıcı seçimi zorunludur.",
  "bdm.form.temel_url.zorunlu": "Bu sağlayıcı için temel adres zorunludur.",
  "bdm.form.temel_adres.varsayilan": "Varsayılan: {adres}",
  "bdm.form.temel_adres.zorunlu": "Bu sağlayıcı için adresi siz girmelisiniz.",
  "bdm.form.api_anahtari.mevcut": "Boş bırakılırsa değişmez. Mevcut: {maske}",
  "bdm.form.api_anahtari.ipucu": "Sağlayıcı anahtarı şifrelenerek saklanır.",
  "bdm.form.aciklama.ipucu": "Kısa bir açıklama",
  "bdm.form.baglam_penceresi.ipucu": "128 – 2.000.000",
  "bdm.form.maks_cikti.ipucu": "16 – 200.000",
  "bdm.form.sicaklik.ipucu": "0 – 2",
  "bdm.form.sistem_istemi.ipucu": "Sen yardımcı bir asistansın…",
  "bdm.form.duzelt": "Kaydetmek için işaretli alanları düzeltin.",
  "bdm.form.olusturuldu": "BDM oluşturuldu.",
  "bdm.form.kaydedildi": "Değişiklikler kaydedildi.",
  "bdm.form.olustur": "BDM oluştur",
  "bdm.form.kaydet": "Değişiklikleri kaydet",
  "bdm.hata.kayit": "Kayıt tamamlanamadı.",
  "bdm.hata.sayi": "{alan} sayı olmalıdır.",
  "bdm.hata.sayi_aralik": "{alan} {alt} ile {ust} arasında olmalıdır.",

  // --- Alan etiketleri
  "bdm.alan.slug": "Slug",
  "bdm.alan.upstream_model": "Upstream model",
  "bdm.alan.temel_adres": "Temel adres",
  "bdm.alan.api_anahtari": "API anahtarı",
  "bdm.alan.aciklama": "Açıklama",
  "bdm.alan.baglam_penceresi": "Bağlam penceresi",
  "bdm.alan.maks_cikti": "Maksimum çıktı",
  "bdm.alan.sicaklik": "Sıcaklık",
  "bdm.alan.sistem_istemi": "Sistem istemi",
  "bdm.alan.konteyner": "Konteyner kimliği",
  "bdm.alan.saglik": "Sağlık",
  "bdm.alan.docker": "Docker",
  "bdm.alan.gpu": "GPU",
  "bdm.alan.bos_disk": "Boş disk",
  "bdm.alan.imaj": "İmaj",
  "bdm.alan.port": "Port",
  "bdm.alan.bellek": "Bellek",
  "bdm.alan.takma_ad": "Takma ad",
  "bdm.alan.oncelik": "Öncelik",
  "bdm.alan.ad": "Ad",
  "bdm.alan.deger": "Değer",

  // --- Ortak değerler ve birimler
  "bdm.deger.var": "Var",
  "bdm.deger.yok": "Yok",
  "bdm.deger.onbellekte": "Önbellekte",
  "bdm.deger.gerekli": "Gerekli",
  "bdm.deger.gerekmez": "Gerekmez",
  "bdm.birim.gb": "{deger} GB",

  // --- Çalışma sekmesi
  "bdm.calisma.baslik": "Çalışma durumu",
  "bdm.calisma.aciklama": "Durum ve sağlık sekme görünürken 10 saniyede bir yoklanır.",
  "bdm.calisma.durum_okunamadi": "Durum okunamadı",
  "bdm.calisma.son_yoklama": "Son yoklama: {zaman}",
  "bdm.calisma.yoklaniyor": "Yoklanıyor…",
  "bdm.calisma.rozet": "Durum rozeti:",
  "bdm.calisma.saglik_bekleniyor": "Sağlık bilgisi bekleniyor…",
  "bdm.calisma.gpu_gerekli": "GPU gerekli",
  "bdm.calisma.gpu_devredisi": "Başlatma ve yeniden başlatma düğmeleri bu nedenle devre dışı.",
  "bdm.calisma.baslatilamaz":
    "Bu durumdan başlatma yapılamaz; önce Hazırlama sekmesinden bağlantıyı doğrulayın veya Durdu durumuna geçin.",
  "bdm.saglik.hazir": "Hazır",
  "bdm.saglik.ayakta": "Ayakta",
  "bdm.saglik.kapali": "Kapalı",

  // --- Günlükler sekmesi
  "bdm.gunluk.baslik": "Konteyner günlükleri",
  "bdm.gunluk.aciklama": "Son 200 satır istenir ve yeni satırlar canlı akıtılır (SSE).",
  "bdm.gunluk.durum.canli": "Canlı",
  "bdm.gunluk.durum.duraklatildi": "Duraklatıldı",
  "bdm.gunluk.durum.kapandi": "Akış kapandı",
  "bdm.gunluk.durum.baglaniyor": "Bağlanıyor…",
  "bdm.gunluk.surdur": "Sürdür",
  "bdm.gunluk.duraklat": "Duraklat",
  "bdm.gunluk.yeniden_baglan": "Yeniden bağlan",
  "bdm.gunluk.temizle": "Temizle",
  "bdm.gunluk.otomatik_kaydir": "Otomatik kaydırma",
  "bdm.gunluk.satir_sayisi": "{sayi} satır",
  "bdm.gunluk.bos": "Henüz günlük satırı yok.",

  // --- Hazırlama sekmesi: doğrulama
  "bdm.hazirlama.dogrulama.baslik": "Bağlantı doğrulama",
  "bdm.hazirlama.dogrulama.aciklama":
    "Sağlayıcı adresine erişim ve model listesi sınanır; gecikme ölçülür.",
  "bdm.hazirlama.dogrulama.eylem": "Bağlantıyı doğrula",
  "bdm.hazirlama.dogrulama.basarili": "Bağlantı başarılı",
  "bdm.hazirlama.dogrulama.basarisiz": "Bağlantı doğrulanamadı",
  "bdm.hazirlama.dogrulama.ozet": "Gecikme: {gecikme} · {model} model",

  // --- Hazırlama sekmesi: ön kontrol
  "bdm.hazirlama.onkontrol.baslik": "Ön kontrol",
  "bdm.hazirlama.onkontrol.aciklama":
    "Docker, GPU, boş disk alanı ve imaj önbelleği denetlenir.",
  "bdm.hazirlama.onkontrol.eylem": "Ön kontrolü çalıştır",
  "bdm.hazirlama.onkontrol.uygunluk": "Uygunluk:",
  "bdm.hazirlama.onkontrol.uygun": "Hazırlamaya uygun",
  "bdm.hazirlama.onkontrol.uygun_degil": "Uygun değil",
  "bdm.hazirlama.onkontrol.uyarilar": "Uyarılar",
  "bdm.hazirlama.onkontrol.uyari_yok": "Ön kontrol uyarısı yok.",

  // --- Hazırlama sekmesi: manifest
  "bdm.hazirlama.manifest.baslik": "Konteyner manifesti",
  "bdm.hazirlama.manifest.aciklama":
    "Çalıştırma komutu, port, GPU bayrağı, bellek tahmini ve ortam değişkenleri.",
  "bdm.hazirlama.manifest.eylem": "Manifest üret",
  "bdm.hazirlama.manifest.komut": "Komut",
  "bdm.hazirlama.manifest.ortam": "Ortam değişkenleri",
  "bdm.hazirlama.manifest.ortam_yok": "Ortam değişkeni yok.",
  "bdm.hazirlama.manifest.maske": "Gizli değerler maskelenmiş olarak gösterilir.",
  "bdm.bildirim.komut_kopyalandi": "Komut kopyalandı.",
  "bdm.hata.komut_kopyalanamadi": "Komut kopyalanamadı.",

  // --- Hazırlama sekmesi: model indirme
  "bdm.hazirlama.indir.baslik": "Modeli indir",
  "bdm.hazirlama.indir.aciklama":
    "Ollama model indirmesi ilerleme akışı olarak izlenir (SSE).",
  "bdm.hazirlama.indir.yok.baslik": "Bu sağlayıcıda indirme yok",
  "bdm.hazirlama.indir.yok.aciklama":
    "Model indirme yalnızca Ollama sağlayıcısında desteklenir.",
  "bdm.hazirlama.indir.eylem": "Modeli indir",
  "bdm.hazirlama.indir.baglaniyor": "Bağlantı kuruluyor…",
  "bdm.hazirlama.indir.durduruldu": "İndirme durduruldu.",
  "bdm.bildirim.indirme_tamam": "Model indirme akışı tamamlandı.",

  // --- Yönlendirme sekmesi
  "bdm.yonlendirme.baslik": "Yönlendirme",
  "bdm.yonlendirme.aciklama":
    "Takma ad model için alternatif isimdir; öncelik yönlendirme sırasını belirler.",
  "bdm.yonlendirme.takma_ad.ipucu": "Boş bırakılırsa mevcut takma ad değişmez.",
  "bdm.yonlendirme.oncelik.ipucu": "0 – 1000 (küçük değer önce denenir)",
  "bdm.yonlendirme.hata.takma_ad": "Takma ad en fazla 80 karakter olabilir.",
  "bdm.yonlendirme.hata.oncelik": "Öncelik 0 ile 1000 arasında bir tam sayı olmalıdır.",
  "bdm.bildirim.yonlendirme_kaydedildi": "Yönlendirme ayarları kaydedildi.",

  // --- Veri katmanı hataları (lib/bdm.ts)
  "bdm.hata.gpu_yok":
    "GPU çalışma zamanı bulunamadı; bu sağlayıcı GPU olmadan başlatılamaz.",
  "bdm.hata.kayit_yok": "BDM kaydı bulunamadı.",
  "bdm.hata.akis": "Akış sırasında beklenmeyen bir hata oluştu.",
  "bdm.hata.akis_baslatilamadi": "Akış başlatılamadı (HTTP {durum}).",
  "bdm.hata.akis_govdesi": "Sunucu akış gövdesi döndürmedi.",
} as const;

export const enBdm: Record<keyof typeof trBdm, string> = {
  // --- List page
  "bdm.baslik": "BDMs",
  "bdm.aciklama": "Manage, prepare and run your connected language models.",
  "bdm.yeni": "New BDM",
  "bdm.yeni.aciklama":
    "The record is created as a draft; it becomes ready once you verify the connection.",
  "bdm.listeye_don": "Back to list",
  "bdm.ara.etiket": "Search BDMs",
  "bdm.ara.ipucu": "Search display name or slug…",
  "bdm.suzgec.saglayici": "Provider filter",
  "bdm.suzgec.tum_saglayicilar": "All providers",
  "bdm.suzgec.durum": "Status filter",
  "bdm.suzgec.tum_durumlar": "All statuses",
  "bdm.suzgec.temizle": "Clear filters",
  "bdm.liste.alinamadi": "Could not load the BDM list",
  "bdm.yeniden_dene": "Try again",
  "bdm.bos.suzgec.baslik": "No BDM matches the filter.",
  "bdm.bos.suzgec.aciklama": "Change the search text or filters and try again.",
  "bdm.bos.baslik": "No BDMs added yet.",
  "bdm.bos.aciklama": "Add your first model and verify its connection.",
  "bdm.kayit.sayisi": "{sayi} records shown.",

  // --- Detail page and tabs
  "bdm.sekme.genel": "General",
  "bdm.sekme.hazirlama": "Preparation",
  "bdm.sekme.calisma": "Runtime",
  "bdm.sekme.gunlukler": "Logs",
  "bdm.sekme.yonlendirme": "Routing",
  "bdm.gecersiz.baslik": "Invalid record",
  "bdm.gecersiz.aciklama": "The BDM id in the address is invalid.",
  "bdm.yuklenemedi": "Could not load the BDM",
  "bdm.yerel": "Local",
  "bdm.uzak": "Remote",
  "bdm.adres_tanimsiz": "address not set",
  "bdm.model_tanimsiz": "model not set",
  "bdm.tanimsiz": "not set",

  // --- Table and row actions
  "bdm.alan.gorunen_ad": "Display name",
  "bdm.alan.saglayici": "Provider",
  "bdm.alan.model": "Model",
  "bdm.alan.durum": "Status",
  "bdm.alan.yer": "Location",
  "bdm.alan.guncellenme": "Updated",
  "bdm.alan.islemler": "Actions",
  "bdm.alan.yeni_gorunen_ad": "New display name",
  "bdm.alan.yeni_ad": "New name",
  "bdm.eylem.duzenle": "Edit",
  "bdm.eylem.kopyala": "Copy",
  "bdm.eylem.calistir": "Run",
  "bdm.eylem.baslat": "Start",
  "bdm.eylem.durdur": "Stop",
  "bdm.eylem.yeniden_baslat": "Restart",
  "bdm.eylem.sil": "Delete",
  "bdm.vazgec": "Cancel",
  "bdm.kaydet": "Save",
  "bdm.bildirim.baslatildi": "{ad} started.",
  "bdm.bildirim.durduruldu": "{ad} stopped.",
  "bdm.bildirim.kopyalandi": "{ad} copied.",
  "bdm.bildirim.silindi": "{ad} deleted.",
  "bdm.bildirim.islem_tamam": "Action completed.",
  "bdm.hata.islem": "The action could not be completed.",
  "bdm.hata.kopyalama": "Copying could not be completed.",
  "bdm.hata.silme": "Deletion could not be completed.",

  // --- Copy and delete dialogs
  "bdm.kopyala.baslik": "Copy BDM",
  "bdm.kopyala.aciklama": "{ad} settings are duplicated as a new draft record.",
  "bdm.kopyala.varsayilan_ad": "{ad} copy",
  "bdm.sil.baslik": "Delete BDM",
  "bdm.sil.aciklama": "This action cannot be undone.",
  "bdm.sil.kalicilik": "Delete permanently",
  "bdm.sil.uyari":
    "{ad} record and its container record are deleted. If there are linked conversation or usage records, the deletion is rejected.",
  "bdm.sil.kart.aciklama":
    "The record is deleted permanently. If there are linked conversation or usage records, the deletion is rejected and the reason is shown.",
  "bdm.sil.onay.baslik": "Confirm deletion",
  "bdm.sil.onay.uyari": "{ad} ({slug}) will be deleted.",

  // --- Row menu reasons
  "bdm.menu.etiket": "Actions for {ad}",
  "bdm.menu.zaten_calisiyor": "This model is already running.",
  "bdm.menu.once_dogrula": "Verify the connection on the Preparation tab first.",
  "bdm.menu.once_durdur": "A model in error state must be stopped first.",
  "bdm.menu.calismiyor": "This model is not running.",
  "bdm.menu.kopyala_yetki": "Only administrators can copy.",
  "bdm.menu.sil_yetki": "Only administrators can delete.",
  "bdm.menu.sil_calisiyor": "A running model cannot be deleted; stop it first.",

  // --- GPU strip and progress bar
  "bdm.gpu.okunamadi": "Could not read the runtime status",
  "bdm.gpu.surucu_yok": "Driver information could not be read.",
  "bdm.gpu.bulunamadi": "No GPU found",
  "bdm.gpu.mesaj":
    "No GPU runtime was found in this environment; GPU-based models cannot be started.",
  "bdm.gpu.devredisi":
    "Start buttons are disabled for vLLM and TGI. You can use the Ollama provider, which does not require a GPU.",
  "bdm.ilerleme.etiket": "Model download progress",
  "bdm.ilerleme.yuzde": "%{yuzde}",
  "bdm.ilerleme.satir": "%{yuzde} · {mesaj}",

  // --- BDM form
  "bdm.form.model.baslik": "Model information",
  "bdm.form.model.aciklama":
    "The display name is shown to clients; the slug is generated from the name if left empty.",
  "bdm.form.parametreler.baslik": "Generation parameters",
  "bdm.form.parametreler.aciklama":
    "The defaults are used for chat requests; they can be overridden per request.",
  "bdm.form.yukleniyor": "Loading the provider list…",
  "bdm.form.saglayicilar.alinamadi": "Could not load the provider list",
  "bdm.form.gpu.baslik": "GPU-based provider",
  "bdm.form.gpu.aciklama":
    "{ad} runs on GPU. If there is no GPU runtime, the preparation and start endpoints return {kod}.",
  "bdm.form.seciniz": "Select…",
  "bdm.form.gorunen_ad.ipucu": "Local Llama 3",
  "bdm.form.gorunen_ad.kisa": "The display name must be at least 2 characters.",
  "bdm.form.slug.ipucu.duzenle": "The slug cannot be changed after creation.",
  "bdm.form.slug.ipucu.yeni": "Generated from the display name if left empty.",
  "bdm.form.saglayici.zorunlu": "Provider selection is required.",
  "bdm.form.temel_url.zorunlu": "The base address is required for this provider.",
  "bdm.form.temel_adres.varsayilan": "Default: {adres}",
  "bdm.form.temel_adres.zorunlu": "You must enter the address for this provider.",
  "bdm.form.api_anahtari.mevcut": "If left empty, it stays unchanged. Current: {maske}",
  "bdm.form.api_anahtari.ipucu": "The provider key is stored encrypted.",
  "bdm.form.aciklama.ipucu": "A short description",
  "bdm.form.baglam_penceresi.ipucu": "128 – 2,000,000",
  "bdm.form.maks_cikti.ipucu": "16 – 200,000",
  "bdm.form.sicaklik.ipucu": "0 – 2",
  "bdm.form.sistem_istemi.ipucu": "You are a helpful assistant…",
  "bdm.form.duzelt": "Fix the marked fields to save.",
  "bdm.form.olusturuldu": "BDM created.",
  "bdm.form.kaydedildi": "Changes saved.",
  "bdm.form.olustur": "Create BDM",
  "bdm.form.kaydet": "Save changes",
  "bdm.hata.kayit": "The record could not be saved.",
  "bdm.hata.sayi": "{alan} must be a number.",
  "bdm.hata.sayi_aralik": "{alan} must be between {alt} and {ust}.",

  // --- Field labels
  "bdm.alan.slug": "Slug",
  "bdm.alan.upstream_model": "Upstream model",
  "bdm.alan.temel_adres": "Base address",
  "bdm.alan.api_anahtari": "API key",
  "bdm.alan.aciklama": "Description",
  "bdm.alan.baglam_penceresi": "Context window",
  "bdm.alan.maks_cikti": "Maximum output",
  "bdm.alan.sicaklik": "Temperature",
  "bdm.alan.sistem_istemi": "System prompt",
  "bdm.alan.konteyner": "Container id",
  "bdm.alan.saglik": "Health",
  "bdm.alan.docker": "Docker",
  "bdm.alan.gpu": "GPU",
  "bdm.alan.bos_disk": "Free disk",
  "bdm.alan.imaj": "Image",
  "bdm.alan.port": "Port",
  "bdm.alan.bellek": "Memory",
  "bdm.alan.takma_ad": "Alias",
  "bdm.alan.oncelik": "Priority",
  "bdm.alan.ad": "Name",
  "bdm.alan.deger": "Value",

  // --- Shared values and units
  "bdm.deger.var": "Yes",
  "bdm.deger.yok": "No",
  "bdm.deger.onbellekte": "Cached",
  "bdm.deger.gerekli": "Required",
  "bdm.deger.gerekmez": "Not required",
  "bdm.birim.gb": "{deger} GB",

  // --- Runtime tab
  "bdm.calisma.baslik": "Runtime status",
  "bdm.calisma.aciklama":
    "Status and health are polled every 10 seconds while the tab is visible.",
  "bdm.calisma.durum_okunamadi": "Could not read the status",
  "bdm.calisma.son_yoklama": "Last poll: {zaman}",
  "bdm.calisma.yoklaniyor": "Polling…",
  "bdm.calisma.rozet": "Status badge:",
  "bdm.calisma.saglik_bekleniyor": "Waiting for health information…",
  "bdm.calisma.gpu_gerekli": "GPU required",
  "bdm.calisma.gpu_devredisi":
    "The start and restart buttons are disabled for this reason.",
  "bdm.calisma.baslatilamaz":
    "This status cannot be started; verify the connection on the Preparation tab first or switch to the Stopped status.",
  "bdm.saglik.hazir": "Ready",
  "bdm.saglik.ayakta": "Up",
  "bdm.saglik.kapali": "Down",

  // --- Logs tab
  "bdm.gunluk.baslik": "Container logs",
  "bdm.gunluk.aciklama":
    "The last 200 lines are requested and new lines are streamed live (SSE).",
  "bdm.gunluk.durum.canli": "Live",
  "bdm.gunluk.durum.duraklatildi": "Paused",
  "bdm.gunluk.durum.kapandi": "Stream closed",
  "bdm.gunluk.durum.baglaniyor": "Connecting…",
  "bdm.gunluk.surdur": "Resume",
  "bdm.gunluk.duraklat": "Pause",
  "bdm.gunluk.yeniden_baglan": "Reconnect",
  "bdm.gunluk.temizle": "Clear",
  "bdm.gunluk.otomatik_kaydir": "Auto-scroll",
  "bdm.gunluk.satir_sayisi": "{sayi} lines",
  "bdm.gunluk.bos": "No log lines yet.",

  // --- Preparation tab: verification
  "bdm.hazirlama.dogrulama.baslik": "Connection verification",
  "bdm.hazirlama.dogrulama.aciklama":
    "Access to the provider address and the model list are probed; latency is measured.",
  "bdm.hazirlama.dogrulama.eylem": "Verify connection",
  "bdm.hazirlama.dogrulama.basarili": "Connection successful",
  "bdm.hazirlama.dogrulama.basarisiz": "Connection could not be verified",
  "bdm.hazirlama.dogrulama.ozet": "Latency: {gecikme} · {model} models",

  // --- Preparation tab: pre-check
  "bdm.hazirlama.onkontrol.baslik": "Pre-check",
  "bdm.hazirlama.onkontrol.aciklama":
    "Docker, GPU, free disk space and the image cache are checked.",
  "bdm.hazirlama.onkontrol.eylem": "Run pre-check",
  "bdm.hazirlama.onkontrol.uygunluk": "Suitability:",
  "bdm.hazirlama.onkontrol.uygun": "Ready for preparation",
  "bdm.hazirlama.onkontrol.uygun_degil": "Not suitable",
  "bdm.hazirlama.onkontrol.uyarilar": "Warnings",
  "bdm.hazirlama.onkontrol.uyari_yok": "No pre-check warnings.",

  // --- Preparation tab: manifest
  "bdm.hazirlama.manifest.baslik": "Container manifest",
  "bdm.hazirlama.manifest.aciklama":
    "Run command, port, GPU flag, memory estimate and environment variables.",
  "bdm.hazirlama.manifest.eylem": "Generate manifest",
  "bdm.hazirlama.manifest.komut": "Command",
  "bdm.hazirlama.manifest.ortam": "Environment variables",
  "bdm.hazirlama.manifest.ortam_yok": "No environment variables.",
  "bdm.hazirlama.manifest.maske": "Secret values are shown masked.",
  "bdm.bildirim.komut_kopyalandi": "Command copied.",
  "bdm.hata.komut_kopyalanamadi": "Command could not be copied.",

  // --- Preparation tab: model download
  "bdm.hazirlama.indir.baslik": "Download model",
  "bdm.hazirlama.indir.aciklama":
    "The Ollama model download is followed as a progress stream (SSE).",
  "bdm.hazirlama.indir.yok.baslik": "No download for this provider",
  "bdm.hazirlama.indir.yok.aciklama":
    "Model download is supported only for the Ollama provider.",
  "bdm.hazirlama.indir.eylem": "Download model",
  "bdm.hazirlama.indir.baglaniyor": "Connecting…",
  "bdm.hazirlama.indir.durduruldu": "Download stopped.",
  "bdm.bildirim.indirme_tamam": "Model download stream completed.",

  // --- Routing tab
  "bdm.yonlendirme.baslik": "Routing",
  "bdm.yonlendirme.aciklama":
    "The alias is an alternative name for the model; the priority determines the routing order.",
  "bdm.yonlendirme.takma_ad.ipucu": "If left empty, the current alias stays unchanged.",
  "bdm.yonlendirme.oncelik.ipucu": "0 – 1000 (a lower value is tried first)",
  "bdm.yonlendirme.hata.takma_ad": "The alias can be at most 80 characters.",
  "bdm.yonlendirme.hata.oncelik": "The priority must be an integer between 0 and 1000.",
  "bdm.bildirim.yonlendirme_kaydedildi": "Routing settings saved.",

  // --- Data layer errors (lib/bdm.ts)
  "bdm.hata.gpu_yok":
    "No GPU runtime was found; this provider cannot be started without a GPU.",
  "bdm.hata.kayit_yok": "BDM record not found.",
  "bdm.hata.akis": "An unexpected error occurred during the stream.",
  "bdm.hata.akis_baslatilamadi": "The stream could not be started (HTTP {durum}).",
  "bdm.hata.akis_govdesi": "The server did not return a stream body.",
};
