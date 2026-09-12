"use client";

import { TriangleAlert } from "lucide-react";

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
  if (yukleniyor) return null;

  if (hata || !surucu) {
    return (
      <Alert tone="warning" title="Çalışma zamanı durumu okunamadı">
        <p>{hata ?? "Sürücü bilgisi alınamadı."}</p>
        <Button variant="secondary" size="sm" className="mt-2" onClick={yenile}>
          Yeniden dene
        </Button>
      </Alert>
    );
  }

  if (surucu.gpu) return null;

  return (
    <Alert tone="warning" title="GPU bulunamadı">
      <p>
        {surucu.mesaj.trim() ||
          "Bu ortamda GPU çalışma zamanı bulunamadı; GPU gerektiren modeller başlatılamaz."}
      </p>
      <p className="flex items-center gap-1.5">
        <TriangleAlert aria-hidden className="size-4 shrink-0" />
        <span>
          vLLM ve TGI için başlatma düğmeleri devre dışı. GPU gerektirmeyen Ollama
          sağlayıcısını kullanabilirsiniz.
        </span>
      </p>
    </Alert>
  );
}
