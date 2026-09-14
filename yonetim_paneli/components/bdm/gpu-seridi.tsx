"use client";

import { TriangleAlert } from "lucide-react";

import { useDil } from "@/lib/dil";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import type { SurucuDurumu } from "@/lib/tipler";

export type GpuSeridiProps = {
  surucu: SurucuDurumu | null;
  yukleniyor: boolean;
  hata: string | null;
  yenile: () => void;
};

/**
 * GPU yoksa gösterilen uyarı bandı: vLLM/TGI başlatma düğmelerinin neden
 * devre dışı olduğunu gerekçesiyle birlikte açıklar.
 */
export function GpuSeridi({ surucu, yukleniyor, hata, yenile }: GpuSeridiProps) {
  const { t } = useDil();

  if (yukleniyor) return null;

  if (hata || !surucu) {
    return (
      <Alert tone="warning" title={t("bdm.gpu.okunamadi")}>
        <p>{hata ?? t("bdm.gpu.surucu_yok")}</p>
        <Button variant="secondary" size="sm" className="mt-2" onClick={yenile}>
          {t("bdm.yeniden_dene")}
        </Button>
      </Alert>
    );
  }

  if (surucu.gpu) return null;

  return (
    <Alert tone="warning" title={t("bdm.gpu.bulunamadi")}>
      <p>{surucu.mesaj.trim() || t("bdm.gpu.mesaj")}</p>
      <p className="flex items-center gap-1.5">
        <TriangleAlert aria-hidden className="size-4 shrink-0" />
        <span>{t("bdm.gpu.devredisi")}</span>
      </p>
    </Alert>
  );
}
