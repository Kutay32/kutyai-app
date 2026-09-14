"use client";

import { useEffect, useRef, useState } from "react";

import { Copy, Download, FileCode2, PlugZap, Server } from "lucide-react";

import {
  cekAkisi,
  hazirlamaDogrula,
  hazirlamaManifest,
  hazirlamaOnKontrol,
  type BdmKaydi,
  type DogrulamaSonucu,
  type Manifest,
  type OnKontrolSonucu,
} from "@/lib/bdm";
import { gecikmeBicimle, sayiBicimle } from "@/lib/bicim";
import { hataMesaji } from "@/lib/api";
import { useDil } from "@/lib/dil";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { IlerlemeCubugu } from "@/components/bdm/ilerleme-cubugu";
import { StatCard } from "@/components/ui/stat-card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";

export type SekmeHazirlamaProps = { bdm: BdmKaydi };

/** Hazırlama sekmesi: doğrulama, ön kontrol, manifest ve model indirme (§10). */
export function SekmeHazirlama({ bdm }: SekmeHazirlamaProps) {
  const { showToast } = useToast();
  const { t } = useDil();

  const [dogrulama, setDogrulama] = useState<DogrulamaSonucu | null>(null);
  const [dogrulamaHatasi, setDogrulamaHatasi] = useState<string | null>(null);
  const [dogrulaniyor, setDogrulaniyor] = useState(false);

  const [onKontrol, setOnKontrol] = useState<OnKontrolSonucu | null>(null);
  const [onKontrolHatasi, setOnKontrolHatasi] = useState<string | null>(null);
  const [onKontrolYukleniyor, setOnKontrolYukleniyor] = useState(false);

  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [manifestHatasi, setManifestHatasi] = useState<string | null>(null);
  const [manifestYukleniyor, setManifestYukleniyor] = useState(false);

  const [yuzde, setYuzde] = useState(0);
  const [cekMesaji, setCekMesaji] = useState("");
  const [cekHatasi, setCekHatasi] = useState<string | null>(null);
  const [cekiliyor, setCekiliyor] = useState(false);
  const cekIptal = useRef<AbortController | null>(null);

  // Sekmeden çıkılınca indirme akışı kapatılır.
  useEffect(() => () => cekIptal.current?.abort(), []);

  async function dogrula() {
    setDogrulaniyor(true);
    setDogrulamaHatasi(null);
    try {
      setDogrulama(await hazirlamaDogrula(bdm.id));
    } catch (hata) {
      setDogrulamaHatasi(hataMesaji(hata));
    } finally {
      setDogrulaniyor(false);
    }
  }

  async function onKontrolCalistir() {
    setOnKontrolYukleniyor(true);
    setOnKontrolHatasi(null);
    try {
      setOnKontrol(await hazirlamaOnKontrol(bdm.id));
    } catch (hata) {
      setOnKontrolHatasi(hataMesaji(hata));
    } finally {
      setOnKontrolYukleniyor(false);
    }
  }

  async function manifestCalistir() {
    setManifestYukleniyor(true);
    setManifestHatasi(null);
    try {
      setManifest(await hazirlamaManifest(bdm.id));
    } catch (hata) {
      setManifest(null);
      setManifestHatasi(hataMesaji(hata));
    } finally {
      setManifestYukleniyor(false);
    }
  }

  async function cekBaslat() {
    cekIptal.current?.abort();
    const denetleyici = new AbortController();
    cekIptal.current = denetleyici;
    setCekiliyor(true);
    setCekHatasi(null);
    setYuzde(0);
    setCekMesaji(t("bdm.hazirlama.indir.baglaniyor"));
    try {
      for await (const olay of cekAkisi(bdm.id, denetleyici.signal)) {
        setYuzde(olay.yuzde);
        setCekMesaji(olay.mesaj);
      }
      showToast(t("bdm.bildirim.indirme_tamam"), "success");
    } catch (hata) {
      if (hata instanceof DOMException && hata.name === "AbortError") return;
      setCekHatasi(hataMesaji(hata));
    } finally {
      setCekiliyor(false);
      cekIptal.current = null;
    }
  }

  const cekEngeli =
    bdm.saglayici === "ollama" ? null : t("bdm.hazirlama.indir.yok.aciklama");

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle>{t("bdm.hazirlama.dogrulama.baslik")}</CardTitle>
          <CardDescription>{t("bdm.hazirlama.dogrulama.aciklama")}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div>
            <Button loading={dogrulaniyor} onClick={() => void dogrula()}>
              <PlugZap aria-hidden className="size-4" />
              {t("bdm.hazirlama.dogrulama.eylem")}
            </Button>
          </div>

          {dogrulamaHatasi ? <Alert tone="danger">{dogrulamaHatasi}</Alert> : null}

          {dogrulama ? (
            <Alert
              tone={dogrulama.basarili ? "success" : "danger"}
              title={
                dogrulama.basarili
                  ? t("bdm.hazirlama.dogrulama.basarili")
                  : t("bdm.hazirlama.dogrulama.basarisiz")
              }
            >
              <p>{dogrulama.mesaj}</p>
              <p className="text-xs">
                {t("bdm.hazirlama.dogrulama.ozet", {
                  gecikme: gecikmeBicimle(dogrulama.gecikme_ms),
                  model: sayiBicimle(dogrulama.modeller.length),
                })}
              </p>
              {dogrulama.modeller.length > 0 ? (
                <ul className="mt-2 flex max-h-32 flex-col gap-1 overflow-y-auto font-mono text-xs">
                  {dogrulama.modeller.map((model) => (
                    <li key={model}>{model}</li>
                  ))}
                </ul>
              ) : null}
            </Alert>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t("bdm.hazirlama.onkontrol.baslik")}</CardTitle>
          <CardDescription>{t("bdm.hazirlama.onkontrol.aciklama")}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div>
            <Button
              variant="secondary"
              loading={onKontrolYukleniyor}
              onClick={() => void onKontrolCalistir()}
            >
              <Server aria-hidden className="size-4" />
              {t("bdm.hazirlama.onkontrol.eylem")}
            </Button>
          </div>

          {onKontrolHatasi ? <Alert tone="danger">{onKontrolHatasi}</Alert> : null}

          {onKontrol ? (
            <>
              <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
                <StatCard
                  label={t("bdm.alan.docker")}
                  value={onKontrol.docker ? t("bdm.deger.var") : t("bdm.deger.yok")}
                />
                <StatCard
                  label={t("bdm.alan.gpu")}
                  value={onKontrol.gpu ? t("bdm.deger.var") : t("bdm.deger.yok")}
                />
                <StatCard
                  label={t("bdm.alan.bos_disk")}
                  value={t("bdm.birim.gb", { deger: sayiBicimle(onKontrol.disk_gb) })}
                />
                <StatCard
                  label={t("bdm.alan.imaj")}
                  value={
                    onKontrol.image_var ? t("bdm.deger.onbellekte") : t("bdm.deger.yok")
                  }
                />
              </div>

              <div className="flex items-center gap-2 text-sm text-neutral-700">
                <span>{t("bdm.hazirlama.onkontrol.uygunluk")}</span>
                <Badge tone={onKontrol.uygun ? "success" : "warning"}>
                  {onKontrol.uygun
                    ? t("bdm.hazirlama.onkontrol.uygun")
                    : t("bdm.hazirlama.onkontrol.uygun_degil")}
                </Badge>
              </div>

              {onKontrol.uyarilar.length > 0 ? (
                <Alert tone="warning" title={t("bdm.hazirlama.onkontrol.uyarilar")}>
                  <ul className="flex list-disc flex-col gap-1 pl-4">
                    {onKontrol.uyarilar.map((uyari) => (
                      <li key={uyari}>{uyari}</li>
                    ))}
                  </ul>
                </Alert>
              ) : (
                <Alert tone="success">{t("bdm.hazirlama.onkontrol.uyari_yok")}</Alert>
              )}
            </>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t("bdm.hazirlama.manifest.baslik")}</CardTitle>
          <CardDescription>{t("bdm.hazirlama.manifest.aciklama")}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div>
            <Button
              variant="secondary"
              loading={manifestYukleniyor}
              onClick={() => void manifestCalistir()}
            >
              <FileCode2 aria-hidden className="size-4" />
              {t("bdm.hazirlama.manifest.eylem")}
            </Button>
          </div>

          {manifestHatasi ? <Alert tone="danger">{manifestHatasi}</Alert> : null}

          {manifest ? (
            <div className="flex flex-col gap-3">
              <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
                <StatCard
                  label={t("bdm.alan.imaj")}
                  value={manifest.image.split("/").pop() ?? manifest.image}
                />
                <StatCard label={t("bdm.alan.port")} value={String(manifest.port)} />
                <StatCard
                  label={t("bdm.alan.gpu")}
                  value={manifest.gpu ? t("bdm.deger.gerekli") : t("bdm.deger.gerekmez")}
                />
                <StatCard
                  label={t("bdm.alan.bellek")}
                  value={t("bdm.birim.gb", { deger: sayiBicimle(manifest.bellek_gb) })}
                />
              </div>

              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium text-neutral-800">
                    {t("bdm.hazirlama.manifest.komut")}
                  </p>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      void navigator.clipboard
                        .writeText(manifest.komut.join(" "))
                        .then(() => showToast(t("bdm.bildirim.komut_kopyalandi"), "success"))
                        .catch(() => showToast(t("bdm.hata.komut_kopyalanamadi"), "danger"));
                    }}
                  >
                    <Copy aria-hidden className="size-4" />
                    {t("bdm.eylem.kopyala")}
                  </Button>
                </div>
                <pre className="overflow-x-auto rounded-lg border border-neutral-200 bg-neutral-50 p-4 font-mono text-xs text-neutral-800">
                  {manifest.komut.join(" ")}
                </pre>
                <p className="font-mono text-xs text-neutral-500">{manifest.image}</p>
              </div>

              <div className="flex flex-col gap-2">
                <p className="text-sm font-medium text-neutral-800">
                  {t("bdm.hazirlama.manifest.ortam")}
                </p>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t("bdm.alan.ad")}</TableHead>
                      <TableHead>{t("bdm.alan.deger")}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {Object.entries(manifest.ortam).length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={2} className="text-neutral-500">
                          {t("bdm.hazirlama.manifest.ortam_yok")}
                        </TableCell>
                      </TableRow>
                    ) : (
                      Object.entries(manifest.ortam).map(([ad, deger]) => (
                        <TableRow key={ad}>
                          <TableCell className="font-mono text-xs">{ad}</TableCell>
                          <TableCell className="font-mono text-xs">{deger}</TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
                <p className="text-xs text-neutral-500">
                  {t("bdm.hazirlama.manifest.maske")}
                </p>
              </div>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t("bdm.hazirlama.indir.baslik")}</CardTitle>
          <CardDescription>{t("bdm.hazirlama.indir.aciklama")}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {cekEngeli ? (
            <Alert tone="info" title={t("bdm.hazirlama.indir.yok.baslik")}>
              <p>{cekEngeli}</p>
            </Alert>
          ) : null}

          <div className="flex items-center gap-2">
            <Button
              loading={cekiliyor}
              disabled={cekEngeli !== null}
              title={cekEngeli ?? undefined}
              onClick={() => void cekBaslat()}
            >
              <Download aria-hidden className="size-4" />
              {t("bdm.hazirlama.indir.eylem")}
            </Button>
            {cekiliyor ? (
              <Button
                variant="secondary"
                onClick={() => {
                  cekIptal.current?.abort();
                  setCekMesaji(t("bdm.hazirlama.indir.durduruldu"));
                }}
              >
                {t("bdm.eylem.durdur")}
              </Button>
            ) : null}
          </div>

          {cekHatasi ? <Alert tone="danger">{cekHatasi}</Alert> : null}

          {cekiliyor || yuzde > 0 || cekMesaji ? (
            <IlerlemeCubugu yuzde={yuzde} mesaj={cekMesaji} />
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
