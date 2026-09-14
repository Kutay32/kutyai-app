"use client";

import { Marka } from "@/components/marka";
import { useDil } from "@/lib/dil";

/** Kimlik sayfalarının ortak düzeni: nötr sahne, ortalanmış tek kolon. */
export default function KimlikDuzeni({ children }: { children: React.ReactNode }) {
  const { t } = useDil();

  return (
    <div className="flex min-h-dvh flex-col items-center justify-center bg-neutral-50 px-4 py-10">
      <div className="w-full max-w-md">
        <header className="mb-6 flex flex-col items-center gap-2 text-center">
          <Marka />
          <p className="text-sm text-neutral-500">{t("genel.aciklama")}</p>
        </header>
        {children}
        <footer className="mt-6 text-center text-[13px] text-neutral-400">
          {t("genel.altbilgi")}
        </footer>
      </div>
    </div>
  );
}
