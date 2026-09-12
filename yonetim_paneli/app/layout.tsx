import type { Metadata } from "next";
import { Geist, Instrument_Serif } from "next/font/google";

import "./globals.css";
import { ToastProvider } from "@/components/ui/toast";

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

export const metadata: Metadata = {
  title: { default: "KutyAI Yönetim Paneli", template: "%s · KutyAI" },
  description: "KutyAI kurumsal BDM platformu yönetim paneli.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="tr" className={`${geist.variable} ${instrumentSerif.variable}`}>
      <body>
        <ToastProvider>{children}</ToastProvider>
      </body>
    </html>
  );
}
