"use client";

import { Activity, Cpu, MessageSquare, RefreshCw } from "lucide-react";

import { istek } from "@/lib/api";
import { gecikmeBicimle, sayiBicimle, tarihSaatBicimle } from "@/lib/bicim";
import { useDil } from "@/lib/dil";
import { useUzakVeri } from "@/lib/kancalar";
import type {
  KullanimOzeti,
  LogKonusmasi,
  SaglikYaniti,
  Sayfa,
  SurucuDurumu,
} from "@/lib/tipler";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { StatCard } from "@/components/ui/stat-card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

/** Bir bloğun yükleniyor/hata durumunu sade biçimde gösterir. */
function BlokDurumu({
  yukleniyor,
  hata,
  yenile,
  children,
}: {
  yukleniyor: boolean;
  hata: string | null;
  yenile: () => void;
  children: React.ReactNode;
}) {
  const { t } = useDil();

  if (yukleniyor) {
    return (
      <div className="flex flex-col gap-2 p-4">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-4 w-2/3" />
      </div>
    );
  }

  if (hata) {
    return (
      <div className="p-4">
        <Alert tone="danger" title={t("kontrol.hata.baslik")}>
          <p>{hata}</p>
          <Button variant="secondary" size="sm" className="mt-2" onClick={yenile}>
            <RefreshCw aria-hidden className="size-4" />
            {t("genel.yeniden_dene")}
          </Button>
        </Alert>
      </div>
    );
  }

  return <>{children}</>;
}

function SistemDurumuKarti() {
  const { t } = useDil();
  const { veri, yukleniyor, hata, yenile } = useUzakVeri<SaglikYaniti>(
    () => istek<SaglikYaniti>("/saglik", { jeton: null }),
    [],
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity aria-hidden className="size-4 text-neutral-500" />
          {t("kontrol.sistem.baslik")}
        </CardTitle>
        <CardDescription>{t("kontrol.sistem.aciklama")}</CardDescription>
      </CardHeader>
      <BlokDurumu yukleniyor={yukleniyor} hata={hata} yenile={yenile}>
        {veri ? (
          <CardContent className="flex flex-col gap-3">
            <div className="flex items-center gap-2">
              <Badge tone={veri.durum === "ayakta" ? "success" : "warning"}>
                {veri.durum === "ayakta" ? t("kontrol.sistem.ayakta") : veri.durum}
              </Badge>
              <span className="text-sm text-neutral-500">
                {t("kontrol.sistem.surum", { surum: veri.surum })}
              </span>
            </div>
            <dl className="grid gap-1 text-sm">
              <div className="flex justify-between gap-4">
                <dt className="text-neutral-500">{t("kontrol.sistem.ortam")}</dt>
                <dd className="text-neutral-900">{veri.ortam}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-neutral-500">{t("kontrol.sistem.zaman")}</dt>
                <dd className="text-neutral-900">{tarihSaatBicimle(veri.zaman)}</dd>
              </div>
            </dl>
          </CardContent>
        ) : null}
      </BlokDurumu>
    </Card>
  );
}

function SurucuDurumuKarti() {
  const { t } = useDil();
  const { veri, yukleniyor, hata, yenile } = useUzakVeri<SurucuDurumu>(() =>
    istek<SurucuDurumu>("/bdm/yonetim/surucu/durum"),
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Cpu aria-hidden className="size-4 text-neutral-500" />
          {t("kontrol.surucu.baslik")}
        </CardTitle>
        <CardDescription>{t("kontrol.surucu.aciklama")}</CardDescription>
      </CardHeader>
      <BlokDurumu yukleniyor={yukleniyor} hata={hata} yenile={yenile}>
        {veri ? (
          <CardContent className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={veri.docker ? "success" : "danger"}>
                {t("kontrol.surucu.docker", {
                  durum: veri.docker ? t("genel.hazir") : t("genel.yok"),
                })}
              </Badge>
              <Badge tone={veri.gpu ? "success" : "warning"}>
                {t("kontrol.surucu.gpu", {
                  durum: veri.gpu ? t("genel.hazir") : t("genel.yok"),
                })}
              </Badge>
              <span className="text-sm text-neutral-500">
                {t("kontrol.surucu.surucu", { surucu: veri.surucu })}
              </span>
            </div>

            {veri.gpu && veri.gpu_listesi.length > 0 ? (
              <ul className="flex flex-col gap-1 text-sm text-neutral-700">
                {veri.gpu_listesi.map((gpu) => (
                  <li key={gpu}>{gpu}</li>
                ))}
              </ul>
            ) : null}

            {veri.mesaj ? <p className="text-sm text-neutral-600">{veri.mesaj}</p> : null}

            {!veri.docker ? (
              <Alert tone="warning" title={t("kontrol.surucu.docker_yok.baslik")}>
                {t("kontrol.surucu.docker_yok.metin")}
              </Alert>
            ) : null}

            {!veri.gpu ? (
              <Alert tone="warning" title={t("kontrol.surucu.gpu_yok.baslik")}>
                {t("kontrol.surucu.gpu_yok.metin")}
              </Alert>
            ) : null}
          </CardContent>
        ) : null}
      </BlokDurumu>
    </Card>
  );
}

