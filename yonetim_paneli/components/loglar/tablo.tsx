"use client";

import type { LogKonusmasi } from "@/lib/tipler";
import { sayiBicimle, tarihSaatBicimle } from "@/lib/bicim";
import Link from "next/link";
import { useRouter } from "next/navigation";

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
  const yonlendir = useRouter();

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Başlık</TableHead>
          <TableHead>Kullanıcı</TableHead>
          <TableHead>Model</TableHead>
          <TableHead>Mesaj</TableHead>
          <TableHead>Token (giriş/çıkış)</TableHead>
          <TableHead>Tarih</TableHead>
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
                {kayit.baslik || "Başlıksız konuşma"}
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
