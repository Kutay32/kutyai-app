"use client";

import { Download, Eye, Trash2 } from "lucide-react";

import { sayiBicimle, tarihSaatBicimle } from "@/lib/bicim";
import { useDil } from "@/lib/dil";
import { boyutBicimle, type DosyaOzeti } from "@/lib/dosyalar";
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

export type DosyaTablosuProps = {
  kayitlar: DosyaOzeti[];
  /** İndirmesi süren dosyanın kimliği; düğme bu satırda kilitlenir. */
  indirilenId: number | null;
  onIndir: (dosya: DosyaOzeti) => void;
  onDetay: (dosya: DosyaOzeti) => void;
  onSil: (dosya: DosyaOzeti) => void;
};

/** Dosya listesi: meta sütunları ve indir/ayrıntı/sil eylemleri. */
export function DosyaTablosu({
  kayitlar,
  indirilenId,
  onIndir,
  onDetay,
  onSil,
}: DosyaTablosuProps) {
  const { t } = useDil();

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>{t("dosya.tablo.ad")}</TableHead>
          <TableHead>{t("dosya.tablo.tur")}</TableHead>
          <TableHead>{t("dosya.tablo.boyut")}</TableHead>
          <TableHead>{t("dosya.tablo.metin")}</TableHead>
          <TableHead>{t("dosya.tablo.olusturulma")}</TableHead>
          <TableHead className="text-right">{t("dosya.tablo.islem")}</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {kayitlar.map((dosya) => (
          <TableRow key={dosya.id}>
            <TableCell className="max-w-xs font-medium text-neutral-900">
              <button
                type="button"
                onClick={() => onDetay(dosya)}
                className="rounded-md text-left transition-colors hover:text-neutral-600 focus:border-neutral-900 focus:outline-none focus:ring-0"
              >
                {dosya.ad}
              </button>
            </TableCell>
            <TableCell>
              <Badge tone="neutral" className="font-mono">
                {dosya.mime}
              </Badge>
            </TableCell>
            <TableCell className="whitespace-nowrap">{boyutBicimle(dosya.boyut)}</TableCell>
            <TableCell className="whitespace-nowrap">
              {dosya.metin_uzunluk > 0 ? (
                t("dosya.metin.uzunluk", { sayi: sayiBicimle(dosya.metin_uzunluk) })
              ) : (
                <span className="text-neutral-500">{t("dosya.metin.yok")}</span>
              )}
            </TableCell>
            <TableCell className="whitespace-nowrap">
              {tarihSaatBicimle(dosya.olusturulma)}
            </TableCell>
            <TableCell>
              <div className="flex items-center justify-end gap-1">
                <Button
                  variant="ghost"
                  size="sm"
                  loading={indirilenId === dosya.id}
                  onClick={() => onIndir(dosya)}
                >
                  <Download aria-hidden className="size-4" />
                  {t("dosya.indir")}
                </Button>
                <Button variant="ghost" size="sm" onClick={() => onDetay(dosya)}>
                  <Eye aria-hidden className="size-4" />
                  {t("dosya.ayrinti")}
                </Button>
                <Button variant="ghost" size="sm" onClick={() => onSil(dosya)}>
                  <Trash2 aria-hidden className="size-4" />
                  {t("dosya.sil")}
                </Button>
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
