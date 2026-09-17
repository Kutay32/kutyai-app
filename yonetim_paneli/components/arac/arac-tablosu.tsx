"use client";

import { Pencil, Play, Trash2 } from "lucide-react";

import type { Arac } from "@/lib/araclar";
import { tarihSaatBicimle } from "@/lib/bicim";
import { useDil } from "@/lib/dil";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export type AracTablosuProps = {
  araclar: Arac[];
  /** Etkinliği sunucuda güncellenen aracın kimliği; anahtar bu satırda kilitlenir. */
  degisenId: number | null;
  /** Araç yazma yetkisi; `false` iken etkinlik rozet olarak gösterilir, eylemler gizlenir. */
  yazabilir: boolean;
  onEtkinDegistir: (arac: Arac, etkin: boolean) => void;
  onDuzenle: (arac: Arac) => void;
  onDene: (arac: Arac) => void;
  onSil: (arac: Arac) => void;
};

/** Araç listesi: tür/uç noktası bilgisi, etkinlik anahtarı ve satır eylemleri. */
export function AracTablosu({
  araclar,
  degisenId,
  yazabilir,
  onEtkinDegistir,
  onDuzenle,
  onDene,
  onSil,
}: AracTablosuProps) {
  const { t } = useDil();

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>{t("arac.tablo.ad")}</TableHead>
          <TableHead>{t("arac.tablo.slug")}</TableHead>
          <TableHead>{t("arac.tablo.tur")}</TableHead>
          <TableHead>{t("arac.tablo.uc")}</TableHead>
          <TableHead>{t("arac.tablo.etkin")}</TableHead>
          <TableHead>{t("arac.tablo.olusturulma")}</TableHead>
          {yazabilir ? (
            <TableHead className="text-right">{t("arac.tablo.islem")}</TableHead>
          ) : null}
        </TableRow>
      </TableHeader>
      <TableBody>
        {araclar.map((arac) => (
          <TableRow key={arac.id}>
            <TableCell className="max-w-xs font-medium text-neutral-900">
              <span className="flex flex-col gap-0.5">
                {arac.ad}
                {arac.aciklama ? (
                  <span className="truncate text-xs font-normal text-neutral-500">
                    {arac.aciklama}
                  </span>
                ) : null}
              </span>
            </TableCell>
            <TableCell>
              <Badge tone="neutral" className="font-mono">
                {arac.slug}
              </Badge>
            </TableCell>
            <TableCell>
              <Badge tone={arac.tur === "yerlesik" ? "info" : "neutral"}>
                {arac.tur === "yerlesik" ? t("arac.tur.yerlesik") : t("arac.tur.webhook")}
              </Badge>
            </TableCell>
            <TableCell className="max-w-xs truncate font-mono text-xs text-neutral-600">
              {arac.uc_noktasi || "—"}
            </TableCell>
            <TableCell>
              {yazabilir ? (
                <Switch
                  id={`arac-etkin-${arac.id}`}
                  checked={arac.etkin}
                  disabled={degisenId === arac.id}
                  label={arac.etkin ? t("arac.etkin.acik") : t("arac.etkin.kapali")}
                  onChange={(etkin) => onEtkinDegistir(arac, etkin)}
                />
              ) : (
                <Badge tone={arac.etkin ? "success" : "neutral"}>
                  {arac.etkin ? t("arac.etkin.acik") : t("arac.etkin.kapali")}
                </Badge>
              )}
            </TableCell>
            <TableCell className="whitespace-nowrap">
              {tarihSaatBicimle(arac.olusturulma)}
            </TableCell>
            {yazabilir ? (
              <TableCell>
                <div className="flex items-center justify-end gap-1">
                  <Button variant="ghost" size="sm" onClick={() => onDene(arac)}>
                    <Play aria-hidden className="size-4" />
                    {t("arac.eylem.dene")}
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => onDuzenle(arac)}>
                    <Pencil aria-hidden className="size-4" />
                    {t("arac.eylem.duzenle")}
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => onSil(arac)}>
                    <Trash2 aria-hidden className="size-4" />
                    {t("arac.eylem.sil")}
                  </Button>
                </div>
              </TableCell>
            ) : null}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
