"use client";

import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { sayiBicimle } from "@/lib/bicim";

export type SayfalamaProps = {
  toplam: number;
  sayfa: number;
  boyut: number;
  boyutlar?: readonly number[];
  onSayfa: (sayfa: number) => void;
  onBoyut?: (boyut: number) => void;
};

/** Sunucu taraflı sayfalama denetimi: kayıt sayısı, sayfa konumu, boyut ve gezinme. */
export function Sayfalama({
  toplam,
  sayfa,
  boyut,
  boyutlar,
  onSayfa,
  onBoyut,
}: SayfalamaProps) {
  const sonSayfa = Math.max(1, Math.ceil(toplam / boyut));

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 p-4">
      <p className="text-sm text-neutral-500">
        Toplam <span className="text-neutral-900">{sayiBicimle(toplam)}</span> kayıt ·{" "}
        {sayfa}/{sonSayfa}. sayfa
      </p>

      <div className="flex items-center gap-2">
        {boyutlar && onBoyut ? (
          <Select
            aria-label="Sayfa boyutu"
            className="w-32"
            value={String(boyut)}
            onChange={(olay) => onBoyut(Number(olay.target.value))}
          >
            {boyutlar.map((secenek) => (
              <option key={secenek} value={secenek}>
                {secenek} kayıt
              </option>
            ))}
          </Select>
        ) : null}

        <Button
          variant="secondary"
          size="sm"
          disabled={sayfa <= 1}
          onClick={() => onSayfa(sayfa - 1)}
        >
          Önceki
        </Button>
        <Button
          variant="secondary"
          size="sm"
          disabled={sayfa >= sonSayfa}
          onClick={() => onSayfa(sayfa + 1)}
        >
          Sonraki
        </Button>
      </div>
    </div>
  );
}
