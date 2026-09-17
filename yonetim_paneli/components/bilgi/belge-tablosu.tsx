"use client";

import { RefreshCw, Trash2 } from "lucide-react";

import { sayiBicimle, tarihSaatBicimle } from "@/lib/bicim";
import { KAYNAK_ANAHTARI, type BelgeOzeti } from "@/lib/bilgi-tabani";
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

export type BelgeTablosuProps = {
  kayitlar: BelgeOzeti[];
  /** Yeniden gömmesi süren belgenin kimliği; düğme bu satırda kilitlenir. */
  tazelenenId: number | null;
  /** RAG yazma yetkisi; `false` iken yalnız ayrıntı görüntülenir. */
  yazabilir: boolean;
  onDetay: (belge: BelgeOzeti) => void;
  onTazele: (belge: BelgeOzeti) => void;
  onSil: (belge: BelgeOzeti) => void;
};

/** Bilgi tabanı belgeleri: kaynak türü, parça sayısı ve bakım eylemleri. */
export function BelgeTablosu({
  kayitlar,
  tazelenenId,
  yazabilir,
  onDetay,
  onTazele,
  onSil,
}: BelgeTablosuProps) {
  const { t } = useDil();

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>{t("bilgi.tablo.ad")}</TableHead>
          <TableHead>{t("bilgi.tablo.kaynak")}</TableHead>
          <TableHead>{t("bilgi.tablo.parca")}</TableHead>
          <TableHead>{t("bilgi.tablo.olusturulma")}</TableHead>
          <TableHead className="text-right">{t("bilgi.tablo.islem")}</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {kayitlar.map((belge) => (
          <TableRow key={belge.id}>
            <TableCell className="max-w-xs font-medium text-neutral-900">
              <button
                type="button"
                onClick={() => onDetay(belge)}
                className="rounded-md text-left transition-colors hover:text-neutral-600 focus:border-neutral-900 focus:outline-none focus:ring-0"
              >
                {belge.ad}
              </button>
            </TableCell>
            <TableCell>
              <Badge tone={belge.kaynak === "dosya" ? "info" : "neutral"}>
                {t(KAYNAK_ANAHTARI[belge.kaynak])}
              </Badge>
            </TableCell>
            <TableCell className="whitespace-nowrap">
              {sayiBicimle(belge.parca_sayisi)}
            </TableCell>
            <TableCell className="whitespace-nowrap">
              {tarihSaatBicimle(belge.olusturulma)}
            </TableCell>
            <TableCell>
              <div className="flex items-center justify-end gap-1">
                <Button variant="ghost" size="sm" onClick={() => onDetay(belge)}>
                  {t("bilgi.ayrinti")}
                </Button>
                {yazabilir ? (
                  <>
                    <Button
                      variant="ghost"
                      size="sm"
                      loading={tazelenenId === belge.id}
                      onClick={() => onTazele(belge)}
                    >
                      <RefreshCw aria-hidden className="size-4" />
                      {t("bilgi.tazele")}
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => onSil(belge)}>
                      <Trash2 aria-hidden className="size-4" />
                      {t("bilgi.sil")}
                    </Button>
                  </>
                ) : null}
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
