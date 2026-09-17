"use client";

import { gecikmeBicimle, sayiBicimle, tarihSaatBicimle } from "@/lib/bicim";
import type { AracCagrisi } from "@/lib/araclar";
import { useDil } from "@/lib/dil";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export type CagriTablosuProps = {
  kayitlar: AracCagrisi[];
  onDetay: (kayit: AracCagrisi) => void;
};

/** Araç çağrı günlüğü: durum, gecikme ve çağrının kaynağı. */
export function CagriTablosu({ kayitlar, onDetay }: CagriTablosuProps) {
  const { t } = useDil();

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>{t("arac.cagri.tablo.arac")}</TableHead>
          <TableHead>{t("arac.cagri.tablo.durum")}</TableHead>
          <TableHead>{t("arac.cagri.tablo.gecikme")}</TableHead>
          <TableHead>{t("arac.cagri.konusma")}</TableHead>
          <TableHead>{t("arac.cagri.tablo.olusturulma")}</TableHead>
          <TableHead className="text-right">{t("arac.cagri.tablo.islem")}</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {kayitlar.map((kayit) => (
          <TableRow key={kayit.id}>
            <TableCell className="font-medium text-neutral-900">
              <span className="flex flex-col gap-0.5">
                {kayit.ad}
                {kayit.hata ? (
                  <span className="max-w-xs truncate text-xs font-normal text-rose-600">
                    {kayit.hata}
                  </span>
                ) : null}
              </span>
            </TableCell>
            <TableCell>
              <Badge tone={kayit.durum === "basarili" ? "success" : "danger"}>
                {kayit.durum === "basarili"
                  ? t("arac.cagri.durum.basarili")
                  : t("arac.cagri.durum.hata")}
              </Badge>
            </TableCell>
            <TableCell className="whitespace-nowrap">
              {gecikmeBicimle(kayit.gecikme_ms)}
            </TableCell>
            <TableCell className="whitespace-nowrap">
              {kayit.konusma_id === null
                ? t("arac.cagri.panel")
                : `#${sayiBicimle(kayit.konusma_id)}`}
            </TableCell>
            <TableCell className="whitespace-nowrap">
              {tarihSaatBicimle(kayit.olusturulma)}
            </TableCell>
            <TableCell className="text-right">
              <Button variant="ghost" size="sm" onClick={() => onDetay(kayit)}>
                {t("arac.cagri.detay")}
              </Button>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
