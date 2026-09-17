/**
 * SSO sayfası metinleri — spec §7 / API.md §15.
 *
 * Alan adları servislerden doğrulandı: OIDC `issuer`, `client_id`, `kapsamlar`,
 * `eposta_claim`, `ad_claim` (`sso_oidc.py`); SAML `idp_sso_url`, `sp_entity_id`,
 * `idp_imza_sertifikasi`, `eposta_ozniteligi`, `ad_ozniteligi` (`sso_saml.py`).
 * İstemci sırrı `ayarlar` içine değil ayrı `sir` alanına yazılır (şifrelenir).
 */
export const trSso = {
  // --- Sayfa
  "sso.baslik": "SSO",
  "sso.aciklama":
    "Organizasyonunuz için OIDC veya SAML 2.0 kimlik sağlayıcısı tanımlayın; kullanıcılar tek oturumla giriş yapar.",

  // --- Tablo
  "sso.yeni": "Yeni sağlayıcı",
  "sso.tablo.ad": "Ad",
  "sso.tablo.tur": "Tür",
  "sso.tablo.slug": "Slug",
  "sso.tablo.durum": "Durum",
  "sso.tablo.sir": "Sır",
  "sso.tablo.olusturulma": "Oluşturulma",
  "sso.tablo.islemler": "İşlemler",
  "sso.bos.baslik": "SSO sağlayıcısı yok",
  "sso.bos.aciklama":
    "Tanımlı bir sağlayıcı yok; OIDC veya SAML 2.0 sağlayıcısı ekleyerek başlayın.",
  "sso.duzenle": "Düzenle",
  "sso.sil": "Sil",
  "sso.durum.etkin": "Etkin",
  "sso.durum.kapali": "Kapalı",
  "sso.sir.tanimli": "Tanımlı",
  "sso.sir.tanimsiz": "Tanımsız",
  "sso.etkin.anahtar": "Etkin",

  // --- Giriş adresi
  "sso.giris_yolu": "Giriş adresi",
  "sso.giris_yolu.ipucu":
    "Bu adresi paylaşarak kullanıcıların SSO ile giriş yapmasını sağlayın; kimlik doğrulayıcıda dönüş adresi olarak ACS adresini kullanın.",
  "sso.kopyala": "Kopyala",
  "sso.kopyalandi": "Giriş adresi kopyalandı.",
  "sso.kopyalanamadi": "Giriş adresi kopyalanamadı.",
  "sso.giris.organizasyon_yok":
    "Aktif organizasyon çözülemediği için giriş adresi gösterilemiyor.",

  // --- Tür
  "sso.tur.oidc": "OIDC",
  "sso.tur.saml": "SAML 2.0",
  "sso.tur.ipucu":
    "OIDC için keşif belgesi (issuer) ve istemci bilgileri, SAML için IdP SSO adresi ve imza sertifikası gerekir.",

  // --- Yeni sağlayıcı (POST /sso/saglayicilar)
  "sso.olustur.baslik": "Yeni SSO sağlayıcısı",
  "sso.olustur.aciklama": "Sağlayıcı türüne göre alanları doldurun; slug addan üretilir.",
  "sso.olustur.gonder": "Oluştur",
  "sso.olustur.basarili": "{ad} sağlayıcısı oluşturuldu.",
  "sso.olustur.hata.baslik": "Sağlayıcı oluşturulamadı",
  "sso.ad": "Ad",
  "sso.ad.zorunlu": "Ad zorunludur.",
  "sso.slug": "Slug",
  "sso.slug.ipucu": "Boş bırakılırsa addan üretilir.",
  "sso.olustur.etkin.ipucu": "Kapalıyken sağlayıcı ile giriş başlatılamaz.",

  // --- Düzenleme (PATCH /sso/saglayicilar/{id})
  "sso.duzenle.baslik": "{ad} sağlayıcısını düzenle",
  "sso.duzenle.sir.ipucu": "Boş bırakılırsa mevcut sır korunur.",
  "sso.duzenle.basarili": "Sağlayıcı güncellendi.",
  "sso.duzenle.hata.baslik": "Sağlayıcı güncellenemedi",
  "sso.duzenle.degisiklik_yok": "Değişiklik yok.",
  "sso.duzenle.sir.tanimli.ipucu":
    "Bu sağlayıcı için sır kayıtlı; gizlilik gereği görüntülenmez, yalnız üzerine yazılabilir.",

  // --- Silme (DELETE /sso/saglayicilar/{id})
  "sso.sil.baslik": "Sağlayıcıyı sil",
  "sso.sil.aciklama": "Sağlayıcı silinir; bu sağlayıcıyla eşlenmiş kimlikler de kaldırılır.",
  "sso.sil.metin": "{baglanti} sağlayıcısı silinecek.",
  "sso.sil.onay": "Sil",
  "sso.sil.basarili": "{ad} sağlayıcısı silindi.",
  "sso.sil.hata.baslik": "Sağlayıcı silinemedi",

  // --- İstemci sırrı
  "sso.sir": "İstemci sırrı (client secret)",
  "sso.sir.uyari": "Sır şifrelenerek saklanır ve bir daha görüntülenmez.",

  // --- OIDC alanları
  "sso.alan.issuer": "Issuer",
  "sso.alan.client_id": "Client ID",
  "sso.alan.kapsamlar": "Kapsamlar",
  "sso.alan.eposta_claim": "E-posta claim'i",
  "sso.alan.ad_claim": "Ad claim'i",
  "sso.ipucu.issuer":
    "Sağlayıcının kök adresi; keşif belgesi kök adresin /.well-known/openid-configuration yolundan okunur.",
  "sso.ipucu.client_id": "Kimlik sağlayıcıda kayıtlı istemci kimliği.",
  "sso.ipucu.kapsamlar": "Boş bırakılırsa openid email profile kullanılır.",
  "sso.ipucu.eposta_claim": "Boş bırakılırsa email, yoksa preferred_username okunur.",
  "sso.ipucu.ad_claim": "Boş bırakılırsa name okunur.",

  // --- SAML alanları
  "sso.alan.idp_sso_url": "IdP SSO adresi",
  "sso.alan.sp_entity_id": "SP entity ID",
  "sso.alan.idp_imza_sertifikasi": "IdP imza sertifikası",
  "sso.alan.eposta_ozniteligi": "E-posta özniteliği",
  "sso.alan.ad_ozniteligi": "Ad özniteliği",
  "sso.ipucu.idp_sso_url": "AuthnRequest bu adrese yönlendirilir.",
  "sso.ipucu.sp_entity_id": "Boş bırakılırsa ACS adresi kullanılır.",
  "sso.ipucu.idp_imza_sertifikasi":
    "PEM veya çıplak base64 sertifika; imza doğrulaması için zorunludur.",
  "sso.ipucu.eposta_ozniteligi": "Boş bırakılırsa NameID içindeki e-posta kullanılır.",
  "sso.ipucu.ad_ozniteligi": "Boş bırakılırsa ad alanı çıkarılmaz.",
  "sso.sertifika.ipucu": "Çok satırlı sertifika metnini buraya yapıştırın.",

  // --- Hata kodları (API.md §17)
  "sso.hata.yapilandirilmamis":
    "Sağlayıcı eksik yapılandırılmış; gerekli alanları doldurup tekrar deneyin.",
  "sso.hata.yetki_yok":
    "SSO sağlayıcılarını yönetmek için bu organizasyonda sahip veya yönetici olmalısınız.",
} as const;

