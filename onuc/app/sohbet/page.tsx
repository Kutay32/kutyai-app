import type { Metadata } from "next";

import { Korumali } from "@/components/korumali";
import { SohbetEkrani } from "@/components/sohbet/sohbet-ekrani";
import { ceviri } from "@/lib/sozluk";
import { dilOku } from "@/lib/sunucu-dil";

export async function generateMetadata(): Promise<Metadata> {
  const dil = await dilOku();
  return { title: ceviri("kabuk.baglanti.sohbet", dil) };
}

export default function SohbetSayfasi() {
  return (
    <Korumali tamYukseklik>
      <SohbetEkrani />
    </Korumali>
  );
}
