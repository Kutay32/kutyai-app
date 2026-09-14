import type { Sozluk } from "./tr";

/**
 * İngilizce mesaj kataloğu (spec §10.2).
 *
 * Tip `Record<keyof Sozluk, string>` olduğu için `tr.ts`'te olup burada olmayan
 * anahtar derleme hatası verir; `npm run tip-kontrol` bunu yakalar.
 */
export const en: Record<keyof Sozluk, string> = {
  // --- General
  "genel.aciklama": "Enterprise large language model platform.",
  "genel.altbilgi": "KutyAI · All actions are logged.",
  "genel.dil": "Language",
  "genel.yukleniyor": "Loading",
  "genel.bildirim.kapat": "Close notification",
  "genel.hata.istek": "Request could not be completed.",
  "genel.hata.baglanti": "Could not reach the server. Check your connection.",

  // --- Application shell
  "kabuk.menu": "Main menu",
  "kabuk.baglanti.sohbet": "Chat",
  "kabuk.baglanti.kullanim": "Usage",
  "kabuk.baglanti.hesap": "Account",
  "kabuk.oturum": "Session",
  "kabuk.bilinmiyor": "Unknown",
  "kabuk.cikis": "Sign out",
  "kabuk.oturum.denetleniyor": "Checking session",

  // --- Role and status labels
  "rol.yonetici": "Administrator",
  "rol.operator": "Operator",
  "rol.izleyici": "Viewer",
  "rol.son_kullanici": "End user",
  "durum.aktif": "Active",
  "durum.beklemede": "Pending",
  "durum.pasif": "Inactive",

  // --- Sign in
  "giris.baslik": "Sign in",
  "giris.aciklama": "Continue with your corporate account.",
  "giris.eposta": "E-mail",
  "giris.eposta.ornek": "name.surname@company.com",
  "giris.parola": "Password",
  "giris.hata": "Could not sign in. Please try again.",
  "giris.dogrulama.metin": "To verify your e-mail address, go to {baglanti}.",
  "giris.dogrulama.baglanti": "the verification page",
  "giris.parolami.unuttum": "Forgot my password",
  "giris.hesap.yok": "Don't have an account?",
  "giris.kayit.ol": "Sign up",

  // --- Sign up
  "kayit.baslik": "Sign up",
  "kayit.aciklama": "Create an account with your corporate e-mail address.",
  "kayit.ad.soyad": "Full name",
  "kayit.eposta": "E-mail",
  "kayit.parola": "Password",
  "kayit.parola.yardim": "At least 8 characters.",
  "kayit.parola.tekrar": "Password (repeat)",
  "kayit.buton": "Create account",
  "kayit.parola.kisa": "Password must be at least 8 characters.",
  "kayit.parola.eslesmiyor": "Passwords do not match.",
  "kayit.hata": "Could not complete sign-up. Please try again.",
  "kayit.basarili.dogrulama":
    "Sign-up received. A verification link has been sent to your e-mail address.",
  "kayit.basarili": "Sign-up received. You can sign in now.",
  "kayit.bildirim": "Your account has been created.",
  "kayit.tamamlandi.baslik": "Sign-up complete",
  "kayit.gelistirme.notu":
    "E-mail delivery is not configured in this environment; you can complete verification via the link.",
  "kayit.dogrula.dugme": "Verify my e-mail",
  "kayit.giris.don": "Back to sign-in",
  "kayit.hesap.var": "Already have an account?",
  "kayit.giris.yap": "Sign in",

  // --- Account
  "hesap.baslik": "My account",
  "hesap.aciklama": "Your session and account details.",
  "hesap.yukleniyor": "Loading account information",
  "hesap.kullanilamiyor": "Account information is unavailable in this version.",
  "hesap.hata": "Could not load account information. Please try again.",
  "hesap.ad.soyad": "Full name",
  "hesap.eposta": "E-mail",
  "hesap.rol": "Role",
  "hesap.durum": "Status",
  "hesap.eposta.dogrulama": "E-mail verification",
  "hesap.dogrulandi": "Verified",
  "hesap.bekliyor": "Pending",
  "hesap.kayit.tarihi": "Registered on",
  "hesap.son.giris": "Last sign-in",
  "hesap.dogrulanmadi": "Your e-mail address is not verified. Go to {baglanti}.",
  "hesap.dogrulama.baglanti": "the verification page",

  // --- E-mail verification
  "dogrula.baslik": "E-mail verification",
  "dogrula.aciklama": "Enter the token from the verification link.",
  "dogrula.jeton": "Verification token",
  "dogrula.jeton.yardim": "The token from the link is filled in automatically.",
  "dogrula.denetleniyor": "Checking the verification link",
  "dogrula.basarili.baslik": "Verified",
  "dogrula.basarili.mesaj":
    "Your e-mail address is verified. You can sign in now.",
  "dogrula.buton": "Verify",
  "dogrula.hata": "Verification could not be completed. Please try again.",
  "dogrula.giris.baglanti": "Sign in",
  "dogrula.giris.don": "Back to sign-in",

  // --- Password reset
  "sifre.baslik": "Password reset",
  "sifre.aciklama":
    "Request a reset link by e-mail or set a new password with the token you have.",
  "sifre.yontem": "Password reset method",
  "sifre.sekme.istek": "Request link",
  "sifre.sekme.sifirla": "Reset with token",
  "sifre.istek.hata": "The request could not be sent. Please try again.",
  "sifre.sifirlama.hata": "Password could not be reset. Please try again.",
  "sifre.baglanti.gonder": "Send reset link",
  "sifre.jeton": "Reset token",
  "sifre.jeton.yardim": "The token from the link is filled in automatically.",
  "sifre.yeni.parola": "New password",
  "sifre.yeni.parola.tekrar": "New password (repeat)",
  "sifre.buton": "Reset password",
  "sifre.giris.don": "Back to sign-in",

  // --- Usage
  "kullanim.baslik": "Usage",
  "kullanim.aciklama":
    "A summary of your requests, tokens and latency. Only your own usage is shown.",
  "kullanim.olcu.toplam_istek": "Total requests",
  "kullanim.olcu.toplam_token": "Total tokens",
  "kullanim.olcu.girdi_token": "Input tokens",
  "kullanim.olcu.cikti_token": "Output tokens",
  "kullanim.olcu.ortalama_gecikme": "Average latency (ms)",
  "kullanim.birim.token": "token",
  "kullanim.veri.yukleniyor": "Loading usage data",
  "kullanim.veri.hata": "Could not load usage data. Please try again.",
  "kullanim.aralik": "Time range",
  "kullanim.gun": "Last {gun} days",
  "kullanim.yeniden.dene": "Try again",
  "kullanim.kota.baslik": "Quota usage",
  "kullanim.kota.aciklama": "Your daily request and monthly token limits.",
  "kullanim.kota.gunluk": "Daily requests",
  "kullanim.kota.aylik": "Monthly tokens",
  "kullanim.kota.sinirsiz": "Unlimited",
  "kullanim.kota.kullanim.etiket": "{etiket} usage",
  "kullanim.kota.sifirlanma": "{etiket} resets on {tarih}.",
  "kullanim.kota.gunluk.sinir": "Daily limit",
  "kullanim.kota.aylik.sinir": "Monthly limit",
  "kullanim.kota.yok":
    "No quota is defined for your account; your usage is not limited.",
  "kullanim.seri.baslik": "Daily token usage",
  "kullanim.seri.aciklama": "Tokens processed per day over the last {gun} days.",
  "kullanim.seri.bos": "No usage recorded in this range.",
  "kullanim.grafik.etiket":
    "Daily token chart: {gun} days, highest day {token} tokens",
  "kullanim.grafik.nokta": "{tarih}: {token} tokens",

  // --- Chat
  "sohbet.yeniden.dene": "Try again",
  "sohbet.bos.baslik": "Start chatting",
  "sohbet.bos.metin":
    "Start messaging with the model you selected. Replies appear as a stream while they are written; you can stop at any time.",
  "sohbet.bos.model.baslik": "No model available",
  "sohbet.bos.model.metin":
    "At least one model must be {durum} for chat. You can refresh this list once your administrator prepares a model.",
  "sohbet.bos.model.vurgu": "ready",
  "sohbet.model.yenile": "Refresh models",
  "sohbet.kod.etiket": "code",
  "sohbet.kod.kopyala": "Copy",
  "sohbet.kod.kopyalandi": "Copied",
  "sohbet.liste.baslik": "Conversations",
  "sohbet.liste.yeni": "New chat",
  "sohbet.liste.ara": "Search conversations",
  "sohbet.liste.bos": "No conversations yet.",
  "sohbet.liste.suzulmus": "{gosterilen} / {toplam} conversations",
  "sohbet.liste.toplam": "{toplam} conversations",
  "sohbet.liste.ilk": "Start your first conversation.",
  "sohbet.liste.eslesme.yok": "No matching conversation found.",
  "sohbet.mesaj.hazirlaniyor": "Preparing a reply…",
  "sohbet.mesaj.durduruldu": "Generation stopped.",
  "sohbet.mesaj.hatali": "The reply could not be completed.",
  "sohbet.mesaj.yeniden.etiket": "Regenerate reply",
  "sohbet.mesaj.yeniden.kullanici": "Regenerate reply",
  "sohbet.mesaj.yeniden": "Regenerate",
  "sohbet.model.etiket": "Model",
  "sohbet.model.secin": "Select a model",
  "sohbet.hata.beklenmeyen":
    "An unexpected error occurred. Please try again.",
  "sohbet.hata.model.gerekli": "Select a model before chatting.",
  "sohbet.uretiliyor": "Generating a reply",
  "sohbet.liste.ac": "Open the conversation list",
  "sohbet.liste.kapat": "Close the conversation list",
  "sohbet.gorunum.etiket": "Conversation",
  "sohbet.girdi.etiket": "Your message",
  "sohbet.girdi.ipucu": "Type your message…",
  "sohbet.girdi.model.secin": "Select a model first",
  "sohbet.girdi.durdur": "Stop",
  "sohbet.girdi.durdur.etiket": "Stop generation",
  "sohbet.girdi.gonder": "Send",
  "sohbet.girdi.kisayol":
    "Enter to send · Shift+Enter for a new line · Esc to stop generation",
  "sohbet.akis.uretim.hata": "The reply could not be generated.",
  "sohbet.akis.istek.hata": "The reply could not be received. Please try again.",
  "sohbet.akis.okunamadi": "The reply stream could not be read.",
};
