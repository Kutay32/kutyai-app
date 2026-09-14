/**
 * Türkçe mesaj kataloğu (spec §10.2).
 *
 * Anahtar düzeni `alan.alt.anahtar`; değişkenler `{ad}` biçiminde yerleştirilir
 * (`lib/dil.tsx` içindeki `t`). Cümle içine React bileşeni (bağlantı vb.)
 * gömülecekse şablona `{baglanti}` yazılır ve çağıran taraf `t(...).split("{baglanti}")`
 * ile parçalar — böylece kelime sırası dile göre kalır.
 *
 * Yeni metin eklerken: anahtarı buraya, İngilizcesini `en.ts`'e ekle; `en.ts`
 * eksik anahtarda derleme hatası verir.
 */
export const tr = {
  // --- Genel
  "genel.aciklama": "Kurumsal büyük dil modeli platformu.",
  "genel.altbilgi": "KutyAI · Tüm işlemler kayıt altına alınır.",
  "genel.dil": "Dil",
  "genel.yukleniyor": "Yükleniyor",
  "genel.bildirim.kapat": "Bildirimi kapat",
  "genel.hata.istek": "İstek tamamlanamadı.",
  "genel.hata.baglanti": "Sunucuya ulaşılamadı. Bağlantınızı denetleyin.",

  // --- Uygulama kabuğu
  "kabuk.menu": "Ana menü",
  "kabuk.baglanti.sohbet": "Sohbet",
  "kabuk.baglanti.kullanim": "Kullanım",
  "kabuk.baglanti.hesap": "Hesap",
  "kabuk.oturum": "Oturum",
  "kabuk.bilinmiyor": "Bilinmiyor",
  "kabuk.cikis": "Çıkış",
  "kabuk.oturum.denetleniyor": "Oturum denetleniyor",

  // --- Rol ve durum etiketleri
  "rol.yonetici": "Yönetici",
  "rol.operator": "Operatör",
  "rol.izleyici": "İzleyici",
  "rol.son_kullanici": "Son kullanıcı",
  "durum.aktif": "Aktif",
  "durum.beklemede": "Beklemede",
  "durum.pasif": "Pasif",

  // --- Giriş
  "giris.baslik": "Giriş yap",
  "giris.aciklama": "Kurumsal hesabınızla devam edin.",
  "giris.eposta": "E-posta",
  "giris.eposta.ornek": "ad.soyad@sirket.com",
  "giris.parola": "Parola",
  "giris.hata": "Giriş yapılamadı. Lütfen tekrar deneyin.",
  "giris.dogrulama.metin": "E-posta adresinizi doğrulamak için {baglanti} gidin.",
  "giris.dogrulama.baglanti": "doğrulama sayfasına",
  "giris.parolami.unuttum": "Parolamı unuttum",
  "giris.hesap.yok": "Hesabınız yok mu?",
  "giris.kayit.ol": "Kayıt olun",

  // --- Kayıt
  "kayit.baslik": "Kayıt ol",
  "kayit.aciklama": "Kurumsal e-posta adresinizle hesap oluşturun.",
  "kayit.ad.soyad": "Ad soyad",
  "kayit.eposta": "E-posta",
  "kayit.parola": "Parola",
  "kayit.parola.yardim": "En az 8 karakter.",
  "kayit.parola.tekrar": "Parola (tekrar)",
  "kayit.buton": "Hesap oluştur",
  "kayit.parola.kisa": "Parola en az 8 karakter olmalı.",
  "kayit.parola.eslesmiyor": "Parolalar birbiriyle eşleşmiyor.",
  "kayit.hata": "Kayıt tamamlanamadı. Lütfen tekrar deneyin.",
  "kayit.basarili.dogrulama":
    "Kayıt alındı. E-posta adresinize doğrulama bağlantısı gönderildi.",
  "kayit.basarili": "Kayıt alındı. Artık giriş yapabilirsiniz.",
  "kayit.bildirim": "Hesabınız oluşturuldu.",
  "kayit.tamamlandi.baslik": "Kayıt tamamlandı",
  "kayit.gelistirme.notu":
    "Bu ortamda e-posta gönderimi tanımlı değil; doğrulamayı bağlantıyla tamamlayabilirsiniz.",
  "kayit.dogrula.dugme": "E-postamı doğrula",
  "kayit.giris.don": "Giriş sayfasına dön",
  "kayit.hesap.var": "Zaten hesabınız var mı?",
  "kayit.giris.yap": "Giriş yapın",

  // --- Hesap
  "hesap.baslik": "Hesabım",
  "hesap.aciklama": "Oturum bilgileriniz ve hesap ayrıntılarınız.",
  "hesap.yukleniyor": "Hesap bilgisi yükleniyor",
  "hesap.kullanilamiyor": "Hesap bilgisi bu sürümde kullanılamıyor.",
  "hesap.hata": "Hesap bilgisi alınamadı. Lütfen tekrar deneyin.",
  "hesap.ad.soyad": "Ad soyad",
  "hesap.eposta": "E-posta",
  "hesap.rol": "Rol",
  "hesap.durum": "Durum",
  "hesap.eposta.dogrulama": "E-posta doğrulaması",
  "hesap.dogrulandi": "Doğrulandı",
  "hesap.bekliyor": "Bekliyor",
  "hesap.kayit.tarihi": "Kayıt tarihi",
  "hesap.son.giris": "Son giriş",
  "hesap.dogrulanmadi": "E-posta adresiniz doğrulanmadı. {baglanti} gidin.",
  "hesap.dogrulama.baglanti": "Doğrulama sayfasına",

  // --- E-posta doğrulama
  "dogrula.baslik": "E-posta doğrulama",
  "dogrula.aciklama": "Doğrulama bağlantısındaki jetonu girin.",
  "dogrula.jeton": "Doğrulama jetonu",
  "dogrula.jeton.yardim": "Bağlantıdaki jeton otomatik doldurulur.",
  "dogrula.denetleniyor": "Doğrulama bağlantısı denetleniyor",
  "dogrula.basarili.baslik": "Doğrulandı",
  "dogrula.basarili.mesaj":
    "E-posta adresiniz doğrulandı. Artık giriş yapabilirsiniz.",
  "dogrula.buton": "Doğrula",
  "dogrula.hata": "Doğrulama tamamlanamadı. Lütfen tekrar deneyin.",
  "dogrula.giris.baglanti": "Giriş yapın",
  "dogrula.giris.don": "Giriş sayfasına dön",

  // --- Parola sıfırlama
  "sifre.baslik": "Parola sıfırlama",
  "sifre.aciklama":
    "E-posta ile sıfırlama bağlantısı isteyin veya elinizdeki jetonla yeni parola belirleyin.",
  "sifre.yontem": "Parola sıfırlama yöntemi",
  "sifre.sekme.istek": "Bağlantı iste",
  "sifre.sekme.sifirla": "Jetonla sıfırla",
  "sifre.istek.hata": "İstek gönderilemedi. Lütfen tekrar deneyin.",
  "sifre.sifirlama.hata": "Parola sıfırlanamadı. Lütfen tekrar deneyin.",
  "sifre.baglanti.gonder": "Sıfırlama bağlantısı gönder",
  "sifre.jeton": "Sıfırlama jetonu",
  "sifre.jeton.yardim": "Bağlantıdaki jeton otomatik doldurulur.",
  "sifre.yeni.parola": "Yeni parola",
  "sifre.yeni.parola.tekrar": "Yeni parola (tekrar)",
  "sifre.buton": "Parolayı sıfırla",
  "sifre.giris.don": "Giriş sayfasına dön",

  // --- Kullanım
  "kullanim.baslik": "Kullanım",
  "kullanim.aciklama":
    "İstek, token ve gecikme özetiniz. Yalnızca kendi kullanımınız gösterilir.",
  "kullanim.olcu.toplam_istek": "Toplam istek",
  "kullanim.olcu.toplam_token": "Toplam token",
  "kullanim.olcu.girdi_token": "Girdi token",
  "kullanim.olcu.cikti_token": "Çıktı token",
  "kullanim.olcu.ortalama_gecikme": "Ortalama gecikme (ms)",
  "kullanim.birim.token": "token",
  "kullanim.veri.yukleniyor": "Kullanım verileri yükleniyor",
  "kullanim.veri.hata": "Kullanım verileri alınamadı. Lütfen tekrar deneyin.",
  "kullanim.aralik": "Zaman aralığı",
  "kullanim.gun": "Son {gun} gün",
  "kullanim.yeniden.dene": "Yeniden dene",
  "kullanim.kota.baslik": "Kota kullanımı",
  "kullanim.kota.aciklama": "Günlük istek ve aylık token sınırlarınız.",
  "kullanim.kota.gunluk": "Günlük istek",
  "kullanim.kota.aylik": "Aylık token",
  "kullanim.kota.sinirsiz": "Sınırsız",
  "kullanim.kota.kullanim.etiket": "{etiket} kullanımı",
  "kullanim.kota.sifirlanma": "{etiket} {tarih} tarihinde sıfırlanır.",
  "kullanim.kota.gunluk.sinir": "Günlük sınır",
  "kullanim.kota.aylik.sinir": "Aylık sınır",
  "kullanim.kota.yok":
    "Hesabınız için tanımlı bir kota yok; kullanımınız sınırlandırılmıyor.",
  "kullanim.seri.baslik": "Günlük token kullanımı",
  "kullanim.seri.aciklama": "Son {gun} günde gün başına işlenen token.",
  "kullanim.seri.bos": "Bu aralıkta kayıtlı kullanım yok.",
  "kullanim.grafik.etiket":
    "Günlük token grafiği: {gun} gün, en yüksek gün {token} token",
  "kullanim.grafik.nokta": "{tarih}: {token} token",

  // --- Sohbet
  "sohbet.yeniden.dene": "Yeniden dene",
  "sohbet.bos.baslik": "Sohbete başlayın",
  "sohbet.bos.metin":
    "Seçtiğiniz modelle mesajlaşmaya başlayın. Yanıtlar yazıldıkça akış hâlinde görünür; dilediğiniz an durdurabilirsiniz.",
  "sohbet.bos.model.baslik": "Kullanılabilir model yok",
  "sohbet.bos.model.metin":
    "Sohbet için en az bir modelin {durum} durumda olması gerekir. Yöneticiniz model hazırladığında bu listeyi yenileyebilirsiniz.",
  "sohbet.bos.model.vurgu": "hazır",
  "sohbet.model.yenile": "Modelleri yenile",
  "sohbet.kod.etiket": "kod",
  "sohbet.kod.kopyala": "Kopyala",
  "sohbet.kod.kopyalandi": "Kopyalandı",
  "sohbet.liste.baslik": "Konuşmalar",
  "sohbet.liste.yeni": "Yeni sohbet",
  "sohbet.liste.ara": "Konuşmalarda ara",
  "sohbet.liste.bos": "Henüz konuşma yok.",
  "sohbet.liste.suzulmus": "{gosterilen} / {toplam} konuşma",
  "sohbet.liste.toplam": "{toplam} konuşma",
  "sohbet.liste.ilk": "İlk konuşmanızı başlatın.",
  "sohbet.liste.eslesme.yok": "Eşleşen konuşma bulunamadı.",
  "sohbet.mesaj.hazirlaniyor": "Yanıt hazırlanıyor…",
  "sohbet.mesaj.durduruldu": "Üretim durduruldu.",
  "sohbet.mesaj.hatali": "Yanıt tamamlanamadı.",
  "sohbet.mesaj.yeniden.etiket": "Yanıtı yeniden üret",
  "sohbet.mesaj.yeniden.kullanici": "Yanıtı yeniden üret",
  "sohbet.mesaj.yeniden": "Yeniden üret",
  "sohbet.model.etiket": "Model",
  "sohbet.model.secin": "Model seçin",
  "sohbet.hata.beklenmeyen":
    "Beklenmeyen bir hata oluştu. Lütfen tekrar deneyin.",
  "sohbet.hata.model.gerekli": "Sohbet için önce bir model seçin.",
  "sohbet.uretiliyor": "Yanıt üretiliyor",
  "sohbet.liste.ac": "Konuşma listesini aç",
  "sohbet.liste.kapat": "Konuşma listesini kapat",
  "sohbet.gorunum.etiket": "Konuşma",
  "sohbet.girdi.etiket": "Mesajınız",
  "sohbet.girdi.ipucu": "Mesajınızı yazın…",
  "sohbet.girdi.model.secin": "Önce bir model seçin",
  "sohbet.girdi.durdur": "Durdur",
  "sohbet.girdi.durdur.etiket": "Üretimi durdur",
  "sohbet.girdi.gonder": "Gönder",
  "sohbet.girdi.kisayol":
    "Enter ile gönder · Shift+Enter yeni satır · Esc ile üretimi durdur",
  "sohbet.akis.uretim.hata": "Yanıt üretilemedi.",
  "sohbet.akis.istek.hata": "Yanıt alınamadı. Lütfen tekrar deneyin.",
  "sohbet.akis.okunamadi": "Yanıt akışı okunamadı.",
} as const;

/** Türkçe katalog tipi; `en.ts` bu anahtarların tamamını vermek zorundadır. */
export type Sozluk = typeof tr;
export type SozlukAnahtari = keyof Sozluk;
