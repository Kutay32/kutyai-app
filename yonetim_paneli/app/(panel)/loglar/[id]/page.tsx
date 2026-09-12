"use client";

import { useState } from "react";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

import { ArrowLeft, Download, Trash2 } from "lucide-react";

import { hataMesaji } from "@/lib/api";
import { gecikmeBicimle, sayiBicimle, tarihSaatBicimle } from "@/lib/bicim";
import {
  DISA_AKTARIM_BICIMLERI,
  DISA_AKTARIM_ETIKETI,
  MESAJ_ROL_ETIKETI,
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
  return (
    <Card>
      <CardHeader>
        <CardTitle>Kayıt Bilgileri</CardTitle>
      </CardHeader>
      <CardContent>
        <dl className="grid gap-4 md:grid-cols-4">
          <BilgiSatiri etiket="Kullanıcı" deger={detay.kullanici_eposta ?? "—"} />
          <BilgiSatiri etiket="Model" deger={detay.bdm_ad ?? "—"} />
          <BilgiSatiri etiket="Oluşturulma" deger={tarihSaatBicimle(detay.olusturulma)} />
          <BilgiSatiri etiket="Son güncelleme" deger={tarihSaatBicimle(detay.guncellenme)} />
          <BilgiSatiri etiket="Mesaj sayısı" deger={sayiBicimle(detay.mesajlar.length)} />
          <BilgiSatiri etiket="Giriş tokenı" deger={sayiBicimle(detay.token_girdi)} />
          <BilgiSatiri etiket="Çıkış tokenı" deger={sayiBicimle(detay.token_cikti)} />
          <BilgiSatiri
            etiket="Kaynak"
            deger={detay.api_anahtari_id ? `API anahtarı #${detay.api_anahtari_id}` : "Panel hesabı"}
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
  const { showToast } = useToast();

  const { veri, yukleniyor, hata, yenile } = useUzakVeri<LogDetayi>(() => {
    if (!Number.isFinite(konusmaId)) throw new Error("Geçersiz kayıt numarası.");
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
      showToast(`${DISA_AKTARIM_ETIKETI[bicim]} indirmesi tarayıcıya gönderildi.`, "success");
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
      showToast("Konuşma kaydı silindi.", "success");
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
        Konuşma kayıtları
      </Link>

      <VeriDurumu yukleniyor={yukleniyor} hata={hata} yenile={yenile}>
        {veri ? (
          <>
            <header className="flex flex-col gap-4">
              <div className="flex flex-col gap-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h1 className="text-2xl font-semibold tracking-tight text-neutral-900">
                    {veri.baslik || "Başlıksız konuşma"}
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
                    {DISA_AKTARIM_ETIKETI[bicim]} indir
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
                  Sil
                </Button>
              </div>
            </header>

            <Alert tone="info" title="Maskeleme sınırı">
              Kayıtlar veritabanına maskelenmiş yazılır (KVKK). Bu sayfa kaydın
              saklandığı hâli gösterir; kullanıcının kendi oturumunda gördüğü metin
              farklı olabilir.
            </Alert>

            <KayitOzeti detay={veri} />

            {veri.sistem_istemi.trim() ? (
              <Card>
                <CardHeader>
                  <CardTitle>Sistem istemi</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm break-words whitespace-pre-wrap text-neutral-700">
                    {veri.sistem_istemi}
                  </p>
                </CardContent>
              </Card>
            ) : null}

            {veri.mesajlar.length > 0 ? (
              <section className="flex flex-col gap-4" aria-label="Mesajlar">
                <h2 className="text-base font-semibold text-neutral-900">
                  Mesajlar ({sayiBicimle(veri.mesajlar.length)})
                </h2>
                {veri.mesajlar.map((mesaj) => (
                  <MesajBaloncugu
                    key={mesaj.id}
                    mesaj={mesaj}
                    etiket={MESAJ_ROL_ETIKETI[mesaj.rol]}
                  />
                ))}
              </section>
            ) : (
              <EmptyState
                title="Mesaj yok"
                description="Bu konuşmada kayıtlı mesaj bulunmuyor."
              />
            )}

            <Dialog
              open={silmeAcik}
              onClose={() => {
                if (!siliniyor) setSilmeAcik(false);
              }}
              title="Konuşmayı sil"
              description="Kayıt ve tüm mesajları kalıcı olarak silinir; bu işlem geri alınamaz."
              footer={
                <>
                  <Button
                    variant="ghost"
                    onClick={() => setSilmeAcik(false)}
                    disabled={siliniyor}
                  >
                    Vazgeç
                  </Button>
                  <Button variant="danger" loading={siliniyor} onClick={() => void sil()}>
                    Kalıcı olarak sil
                  </Button>
                </>
              }
            >
              {silmeHatasi ? (
                <Alert tone="danger" title="Silinemedi">
                  {silmeHatasi}
                </Alert>
              ) : (
                <p className="text-sm text-neutral-600">
                  “{veri.baslik || "Başlıksız konuşma"}” kaydı silinecek.
                </p>
              )}
            </Dialog>
          </>
        ) : null}
      </VeriDurumu>
    </div>
  );
}
