/**
 * Organizasyon (kiracı) sayfası metinleri — spec §2.5 / API.md §15.
 *
 * Anahtar düzeni `organizasyon.alan.alt_anahtar`; cümle içine React düğümü
 * gömülecek şablonlar `{baglanti}` ile parçalanır (`t(...).split("{baglanti}")`).
 */
export const trOrganizasyon = {
  // --- Organizasyonlar listesi
  "organizasyon.baslik": "Organizasyonlar",
  "organizasyon.aciklama":
    "Üye olduğunuz organizasyonlar; ad, durum ve üye rolleri buradan yönetilir.",
  "organizasyon.yeni": "Yeni organizasyon",
  "organizasyon.sec": "Yönet",
  "organizasyon.tablo.ad": "Ad",
  "organizasyon.tablo.slug": "Slug",
  "organizasyon.tablo.rol": "Rolünüz",
  "organizasyon.tablo.durum": "Durum",
  "organizasyon.tablo.olusturulma": "Oluşturulma",
  "organizasyon.tablo.islemler": "İşlemler",
  "organizasyon.bos.baslik": "Organizasyon bulunamadı",
  "organizasyon.bos.aciklama":
    "Üye olduğunuz bir organizasyon yok; yeni bir organizasyon oluşturabilirsiniz.",
  "organizasyon.detay.baslik": "{ad} organizasyonu",
  "organizasyon.detay.secim.ipucu": "Üyeleri yönetmek için listeden bir organizasyon seçin.",
  "organizasyon.yetki.ipucu":
    "Bu organizasyonda yönetim yetkiniz yok; yalnızca görüntüleyebilirsiniz.",

  // --- Organizasyon bilgisi (PATCH /organizasyonlar/{id})
  "organizasyon.bilgi.baslik": "Organizasyon bilgisi",
  "organizasyon.bilgi.aciklama": "Ad ve durum sahip veya yönetici tarafından güncellenir.",
  "organizasyon.bilgi.ad": "Organizasyon adı",
  "organizasyon.bilgi.durum": "Durum",
  "organizasyon.bilgi.slug.ipucu": "Slug oluşturulduktan sonra değiştirilemez.",
  "organizasyon.bilgi.kaydet": "Kaydet",
  "organizasyon.bilgi.basarili": "Organizasyon güncellendi.",
  "organizasyon.bilgi.hata.baslik": "Organizasyon güncellenemedi",
  "organizasyon.bilgi.degisiklik_yok": "Değişiklik yok.",

  // --- Yeni organizasyon (POST /organizasyonlar)
  "organizasyon.olustur.baslik": "Yeni organizasyon",
  "organizasyon.olustur.aciklama": "Oluşturan kişi otomatik olarak sahip rolüyle eklenir.",
  "organizasyon.olustur.ad": "Ad",
  "organizasyon.olustur.slug": "Slug",
  "organizasyon.olustur.slug.ipucu": "Boş bırakılırsa addan üretilir.",
  "organizasyon.olustur.gonder": "Oluştur",
  "organizasyon.olustur.basarili": "{ad} oluşturuldu; sahip rolüyle eklendiniz.",
  "organizasyon.olustur.hata.baslik": "Organizasyon oluşturulamadı",

  // --- Üyeler (GET/POST/PATCH/DELETE /organizasyonlar/{id}/uyeler)
  "organizasyon.uyeler.baslik": "Üyeler",
  "organizasyon.uyeler.aciklama":
    "Yetki kararı kiracı içindeki üyelik rolüne göre verilir (API.md §15).",
  "organizasyon.uyeler.ekle": "Üye ekle",
  "organizasyon.uyeler.bos.baslik": "Üye bulunamadı",
  "organizasyon.uyeler.bos.aciklama": "Bu organizasyona henüz üye eklenmemiş.",
  "organizasyon.uyeler.tablo.eposta": "E-posta",
  "organizasyon.uyeler.tablo.ad_soyad": "Ad soyad",
  "organizasyon.uyeler.tablo.rol": "Rol",
  "organizasyon.uyeler.tablo.durum": "Durum",
  "organizasyon.uyeler.tablo.olusturulma": "Üyelik tarihi",
  "organizasyon.uyeler.tablo.islemler": "İşlemler",
  "organizasyon.uyeler.siz": "Siz",
  "organizasyon.uyeler.son_sahip": "Son sahip",
  "organizasyon.uyeler.duzenle": "Düzenle",
  "organizasyon.uyeler.cikar": "Çıkar",
  "organizasyon.uyeler.koruma.ipucu":
    "Son sahip düşürülemez veya çıkarılamaz; kendi sahip rolünüzü de düşüremezsiniz.",

  "organizasyon.uye_ekle.baslik": "Üye ekle",
  "organizasyon.uye_ekle.aciklama": "Kayıtlı bir kullanıcıyı e-posta ile organizasyona ekleyin.",
  "organizasyon.uye_ekle.eposta.ipucu": "Kullanıcı platformda önceden kayıtlı olmalıdır.",
  "organizasyon.uye_ekle.gonder": "Ekle",
  "organizasyon.uye_ekle.basarili": "{eposta} organizasyona eklendi.",
  "organizasyon.uye_ekle.hata.baslik": "Üye eklenemedi",

  "organizasyon.uye_duzenle.baslik": "Üyeyi düzenle",
  "organizasyon.uye_duzenle.basarili": "Üyelik güncellendi.",
  "organizasyon.uye_duzenle.hata.baslik": "Üyelik güncellenemedi",
  "organizasyon.uye_duzenle.degisiklik_yok": "Değişiklik yok.",
  "organizasyon.uye_duzenle.son_sahip.ipucu":
    "Son sahip korunur: rolü düşürülemez ve durumu pasife alınamaz.",
  "organizasyon.uye_duzenle.kendini_dusurme.ipucu":
    "Kendi sahip rolünüzü düşüremezsiniz; önce başka bir üyeyi sahip yapın.",

  "organizasyon.uye_sil.baslik": "Üyeyi çıkar",
  "organizasyon.uye_sil.aciklama": "Üyelik silinir; kullanıcı hesabı ve diğer üyelikleri korunur.",
  "organizasyon.uye_sil.metin": "{baglanti} bu organizasyondan çıkarılacak.",
  "organizasyon.uye_sil.kendini.ipucu": "Kendi sahip üyeliğinizi silemezsiniz.",
  "organizasyon.uye_sil.onay": "Çıkar",
  "organizasyon.uye_sil.basarili": "{eposta} organizasyondan çıkarıldı.",
  "organizasyon.uye_sil.hata.baslik": "Üye çıkarılamadı",

  // --- Hata kodları (API.md §17)
  "organizasyon.hata.gecersiz_gecis":
    "Bu değişikliğe izin verilmiyor: son sahip düşürülemez veya silinemez, kendi sahip rolünüzü de düşüremezsiniz.",
  "organizasyon.hata.yetki_yok":
    "Bu organizasyonu yönetmek için sahip veya yönetici rolüne sahip olmalısınız.",
} as const;

