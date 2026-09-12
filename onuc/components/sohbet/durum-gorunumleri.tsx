"use client";

import { RefreshCw } from "lucide-react";

import { Buton } from "@/components/ui/buton";

export type HataBandiOzellikleri = {
  mesaj: string;
  onYenidenDene?: (() => void) | null;
};

/** Hata bandı: sunucudan gelen `hata.mesaj` ve tekrarlama eylemi. */
export function HataBandi({ mesaj, onYenidenDene = null }: HataBandiOzellikleri) {
  return (
    <div
      role="alert"
      className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-rose-200 bg-white p-3"
    >
      <p className="text-[13px] text-rose-600">{mesaj}</p>
      {onYenidenDene ? (
        <Buton tur="ikincil" boyut="kucuk" onClick={onYenidenDene}>
          <RefreshCw aria-hidden className="size-3.5" />
          Yeniden dene
        </Buton>
      ) : null}
    </div>
  );
}

/** Yanıt beklenirken gösterilen iskelet baloncuklar. */
export function MesajIskeleti() {
  return (
    <div className="flex flex-col gap-4" aria-hidden>
      <div className="h-12 w-2/3 animate-pulse self-end rounded-2xl bg-neutral-100" />
      <div className="h-24 w-4/5 animate-pulse self-start rounded-2xl bg-neutral-100" />
      <div className="h-12 w-1/2 animate-pulse self-end rounded-2xl bg-neutral-100" />
    </div>
  );
}

/** Konuşma listesi yüklenirken gösterilen iskelet satırlar. */
export function KonusmaIskeleti() {
  return (
    <div className="flex flex-col gap-2" aria-hidden>
      {[0, 1, 2, 3].map((sira) => (
        <div key={sira} className="h-12 animate-pulse rounded-lg bg-neutral-100" />
      ))}
    </div>
  );
}

/** Mesaj yokken gösterilen yönlendirici boş durum. */
export function SohbetBosDurumu({
  modelVar,
  onYenile,
}: {
  modelVar: boolean;
  onYenile: () => void;
}) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
      <h2 className="marka-serif text-2xl text-neutral-900">
        {modelVar ? "Sohbete başlayın" : "Kullanılabilir model yok"}
      </h2>
      {modelVar ? (
        <p className="max-w-md text-sm text-neutral-500">
          Seçtiğiniz modelle mesajlaşmaya başlayın. Yanıtlar yazıldıkça akış hâlinde
          görünür; dilediğiniz an durdurabilirsiniz.
        </p>
      ) : (
        <>
          <p className="max-w-md text-sm text-neutral-500">
            Sohbet için en az bir modelin <strong className="font-medium">hazır</strong>{" "}
            durumda olması gerekir. Yöneticiniz model hazırladığında bu listeyi
            yenileyebilirsiniz.
          </p>
          <Buton tur="ikincil" boyut="kucuk" onClick={onYenile}>
            <RefreshCw aria-hidden className="size-3.5" />
            Modelleri yenile
          </Buton>
        </>
      )}
    </div>
  );
}
