"use client";

import { useId, useRef, useState } from "react";
import { Send, Square } from "lucide-react";

import { Buton } from "@/components/ui/buton";
import { useDil } from "@/lib/dil";

export type SohbetGirdisiOzellikleri = {
  /** Bir yanıt akmakta. */
  gonderiliyor: boolean;
  /** Gönderim yapılabilir (seçili model var). */
  gonderilebilir: boolean;
  onGonder: (metin: string) => void;
  onDurdur: () => void;
};

/**
 * Mesaj yazma alanı: `Enter` gönderir, `Shift+Enter` satır açar.
 * `Esc` ile üretimi durdurma ekran düzeyinde dinlenir.
 */
export function SohbetGirdisi({
  gonderiliyor,
  gonderilebilir,
  onGonder,
  onDurdur,
}: SohbetGirdisiOzellikleri) {
  const { t } = useDil();
  const [metin, setMetin] = useState("");
  const alanRef = useRef<HTMLTextAreaElement>(null);
  const alanId = useId();

  function yukseklikAyarla(alan: HTMLTextAreaElement) {
    alan.style.height = "auto";
    alan.style.height = `${Math.min(alan.scrollHeight, 160)}px`;
  }

  function gonder() {
    const temiz = metin.trim();
    if (!temiz || gonderiliyor || !gonderilebilir) return;
    onGonder(temiz);
    setMetin("");
    const alan = alanRef.current;
    if (alan) {
      alan.style.height = "auto";
      alan.focus();
    }
  }

  function tusaBasildi(olay: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (olay.key !== "Enter" || olay.shiftKey || olay.nativeEvent.isComposing) return;
    olay.preventDefault();
    gonder();
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-end gap-2 rounded-2xl border border-neutral-200 p-2 transition-colors focus-within:border-neutral-900">
        <label htmlFor={alanId} className="sr-only">
          {t("sohbet.girdi.etiket")}
        </label>
        <textarea
          ref={alanRef}
          id={alanId}
          rows={1}
          value={metin}
          onChange={(olay) => {
            setMetin(olay.target.value);
            yukseklikAyarla(olay.target);
          }}
          onKeyDown={tusaBasildi}
          placeholder={
            gonderilebilir ? t("sohbet.girdi.ipucu") : t("sohbet.girdi.model.secin")
          }
          disabled={!gonderilebilir}
          className="max-h-40 min-h-10 w-full resize-none bg-transparent px-2 py-2 text-sm text-neutral-900 placeholder:text-neutral-400 focus:outline-none disabled:cursor-not-allowed disabled:text-neutral-500"
        />
        {gonderiliyor ? (
          <Buton
            tur="ikincil"
            boyut="kucuk"
            onClick={onDurdur}
            aria-label={t("sohbet.girdi.durdur.etiket")}
          >
            <Square aria-hidden className="size-3.5" />
            {t("sohbet.girdi.durdur")}
          </Buton>
        ) : (
          <Buton
            boyut="kucuk"
            onClick={gonder}
            disabled={!gonderilebilir || metin.trim().length === 0}
          >
            <Send aria-hidden className="size-3.5" />
            {t("sohbet.girdi.gonder")}
          </Buton>
        )}
      </div>
      <p className="px-1 text-[11px] text-neutral-500">{t("sohbet.girdi.kisayol")}</p>
    </div>
  );
}
