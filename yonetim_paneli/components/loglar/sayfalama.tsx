"use client";

import { useDil } from "@/lib/dil";
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
  const { t } = useDil();
  const sonSayfa = Math.max(1, Math.ceil(toplam / boyut));
  // Toplam sayısı cümle içinde vurgulu kalır; şablon `{baglanti}` ile parçalanır.
  const [once, sonra] = t("kayit.sayfalama.ozet", {
    sayfa,
    son: sonSayfa,
  }).split("{baglanti}");

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 p-4">
      <p className="text-sm text-neutral-500">
        {once}
        <span className="text-neutral-900">{sayiBicimle(toplam)}</span>
        {sonra}
      </p>

      <div className="flex items-center gap-2">
        {boyutlar && onBoyut ? (
          <Select
            aria-label={t("kayit.sayfalama.boyut.aria")}
            className="w-32"
            value={String(boyut)}
            onChange={(olay) => onBoyut(Number(olay.target.value))}
          >
            {boyutlar.map((secenek) => (
              <option key={secenek} value={secenek}>
                {t("kayit.sayfalama.boyut.secenek", { sayi: secenek })}
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
          {t("kayit.sayfalama.onceki")}
        </Button>
        <Button
          variant="secondary"
          size="sm"
          disabled={sayfa >= sonSayfa}
          onClick={() => onSayfa(sayfa + 1)}
        >
          {t("kayit.sayfalama.sonraki")}
        </Button>
      </div>
    </div>
  );
}
