"use client";

import { useState } from "react";

import { KeyRound, Link2, Plus, Trash2 } from "lucide-react";

import { useDil } from "@/lib/dil";
import { useUzakVeri } from "@/lib/kancalar";
import { aktifOrganizasyonRolu, aktifOrganizasyonSlug, organizasyonYonetebilirMi } from "@/lib/organizasyonlar";
import {
  SSO_TURU_ANAHTARI,
  saglayicilariGetir,
  type SsoSaglayici,
} from "@/lib/sso";
import { GirisAdresiDiyalogu } from "@/components/sso/giris-adresi-diyalogu";
import {
  SaglayiciDuzenleDiyalogu,
  SaglayiciOlusturDiyalogu,
  SaglayiciSilDiyalogu,
} from "@/components/sso/saglayici-diyalogu";
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
 * SSO sayfası: `GET/POST/PATCH/DELETE /sso/saglayicilar` yönetimi (spec §7).
 * OIDC ve SAML sağlayıcıları aynı tabloda; alanlar türe göre değişir.
 */
export default function SsoSayfasi() {
  const { t } = useDil();
  const liste = useUzakVeri<SsoSaglayici[]>(() => saglayicilariGetir());
  const rol = useUzakVeri(aktifOrganizasyonRolu);
  const slug = useUzakVeri(aktifOrganizasyonSlug);

  const [olusturAcik, setOlusturAcik] = useState(false);
  const [duzenlenen, setDuzenlenen] = useState<SsoSaglayici | null>(null);
  const [silinen, setSilinen] = useState<SsoSaglayici | null>(null);
  const [adresGosterilen, setAdresGosterilen] = useState<SsoSaglayici | null>(null);

  // Rol bilinmiyorsa düğmeler gizlenmez; yetki kararı sunucuda kalır (403 → katalog mesajı).
  const yonetebilir = rol.veri === null || organizasyonYonetebilirMi(rol.veri ?? undefined);
  const saglayicilar = liste.veri ?? [];

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold tracking-tight text-neutral-900">
            {t("sso.baslik")}
          </h1>
          <p className="text-sm text-neutral-500">{t("sso.aciklama")}</p>
        </div>
        {yonetebilir ? (
          <Button onClick={() => setOlusturAcik(true)}>
            <Plus aria-hidden className="size-4" />
            {t("sso.yeni")}
          </Button>
        ) : null}
      </header>

      <Card className="rounded-2xl">
        <VeriDurumu yukleniyor={liste.yukleniyor} hata={liste.hata} yenile={liste.yenile}>
          {saglayicilar.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("sso.tablo.ad")}</TableHead>
                  <TableHead>{t("sso.tablo.tur")}</TableHead>
                  <TableHead>{t("sso.tablo.slug")}</TableHead>
                  <TableHead>{t("sso.tablo.durum")}</TableHead>
                  <TableHead>{t("sso.tablo.sir")}</TableHead>
                  <TableHead className="text-right">{t("sso.tablo.islemler")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {saglayicilar.map((saglayici) => (
                  <TableRow key={saglayici.id}>
                    <TableCell className="font-medium text-neutral-900">
                      {saglayici.ad}
                    </TableCell>
                    <TableCell>
                      <Badge tone="info">{t(SSO_TURU_ANAHTARI[saglayici.tur])}</Badge>
                    </TableCell>
                    <TableCell className="font-mono text-xs">{saglayici.slug}</TableCell>
                    <TableCell>
                      <Badge tone={saglayici.etkin ? "success" : "neutral"}>
                        {t(saglayici.etkin ? "sso.durum.etkin" : "sso.durum.kapali")}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge tone={saglayici.sir_tanimli ? "success" : "warning"}>
                        <KeyRound aria-hidden className="size-3" />
                        {t(saglayici.sir_tanimli ? "sso.sir.tanimli" : "sso.sir.tanimsiz")}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap items-center justify-end gap-2">
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => setAdresGosterilen(saglayici)}
                        >
                          <Link2 aria-hidden className="size-4" />
                          {t("sso.giris_yolu")}
                        </Button>
                        {yonetebilir ? (
                          <>
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => setDuzenlenen(saglayici)}
                            >
                              {t("sso.duzenle")}
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setSilinen(saglayici)}
                            >
                              <Trash2 aria-hidden className="size-4" />
                              {t("sso.sil")}
                            </Button>
                          </>
                        ) : null}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="p-4">
              <EmptyState
                icon={<KeyRound aria-hidden className="size-5" />}
                title={t("sso.bos.baslik")}
                description={t("sso.bos.aciklama")}
                action={
                  yonetebilir ? (
                    <Button onClick={() => setOlusturAcik(true)}>
                      <Plus aria-hidden className="size-4" />
                      {t("sso.yeni")}
                    </Button>
                  ) : undefined
                }
              />
            </div>
          )}
        </VeriDurumu>
      </Card>

      <SaglayiciOlusturDiyalogu
        acik={olusturAcik}
        onKapat={() => setOlusturAcik(false)}
        onOlusturuldu={liste.yenile}
      />

      {duzenlenen ? (
        <SaglayiciDuzenleDiyalogu
          key={duzenlenen.id}
          saglayici={duzenlenen}
          onKapat={() => setDuzenlenen(null)}
          onKaydedildi={liste.yenile}
        />
      ) : null}

      {silinen ? (
        <SaglayiciSilDiyalogu
          key={silinen.id}
          saglayici={silinen}
          onKapat={() => setSilinen(null)}
          onSilindi={liste.yenile}
        />
      ) : null}

      {adresGosterilen ? (
        <GirisAdresiDiyalogu
          key={adresGosterilen.id}
          saglayici={adresGosterilen}
          organizasyonSlug={slug.veri}
          onKapat={() => setAdresGosterilen(null)}
        />
      ) : null}
    </div>
  );
}
