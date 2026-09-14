"use client";

import { useState } from "react";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

import { ArrowLeft, Download, Trash2 } from "lucide-react";

import { hataMesaji } from "@/lib/api";
import { gecikmeBicimle, sayiBicimle, tarihSaatBicimle } from "@/lib/bicim";
import { useDil } from "@/lib/dil";
import {
  DISA_AKTARIM_BICIMLERI,
  DISA_AKTARIM_ETIKETI,
  MESAJ_ROL_ANAHTARI,
  logDetayiGetir,
  logDisaAktar,
  logSil,
  type DisaAktarimBicimi,
  type LogDetayi,
} from "@/lib/loglar";
import { useUzakVeri } from "@/lib/kancalar";
import { MesajBaloncugu } from "@/components/loglar/mesaj-baloncugu";
import { VeriDurumu } from "@/components/loglar/veri-durumu";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { useToast } from "@/components/ui/toast";

function BilgiSatiri({ etiket, deger }: { etiket: string; deger: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-xs tracking-wide text-neutral-500 uppercase">{etiket}</dt>
      <dd className="text-sm break-words text-neutral-900">{deger}</dd>
    </div>
  );
}

function KayitOzeti({ detay }: { detay: LogDetayi }) {
  const { t } = useDil();

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("kayit.detay.bilgileri")}</CardTitle>
      </CardHeader>
      <CardContent>
        <dl className="grid gap-4 md:grid-cols-4">
          <BilgiSatiri etiket={t("kayit.detay.kullanici")} deger={detay.kullanici_eposta ?? "—"} />
          <BilgiSatiri etiket={t("kayit.detay.model")} deger={detay.bdm_ad ?? "—"} />
          <BilgiSatiri
            etiket={t("kayit.detay.olusturulma")}
            deger={tarihSaatBicimle(detay.olusturulma)}
          />
          <BilgiSatiri
            etiket={t("kayit.detay.guncellenme")}
            deger={tarihSaatBicimle(detay.guncellenme)}
          />
          <BilgiSatiri
            etiket={t("kayit.detay.mesaj_sayisi")}
            deger={sayiBicimle(detay.mesajlar.length)}
          />
          <BilgiSatiri
            etiket={t("kayit.detay.token_girdi")}
            deger={sayiBicimle(detay.token_girdi)}
          />
          <BilgiSatiri
            etiket={t("kayit.detay.token_cikti")}
            deger={sayiBicimle(detay.token_cikti)}
          />
          <BilgiSatiri
            etiket={t("kayit.detay.kaynak")}
            deger={
              detay.api_anahtari_id
                ? t("kayit.detay.kaynak.api", { no: detay.api_anahtari_id })
                : t("kayit.detay.kaynak.panel")
            }
          />
        </dl>
      </CardContent>
    </Card>
  );
}

