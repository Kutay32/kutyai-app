"use client";

import { Kart } from "@/components/ui/kart";

export type YetkiKartiOzellikleri = {
  baslik: string;
  metin: string;
};

/**
 * Yetkisiz oturumlara gösterilen bilgi kartı.
 * Menüde bağlantı çıkmaz; adres doğrudan açılırsa sayfa bununla karşılanır.
 */
export function YetkiKarti({ baslik, metin }: YetkiKartiOzellikleri) {
  return (
    <Kart role="status" className="flex flex-col gap-1">
      <h2 className="text-lg font-medium text-neutral-900">{baslik}</h2>
      <p className="text-sm text-neutral-500">{metin}</p>
    </Kart>
  );
}
