import type { Metadata } from "next";
import { Geist, Geist_Mono, Instrument_Serif } from "next/font/google";

import { BildirimSaglayici } from "@/components/ui/bildirim";
import { DilSaglayici } from "@/lib/dil";
import { ceviri } from "@/lib/sozluk";
import { dilOku } from "@/lib/sunucu-dil";

import "./globals.css";

const geist = Geist({
  subsets: ["latin"],
  variable: "--font-geist-sans",
  display: "swap",
});

const geistMono = Geist_Mono({
  subsets: ["latin"],
  variable: "--font-geist-mono",
  display: "swap",
});

const instrumentSerif = Instrument_Serif({
  subsets: ["latin"],
  weight: "400",
  variable: "--font-instrument-serif",
  display: "swap",
});

export async function generateMetadata(): Promise<Metadata> {
  const dil = await dilOku();
  return {
    title: {
      default: "KutyAI",
      template: "%s · KutyAI",
    },
    description: ceviri("genel.aciklama", dil),
  };
}

export default async function KokDuzen({ children }: { children: React.ReactNode }) {
  const dil = await dilOku();

  return (
    <html
      lang={dil}
      className={`${geist.variable} ${geistMono.variable} ${instrumentSerif.variable}`}
    >
      <body className="min-h-dvh bg-white text-neutral-900 antialiased">
        <DilSaglayici baslangicDili={dil}>
          <BildirimSaglayici>{children}</BildirimSaglayici>
        </DilSaglayici>
      </body>
    </html>
  );
}
