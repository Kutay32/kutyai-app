"use client";

import { useState } from "react";

import { Building2, Plus } from "lucide-react";

import { tarihSaatBicimle } from "@/lib/bicim";
import { useDil } from "@/lib/dil";
import { ORGANIZASYON_DURUMU_ANAHTARI, UYELIK_ROL_ANAHTARI } from "@/lib/etiketler";
import { useUzakVeri } from "@/lib/kancalar";
import { organizasyonlariGetir } from "@/lib/organizasyonlar";
import type { Organizasyon } from "@/lib/tipler";
import { OrganizasyonBilgiFormu } from "@/components/organizasyon/organizasyon-bilgi-formu";
import { UyePanosu } from "@/components/organizasyon/uye-panosu";
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
import { OrganizasyonOlusturDiyalogu } from "./organizasyon-diyaloglari";

/** `GET /organizasyonlar` ile üyelikleri listeler; seçilen kiracının üyelerini yönetir. */
export default function OrganizasyonlarSayfasi() {
  const { t } = useDil();
  const liste = useUzakVeri<Organizasyon[]>(() => organizasyonlariGetir());
  const [seciliId, setSeciliId] = useState<number | null>(null);
  const [olusturAcik, setOlusturAcik] = useState(false);

  const organizasyonlar = liste.veri ?? [];
  // Kayıtlı seçim yoksa (veya silindiyse) ilk organizasyon gösterilir.
  const secili =
    organizasyonlar.find((organizasyon) => organizasyon.id === seciliId) ??
    organizasyonlar[0] ??
    null;

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold tracking-tight text-neutral-900">
            {t("organizasyon.baslik")}
          </h1>
          <p className="text-sm text-neutral-500">{t("organizasyon.aciklama")}</p>
        </div>
        <Button onClick={() => setOlusturAcik(true)}>
          <Plus aria-hidden className="size-4" />
          {t("organizasyon.yeni")}
        </Button>
      </header>

      <Card className="rounded-2xl">
        <VeriDurumu yukleniyor={liste.yukleniyor} hata={liste.hata} yenile={liste.yenile}>
          {organizasyonlar.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("organizasyon.tablo.ad")}</TableHead>
                  <TableHead>{t("organizasyon.tablo.slug")}</TableHead>
                  <TableHead>{t("organizasyon.tablo.rol")}</TableHead>
                  <TableHead>{t("organizasyon.tablo.durum")}</TableHead>
                  <TableHead>{t("organizasyon.tablo.olusturulma")}</TableHead>
                  <TableHead className="text-right">
                    {t("organizasyon.tablo.islemler")}
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {organizasyonlar.map((organizasyon) => (
                  <TableRow
                    key={organizasyon.id}
                    className={secili?.id === organizasyon.id ? "bg-neutral-50" : undefined}
                  >
                    <TableCell className="font-medium text-neutral-900">
                      {organizasyon.ad}
                    </TableCell>
                    <TableCell className="font-mono text-xs">{organizasyon.slug}</TableCell>
                    <TableCell>
                      {organizasyon.rol ? t(UYELIK_ROL_ANAHTARI[organizasyon.rol]) : "—"}
                    </TableCell>
                    <TableCell>
                      <Badge
                        tone={organizasyon.durum === "aktif" ? "success" : "warning"}
                      >
                        {t(ORGANIZASYON_DURUMU_ANAHTARI[organizasyon.durum])}
                      </Badge>
                    </TableCell>
                    <TableCell className="whitespace-nowrap">
                      {tarihSaatBicimle(organizasyon.olusturulma)}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center justify-end">
                        <Button
                          variant={secili?.id === organizasyon.id ? "primary" : "secondary"}
                          size="sm"
                          onClick={() => setSeciliId(organizasyon.id)}
                        >
                          {t("organizasyon.sec")}
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="p-4">
              <EmptyState
                icon={<Building2 aria-hidden className="size-5" />}
                title={t("organizasyon.bos.baslik")}
                description={t("organizasyon.bos.aciklama")}
                action={
                  <Button onClick={() => setOlusturAcik(true)}>
                    <Plus aria-hidden className="size-4" />
                    {t("organizasyon.yeni")}
                  </Button>
                }
              />
            </div>
          )}
        </VeriDurumu>
      </Card>

      {secili ? (
        <section className="flex flex-col gap-6">
          <h2 className="text-lg font-semibold tracking-tight text-neutral-900">
            {t("organizasyon.detay.baslik", { ad: secili.ad })}
          </h2>
          <OrganizasyonBilgiFormu
            key={`bilgi-${secili.id}`}
            organizasyon={secili}
            onKaydedildi={liste.yenile}
          />
          {/* `son_kullanici` rolü üye listesini okuyamaz (`GORUNTULEME_ROLLERI` dışı). */}
          {secili.rol !== "son_kullanici" ? (
            <UyePanosu key={`uyeler-${secili.id}`} organizasyon={secili} />
          ) : null}
        </section>
      ) : (
        !liste.yukleniyor && !liste.hata ? (
          <p className="text-sm text-neutral-500">{t("organizasyon.detay.secim.ipucu")}</p>
        ) : null
      )}

      <OrganizasyonOlusturDiyalogu
        acik={olusturAcik}
        onKapat={() => setOlusturAcik(false)}
        onOlusturuldu={(organizasyonId) => {
          setSeciliId(organizasyonId);
          liste.yenile();
        }}
      />
    </div>
  );
}
