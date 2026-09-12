/** Form denetimleri ve odak halkaları için ortak sınıflar. */

/** Kenarlık-odaklı odak göstergesi (tasarım dili: `focus:border-neutral-900 focus:ring-0`). */
export const FOCUS_RING = "focus:border-neutral-900 focus:outline-none focus:ring-0";

/** Metin alanları, seçim kutuları ve metin kutuları için ortak gövde. */
export const FIELD_CONTROL =
  "w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 placeholder:text-neutral-400 transition-colors focus:border-neutral-900 focus:outline-none focus:ring-0 disabled:cursor-not-allowed disabled:bg-neutral-100 disabled:text-neutral-500";

/** Doğrulama hatası taşıyan denetimlerin kenarlığı. */
export const FIELD_INVALID =
  "border-rose-500 focus:border-rose-600 aria-invalid:border-rose-500 aria-invalid:focus:border-rose-600";
