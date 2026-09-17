/**
 * Faturalama sayfası metinleri — spec §6 / API.md §15, §17.
 *
 * Abonelik, plan ve fatura durum etiketleri burada tutulur; fatura tutarları
 * sunucudan biçimlenmiş gelir (`aylik_fiyat`, `tutar`).
 */
export const trFaturalama = {
  // --- Sayfa
  "faturalama.baslik": "Faturalama",
  "faturalama.aciklama":
    "Aboneliği yönetin, planları karşılaştırın ve fatura kayıtlarını görüntüleyin.",

  // --- Abonelik
  "faturalama.abonelik.baslik": "Abonelik",
  "faturalama.abonelik.aciklama": "Aktif organizasyonun plan, dönem ve erişim durumu.",
  "faturalama.abonelik.yok": "Etkin abonelik yok",
  "faturalama.abonelik.yok.aciklama":
    "Aşağıdaki planlardan birini seçerek aboneliği başlatın; plan limitleri organizasyon kotasına uygulanır.",
  "faturalama.abonelik.plan": "Plan",
  "faturalama.abonelik.durum": "Durum",
  "faturalama.abonelik.donem": "Dönem",
  "faturalama.abonelik.donem_araligi": "{baslangic} — {bitis}",
  "faturalama.abonelik.saglayici": "Ödeme sağlayıcısı",
  "faturalama.abonelik.erisim": "Erişim",
  "faturalama.abonelik.erisim.var": "Açık",
  "faturalama.abonelik.erisim.yok": "Kısıtlı",
  "faturalama.abonelik.erisim.ipucu":
    "Gecikmiş veya iptal edilmiş abonelikte sohbet uçları 402 abonelik_gecikmis döner.",
  "faturalama.abonelik.durum.deneme": "Deneme",
  "faturalama.abonelik.durum.aktif": "Aktif",
  "faturalama.abonelik.durum.gecikmis": "Gecikmiş",
  "faturalama.abonelik.durum.iptal": "İptal",
  "faturalama.abonelik.iptal": "Aboneliği iptal et",
  "faturalama.abonelik.iptal.baslik": "Aboneliği iptal et",
  "faturalama.abonelik.iptal.aciklama": "Abonelik iptal edilir ve erişim kısıtlanır.",
  "faturalama.abonelik.iptal.metin": "{baglanti} planına ait abonelik iptal edilecek.",
  "faturalama.abonelik.iptal.onay": "İptal et",
  "faturalama.abonelik.iptal.basarili": "Abonelik iptal edildi.",
  "faturalama.abonelik.iptal.hata.baslik": "Abonelik iptal edilemedi",

  // --- Planlar
  "faturalama.planlar.baslik": "Planlar",
  "faturalama.planlar.aciklama":
    "Plan seçildiğinde organizasyon kotası plan limitleriyle güncellenir.",
  "faturalama.planlar.bos": "Etkin plan bulunamadı.",
  "faturalama.plan.dahil_istek": "Günlük istek",
  "faturalama.plan.dahil_token": "Aylık token",
  "faturalama.plan.sinirsiz": "Sınırsız",
  "faturalama.plan.sec": "Bu planı seç",
  "faturalama.plan.secili": "Geçerli plan",

  // --- Abone olma (POST /faturalama/abonelik)
  "faturalama.abone.baslik": "{ad} planına abone ol",
  "faturalama.abone.aciklama": "Dönem uzunluğu ve ilk fatura tutarı aşağıda gösterilir.",
  "faturalama.abone.donem": "Dönem (gün)",
  "faturalama.abone.fatura": "İlk fatura",
  "faturalama.abone.gonder": "Aboneliği başlat",
  "faturalama.abone.basarili": "Abonelik başlatıldı.",
  "faturalama.abone.odeme": "Ödeme sayfasına git",
  "faturalama.abone.odeme.ipucu": "Ödeme bağlantısı yeni sekmede açılır.",
  "faturalama.abone.hata.baslik": "Abonelik başlatılamadı",

  // --- Faturalar
  "faturalama.faturalar.baslik": "Faturalar",
  "faturalama.faturalar.aciklama": "Aktif organizasyonun fatura kayıtları (en yeni önce).",
  "faturalama.faturalar.bos.baslik": "Fatura bulunamadı",
  "faturalama.faturalar.bos.aciklama": "Abonelik başlatıldığında ilk fatura burada görünür.",
  "faturalama.fatura.no": "Fatura",
  "faturalama.fatura.tutar": "Tutar",
  "faturalama.fatura.durum": "Durum",
  "faturalama.fatura.olusturulma": "Oluşturulma",
  "faturalama.fatura.odeme_tarihi": "Ödeme tarihi",
  "faturalama.fatura.islemler": "İşlemler",
  "faturalama.fatura.kalemler": "Kalemler",
  "faturalama.fatura.kalemler_yok": "Fatura kalemi kayıtlı değil.",
  "faturalama.fatura.durum.taslak": "Taslak",
  "faturalama.fatura.durum.odendi": "Ödendi",
  "faturalama.fatura.durum.basarisiz": "Başarısız",
  "faturalama.fatura.durum.iade": "İade",
  "faturalama.fatura.detay": "Detay",
  "faturalama.fatura.detay.baslik": "{id} numaralı fatura",
  "faturalama.fatura.odendi": "Ödendi olarak işaretle",
  "faturalama.fatura.odendi.baslik": "Faturayı ödendi olarak işaretle",
  "faturalama.fatura.odendi.aciklama":
    "Elle tahsilat yalnızca yerel ödeme sağlayıcısında kullanılabilir.",
  "faturalama.fatura.odendi.onay": "Ödendi işaretle",
  "faturalama.fatura.odendi.basarili": "Fatura ödendi olarak işaretlendi.",
  "faturalama.fatura.odendi.hata.baslik": "Fatura işaretlenemedi",
  "faturalama.fatura.odeme": "Ödeme bağlantısı oluştur",
  "faturalama.fatura.odeme.basarili": "Ödeme oturumu oluşturuldu.",
  "faturalama.fatura.odeme.baglanti_yok": "Ödeme sağlayıcısı bağlantı döndürmedi.",
  "faturalama.fatura.odeme.hata.baslik": "Ödeme oturumu oluşturulamadı",
  "faturalama.fatura.odeme.ipucu": "Ödeme bağlantısı yeni sekmede açılır.",

  // --- Hata kodları (API.md §17)
  "faturalama.hata.plan_bulunamadi": "Seçilen plan bulunamadı veya etkin değil.",
  "faturalama.hata.abonelik_yok": "İptal edilecek etkin abonelik yok.",
  "faturalama.hata.odeme_saglayici_yok":
    "Ödeme sağlayıcısı yapılandırılmamış; sunucu ayarlarını kontrol edin.",
  "faturalama.hata.yetki_yok":
    "Faturalama işlemleri için bu organizasyonda sahip veya yönetici olmalısınız.",
} as const;

