"use client";

import { useState } from "react";

import { useDil } from "@/lib/dil";
import { tarihSaatBicimle } from "@/lib/bicim";
import {
  ABONELIK_DURUMU_ANAHTARI,
  ABONELIK_DURUMU_TONU,
  type Abonelik,
} from "@/lib/faturalama";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { AbonelikIptalDiyalogu } from "./faturalama-diyaloglari";

/** Aktif abonelik özeti; iptal eylemi `POST /faturalama/abonelik/iptal` çağırır. */
export function AbonelikKarti({
  abonelik,
  duzenleyebilir,
  onDegisti,
}: {
  abonelik: Abonelik | null;
  /** Faturalama yazma yetkisi; `false` iken yalnız özet gösterilir. */
  duzenleyebilir: boolean;
  onDegisti: () => void;
}) {
  const { t } = useDil();
  const [iptalAcik, setIptalAcik] = useState(false);

  return (
    <Card className="rounded-2xl">
      <CardHeader className="flex-row items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <CardTitle>{t("faturalama.abonelik.baslik")}</CardTitle>
          <CardDescription>{t("faturalama.abonelik.aciklama")}</CardDescription>
        </div>
        {abonelik ? (
          <Badge tone={ABONELIK_DURUMU_TONU[abonelik.durum]}>
            {t(ABONELIK_DURUMU_ANAHTARI[abonelik.durum])}
          </Badge>
        ) : null}
      </CardHeader>

      <CardContent className="flex flex-col gap-4">
        {abonelik ? (
          <>
            <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div className="flex flex-col gap-1">
                <dt className="text-xs tracking-wide text-neutral-500 uppercase">
                  {t("faturalama.abonelik.plan")}
                </dt>
                <dd className="text-sm font-medium text-neutral-900">
                  {abonelik.plan?.ad ?? "—"}
                </dd>
              </div>
              <div className="flex flex-col gap-1">
                <dt className="text-xs tracking-wide text-neutral-500 uppercase">
                  {t("faturalama.abonelik.donem")}
                </dt>
                <dd className="text-sm text-neutral-900">
                  {t("faturalama.abonelik.donem_araligi", {
                    baslangic: tarihSaatBicimle(abonelik.donem_basi),
                    bitis: tarihSaatBicimle(abonelik.donem_sonu),
                  })}
                </dd>
              </div>
              <div className="flex flex-col gap-1">
                <dt className="text-xs tracking-wide text-neutral-500 uppercase">
                  {t("faturalama.abonelik.saglayici")}
                </dt>
                <dd className="text-sm text-neutral-900">{abonelik.saglayici || "—"}</dd>
              </div>
              <div className="flex flex-col gap-1">
                <dt className="text-xs tracking-wide text-neutral-500 uppercase">
                  {t("faturalama.abonelik.erisim")}
                </dt>
                <dd>
                  <Badge tone={abonelik.erisim ? "success" : "danger"}>
                    {t(
                      abonelik.erisim
                        ? "faturalama.abonelik.erisim.var"
                        : "faturalama.abonelik.erisim.yok",
                    )}
                  </Badge>
                </dd>
              </div>
            </dl>

            <p className="text-xs text-neutral-500">{t("faturalama.abonelik.erisim.ipucu")}</p>

            {duzenleyebilir && abonelik.durum !== "iptal" ? (
              <div>
                <Button variant="danger" onClick={() => setIptalAcik(true)}>
                  {t("faturalama.abonelik.iptal")}
                </Button>
              </div>
            ) : null}
          </>
        ) : (
          <p className="text-sm text-neutral-500">
            <span className="font-medium text-neutral-900">
              {t("faturalama.abonelik.yok")}.
            </span>{" "}
            {t("faturalama.abonelik.yok.aciklama")}
          </p>
        )}
      </CardContent>

      {iptalAcik && abonelik ? (
        <AbonelikIptalDiyalogu
          abonelik={abonelik}
          onKapat={() => setIptalAcik(false)}
          onIptalEdildi={onDegisti}
        />
      ) : null}
    </Card>
  );
}
