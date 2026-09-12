"use client";

import { Activity, Cpu, MessageSquare, RefreshCw } from "lucide-react";

import { istek } from "@/lib/api";
import { gecikmeBicimle, sayiBicimle, tarihSaatBicimle } from "@/lib/bicim";
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
        <Alert tone="danger" title="Veri alınamadı">
          <p>{hata}</p>
          <Button variant="secondary" size="sm" className="mt-2" onClick={yenile}>
            <RefreshCw aria-hidden className="size-4" />
            Yeniden dene
          </Button>
        </Alert>
      </div>
    );
  }

  return <>{children}</>;
}

function SistemDurumuKarti() {
  const { veri, yukleniyor, hata, yenile } = useUzakVeri<SaglikYaniti>(
    () => istek<SaglikYaniti>("/saglik", { jeton: null }),
    [],
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity aria-hidden className="size-4 text-neutral-500" />
          Sistem Durumu
        </CardTitle>
        <CardDescription>API sunucusunun canlılık bilgisi.</CardDescription>
      </CardHeader>
      <BlokDurumu yukleniyor={yukleniyor} hata={hata} yenile={yenile}>
        {veri ? (
          <CardContent className="flex flex-col gap-3">
            <div className="flex items-center gap-2">
              <Badge tone={veri.durum === "ayakta" ? "success" : "warning"}>
                {veri.durum === "ayakta" ? "Ayakta" : veri.durum}
              </Badge>
              <span className="text-sm text-neutral-500">Sürüm {veri.surum}</span>
            </div>
            <dl className="grid gap-1 text-sm">
              <div className="flex justify-between gap-4">
                <dt className="text-neutral-500">Ortam</dt>
                <dd className="text-neutral-900">{veri.ortam}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-neutral-500">Sunucu zamanı</dt>
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
  const { veri, yukleniyor, hata, yenile } = useUzakVeri<SurucuDurumu>(() =>
    istek<SurucuDurumu>("/bdm/yonetim/surucu/durum"),
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Cpu aria-hidden className="size-4 text-neutral-500" />
          Sürücü ve GPU
        </CardTitle>
        <CardDescription>Konteyner çalışma zamanı ve hızlandırıcı durumu.</CardDescription>
      </CardHeader>
      <BlokDurumu yukleniyor={yukleniyor} hata={hata} yenile={yenile}>
        {veri ? (
          <CardContent className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={veri.docker ? "success" : "danger"}>
                Docker {veri.docker ? "hazır" : "yok"}
              </Badge>
              <Badge tone={veri.gpu ? "success" : "warning"}>
                GPU {veri.gpu ? "hazır" : "yok"}
              </Badge>
              <span className="text-sm text-neutral-500">Sürücü: {veri.surucu}</span>
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
              <Alert tone="warning" title="Docker bulunamadı">
                Docker çalışma zamanı olmadan yerel konteyner modelleri
                (Ollama, vLLM, TGI) başlatılamaz.
              </Alert>
            ) : null}

            {!veri.gpu ? (
              <Alert tone="warning" title="GPU bulunamadı">
                Bu sunucuda GPU yok; vLLM ve TGI gibi GPU gerektiren modeller
                başlatılamaz. Ollama gibi CPU uyumlu bir sağlayıcı seçin veya GPU
                çalışma zamanını kurun.
              </Alert>
            ) : null}
          </CardContent>
        ) : null}
      </BlokDurumu>
    </Card>
  );
}

function KullanimOzetiKarti() {
  const { veri, yukleniyor, hata, yenile } = useUzakVeri<KullanimOzeti>(() =>
    istek<KullanimOzeti>("/kullanim/ozet?gun=30"),
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle>Kullanım Özeti</CardTitle>
        <CardDescription>Son 30 günün toplu kullanım değerleri.</CardDescription>
      </CardHeader>
      <BlokDurumu yukleniyor={yukleniyor} hata={hata} yenile={yenile}>
        {veri ? (
          <CardContent className="grid gap-3 md:grid-cols-3">
            <StatCard label="Toplam istek" value={sayiBicimle(veri.toplam_istek)} />
            <StatCard label="Toplam token" value={sayiBicimle(veri.toplam_token)} />
            <StatCard label="Ortalama gecikme" value={gecikmeBicimle(veri.ortalama_gecikme_ms)} />
            <StatCard label="Başarılı" value={sayiBicimle(veri.basarili)} />
            <StatCard label="Hatalı" value={sayiBicimle(veri.hatali)} />
            <StatCard label="Kota aşımı" value={sayiBicimle(veri.kota_asimi)} />
          </CardContent>
        ) : null}
      </BlokDurumu>
    </Card>
  );
}

function SonKonusmalarKarti() {
  const { veri, yukleniyor, hata, yenile } = useUzakVeri<Sayfa<LogKonusmasi>>(() =>
    istek<Sayfa<LogKonusmasi>>("/loglar/konusmalar?boyut=5"),
  );

  return (
    <Card className="rounded-2xl">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MessageSquare aria-hidden className="size-4 text-neutral-500" />
          Son Konuşmalar
        </CardTitle>
        <CardDescription>En güncel beş konuşma kaydı.</CardDescription>
      </CardHeader>
      <BlokDurumu yukleniyor={yukleniyor} hata={hata} yenile={yenile}>
        {veri ? (
          veri.kayitlar.length > 0 ? (
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Başlık</TableHead>
                    <TableHead>Kullanıcı</TableHead>
                    <TableHead>Model</TableHead>
                    <TableHead>Mesaj</TableHead>
                    <TableHead>Tarih</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {veri.kayitlar.map((kayit) => (
                    <TableRow key={kayit.id}>
                      <TableCell className="font-medium text-neutral-900">
                        {kayit.baslik || "Başlıksız konuşma"}
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
                title="Henüz konuşma yok"
                description="Kullanıcılar sohbet etmeye başladığında kayıtlar burada listelenir."
              />
            </CardContent>
          )
        ) : null}
      </BlokDurumu>
    </Card>
  );
}

export default function KontrolPaneliSayfasi() {
  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight text-neutral-900">
          Kontrol Paneli
        </h1>
        <p className="text-sm text-neutral-500">
          Platformun genel durumu, kullanım değerleri ve son konuşmalar.
        </p>
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
