"use client";

import { useState } from "react";

import { ExternalLink, FileText } from "lucide-react";

import { sayiBicimle, tarihSaatBicimle } from "@/lib/bicim";
import { cn } from "@/lib/cn";
import { useDil } from "@/lib/dil";
import {
  FATURA_DURUMU_ANAHTARI,
  FATURA_DURUMU_TONU,
  FATURA_SAYFA_BOYUTLARI,
  elleTahsilatYapilabilirMi,
  faturalamaHatasi,
  odemeOturumuOlustur,
  type Fatura,
} from "@/lib/faturalama";
import type { Sayfa } from "@/lib/tipler";
import { Sayfalama } from "@/components/loglar/sayfalama";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { FOCUS_RING } from "@/components/ui/stiller";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";
import { FaturaDetayDiyalogu, FaturaOdendiDiyalogu } from "./faturalama-diyaloglari";

/**
 * `GET /faturalama/faturalar` tablosu. Eylemler sağlayıcıya göre ayrılır:
 * elle tahsilat yalnız `yerel`, ödeme oturumu yalnız `stripe`.
 */
export function FaturaTablosu({
  sayfa,
  saglayici,
  duzenleyebilir,
  onSayfa,
  onBoyut,
  onDegisti,
}: {
  sayfa: Sayfa<Fatura>;
  saglayici: string | undefined;
  /** Faturalama yazma yetkisi; `false` iken ödeme/tahsilat düğmeleri gizlenir. */
  duzenleyebilir: boolean;
  onSayfa: (sayfa: number) => void;
  onBoyut: (boyut: number) => void;
  onDegisti: () => void;
}) {
  const { t } = useDil();
  const { showToast } = useToast();
  const [detay, setDetay] = useState<Fatura | null>(null);
  const [odendiFatura, setOdendiFatura] = useState<Fatura | null>(null);
  const [baglantilar, setBaglantilar] = useState<Record<number, string>>({});
  const [isleniyorId, setIsleniyorId] = useState<number | null>(null);
  const [hata, setHata] = useState<string | null>(null);

  const elleTahsilat = elleTahsilatYapilabilirMi(saglayici);
  const stripe = saglayici === "stripe";

  const baglantiOlustur = async (fatura: Fatura) => {
    setIsleniyorId(fatura.id);
    setHata(null);
    try {
      const oturum = await odemeOturumuOlustur(fatura.id);
      const adres = oturum.url;
      if (adres) {
        setBaglantilar((onceki) => ({ ...onceki, [fatura.id]: adres }));
        showToast(t("faturalama.fatura.odeme.basarili"), "success");
      } else {
        showToast(t("faturalama.fatura.odeme.baglanti_yok"), "warning");
      }
      onDegisti();
    } catch (sebep) {
      setHata(faturalamaHatasi(sebep));
    } finally {
      setIsleniyorId(null);
    }
  };

  return (
    <Card className="rounded-2xl">
      <div className="flex flex-col gap-1 p-4">
        <h2 className="text-base font-semibold text-neutral-900">
          {t("faturalama.faturalar.baslik")}
        </h2>
        <p className="text-sm text-neutral-500">{t("faturalama.faturalar.aciklama")}</p>
      </div>

      {hata ? (
        <div className="px-4 pb-4">
          <Alert tone="danger" title={t("faturalama.fatura.odeme.hata.baslik")}>
            {hata}
          </Alert>
        </div>
      ) : null}

      {sayfa.kayitlar.length > 0 ? (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("faturalama.fatura.no")}</TableHead>
                <TableHead>{t("faturalama.fatura.tutar")}</TableHead>
                <TableHead>{t("faturalama.fatura.durum")}</TableHead>
                <TableHead>{t("faturalama.fatura.olusturulma")}</TableHead>
                <TableHead>{t("faturalama.fatura.odeme_tarihi")}</TableHead>
                <TableHead className="text-right">
                  {t("faturalama.fatura.islemler")}
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sayfa.kayitlar.map((fatura) => {
                const odendi = fatura.durum === "odendi";
                const baglanti = baglantilar[fatura.id];
                return (
                  <TableRow key={fatura.id}>
                    <TableCell className="font-medium text-neutral-900">
                      #{sayiBicimle(fatura.id)}
                    </TableCell>
                    <TableCell className="whitespace-nowrap">{fatura.tutar}</TableCell>
                    <TableCell>
                      <Badge tone={FATURA_DURUMU_TONU[fatura.durum]}>
                        {t(FATURA_DURUMU_ANAHTARI[fatura.durum])}
                      </Badge>
                    </TableCell>
                    <TableCell className="whitespace-nowrap">
                      {tarihSaatBicimle(fatura.olusturulma)}
                    </TableCell>
                    <TableCell className="whitespace-nowrap">
                      {fatura.odeme_tarihi ? tarihSaatBicimle(fatura.odeme_tarihi) : "—"}
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap items-center justify-end gap-2">
                        <Button variant="secondary" size="sm" onClick={() => setDetay(fatura)}>
                          {t("faturalama.fatura.detay")}
                        </Button>

                        {baglanti ? (
                          <a
                            href={baglanti}
                            target="_blank"
                            rel="noreferrer"
                            className={cn(
                              "inline-flex h-8 items-center justify-center gap-1.5 rounded-md border border-neutral-300 bg-white px-3 text-sm font-medium whitespace-nowrap text-neutral-900 transition-colors hover:border-neutral-900",
                              FOCUS_RING,
                            )}
                          >
                            <ExternalLink aria-hidden className="size-4" />
                            {t("faturalama.abone.odeme")}
                          </a>
                        ) : duzenleyebilir && stripe && !odendi ? (
                          <Button
                            variant="secondary"
                            size="sm"
                            loading={isleniyorId === fatura.id}
                            onClick={() => void baglantiOlustur(fatura)}
                          >
                            {t("faturalama.fatura.odeme")}
                          </Button>
                        ) : null}

                        {duzenleyebilir && elleTahsilat && !odendi ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setOdendiFatura(fatura)}
                          >
                            {t("faturalama.fatura.odendi")}
                          </Button>
                        ) : null}
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
          <div className="border-t border-neutral-200">
            <Sayfalama
              toplam={sayfa.toplam}
              sayfa={sayfa.sayfa}
              boyut={sayfa.boyut}
              boyutlar={FATURA_SAYFA_BOYUTLARI}
              onSayfa={onSayfa}
              onBoyut={onBoyut}
            />
          </div>
        </>
      ) : (
        <div className="p-4">
          <EmptyState
            icon={<FileText aria-hidden className="size-5" />}
            title={t("faturalama.faturalar.bos.baslik")}
            description={t("faturalama.faturalar.bos.aciklama")}
          />
        </div>
      )}

      {detay ? <FaturaDetayDiyalogu fatura={detay} onKapat={() => setDetay(null)} /> : null}

      {odendiFatura ? (
        <FaturaOdendiDiyalogu
          fatura={odendiFatura}
          onKapat={() => setOdendiFatura(null)}
          onIsaretlendi={onDegisti}
        />
      ) : null}
    </Card>
  );
}
