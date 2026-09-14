"use client";

import { ScrollText } from "lucide-react";

import { tarihSaatBicimle } from "@/lib/bicim";
import { useDil } from "@/lib/dil";
import {
  AYRINTI_ANAHTARI,
  ayrintiDegeri,
  type IslemKaydi,
} from "@/lib/islem-kayitlari";
import { Badge } from "@/components/ui/badge";
import { Drawer } from "@/components/ui/drawer";

function Cift({ etiket, deger }: { etiket: string; deger: string }) {
  return (
    <div className="flex flex-col gap-1">
      <dt className="text-xs tracking-wide text-neutral-500 uppercase">{etiket}</dt>
      <dd className="text-sm break-words text-neutral-900">{deger}</dd>
    </div>
  );
}

/** Tek denetim kaydının ayrıntısını anahtar-değer listesi olarak gösteren çekmece. */
export function AyrintiCekmecesi({
  kayit,
  onKapat,
}: {
  kayit: IslemKaydi | null;
  onKapat: () => void;
}) {
  const { t } = useDil();
  const satirlar = Object.entries(kayit?.ayrinti ?? {});

  return (
    <Drawer
      open={kayit !== null}
      onClose={onKapat}
      title={kayit?.eylem ?? t("islem.kayit")}
      description={kayit ? tarihSaatBicimle(kayit.olusturulma) : undefined}
    >
      {kayit ? (
        <div className="flex flex-col gap-6">
          <dl className="grid gap-4">
            <Cift etiket={t("islem.alan.kayit_no")} deger={String(kayit.id)} />
            <Cift
              etiket={t("islem.alan.kullanici")}
              deger={kayit.kullanici_eposta ?? "—"}
            />
            <Cift
              etiket={t("islem.alan.hedef")}
              deger={kayit.hedef_tur ? `${kayit.hedef_tur}${kayit.hedef_id ? ` #${kayit.hedef_id}` : ""}` : "—"}
            />
            <Cift etiket={t("islem.alan.ip")} deger={kayit.ip || "—"} />
          </dl>

          <div className="flex flex-col gap-3">
            <h3 className="text-sm font-semibold text-neutral-900">{t("islem.ayrinti.baslik")}</h3>
            {satirlar.length > 0 ? (
              <dl className="flex flex-col gap-3 rounded-lg border border-neutral-200 p-4">
                {satirlar.map(([anahtar, deger]) => {
                  const anahtarCeviri = AYRINTI_ANAHTARI[anahtar];
                  return (
                    <Cift
                      key={anahtar}
                      etiket={anahtarCeviri ? t(anahtarCeviri) : anahtar}
                      deger={ayrintiDegeri(deger)}
                    />
                  );
                })}
              </dl>
            ) : (
              <p className="text-sm text-neutral-500">{t("islem.ayrinti.bos")}</p>
            )}
          </div>
        </div>
      ) : (
        <p className="flex items-center gap-2 text-sm text-neutral-500">
          <ScrollText aria-hidden className="size-4" />
          {t("islem.ayrinti.secili_degil")}
        </p>
      )}
    </Drawer>
  );
}

export function EylemRozeti({ eylem }: { eylem: string }) {
  const tone =
    eylem.includes("sil") || eylem.includes("iptal") || eylem.includes("pasiflestir")
      ? "danger"
      : eylem.includes("olustur") || eylem.includes("baslat")
        ? "success"
        : "neutral";
  return <Badge tone={tone}>{eylem}</Badge>;
}
