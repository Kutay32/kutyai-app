"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { sayiBicimle, tarihSaatBicimle } from "@/lib/bicim";
import { useDil } from "@/lib/dil";
import type { LogKonusmasi } from "@/lib/tipler";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

/** Konuşma kayıtları tablosu; satıra tıklama detay sayfasına götürür. */
export function LogTablosu({ kayitlar }: { kayitlar: LogKonusmasi[] }) {
  const { t } = useDil();
  const yonlendir = useRouter();

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>{t("kayit.tablo.baslik")}</TableHead>
          <TableHead>{t("kayit.tablo.kullanici")}</TableHead>
          <TableHead>{t("kayit.tablo.model")}</TableHead>
          <TableHead>{t("kayit.tablo.mesaj")}</TableHead>
          <TableHead>{t("kayit.tablo.token")}</TableHead>
          <TableHead>{t("kayit.tablo.tarih")}</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {kayitlar.map((kayit) => (
          <TableRow
            key={kayit.id}
            className="cursor-pointer"
            onClick={(olay) => {
              // Başlıktaki bağlantı kendi gezinmesini yapar; çift yönlendirme olmasın.
              if ((olay.target as HTMLElement).closest("a")) return;
              yonlendir.push(`/loglar/${kayit.id}`);
            }}
          >
            <TableCell className="max-w-xs font-medium text-neutral-900">
              <Link
                href={`/loglar/${kayit.id}`}
                className="rounded-md focus:border-neutral-900 focus:outline-none focus:ring-0"
              >
                {kayit.baslik || t("kayit.basliksiz")}
              </Link>
            </TableCell>
            <TableCell>{kayit.kullanici_eposta ?? "—"}</TableCell>
            <TableCell>{kayit.bdm_ad ?? "—"}</TableCell>
            <TableCell>{sayiBicimle(kayit.mesaj_sayisi)}</TableCell>
            <TableCell className="whitespace-nowrap">
              {sayiBicimle(kayit.token_girdi)} / {sayiBicimle(kayit.token_cikti)}
            </TableCell>
            <TableCell className="whitespace-nowrap">
              {tarihSaatBicimle(kayit.olusturulma)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
