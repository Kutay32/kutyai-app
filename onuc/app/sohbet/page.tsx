import type { Metadata } from "next";

import { Korumali } from "@/components/korumali";
import { SohbetEkrani } from "@/components/sohbet/sohbet-ekrani";

export const metadata: Metadata = {
  title: "Sohbet",
};

export default function SohbetSayfasi() {
  return (
    <Korumali tamYukseklik>
      <SohbetEkrani />
    </Korumali>
  );
}
