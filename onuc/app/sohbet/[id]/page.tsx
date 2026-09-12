import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { Korumali } from "@/components/korumali";
import { SohbetEkrani } from "@/components/sohbet/sohbet-ekrani";

export const metadata: Metadata = {
  title: "Sohbet",
};

export default async function SohbetKonusmaSayfasi({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const konusmaId = Number.parseInt(id, 10);
  if (!Number.isFinite(konusmaId) || konusmaId < 1) notFound();

  return (
    <Korumali tamYukseklik>
      <SohbetEkrani baslangicKonusmaId={konusmaId} />
    </Korumali>
  );
}
