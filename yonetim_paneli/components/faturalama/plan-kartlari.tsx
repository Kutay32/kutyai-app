"use client";

import { Check } from "lucide-react";

import { sayiBicimle } from "@/lib/bicim";
import { useDil } from "@/lib/dil";
import type { Plan } from "@/lib/faturalama";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

function Kotasi({ etiket, deger }: { etiket: string; deger: number | null }) {
  const { t } = useDil();
  return (
    <div className="flex items-center justify-between gap-3 text-sm">
      <span className="text-neutral-500">{etiket}</span>
      <span className="font-medium text-neutral-900">
        {deger === null ? t("faturalama.plan.sinirsiz") : sayiBicimle(deger)}
      </span>
    </div>
  );
}

/** `GET /faturalama/planlar` kartları; seçim `POST /faturalama/abonelik` ile yapılır. */
export function PlanKartlari({
  planlar,
  gecerliPlanId,
  duzenleyebilir,
  onSec,
}: {
  planlar: Plan[];
  gecerliPlanId: number | null;
  /** Faturalama yazma yetkisi; `false` iken planlar yalnız tanıtım amaçlı listelenir. */
  duzenleyebilir: boolean;
  onSec: (plan: Plan) => void;
}) {
  const { t } = useDil();

  return (
    <section className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h2 className="text-lg font-semibold tracking-tight text-neutral-900">
          {t("faturalama.planlar.baslik")}
        </h2>
        <p className="text-sm text-neutral-500">{t("faturalama.planlar.aciklama")}</p>
      </div>

      {planlar.length === 0 ? (
        <p className="text-sm text-neutral-500">{t("faturalama.planlar.bos")}</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {planlar.map((plan) => {
            const gecerli = plan.id === gecerliPlanId;
            const ozellikler = Object.entries(plan.ozellikler ?? {});
            return (
              <Card key={plan.id} className="flex flex-col gap-4 rounded-2xl p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex flex-col gap-1">
                    <h3 className="text-base font-semibold text-neutral-900">{plan.ad}</h3>
                    <p className="text-lg font-semibold tracking-tight text-neutral-900">
                      {plan.aylik_fiyat}
                    </p>
                  </div>
                  {gecerli ? (
                    <Badge tone="success">
                      <Check aria-hidden className="size-3" />
                      {t("faturalama.plan.secili")}
                    </Badge>
                  ) : null}
                </div>

                <div className="flex flex-col gap-2 border-t border-neutral-200 pt-4">
                  <Kotasi
                    etiket={t("faturalama.plan.dahil_istek")}
                    deger={plan.dahil_istek}
                  />
                  <Kotasi
                    etiket={t("faturalama.plan.dahil_token")}
                    deger={plan.dahil_token}
                  />
                </div>

                {ozellikler.length > 0 ? (
                  <ul className="flex flex-wrap gap-2">
                    {ozellikler.map(([anahtar, deger]) => (
                      <li key={anahtar}>
                        <Badge tone="neutral">
                          {anahtar}: {String(deger)}
                        </Badge>
                      </li>
                    ))}
                  </ul>
                ) : null}

                {duzenleyebilir ? (
                  <div className="mt-auto">
                    <Button disabled={gecerli} onClick={() => onSec(plan)} className="w-full">
                      {t("faturalama.plan.sec")}
                    </Button>
                  </div>
                ) : null}
              </Card>
            );
          })}
        </div>
      )}
    </section>
  );
}
