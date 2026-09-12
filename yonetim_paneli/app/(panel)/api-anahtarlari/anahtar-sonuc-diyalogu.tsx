"use client";

import { useEffect, useState } from "react";

import { Check, Copy } from "lucide-react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

export type AnahtarSonucDiyaloguProps = {
  ad: string;
  tamAnahtar: string;
  /** Yalnızca kullanıcı anahtarı kaydettiğini onaylayınca çağrılır. */
  onKapat: () => void;
};

function geciciAlanlaKopyala(metin: string): void {
  const alan = document.createElement("textarea");
  alan.value = metin;
  alan.setAttribute("readonly", "");
  alan.style.position = "fixed";
  alan.style.opacity = "0";
  document.body.append(alan);
  alan.select();
  document.execCommand("copy");
  alan.remove();
}

/**
 * Tam anahtarı gösteren **kapatılamaz** katman. ESC, arka plan tıklaması ve
 * kapatma düğmesi yoktur; `tam_anahtar` bir daha sunucudan alınamadığı için
 * tek çıkış yolu kullanıcının kaydettiğini onaylamasıdır.
 */
export function AnahtarSonucDiyalogu({ ad, tamAnahtar, onKapat }: AnahtarSonucDiyaloguProps) {
  const [kopyalandi, setKopyalandi] = useState(false);
  const [kopyalamaHatasi, setKopyalamaHatasi] = useState<string | null>(null);

  useEffect(() => {
    const tasma = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = tasma;
    };
  }, []);

  const kopyala = async () => {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(tamAnahtar);
      } else {
        geciciAlanlaKopyala(tamAnahtar);
      }
      setKopyalandi(true);
      setKopyalamaHatasi(null);
    } catch {
      setKopyalamaHatasi("Kopyalanamadı; anahtarı elle seçip kopyalayın.");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div aria-hidden className="absolute inset-0 bg-neutral-900/40" />

      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="anahtar-sonuc-baslik"
        className="relative z-10 flex w-full max-w-lg flex-col rounded-2xl border border-neutral-200 bg-white"
      >
        <div className="flex flex-col gap-1 border-b border-neutral-200 p-4">
          <h2 id="anahtar-sonuc-baslik" className="text-base font-semibold text-neutral-900">
            API anahtarı oluşturuldu
          </h2>
          <p className="text-sm text-neutral-500">{ad}</p>
        </div>

        <div className="flex flex-col gap-4 p-4">
          <Alert tone="danger" title="Bu anahtar bir daha gösterilmeyecek">
            Sunucu tam anahtarı yalnızca bu yanıtta döndürür. Şimdi kopyalayıp
            güvenli bir yere kaydedin; bu pencere kapandıktan sonra anahtarı
            yeniden görüntülemenin bir yolu yoktur.
          </Alert>

          <p className="rounded-lg border border-neutral-200 bg-neutral-50 p-3 font-mono text-sm break-all text-neutral-900 select-all">
            {tamAnahtar}
          </p>

          {kopyalamaHatasi ? (
            <p role="alert" className="text-xs text-rose-600">
              {kopyalamaHatasi}
            </p>
          ) : null}

          <Button
            autoFocus
            variant="secondary"
            onClick={() => void kopyala()}
          >
            {kopyalandi ? <Check aria-hidden className="size-4" /> : <Copy aria-hidden className="size-4" />}
            {kopyalandi ? "Kopyalandı" : "Kopyala"}
          </Button>
        </div>

        <div className="flex items-center justify-end gap-2 border-t border-neutral-200 p-4">
          <Button onClick={onKapat}>Kaydettim, kapat</Button>
        </div>
      </div>
    </div>
  );
}
