import type { Metadata } from "next";
import { Geist, Geist_Mono, Instrument_Serif } from "next/font/google";

import { BildirimSaglayici } from "@/components/ui/bildirim";

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

export const metadata: Metadata = {
  title: {
    default: "KutyAI",
    template: "%s · KutyAI",
  },
  description: "Kurumsal büyük dil modeli platformu.",
};

export default function KokDuzen({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="tr"
      className={`${geist.variable} ${geistMono.variable} ${instrumentSerif.variable}`}
    >
      <body className="min-h-dvh bg-white text-neutral-900 antialiased">
        <BildirimSaglayici>{children}</BildirimSaglayici>
      </body>
    </html>
  );
}
