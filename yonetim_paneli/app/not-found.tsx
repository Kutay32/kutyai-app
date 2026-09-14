import Link from "next/link";

import { ceviri } from "@/lib/sozluk";
import { dilOku } from "@/lib/sunucu-dil";

export default async function BulunamadiSayfasi() {
  const dil = await dilOku();

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-4 text-center">
      <p className="font-serif text-3xl tracking-tight text-neutral-900">
        {ceviri("bulunamadi.baslik", dil)}
      </p>
      <p className="max-w-md text-sm text-neutral-500">{ceviri("bulunamadi.metin", dil)}</p>
      <Link
        href="/"
        className="rounded-md border border-neutral-900 bg-neutral-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-neutral-800 focus:outline-none focus:border-neutral-900 focus:ring-0"
      >
        {ceviri("bulunamadi.don", dil)}
      </Link>
    </main>
  );
}
