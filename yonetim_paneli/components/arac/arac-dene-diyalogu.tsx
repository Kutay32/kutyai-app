"use client";

import { useEffect, useState } from "react";

import { Play } from "lucide-react";

import { ApiHatasi, hataMesaji } from "@/lib/api";
import { gecikmeBicimle } from "@/lib/bicim";
import {
  aracDene,
  hataNedeni,
  semaAlanlari,
  type Arac,
  type DenemeSonucu,
  type SemaAlani,
} from "@/lib/araclar";
import { useDil } from "@/lib/dil";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";

export type AracDeneDiyaloguProps = {
  acik: boolean;
  arac: Arac | null;
  onKapat: () => void;
  /** Başarılı/hatalı çağrı sonrası listeyi tazelemek için. */
  onCalistirildi: () => void;
  /** Çağrı günlüğü sekmesine geçmek için (opsiyonel). */
  onGecmise?: () => void;
};

const METIN_TURLERI = new Set(["object", "array"]);

/**
 * Aracı argümanlarla çalıştırır ve sonucu gösterir.
 *
 * Form aracın JSON şemasından üretilir; şema boşsa serbest JSON gövdesi kabul
 * edilir. Webhook hatalarında sunucunun `ayrinti.neden` metni (zaman aşımı,
 * HTTP durum kodu vb.) ayrıca gösterilir (API.md §19).
 */
