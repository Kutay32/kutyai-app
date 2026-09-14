import type { Metadata } from "next";
import { Geist, Instrument_Serif } from "next/font/google";

import "./globals.css";
import { ToastProvider } from "@/components/ui/toast";
import { DilSaglayici } from "@/lib/dil";
import { ceviri } from "@/lib/sozluk";
import { dilOku } from "@/lib/sunucu-dil";

const geist = Geist({
  subsets: ["latin", "latin-ext"],
  variable: "--font-geist",
  display: "swap",
});

const instrumentSerif = Instrument_Serif({
  subsets: ["latin", "latin-ext"],
  weight: "400",
  variable: "--font-instrument-serif",
  display: "swap",
});

export async function generateMetadata(): Promise<Metadata> {
  const dil = await dilOku();
  return {
    title: { default: ceviri("genel.baslik", dil), template: "%s · KutyAI" },
    description: ceviri("genel.aciklama", dil),
  };
}

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const dil = await dilOku();

  return (
    <html lang={dil} className={`${geist.variable} ${instrumentSerif.variable}`}>
      <body>
        <DilSaglayici baslangicDili={dil}>
          <ToastProvider>{children}</ToastProvider>
        </DilSaglayici>
      </body>
    </html>
  );
}
