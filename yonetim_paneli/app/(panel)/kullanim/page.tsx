"use client";

import { useState } from "react";

import { BarChart3 } from "lucide-react";

import { gecikmeBicimle, sayiBicimle } from "@/lib/bicim";
import {
  GUN_SECENEKLERI,
  KIRILIMLAR,
  KIRILIM_ETIKETI,
  kullanimOzetiGetir,
  kullanimZamanSerisiGetir,
  seriyiSirala,
  type GunSecenegi,
  type Kirilim,
  type ZamanSerisiKaydi,
} from "@/lib/kullanim";
import { useUzakVeri } from "@/lib/kancalar";
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

const OLCU_ETIKETI: Record<CubukOlcusu, string> = {
  istek: "İstek",
  token: "Token",
};

function OzetKartlari({ ozet }: { ozet: KullanimOzeti }) {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      <StatCard label="Toplam istek" value={sayiBicimle(ozet.toplam_istek)} />
      <StatCard label="Toplam token" value={sayiBicimle(ozet.toplam_token)} />
      <StatCard label="Ortalama gecikme" value={gecikmeBicimle(ozet.ortalama_gecikme_ms)} />
      <StatCard label="Başarılı" value={sayiBicimle(ozet.basarili)} />
      <StatCard label="Hatalı" value={sayiBicimle(ozet.hatali)} />
      <StatCard label="Kota aşımı" value={sayiBicimle(ozet.kota_asimi)} />
    </div>
  );
}

function KirilimTablosu({ seri }: { seri: ZamanSerisiKaydi[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Kırılım</TableHead>
          <TableHead className="text-right">İstek</TableHead>
          <TableHead className="text-right">Token</TableHead>
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
          <h1 className="text-2xl font-semibold tracking-tight text-neutral-900">Kullanım</h1>
          <p className="text-sm text-neutral-500">
            İstek, token ve gecikme değerleri; model veya kullanıcı kırılımında.
          </p>
        </div>

        <Tabs
          className="w-fit"
          items={GUN_SECENEKLERI.map((secenek) => ({
            value: String(secenek),
            label: `${secenek} gün`,
          }))}
          value={String(gun)}
          onValueChange={(deger) => setGun(Number(deger) as GunSecenegi)}
        />
      </header>

      <section className="flex flex-col gap-4" aria-label="Kullanım özeti">
        <h2 className="text-base font-semibold text-neutral-900">Özet</h2>
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

      <section className="flex flex-col gap-4" aria-label="Kırılım grafiği">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <h2 className="text-base font-semibold text-neutral-900">Kırılım</h2>
          <Tabs
            className="w-fit"
            items={KIRILIMLAR.map((secenek) => ({
              value: secenek,
              label: KIRILIM_ETIKETI[secenek],
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
                {KIRILIM_ETIKETI[kirilim]} kullanım
              </CardTitle>
              <CardDescription>
                Son {gun} günün {OLCU_ETIKETI[olcu].toLocaleLowerCase("tr")} toplamı.
              </CardDescription>
            </div>
            <Select
              aria-label="Ölçü"
              className="w-36"
              value={olcu}
              onChange={(olay) => setOlcu(olay.target.value as CubukOlcusu)}
            >
              <option value="token">Token</option>
              <option value="istek">İstek</option>
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
                  title="Bu aralıkta kullanım yok"
                  description="Seçilen gün aralığında kayıtlı istek bulunmuyor."
                />
              </CardContent>
            )}
          </VeriDurumu>
        </Card>
      </section>
    </div>
  );
}