export const enOrganizasyon: Record<keyof typeof trOrganizasyon, string> = {
  // --- Organizations list
  "organizasyon.baslik": "Organizations",
  "organizasyon.aciklama":
    "The organizations you belong to; manage names, status and member roles here.",
  "organizasyon.yeni": "New organization",
  "organizasyon.sec": "Manage",
  "organizasyon.tablo.ad": "Name",
  "organizasyon.tablo.slug": "Slug",
  "organizasyon.tablo.rol": "Your role",
  "organizasyon.tablo.durum": "Status",
  "organizasyon.tablo.olusturulma": "Created",
  "organizasyon.tablo.islemler": "Actions",
  "organizasyon.bos.baslik": "No organizations found",
  "organizasyon.bos.aciklama":
    "You do not belong to any organization yet; you can create a new one.",
  "organizasyon.detay.baslik": "{ad} organization",
  "organizasyon.detay.secim.ipucu": "Select an organization from the list to manage its members.",
  "organizasyon.yetki.ipucu":
    "You do not have management rights in this organization; it is read-only for you.",

  // --- Organization details (PATCH /organizasyonlar/{id})
  "organizasyon.bilgi.baslik": "Organization details",
  "organizasyon.bilgi.aciklama":
    "The name and status are updated by an owner or administrator.",
  "organizasyon.bilgi.ad": "Organization name",
  "organizasyon.bilgi.durum": "Status",
  "organizasyon.bilgi.slug.ipucu": "The slug cannot be changed once created.",
  "organizasyon.bilgi.kaydet": "Save",
  "organizasyon.bilgi.basarili": "Organization updated.",
  "organizasyon.bilgi.hata.baslik": "Could not update the organization",
  "organizasyon.bilgi.degisiklik_yok": "No changes.",

  // --- New organization (POST /organizasyonlar)
  "organizasyon.olustur.baslik": "New organization",
  "organizasyon.olustur.aciklama": "The creator is automatically added with the owner role.",
  "organizasyon.olustur.ad": "Name",
  "organizasyon.olustur.slug": "Slug",
  "organizasyon.olustur.slug.ipucu": "If left blank it is generated from the name.",
  "organizasyon.olustur.gonder": "Create",
  "organizasyon.olustur.basarili": "{ad} created; you were added with the owner role.",
  "organizasyon.olustur.hata.baslik": "Could not create the organization",

  // --- Members (GET/POST/PATCH/DELETE /organizasyonlar/{id}/uyeler)
  "organizasyon.uyeler.baslik": "Members",
  "organizasyon.uyeler.aciklama":
    "Authorization is decided by the membership role within the tenant (API.md §15).",
  "organizasyon.uyeler.ekle": "Add member",
  "organizasyon.uyeler.bos.baslik": "No members found",
  "organizasyon.uyeler.bos.aciklama": "No members have been added to this organization yet.",
  "organizasyon.uyeler.tablo.eposta": "E-mail",
  "organizasyon.uyeler.tablo.ad_soyad": "Full name",
  "organizasyon.uyeler.tablo.rol": "Role",
  "organizasyon.uyeler.tablo.durum": "Status",
  "organizasyon.uyeler.tablo.olusturulma": "Joined",
  "organizasyon.uyeler.tablo.islemler": "Actions",
  "organizasyon.uyeler.siz": "You",
  "organizasyon.uyeler.son_sahip": "Last owner",
  "organizasyon.uyeler.duzenle": "Edit",
  "organizasyon.uyeler.cikar": "Remove",
  "organizasyon.uyeler.koruma.ipucu":
    "The last owner cannot be demoted or removed, and you cannot demote your own owner role.",

  "organizasyon.uye_ekle.baslik": "Add member",
  "organizasyon.uye_ekle.aciklama": "Add an existing user to the organization by e-mail.",
  "organizasyon.uye_ekle.eposta.ipucu": "The user must already have an account.",
  "organizasyon.uye_ekle.gonder": "Add",
  "organizasyon.uye_ekle.basarili": "{eposta} was added to the organization.",
  "organizasyon.uye_ekle.hata.baslik": "Could not add the member",

  "organizasyon.uye_duzenle.baslik": "Edit member",
  "organizasyon.uye_duzenle.basarili": "Membership updated.",
  "organizasyon.uye_duzenle.hata.baslik": "Could not update the membership",
  "organizasyon.uye_duzenle.degisiklik_yok": "No changes.",
  "organizasyon.uye_duzenle.son_sahip.ipucu":
    "The last owner is protected: the role cannot be lowered and the status cannot be set to inactive.",
  "organizasyon.uye_duzenle.kendini_dusurme.ipucu":
    "You cannot demote your own owner role; make another member an owner first.",

  "organizasyon.uye_sil.baslik": "Remove member",
  "organizasyon.uye_sil.aciklama":
    "The membership is deleted; the user account and other memberships are kept.",
  "organizasyon.uye_sil.metin": "{baglanti} will be removed from this organization.",
  "organizasyon.uye_sil.kendini.ipucu": "You cannot delete your own owner membership.",
  "organizasyon.uye_sil.onay": "Remove",
  "organizasyon.uye_sil.basarili": "{eposta} was removed from the organization.",
  "organizasyon.uye_sil.hata.baslik": "Could not remove the member",

  // --- Error codes (API.md §17)
  "organizasyon.hata.gecersiz_gecis":
    "This change is not allowed: the last owner cannot be demoted or deleted, and you cannot demote your own owner role.",
  "organizasyon.hata.yetki_yok":
    "You must be an owner or administrator to manage this organization.",
};
