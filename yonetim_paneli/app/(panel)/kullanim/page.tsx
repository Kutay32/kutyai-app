"use client";

import { useState } from "react";

import { BarChart3 } from "lucide-react";

import { gecikmeBicimle, sayiBicimle } from "@/lib/bicim";
import { useDil } from "@/lib/dil";
import {
  GUN_SECENEKLERI,
  KIRILIMLAR,
  KIRILIM_ANAHTARI,
  kullanimOzetiGetir,
  kullanimZamanSerisiGetir,
  seriyiSirala,
  type GunSecenegi,
  type Kirilim,
  type ZamanSerisiKaydi,
} from "@/lib/kullanim";
import { useUzakVeri } from "@/lib/kancalar";
import type { SozlukAnahtari } from "@/lib/sozluk";
import type { KullanimOzeti } from "@/lib/tipler";
import { CubukGrafik, type CubukOlcusu } from "./grafik";
import { VeriDurumu } from "@/components/loglar/veri-durumu";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Select } from "@/components/ui/select";
import { StatCard } from "@/components/ui/stat-card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs } from "@/components/ui/tabs";

const OLCU_ANAHTARI: Record<CubukOlcusu, SozlukAnahtari> = {
  istek: "kullanim.olcu.istek",
  token: "kullanim.olcu.token",
};

function OzetKartlari({ ozet }: { ozet: KullanimOzeti }) {
  const { t } = useDil();

  return (
    <div className="grid gap-4 md:grid-cols-3">
      <StatCard label={t("kullanim.ozet.toplam_istek")} value={sayiBicimle(ozet.toplam_istek)} />
      <StatCard label={t("kullanim.ozet.toplam_token")} value={sayiBicimle(ozet.toplam_token)} />
      <StatCard
        label={t("kullanim.ozet.ortalama_gecikme")}
        value={gecikmeBicimle(ozet.ortalama_gecikme_ms)}
      />
      <StatCard label={t("kullanim.ozet.basarili")} value={sayiBicimle(ozet.basarili)} />
      <StatCard label={t("kullanim.ozet.hatali")} value={sayiBicimle(ozet.hatali)} />
      <StatCard label={t("kullanim.ozet.kota_asimi")} value={sayiBicimle(ozet.kota_asimi)} />
    </div>
  );
}

function KirilimTablosu({ seri }: { seri: ZamanSerisiKaydi[] }) {
  const { t } = useDil();

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>{t("kullanim.kirilim.baslik")}</TableHead>
          <TableHead className="text-right">{t("kullanim.olcu.istek")}</TableHead>
          <TableHead className="text-right">{t("kullanim.olcu.token")}</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {seri.map((kayit) => (
          <TableRow key={kayit.etiket}>
            <TableCell className="break-words text-neutral-900">{kayit.etiket}</TableCell>
            <TableCell className="text-right">{sayiBicimle(kayit.istek)}</TableCell>
            <TableCell className="text-right">{sayiBicimle(kayit.token)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export default function KullanimSayfasi() {
  const { t, dil } = useDil();
  const [gun, setGun] = useState<GunSecenegi>(30);
  const [kirilim, setKirilim] = useState<Kirilim>("bdm");
  const [olcu, setOlcu] = useState<CubukOlcusu>("token");

  const ozet = useUzakVeri<KullanimOzeti>(() => kullanimOzetiGetir(gun), [gun]);
  const seri = useUzakVeri<ZamanSerisiKaydi[]>(
    () => kullanimZamanSerisiGetir(gun, kirilim),
    [gun, kirilim],
  );

  const sirali = seri.veri ? seriyiSirala(seri.veri, olcu) : [];

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold tracking-tight text-neutral-900">
            {t("kullanim.baslik")}
          </h1>
          <p className="text-sm text-neutral-500">{t("kullanim.aciklama")}</p>
        </div>

        <Tabs
          className="w-fit"
          items={GUN_SECENEKLERI.map((secenek) => ({
            value: String(secenek),
            label: t("kullanim.gun", { gun: secenek }),
          }))}
          value={String(gun)}
          onValueChange={(deger) => setGun(Number(deger) as GunSecenegi)}
        />
      </header>

      <section className="flex flex-col gap-4" aria-label={t("kullanim.ozet.aria")}>
        <h2 className="text-base font-semibold text-neutral-900">{t("kullanim.ozet.baslik")}</h2>
        <Card className="rounded-2xl">
          <VeriDurumu
            yukleniyor={ozet.yukleniyor}
            hata={ozet.hata}
            yenile={ozet.yenile}
          >
            {ozet.veri ? (
              <CardContent className="grid gap-4 pt-4">
                <OzetKartlari ozet={ozet.veri} />
              </CardContent>
            ) : null}
          </VeriDurumu>
        </Card>
      </section>

      <section className="flex flex-col gap-4" aria-label={t("kullanim.kirilim.aria")}>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <h2 className="text-base font-semibold text-neutral-900">
            {t("kullanim.kirilim.baslik")}
          </h2>
          <Tabs
            className="w-fit"
            items={KIRILIMLAR.map((secenek) => ({
              value: secenek,
              label: t(KIRILIM_ANAHTARI[secenek]),
            }))}
            value={kirilim}
            onValueChange={(deger) => setKirilim(deger as Kirilim)}
          />
        </div>

        <Card className="rounded-2xl">
          <CardHeader className="flex-row items-center justify-between gap-4">
            <div className="flex flex-col gap-1">
              <CardTitle className="flex items-center gap-2">
                <BarChart3 aria-hidden className="size-4 text-neutral-500" />
                {t("kullanim.grafik.baslik", { kirilim: t(KIRILIM_ANAHTARI[kirilim]) })}
              </CardTitle>
              <CardDescription>
                {t("kullanim.grafik.aciklama", {
                  gun,
                  olcu: t(OLCU_ANAHTARI[olcu]).toLocaleLowerCase(dil),
                })}
              </CardDescription>
            </div>
            <Select
              aria-label={t("kullanim.olcu.aria")}
              className="w-36"
              value={olcu}
              onChange={(olay) => setOlcu(olay.target.value as CubukOlcusu)}
            >
              <option value="token">{t("kullanim.olcu.token")}</option>
              <option value="istek">{t("kullanim.olcu.istek")}</option>
            </Select>
          </CardHeader>

          <VeriDurumu yukleniyor={seri.yukleniyor} hata={seri.hata} yenile={seri.yenile}>
            {sirali.length > 0 ? (
              <CardContent className="flex flex-col gap-4">
                <CubukGrafik seri={sirali} olcu={olcu} />
                <div className="rounded-lg border border-neutral-200">
                  <KirilimTablosu seri={sirali} />
                </div>
              </CardContent>
            ) : (
              <CardContent>
                <EmptyState
                  icon={<BarChart3 aria-hidden className="size-5" />}
                  title={t("kullanim.bos.baslik")}
                  description={t("kullanim.bos.aciklama")}
                />
              </CardContent>
            )}
          </VeriDurumu>
        </Card>
      </section>
    </div>
  );
}
