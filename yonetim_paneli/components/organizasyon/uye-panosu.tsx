"use client";

import { useState } from "react";

import { UserPlus, Users } from "lucide-react";

import { tarihSaatBicimle } from "@/lib/bicim";
import { useDil } from "@/lib/dil";
import {
  KULLANICI_DURUMU_ANAHTARI,
  KULLANICI_DURUMU_TONU,
  UYELIK_ROL_ANAHTARI,
} from "@/lib/etiketler";
import { useUzakVeri } from "@/lib/kancalar";
import { organizasyonYonetebilirMi, sonSahipMi, uyeleriGetir } from "@/lib/organizasyonlar";
import { kullaniciOku } from "@/lib/oturum";
import type { Organizasyon, OrganizasyonUyesi } from "@/lib/tipler";
import { VeriDurumu } from "@/components/loglar/veri-durumu";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { UyeDuzenleDiyalogu, UyeEkleDiyalogu, UyeSilDiyalogu } from "./uye-diyaloglari";

/**
 * `GET/POST/PATCH/DELETE /organizasyonlar/{id}/uyeler` panosu.
 * Son sahip ve kendi sahip rolü koruması arayüzde de uygulanır (`409 gecersiz_gecis`
 * yalnız yarış durumları için yedek kalır).
 */
export function UyePanosu({ organizasyon }: { organizasyon: Organizasyon }) {
  const { t } = useDil();
  const liste = useUzakVeri<OrganizasyonUyesi[]>(
    () => uyeleriGetir(organizasyon.id),
    [organizasyon.id],
  );

  const [ekleAcik, setEkleAcik] = useState(false);
  const [duzenlenen, setDuzenlenen] = useState<OrganizasyonUyesi | null>(null);
  const [silinen, setSilinen] = useState<OrganizasyonUyesi | null>(null);

  const kendimId = kullaniciOku()?.id;
  const yonetebilir = organizasyonYonetebilirMi(organizasyon.rol);
  const uyeler = liste.veri ?? [];

  return (
    <Card className="rounded-2xl">
      <CardHeader className="flex-row items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <CardTitle>{t("organizasyon.uyeler.baslik")}</CardTitle>
          <CardDescription>{t("organizasyon.uyeler.aciklama")}</CardDescription>
        </div>
        {yonetebilir ? (
          <Button onClick={() => setEkleAcik(true)}>
            <UserPlus aria-hidden className="size-4" />
            {t("organizasyon.uyeler.ekle")}
          </Button>
        ) : null}
      </CardHeader>

      <CardContent className="flex flex-col gap-3">
        {uyeler.some((uye) => sonSahipMi(uye, uyeler)) ? (
          <p className="text-xs text-neutral-500">{t("organizasyon.uyeler.koruma.ipucu")}</p>
        ) : null}

        <VeriDurumu yukleniyor={liste.yukleniyor} hata={liste.hata} yenile={liste.yenile}>
          {uyeler.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("organizasyon.uyeler.tablo.eposta")}</TableHead>
                  <TableHead>{t("organizasyon.uyeler.tablo.ad_soyad")}</TableHead>
                  <TableHead>{t("organizasyon.uyeler.tablo.rol")}</TableHead>
                  <TableHead>{t("organizasyon.uyeler.tablo.durum")}</TableHead>
                  <TableHead>{t("organizasyon.uyeler.tablo.olusturulma")}</TableHead>
                  {yonetebilir ? (
                    <TableHead className="text-right">
                      {t("organizasyon.uyeler.tablo.islemler")}
                    </TableHead>
                  ) : null}
                </TableRow>
              </TableHeader>
              <TableBody>
                {uyeler.map((uye) => {
                  const sonSahip = sonSahipMi(uye, uyeler);
                  const kendiSahipligi = uye.kullanici_id === kendimId && uye.rol === "sahip";
                  return (
                    <TableRow key={uye.kullanici_id}>
                      <TableCell className="font-medium text-neutral-900">
                        <span className="flex flex-wrap items-center gap-2">
                          {uye.eposta ?? "—"}
                          {uye.kullanici_id === kendimId ? (
                            <Badge tone="info">{t("organizasyon.uyeler.siz")}</Badge>
                          ) : null}
                          {sonSahip ? (
                            <Badge tone="warning">{t("organizasyon.uyeler.son_sahip")}</Badge>
                          ) : null}
                        </span>
                      </TableCell>
                      <TableCell>{uye.ad_soyad || "—"}</TableCell>
                      <TableCell>{t(UYELIK_ROL_ANAHTARI[uye.rol])}</TableCell>
                      <TableCell>
                        <Badge tone={KULLANICI_DURUMU_TONU[uye.durum]}>
                          {t(KULLANICI_DURUMU_ANAHTARI[uye.durum])}
                        </Badge>
                      </TableCell>
                      <TableCell className="whitespace-nowrap">
                        {tarihSaatBicimle(uye.olusturulma)}
                      </TableCell>
                      {yonetebilir ? (
                        <TableCell>
                          <div className="flex items-center justify-end gap-2">
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => setDuzenlenen(uye)}
                            >
                              {t("organizasyon.uyeler.duzenle")}
                            </Button>
                            {!sonSahip && !kendiSahipligi ? (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setSilinen(uye)}
                              >
                                {t("organizasyon.uyeler.cikar")}
                              </Button>
                            ) : null}
                          </div>
                        </TableCell>
                      ) : null}
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          ) : (
            <EmptyState
              icon={<Users aria-hidden className="size-5" />}
              title={t("organizasyon.uyeler.bos.baslik")}
              description={t("organizasyon.uyeler.bos.aciklama")}
            />
          )}
        </VeriDurumu>
      </CardContent>

      <UyeEkleDiyalogu
        organizasyonId={organizasyon.id}
        acik={ekleAcik}
        onKapat={() => setEkleAcik(false)}
        onEklendi={liste.yenile}
      />

      {duzenlenen ? (
        <UyeDuzenleDiyalogu
          organizasyonId={organizasyon.id}
          uye={duzenlenen}
          uyeler={uyeler}
          kendimId={kendimId}
          onKapat={() => setDuzenlenen(null)}
          onKaydedildi={liste.yenile}
        />
      ) : null}

      {silinen ? (
        <UyeSilDiyalogu
          organizasyonId={organizasyon.id}
          uye={silinen}
          onKapat={() => setSilinen(null)}
          onSilindi={liste.yenile}
        />
      ) : null}
    </Card>
  );
}