export function AracDeneDiyalogu({
  acik,
  arac,
  onKapat,
  onCalistirildi,
  onGecmise,
}: AracDeneDiyaloguProps) {
  const { t } = useDil();
  const alanlar: SemaAlani[] = semaAlanlari(arac?.json_sema);

  const [degerler, setDegerler] = useState<Record<string, string>>({});
  const [mantiksal, setMantiksal] = useState<Record<string, boolean>>({});
  const [serbest, setSerbest] = useState("{}");
  const [alanHatalari, setAlanHatalari] = useState<Record<string, string | null>>({});
  const [hata, setHata] = useState<{ mesaj: string; neden: string | null; kod: string } | null>(
    null,
  );
  const [sonuc, setSonuc] = useState<DenemeSonucu | null>(null);
  const [calisiyor, setCalisiyor] = useState(false);

  useEffect(() => {
    if (!acik) return;
    setDegerler({});
    setMantiksal({});
    setSerbest("{}");
    setAlanHatalari({});
    setHata(null);
    setSonuc(null);
  }, [acik, arac]);

  const kapat = () => {
    onKapat();
    setHata(null);
    setSonuc(null);
  };

  const calistir = async (olay: React.FormEvent<HTMLFormElement>) => {
    olay.preventDefault();
    const argumanlar: Record<string, unknown> = {};
    const bulunan: Record<string, string | null> = {};

    if (alanlar.length === 0) {
      try {
        const cozulen = JSON.parse(serbest.trim() || "{}") as unknown;
        if (cozulen === null || typeof cozulen !== "object" || Array.isArray(cozulen)) {
          bulunan.serbest = t("arac.dene.arguman.gecersiz");
        } else {
          Object.assign(argumanlar, cozulen as Record<string, unknown>);
        }
      } catch {
        bulunan.serbest = t("arac.dene.arguman.gecersiz");
      }
    } else {
      for (const alan of alanlar) {
        if (alan.tur === "boolean") {
          argumanlar[alan.ad] = mantiksal[alan.ad] ?? false;
          continue;
        }
        const ham = (degerler[alan.ad] ?? "").trim();
        if (!ham) {
          if (alan.zorunlu) bulunan[alan.ad] = t("arac.dene.zorunlu", { alan: alan.ad });
          continue;
        }
        if (alan.tur === "number" || alan.tur === "integer") {
          const sayi = Number(ham);
          if (!Number.isFinite(sayi)) {
            bulunan[alan.ad] = t("arac.dene.sayi.gecersiz", { alan: alan.ad });
            continue;
          }
          argumanlar[alan.ad] = alan.tur === "integer" ? Math.trunc(sayi) : sayi;
          continue;
        }
        if (METIN_TURLERI.has(alan.tur)) {
          try {
            argumanlar[alan.ad] = JSON.parse(ham) as unknown;
          } catch {
            bulunan[alan.ad] = t("arac.dene.arguman.gecersiz");
          }
          continue;
        }
        argumanlar[alan.ad] = ham;
      }
    }

    setAlanHatalari(bulunan);
    if (Object.values(bulunan).some(Boolean) || !arac) return;

    setHata(null);
    setSonuc(null);
    setCalisiyor(true);
    try {
      const yanit = await aracDene(arac.id, argumanlar);
      setSonuc(yanit);
    } catch (sebep) {
      // 400: şema ihlali, 502: webhook/çalıştırma hatası (imza, zaman aşımı, durum kodu).
      setHata({
        mesaj: hataMesaji(sebep),
        neden: hataNedeni(sebep),
        kod: sebep instanceof ApiHatasi ? sebep.kod : "bilinmeyen_hata",
      });
    } finally {
      setCalisiyor(false);
      onCalistirildi();
    }
  };

  return (
    <Dialog
      open={acik}
      onClose={kapat}
      className="max-h-[90vh] overflow-y-auto"
      title={t("arac.dene.baslik")}
      description={arac ? `${arac.ad} · ${arac.slug}` : t("arac.dene.aciklama")}
      footer={
        <>
          <Button variant="ghost" onClick={kapat} disabled={calisiyor}>
            {t("arac.vazgec")}
          </Button>
          <Button
            type="submit"
            form="arac-dene-formu"
            loading={calisiyor}
            disabled={arac === null}
          >
            <Play aria-hidden className="size-4" />
            {t("arac.dene.gonder")}
          </Button>
        </>
      }
    >
      <form id="arac-dene-formu" onSubmit={calistir} className="flex flex-col gap-4">
        {hata ? (
          <Alert tone="danger" title={t("arac.dene.hata.baslik")}>
            <div className="flex flex-col gap-1">
              <span className="flex flex-wrap items-center gap-2">
                <Badge tone="danger">{hata.kod}</Badge>
                {hata.mesaj}
              </span>
              {hata.neden ? <span>{hata.neden}</span> : null}
            </div>
          </Alert>
        ) : null}

        {sonuc ? (
          <div className="flex flex-col gap-3 rounded-lg border border-neutral-200 bg-neutral-50 p-3">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={sonuc.durum === "basarili" ? "success" : "danger"}>
                {sonuc.durum === "basarili"
                  ? t("arac.cagri.durum.basarili")
                  : t("arac.cagri.durum.hata")}
              </Badge>
              <span className="text-xs text-neutral-500">
                {t("arac.dene.gecikme")}: {gecikmeBicimle(sonuc.gecikme_ms)}
              </span>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-xs font-medium tracking-wide text-neutral-500 uppercase">
                {t("arac.dene.sonuc")}
              </span>
              <pre className="max-h-64 overflow-auto rounded-md border border-neutral-200 bg-white p-2 font-mono text-xs break-words whitespace-pre-wrap text-neutral-800">
                {JSON.stringify(sonuc.sonuc, null, 2)}
              </pre>
            </div>
            {onGecmise ? (
              <Button variant="secondary" size="sm" onClick={onGecmise}>
                {t("arac.dene.gecmis")}
              </Button>
            ) : null}
          </div>
        ) : null}

        <div className="flex flex-col gap-3">
          <h3 className="text-sm font-semibold text-neutral-900">
            {t("arac.dene.argumanlar")}
          </h3>

          {alanlar.length === 0 ? (
            <Field
              label={t("arac.dene.arguman.json")}
              hint={t("arac.dene.arguman.json.ipucu")}
              error={alanHatalari.serbest}
            >
              {({ id, invalid, ...erisim }) => (
                <Textarea
                  id={id}
                  {...erisim}
                  invalid={invalid}
                  rows={4}
                  className="font-mono text-xs"
                  value={serbest}
                  onChange={(olay) => setSerbest(olay.target.value)}
                />
              )}
            </Field>
          ) : (
            alanlar.map((alan) =>
              alan.tur === "boolean" ? (
                <Field key={alan.ad} label={alan.ad} hint={alan.aciklama || undefined}>
                  {({ id }) => (
                    <Switch
                      id={id}
                      checked={mantiksal[alan.ad] ?? false}
                      onChange={(deger) =>
                        setMantiksal((onceki) => ({ ...onceki, [alan.ad]: deger }))
                      }
                    />
                  )}
                </Field>
              ) : (
                <Field
                  key={alan.ad}
                  label={alan.ad}
                  hint={alan.aciklama || undefined}
                  error={alanHatalari[alan.ad]}
                  required={alan.zorunlu}
                >
                  {({ id, invalid, ...erisim }) =>
                    METIN_TURLERI.has(alan.tur) ? (
                      <Textarea
                        id={id}
                        {...erisim}
                        invalid={invalid}
                        rows={3}
                        className="font-mono text-xs"
                        value={degerler[alan.ad] ?? ""}
                        onChange={(olay) =>
                          setDegerler((onceki) => ({ ...onceki, [alan.ad]: olay.target.value }))
                        }
                      />
                    ) : (
                      <Input
                        id={id}
                        {...erisim}
                        invalid={invalid}
                        type={
                          alan.tur === "number" || alan.tur === "integer" ? "number" : "text"
                        }
                        value={degerler[alan.ad] ?? ""}
                        onChange={(olay) =>
                          setDegerler((onceki) => ({ ...onceki, [alan.ad]: olay.target.value }))
                        }
                      />
                    )
                  }
                </Field>
              ),
            )
          )}
        </div>
      </form>
    </Dialog>
  );
}
