"use client";

import { useState } from "react";

import { Mail } from "lucide-react";

import { useDil } from "@/lib/dil";
import { useUzakVeri } from "@/lib/kancalar";
import {
  aktifOrganizasyonRolu,
  organizasyonYonetebilirMi,
} from "@/lib/organizasyonlar";
import {
  SABLON_DILI_ANAHTARI,
  SABLON_KODU_ANAHTARI,
  sablonlariGetir,
  type PostaSablonu,
} from "@/lib/posta-sablonlari";
import { SablonDuzenleDrawer } from "@/components/posta/sablon-duzenle-drawer";
import { SablonOnizleDiyalogu } from "@/components/posta/sablon-onizle-diyalogu";
import { VeriDurumu } from "@/components/loglar/veri-durumu";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

/**
 * Posta şablonları sayfası: `GET /posta-sablonlari` kataloğu (6 kod × TR/EN),
 * düzenleme `PUT /posta-sablonlari`, önizleme `POST /posta-sablonlari/{kod}/onizle`.
 */
export default function PostaSablonlariSayfasi() {
  const { t } = useDil();
  const liste = useUzakVeri<PostaSablonu[]>(() => sablonlariGetir());
  const rol = useUzakVeri(aktifOrganizasyonRolu);
  const [duzenlenen, setDuzenlenen] = useState<PostaSablonu | null>(null);
  const [onizlenen, setOnizlenen] = useState<PostaSablonu | null>(null);

  // Rol bilinmiyorsa düğmeler gizlenmez; yetki kararı sunucuda kalır (403 → katalog mesajı).
  const duzenleyebilir = rol.veri === null || organizasyonYonetebilirMi(rol.veri ?? undefined);
  const sablonlar = liste.veri ?? [];

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight text-neutral-900">
          {t("posta.baslik")}
        </h1>
        <p className="text-sm text-neutral-500">{t("posta.aciklama")}</p>
      </header>

      <Card className="rounded-2xl">
        <VeriDurumu yukleniyor={liste.yukleniyor} hata={liste.hata} yenile={liste.yenile}>
          {sablonlar.length > 0 ? (
            <>
              <p className="p-4 text-xs text-neutral-500">{t("posta.degisken.ipucu")}</p>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t("posta.tablo.kod")}</TableHead>
                    <TableHead>{t("posta.tablo.dil")}</TableHead>
                    <TableHead>{t("posta.tablo.konu")}</TableHead>
                    <TableHead>{t("posta.tablo.kaynak")}</TableHead>
                    <TableHead className="text-right">{t("posta.tablo.islemler")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sablonlar.map((sablon) => (
                    <TableRow key={`${sablon.kod}-${sablon.dil}`}>
                      <TableCell className="font-medium text-neutral-900">
                        {t(SABLON_KODU_ANAHTARI[sablon.kod])}
                      </TableCell>
                      <TableCell>
                        <Badge tone="neutral">{t(SABLON_DILI_ANAHTARI[sablon.dil])}</Badge>
                      </TableCell>
                      <TableCell className="max-w-md truncate">{sablon.konu}</TableCell>
                      <TableCell>
                        <Badge tone={sablon.ozel ? "info" : "neutral"}>
                          {t(
                            sablon.ozel ? "posta.etiket.ozel" : "posta.etiket.varsayilan",
                          )}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => setOnizlenen(sablon)}
                          >
                            {t("posta.onizle")}
                          </Button>
                          {duzenleyebilir ? (
                            <Button size="sm" onClick={() => setDuzenlenen(sablon)}>
                              {t("posta.duzenle")}
                            </Button>
                          ) : null}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </>
          ) : (
            <div className="p-4">
              <EmptyState
                icon={<Mail aria-hidden className="size-5" />}
                title={t("posta.bos.baslik")}
                description={t("posta.bos.aciklama")}
              />
            </div>
          )}
        </VeriDurumu>
      </Card>

      {duzenlenen ? (
        <SablonDuzenleDrawer
          key={`${duzenlenen.kod}-${duzenlenen.dil}`}
          sablon={duzenlenen}
          onKapat={() => setDuzenlenen(null)}
          onKaydedildi={liste.yenile}
        />
      ) : null}

      {onizlenen ? (
        <SablonOnizleDiyalogu
          key={`${onizlenen.kod}-${onizlenen.dil}`}
          sablon={onizlenen}
          onKapat={() => setOnizlenen(null)}
        />
      ) : null}
    </div>
  );
}
