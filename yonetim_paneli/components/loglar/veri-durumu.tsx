"use client";

import { RefreshCw } from "lucide-react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

export type VeriDurumuProps = {
  yukleniyor: boolean;
  hata: string | null;
  yenile: () => void;
  children: React.ReactNode;
};

/** Uzak veri bloğunun yükleniyor/hata/gövde durumlarını tek yerde toplar. */
export function VeriDurumu({ yukleniyor, hata, yenile, children }: VeriDurumuProps) {
  if (yukleniyor) {
    return (
      <div aria-busy className="flex flex-col gap-2 p-4">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-4 w-2/3" />
      </div>
    );
  }

  if (hata) {
    return (
      <div className="p-4">
        <Alert tone="danger" title="Veri alınamadı">
          <p>{hata}</p>
          <Button variant="secondary" size="sm" className="mt-2" onClick={yenile}>
            <RefreshCw aria-hidden className="size-4" />
            Yeniden dene
          </Button>
        </Alert>
      </div>
    );
  }

  return <>{children}</>;
}