function KullanimOzetiKarti() {
  const { t } = useDil();
  const { veri, yukleniyor, hata, yenile } = useUzakVeri<KullanimOzeti>(() =>
    istek<KullanimOzeti>("/kullanim/ozet?gun=30"),
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("kontrol.kullanim.baslik")}</CardTitle>
        <CardDescription>{t("kontrol.kullanim.aciklama")}</CardDescription>
      </CardHeader>
      <BlokDurumu yukleniyor={yukleniyor} hata={hata} yenile={yenile}>
        {veri ? (
          <CardContent className="grid gap-3 md:grid-cols-3">
            <StatCard
              label={t("kontrol.kullanim.toplam_istek")}
              value={sayiBicimle(veri.toplam_istek)}
            />
            <StatCard
              label={t("kontrol.kullanim.toplam_token")}
              value={sayiBicimle(veri.toplam_token)}
            />
            <StatCard
              label={t("kontrol.kullanim.ortalama_gecikme")}
              value={gecikmeBicimle(veri.ortalama_gecikme_ms)}
            />
            <StatCard
              label={t("kontrol.kullanim.basarili")}
              value={sayiBicimle(veri.basarili)}
            />
            <StatCard label={t("kontrol.kullanim.hatali")} value={sayiBicimle(veri.hatali)} />
            <StatCard
              label={t("kontrol.kullanim.kota_asimi")}
              value={sayiBicimle(veri.kota_asimi)}
            />
          </CardContent>
        ) : null}
      </BlokDurumu>
    </Card>
  );
}

function SonKonusmalarKarti() {
  const { t } = useDil();
  const { veri, yukleniyor, hata, yenile } = useUzakVeri<Sayfa<LogKonusmasi>>(() =>
    istek<Sayfa<LogKonusmasi>>("/loglar/konusmalar?boyut=5"),
  );

  return (
    <Card className="rounded-2xl">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MessageSquare aria-hidden className="size-4 text-neutral-500" />
          {t("kontrol.konusmalar.baslik")}
        </CardTitle>
        <CardDescription>{t("kontrol.konusmalar.aciklama")}</CardDescription>
      </CardHeader>
      <BlokDurumu yukleniyor={yukleniyor} hata={hata} yenile={yenile}>
        {veri ? (
          veri.kayitlar.length > 0 ? (
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t("kontrol.tablo.baslik")}</TableHead>
                    <TableHead>{t("kontrol.tablo.kullanici")}</TableHead>
                    <TableHead>{t("kontrol.tablo.model")}</TableHead>
                    <TableHead>{t("kontrol.tablo.mesaj")}</TableHead>
                    <TableHead>{t("kontrol.tablo.tarih")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {veri.kayitlar.map((kayit) => (
                    <TableRow key={kayit.id}>
                      <TableCell className="font-medium text-neutral-900">
                        {kayit.baslik || t("kontrol.konusmalar.basliksiz")}
                      </TableCell>
                      <TableCell>{kayit.kullanici_eposta ?? "—"}</TableCell>
                      <TableCell>{kayit.bdm_ad}</TableCell>
                      <TableCell>{sayiBicimle(kayit.mesaj_sayisi)}</TableCell>
                      <TableCell>{tarihSaatBicimle(kayit.olusturulma)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          ) : (
            <CardContent>
              <EmptyState
                icon={<MessageSquare aria-hidden className="size-5" />}
                title={t("kontrol.konusmalar.bos.baslik")}
                description={t("kontrol.konusmalar.bos.metin")}
              />
            </CardContent>
          )
        ) : null}
      </BlokDurumu>
    </Card>
  );
}

export default function KontrolPaneliSayfasi() {
  const { t } = useDil();

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight text-neutral-900">
          {t("menu.kontrol")}
        </h1>
        <p className="text-sm text-neutral-500">{t("kontrol.aciklama")}</p>
      </header>

      <div className="grid gap-4 md:grid-cols-2">
        <SistemDurumuKarti />
        <SurucuDurumuKarti />
      </div>

      <KullanimOzetiKarti />
      <SonKonusmalarKarti />
    </div>
  );
}
