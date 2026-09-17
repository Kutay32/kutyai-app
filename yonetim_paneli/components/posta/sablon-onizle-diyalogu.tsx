"use client";

import { useCallback, useEffect, useState } from "react";

import { useDil } from "@/lib/dil";
import {
  SABLON_DILI_ANAHTARI,
  SABLON_KODU_ANAHTARI,
  degiskenleriBul,
  sablonHatasi,
  sablonOnizle,
  type PostaSablonu,
  type SablonOnizlemesi,
} from "@/lib/posta-sablonlari";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * `POST /posta-sablonlari/{kod}/onizle` — kayıtlı şablonu örnek değerlerle doldurur.
 * Kullanıcı değişken girerse sunucudaki örnek değeri geçersiz kılar.
 */
export function SablonOnizleDiyalogu({
  sablon,
  onKapat,
}: {
  sablon: PostaSablonu;
  onKapat: () => void;
}) {
  const { t } = useDil();
  const degiskenler = degiskenleriBul(sablon.konu, sablon.govde_metin, sablon.govde_html);

  const [degerler, setDegerler] = useState<Record<string, string>>({});
  const [onizleme, setOnizleme] = useState<SablonOnizlemesi | null>(null);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [hata, setHata] = useState<string | null>(null);

  const yukle = useCallback(
    async (girilenler: Record<string, string>) => {
      setYukleniyor(true);
      setHata(null);
      try {
        const dolu: Record<string, string> = {};
        for (const [anahtar, deger] of Object.entries(girilenler)) {
          if (deger.trim()) dolu[anahtar] = deger.trim();
        }
        setOnizleme(await sablonOnizle(sablon.kod, sablon.dil, dolu));
      } catch (sebep) {
        setHata(sablonHatasi(sebep));
      } finally {
        setYukleniyor(false);
      }
    },
    [sablon.kod, sablon.dil],
  );

  useEffect(() => {
    void yukle({});
  }, [yukle]);

  return (
    <Dialog
      open
      onClose={onKapat}
      title={t("posta.onizle.baslik", { ad: t(SABLON_KODU_ANAHTARI[sablon.kod]) })}
      description={t("posta.onizle.aciklama")}
      className="max-w-2xl"
      footer={<Button onClick={onKapat}>{t("genel.kapat")}</Button>}
    >
      <div className="flex flex-col gap-4">
        <p className="text-xs text-neutral-500">{t("posta.onizle.kayitli.ipucu")}</p>

        {hata ? (
          <Alert tone="danger" title={t("posta.onizle.hata.baslik")}>
            {hata}
          </Alert>
        ) : null}

        {degiskenler.length > 0 ? (
          <div className="flex flex-col gap-3">
            <p className="text-xs tracking-wide text-neutral-500 uppercase">
              {t("posta.onizle.degiskenler")}
            </p>
            <div className="grid gap-3 sm:grid-cols-2">
              {degiskenler.map((degisken) => (
                <Field key={degisken} label={`{{${degisken}}}`}>
                  {({ id, ...erisim }) => (
                    <Input
                      id={id}
                      {...erisim}
                      autoComplete="off"
                      value={degerler[degisken] ?? ""}
                      onChange={(olay) =>
                        setDegerler((onceki) => ({
                          ...onceki,
                          [degisken]: olay.target.value,
                        }))
                      }
                    />
                  )}
                </Field>
              ))}
            </div>
            <div>
              <Button
                variant="secondary"
                loading={yukleniyor}
                onClick={() => void yukle(degerler)}
              >
                {t("posta.onizle.gonder")}
              </Button>
            </div>
          </div>
        ) : (
          <p className="text-sm text-neutral-500">{t("posta.onizle.degisken.yok")}</p>
        )}

        <div className="flex items-center justify-between gap-3">
          <p className="text-xs tracking-wide text-neutral-500 uppercase">
            {t("posta.onizle.konu")}
          </p>
          <span className="text-xs text-neutral-500">
            {t(SABLON_DILI_ANAHTARI[sablon.dil])}
          </span>
        </div>

        {yukleniyor ? (
          <div className="flex flex-col gap-2" aria-busy>
            <Skeleton className="h-5 w-2/3" />
            <Skeleton className="h-24 w-full" />
          </div>
        ) : onizleme ? (
          <div className="flex flex-col gap-4">
            <p className="text-sm font-medium text-neutral-900">{onizleme.konu}</p>

            <div className="flex flex-col gap-1">
              <p className="text-xs tracking-wide text-neutral-500 uppercase">
                {t("posta.onizle.govde_metin")}
              </p>
              <pre className="overflow-x-auto rounded-lg border border-neutral-200 bg-neutral-50 p-3 text-sm whitespace-pre-wrap text-neutral-800">
                {onizleme.govde_metin}
              </pre>
            </div>

            <div className="flex flex-col gap-1">
              <p className="text-xs tracking-wide text-neutral-500 uppercase">
                {t("posta.onizle.govde_html")}
              </p>
              <pre className="overflow-x-auto rounded-lg border border-neutral-200 bg-neutral-50 p-3 text-xs whitespace-pre-wrap text-neutral-800">
                {onizleme.govde_html}
              </pre>
            </div>
          </div>
        ) : (
          <p className="text-sm text-neutral-500">{t("posta.onizle.bos")}</p>
        )}
      </div>
    </Dialog>
  );
}