export const enSso: Record<keyof typeof trSso, string> = {
  // --- Page
  "sso.baslik": "SSO",
  "sso.aciklama":
    "Define an OIDC or SAML 2.0 identity provider for your organization so users can sign in with single sign-on.",

  // --- Table
  "sso.yeni": "New provider",
  "sso.tablo.ad": "Name",
  "sso.tablo.tur": "Type",
  "sso.tablo.slug": "Slug",
  "sso.tablo.durum": "Status",
  "sso.tablo.sir": "Secret",
  "sso.tablo.olusturulma": "Created",
  "sso.tablo.islemler": "Actions",
  "sso.bos.baslik": "No SSO provider",
  "sso.bos.aciklama":
    "No provider is defined yet; start by adding an OIDC or SAML 2.0 provider.",
  "sso.duzenle": "Edit",
  "sso.sil": "Delete",
  "sso.durum.etkin": "Enabled",
  "sso.durum.kapali": "Disabled",
  "sso.sir.tanimli": "Set",
  "sso.sir.tanimsiz": "Not set",
  "sso.etkin.anahtar": "Enabled",

  // --- Sign-in address
  "sso.giris_yolu": "Sign-in address",
  "sso.giris_yolu.ipucu":
    "Share this address so users can sign in with SSO; use the ACS address as the callback in the identity provider.",
  "sso.kopyala": "Copy",
  "sso.kopyalandi": "Sign-in address copied.",
  "sso.kopyalanamadi": "Could not copy the sign-in address.",
  "sso.giris.organizasyon_yok":
    "The active organization could not be resolved, so the sign-in address cannot be shown.",

  // --- Type
  "sso.tur.oidc": "OIDC",
  "sso.tur.saml": "SAML 2.0",
  "sso.tur.ipucu":
    "OIDC needs a discovery issuer and client credentials; SAML needs the IdP SSO address and a signing certificate.",

  // --- New provider (POST /sso/saglayicilar)
  "sso.olustur.baslik": "New SSO provider",
  "sso.olustur.aciklama":
    "Fill in the fields for the provider type; the slug is generated from the name.",
  "sso.olustur.gonder": "Create",
  "sso.olustur.basarili": "{ad} provider created.",
  "sso.olustur.hata.baslik": "Could not create the provider",
  "sso.ad": "Name",
  "sso.ad.zorunlu": "The name is required.",
  "sso.slug": "Slug",
  "sso.slug.ipucu": "If left blank it is generated from the name.",
  "sso.olustur.etkin.ipucu": "While disabled, sign-in cannot be started with this provider.",

  // --- Editing (PATCH /sso/saglayicilar/{id})
  "sso.duzenle.baslik": "Edit the {ad} provider",
  "sso.duzenle.sir.ipucu": "If left blank the current secret is kept.",
  "sso.duzenle.basarili": "Provider updated.",
  "sso.duzenle.hata.baslik": "Could not update the provider",
  "sso.duzenle.degisiklik_yok": "No changes.",
  "sso.duzenle.sir.tanimli.ipucu":
    "A secret is stored for this provider; for security it is never displayed and can only be overwritten.",

  // --- Deleting (DELETE /sso/saglayicilar/{id})
  "sso.sil.baslik": "Delete provider",
  "sso.sil.aciklama": "The provider is deleted; linked identities are removed as well.",
  "sso.sil.metin": "The {baglanti} provider will be deleted.",
  "sso.sil.onay": "Delete",
  "sso.sil.basarili": "{ad} provider deleted.",
  "sso.sil.hata.baslik": "Could not delete the provider",

  // --- Client secret
  "sso.sir": "Client secret",
  "sso.sir.uyari": "The secret is stored encrypted and never shown again.",

  // --- OIDC fields
  "sso.alan.issuer": "Issuer",
  "sso.alan.client_id": "Client ID",
  "sso.alan.kapsamlar": "Scopes",
  "sso.alan.eposta_claim": "E-mail claim",
  "sso.alan.ad_claim": "Name claim",
  "sso.ipucu.issuer":
    "The provider's base address; the discovery document is read from the /.well-known/openid-configuration path of the base address.",
  "sso.ipucu.client_id": "The client identifier registered with the identity provider.",
  "sso.ipucu.kapsamlar": "If left blank, openid email profile is used.",
  "sso.ipucu.eposta_claim": "If left blank, email is read, then preferred_username.",
  "sso.ipucu.ad_claim": "If left blank, name is read.",

  // --- SAML fields
  "sso.alan.idp_sso_url": "IdP SSO address",
  "sso.alan.sp_entity_id": "SP entity ID",
  "sso.alan.idp_imza_sertifikasi": "IdP signing certificate",
  "sso.alan.eposta_ozniteligi": "E-mail attribute",
  "sso.alan.ad_ozniteligi": "Name attribute",
  "sso.ipucu.idp_sso_url": "The AuthnRequest is redirected to this address.",
  "sso.ipucu.sp_entity_id": "If left blank, the ACS address is used.",
  "sso.ipucu.idp_imza_sertifikasi":
    "PEM or bare base64 certificate; required for signature verification.",
  "sso.ipucu.eposta_ozniteligi": "If left blank, the e-mail inside NameID is used.",
  "sso.ipucu.ad_ozniteligi": "If left blank, no name field is extracted.",
  "sso.sertifika.ipucu": "Paste the multi-line certificate text here.",

  // --- Error codes (API.md §17)
  "sso.hata.yapilandirilmamis":
    "The provider is misconfigured; fill in the required fields and try again.",
  "sso.hata.yetki_yok":
    "You must be an owner or administrator in this organization to manage SSO providers.",
};