export default function LogDetaySayfasi() {
  const parametreler = useParams<{ id: string }>();
  const konusmaId = Number(parametreler.id);
  const yonlendir = useRouter();
  const { t } = useDil();
  const { showToast } = useToast();

  const { veri, yukleniyor, hata, yenile } = useUzakVeri<LogDetayi>(() => {
    if (!Number.isFinite(konusmaId)) throw new Error(t("kayit.gecersiz_no"));
    return logDetayiGetir(konusmaId);
  }, [konusmaId]);

  const [indirilen, setIndirilen] = useState<DisaAktarimBicimi | null>(null);
  const [silmeAcik, setSilmeAcik] = useState(false);
  const [siliniyor, setSiliniyor] = useState(false);
  const [silmeHatasi, setSilmeHatasi] = useState<string | null>(null);

  const indir = async (bicim: DisaAktarimBicimi) => {
    setIndirilen(bicim);
    try {
      await logDisaAktar(konusmaId, bicim);
      showToast(t("kayit.indir.bildirim", { bicim: DISA_AKTARIM_ETIKETI[bicim] }), "success");
    } catch (sebep) {
      showToast(hataMesaji(sebep), "danger");
    } finally {
      setIndirilen(null);
    }
  };

  const sil = async () => {
    setSiliniyor(true);
    setSilmeHatasi(null);
    try {
      await logSil(konusmaId);
      showToast(t("kayit.sil.bildirim"), "success");
      yonlendir.push("/loglar");
    } catch (sebep) {
      setSilmeHatasi(hataMesaji(sebep));
    } finally {
      setSiliniyor(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <Link
        href="/loglar"
        className="flex w-fit items-center gap-1 rounded-md text-sm text-neutral-600 transition-colors hover:text-neutral-900 focus:border-neutral-900 focus:outline-none focus:ring-0"
      >
        <ArrowLeft aria-hidden className="size-4" />
        {t("kayit.loglar.geri")}
      </Link>

      <VeriDurumu yukleniyor={yukleniyor} hata={hata} yenile={yenile}>
        {veri ? (
          <>
            <header className="flex flex-col gap-4">
              <div className="flex flex-col gap-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h1 className="text-2xl font-semibold tracking-tight text-neutral-900">
                    {veri.baslik || t("kayit.basliksiz")}
                  </h1>
                  <Badge tone="neutral">#{veri.id}</Badge>
                </div>
                <p className="text-sm text-neutral-500">
                  {tarihSaatBicimle(veri.olusturulma)} · {veri.kullanici_eposta ?? "—"} ·{" "}
                  {veri.bdm_ad ?? "—"}
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                {DISA_AKTARIM_BICIMLERI.map((bicim) => (
                  <Button
                    key={bicim}
                    variant="secondary"
                    size="sm"
                    loading={indirilen === bicim}
                    onClick={() => void indir(bicim)}
                  >
                    <Download aria-hidden className="size-4" />
                    {t("kayit.indir", { bicim: DISA_AKTARIM_ETIKETI[bicim] })}
                  </Button>
                ))}
                <Button
                  variant="danger"
                  size="sm"
                  className="md:ml-auto"
                  onClick={() => {
                    setSilmeHatasi(null);
                    setSilmeAcik(true);
                  }}
                >
                  <Trash2 aria-hidden className="size-4" />
                  {t("kayit.sil.dugme")}
                </Button>
              </div>
            </header>

            <Alert tone="info" title={t("kayit.detay.maskeleme.baslik")}>
              {t("kayit.detay.maskeleme.govde")}
            </Alert>

            <KayitOzeti detay={veri} />

            {veri.sistem_istemi.trim() ? (
              <Card>
                <CardHeader>
                  <CardTitle>{t("kayit.detay.sistem_istemi")}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm break-words whitespace-pre-wrap text-neutral-700">
                    {veri.sistem_istemi}
                  </p>
                </CardContent>
              </Card>
            ) : null}

            {veri.mesajlar.length > 0 ? (
              <section className="flex flex-col gap-4" aria-label={t("kayit.detay.mesajlar.aria")}>
                <h2 className="text-base font-semibold text-neutral-900">
                  {t("kayit.detay.mesajlar", { sayi: sayiBicimle(veri.mesajlar.length) })}
                </h2>
                {veri.mesajlar.map((mesaj) => (
                  <MesajBaloncugu
                    key={mesaj.id}
                    mesaj={mesaj}
                    etiket={t(MESAJ_ROL_ANAHTARI[mesaj.rol])}
                  />
                ))}
              </section>
            ) : (
              <EmptyState
                title={t("kayit.detay.mesaj_yok.baslik")}
                description={t("kayit.detay.mesaj_yok.aciklama")}
              />
            )}

            <Dialog
              open={silmeAcik}
              onClose={() => {
                if (!siliniyor) setSilmeAcik(false);
              }}
              title={t("kayit.sil.baslik")}
              description={t("kayit.sil.aciklama")}
              footer={
                <>
                  <Button
                    variant="ghost"
                    onClick={() => setSilmeAcik(false)}
                    disabled={siliniyor}
                  >
                    {t("kayit.sil.vazgec")}
                  </Button>
                  <Button variant="danger" loading={siliniyor} onClick={() => void sil()}>
                    {t("kayit.sil.onayla")}
                  </Button>
                </>
              }
            >
              {silmeHatasi ? (
                <Alert tone="danger" title={t("kayit.sil.hata.baslik")}>
                  {silmeHatasi}
                </Alert>
              ) : (
                <p className="text-sm text-neutral-600">
                  {t("kayit.sil.soru", { baslik: veri.baslik || t("kayit.basliksiz") })}
                </p>
              )}
            </Dialog>
          </>
        ) : null}
      </VeriDurumu>
    </div>
  );
}
