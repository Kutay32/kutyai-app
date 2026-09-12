import Link from "next/link";

export default function BulunamadiSayfasi() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-4 text-center">
      <p className="font-serif text-3xl tracking-tight text-neutral-900">Sayfa bulunamadı</p>
      <p className="max-w-md text-sm text-neutral-500">
        Aradığınız sayfa taşınmış veya hiç var olmamış olabilir.
      </p>
      <Link
        href="/"
        className="rounded-md border border-neutral-900 bg-neutral-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-neutral-800 focus:outline-none focus:border-neutral-900 focus:ring-0"
      >
        Kontrol paneline dön
      </Link>
    </main>
  );
}