export const enFaturalama: Record<keyof typeof trFaturalama, string> = {
  // --- Page
  "faturalama.baslik": "Billing",
  "faturalama.aciklama":
    "Manage the subscription, compare plans and review invoice records.",

  // --- Subscription
  "faturalama.abonelik.baslik": "Subscription",
  "faturalama.abonelik.aciklama":
    "Plan, period and access status of the active organization.",
  "faturalama.abonelik.yok": "No active subscription",
  "faturalama.abonelik.yok.aciklama":
    "Start a subscription by choosing one of the plans below; plan limits are applied to the organization quota.",
  "faturalama.abonelik.plan": "Plan",
  "faturalama.abonelik.durum": "Status",
  "faturalama.abonelik.donem": "Period",
  "faturalama.abonelik.donem_araligi": "{baslangic} — {bitis}",
  "faturalama.abonelik.saglayici": "Payment provider",
  "faturalama.abonelik.erisim": "Access",
  "faturalama.abonelik.erisim.var": "Open",
  "faturalama.abonelik.erisim.yok": "Restricted",
  "faturalama.abonelik.erisim.ipucu":
    "With an overdue or cancelled subscription the chat endpoints return 402 abonelik_gecikmis.",
  "faturalama.abonelik.durum.deneme": "Trial",
  "faturalama.abonelik.durum.aktif": "Active",
  "faturalama.abonelik.durum.gecikmis": "Overdue",
  "faturalama.abonelik.durum.iptal": "Cancelled",
  "faturalama.abonelik.iptal": "Cancel subscription",
  "faturalama.abonelik.iptal.baslik": "Cancel subscription",
  "faturalama.abonelik.iptal.aciklama":
    "The subscription is cancelled and access is restricted.",
  "faturalama.abonelik.iptal.metin": "The subscription for the {baglanti} plan will be cancelled.",
  "faturalama.abonelik.iptal.onay": "Cancel",
  "faturalama.abonelik.iptal.basarili": "Subscription cancelled.",
  "faturalama.abonelik.iptal.hata.baslik": "Could not cancel the subscription",

  // --- Plans
  "faturalama.planlar.baslik": "Plans",
  "faturalama.planlar.aciklama":
    "When a plan is chosen, the organization quota is updated with the plan limits.",
  "faturalama.planlar.bos": "No active plan found.",
  "faturalama.plan.dahil_istek": "Daily requests",
  "faturalama.plan.dahil_token": "Monthly tokens",
  "faturalama.plan.sinirsiz": "Unlimited",
  "faturalama.plan.sec": "Choose this plan",
  "faturalama.plan.secili": "Current plan",

  // --- Subscribe (POST /faturalama/abonelik)
  "faturalama.abone.baslik": "Subscribe to the {ad} plan",
  "faturalama.abone.aciklama":
    "The period length and the first invoice amount are shown below.",
  "faturalama.abone.donem": "Period (days)",
  "faturalama.abone.fatura": "First invoice",
  "faturalama.abone.gonder": "Start subscription",
  "faturalama.abone.basarili": "Subscription started.",
  "faturalama.abone.odeme": "Go to the payment page",
  "faturalama.abone.odeme.ipucu": "The payment link opens in a new tab.",
  "faturalama.abone.hata.baslik": "Could not start the subscription",

  // --- Invoices
  "faturalama.faturalar.baslik": "Invoices",
  "faturalama.faturalar.aciklama": "Invoice records of the active organization (newest first).",
  "faturalama.faturalar.bos.baslik": "No invoices found",
  "faturalama.faturalar.bos.aciklama":
    "The first invoice appears here once a subscription is started.",
  "faturalama.fatura.no": "Invoice",
  "faturalama.fatura.tutar": "Amount",
  "faturalama.fatura.durum": "Status",
  "faturalama.fatura.olusturulma": "Created",
  "faturalama.fatura.odeme_tarihi": "Paid at",
  "faturalama.fatura.islemler": "Actions",
  "faturalama.fatura.kalemler": "Line items",
  "faturalama.fatura.kalemler_yok": "No line items recorded for this invoice.",
  "faturalama.fatura.durum.taslak": "Draft",
  "faturalama.fatura.durum.odendi": "Paid",
  "faturalama.fatura.durum.basarisiz": "Failed",
  "faturalama.fatura.durum.iade": "Refunded",
  "faturalama.fatura.detay": "Details",
  "faturalama.fatura.detay.baslik": "Invoice {id}",
  "faturalama.fatura.odendi": "Mark as paid",
  "faturalama.fatura.odendi.baslik": "Mark the invoice as paid",
  "faturalama.fatura.odendi.aciklama":
    "Manual collection is available only with the local payment provider.",
  "faturalama.fatura.odendi.onay": "Mark as paid",
  "faturalama.fatura.odendi.basarili": "The invoice was marked as paid.",
  "faturalama.fatura.odendi.hata.baslik": "Could not mark the invoice",
  "faturalama.fatura.odeme": "Create a payment link",
  "faturalama.fatura.odeme.basarili": "Payment session created.",
  "faturalama.fatura.odeme.baglanti_yok": "The payment provider returned no link.",
  "faturalama.fatura.odeme.hata.baslik": "Could not create the payment session",
  "faturalama.fatura.odeme.ipucu": "The payment link opens in a new tab.",

  // --- Error codes (API.md §17)
  "faturalama.hata.plan_bulunamadi": "The selected plan was not found or is inactive.",
  "faturalama.hata.abonelik_yok": "There is no active subscription to cancel.",
  "faturalama.hata.odeme_saglayici_yok":
    "The payment provider is not configured; check the server settings.",
  "faturalama.hata.yetki_yok":
    "You must be an owner or administrator in this organization for billing operations.",
};
