"use client";

import { useEffect, useRef, useState } from "react";
import { Check, Copy } from "lucide-react";

import { useDil } from "@/lib/dil";

/** Panoya kopyalar; Clipboard API yoksa gizli alan + `execCommand` yedeği kullanır. */
async function panoyaKopyala(metin: string): Promise<boolean> {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(metin);
      return true;
    }
  } catch {
    // Güvenli olmayan bağlam veya izin reddi: yedek yola düşülür.
  }
  try {
    const alan = document.createElement("textarea");
    alan.value = metin;
    alan.setAttribute("readonly", "");
    alan.style.position = "fixed";
    alan.style.opacity = "0";
    document.body.appendChild(alan);
    alan.select();
    const basarili = document.execCommand("copy");
    document.body.removeChild(alan);
    return basarili;
  } catch {
    return false;
  }
}

export type KodBloguOzellikleri = {
  /** `language-*` sınıfından çözülen dil etiketi; yoksa `null`. */
  dil: string | null;
  metin: string;
};

/** Sohbet yanıtındaki kod bloğu ve panoya kopyalama düğmesi. */
export function KodBlogu({ dil: kodDili, metin }: KodBloguOzellikleri) {
  const { t } = useDil();
  const [kopyalandi, setKopyalandi] = useState(false);
  const zamanlayici = useRef<number | undefined>(undefined);

  useEffect(
    () => () => {
      clearTimeout(zamanlayici.current);
    },
    [],
  );

  async function kopyala() {
    if (!(await panoyaKopyala(metin))) return;
    setKopyalandi(true);
    clearTimeout(zamanlayici.current);
    zamanlayici.current = window.setTimeout(() => setKopyalandi(false), 1600);
  }

  return (
    <figure className="my-3 overflow-hidden rounded-lg border border-neutral-200 bg-neutral-50">
      <figcaption className="flex items-center justify-between gap-2 border-b border-neutral-200 px-3 py-1.5">
        <span className="font-mono text-[11px] tracking-wide text-neutral-500 uppercase">
          {kodDili ?? t("sohbet.kod.etiket")}
        </span>
        <button
          type="button"
          onClick={kopyala}
          className="inline-flex items-center gap-1.5 rounded-md border border-transparent px-2 py-1 text-[11px] text-neutral-500 transition-colors hover:border-neutral-200 hover:text-neutral-900 focus:border-neutral-900 focus:ring-0"
        >
          {kopyalandi ? (
            <Check aria-hidden className="size-3" />
          ) : (
            <Copy aria-hidden className="size-3" />
          )}
          {kopyalandi ? t("sohbet.kod.kopyalandi") : t("sohbet.kod.kopyala")}
        </button>
      </figcaption>
      <pre className="overflow-x-auto p-3 text-[13px] leading-relaxed">
        <code className="font-mono">{metin}</code>
      </pre>
    </figure>
  );
}
