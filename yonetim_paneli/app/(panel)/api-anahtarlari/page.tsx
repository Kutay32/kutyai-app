"use client";

import { useState } from "react";

import { KeyRound, Plus } from "lucide-react";

import { hataMesaji, istek } from "@/lib/api";
import { tarihSaatBicimle } from "@/lib/bicim";
import {
  ANAHTAR_DURUMU_ETIKETI,
  anahtarIptal,
  anahtarOlustur,
  anahtarlariGetir,
  type ApiAnahtari,
  type YeniApiAnahtari,
} from "@/lib/anahtarlar";
import { useUzakVeri } from "@/lib/kancalar";
import type { Bdm } from "@/lib/tipler";
import { VeriDurumu } from "@/components/loglar/veri-durumu";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";
import { AnahtarSonucDiyalogu } from "./anahtar-sonuc-diyalogu";

const EN_KISA_AD = 2;

function YeniAnahtarDiyalogu({
  bdmler,
  acik,
  onKapat,
  onOlusturuldu,
}: {
  bdmler: Bdm[];
  acik: boolean;
  onKapat: () => void;
  onOlusturuldu: (anahtar: YeniApiAnahtari) => void;
}) {
  const [ad, setAd] = useState("");
  const [secililer, setSecililer] = useState<string[]>([]);
  const [adHatasi, setAdHatasi] = useState<string | null>(null);
  const [sunucuHatasi, setSunucuHatasi] = useState<string | null>(null);
  const [olusturuluyor, setOlusturuluyor] = useState(false);

  const kapat = () => {
    onKapat();
    setAd("");
    setSecililer([]);
    setAdHatasi(null);
    setSunucuHatasi(null);
  };

  const gonder = async (olay: React.FormEvent<HTMLFormElement>) => {
    olay.preventDefault();
    const temizAd = ad.trim();
    const hata =
      temizAd.length === 0
        ? "Anahtar adı zorunludur."
        : temizAd.length < EN_KISA_AD
          ? `Anahtar adı en az ${EN_KISA_AD} karakter olmalıdır.`
          : null;
    setAdHatasi(hata);
    if (hata) return;

    setOlusturuluyor(true);
    setSunucuHatasi(null);
    try {
      const olusan = await anahtarOlustur({ ad: temizAd, izinli_modeller: secililer });
      onOlusturuldu(olusan);
      kapat();
    } catch (sebep) {
      setSunucuHatasi(hataMesaji(sebep));
    } finally {
      setOlusturuluyor(false);
    }
  };

  const degistir = (slug: string, secili: boolean) => {
    setSecililer((onceki) =>
      secili ? [...onceki, slug] : onceki.filter((deger) => deger !== slug),
    );
  };

  return (
    <Dialog
      open={acik}
      onClose={kapat}
      title="Yeni API anahtarı"
      description="Anahtar yalnızca oluşturma yanıtında tam olarak gösterilir."
      footer={
        <>
          <Button variant="ghost" onClick={kapat} disabled={olusturuluyor}>
            Vazgeç
          </Button>
          <Button type="submit" form="anahtar-formu" loading={olusturuluyor}>
            Anahtar oluştur
          </Button>
        </>
      }
    >
      <form id="anahtar-formu" onSubmit={gonder} className="flex flex-col gap-4">
        {sunucuHatasi ? (
          <Alert tone="danger" title="Anahtar oluşturulamadı">
            {sunucuHatasi}
          </Alert>
        ) : null}

        <Field label="Anahtar adı" error={adHatasi} required>
          {({ id, invalid, ...erisim }) => (
            <Input
              id={id}
              {...erisim}
              invalid={invalid}
              placeholder="ör. Muhasebe entegrasyonu"
              value={ad}
              onChange={(olay) => setAd(olay.target.value)}
            />
          )}
        </Field>

        <div className="flex flex-col gap-1.5">
          <p className="text-sm font-medium text-neutral-800">İzinli modeller</p>
          {bdmler.length > 0 ? (
            <>
              <div className="max-h-48 overflow-y-auto rounded-lg border border-neutral-200 p-2">
                {bdmler.map((bdm) => (
                  <label
                    key={bdm.id}
                    className="flex items-center gap-2 rounded-md p-2 text-sm hover:bg-neutral-50"
                  >
                    <input
                      type="checkbox"
                      className="size-4 accent-neutral-900"
                      checked={secililer.includes(bdm.slug)}
                      onChange={(olay) => degistir(bdm.slug, olay.target.checked)}
                    />
                    <span className="text-neutral-900">{bdm.gorunen_ad}</span>
                    <span className="text-xs text-neutral-500">{bdm.slug}</span>
                  </label>
                ))}
              </div>
              <p className="text-xs text-neutral-500">
                {secililer.length > 0
                  ? `${secililer.length} model seçildi.`
                  : "Hiçbiri seçilmezse anahtar tüm modellere erişebilir."}
              </p>
            </>
          ) : (
            <p className="text-xs text-neutral-500">
              Katalogda model yok; anahtar tüm modellere erişecek şekilde oluşturulacak.
            </p>
          )}
        </div>
      </form>
    </Dialog>
  );
}

export default function ApiAnahtarlariSayfasi() {
  const { showToast } = useToast();
  const liste = useUzakVeri<ApiAnahtari[]>(anahtarlariGetir, []);
  const bdmListesi = useUzakVeri<Bdm[]>(() => istek<Bdm[]>("/bdm"), []);

  const [olusturAcik, setOlusturAcik] = useState(false);
  const [olusan, setOlusan] = useState<YeniApiAnahtari | null>(null);
  const [iptalEdilen, setIptalEdilen] = useState<ApiAnahtari | null>(null);
  const [iptalHatasi, setIptalHatasi] = useState<string | null>(null);
  const [iptalEdiliyor, setIptalEdiliyor] = useState(false);

  const modelAdi = (slug: string) =>
    bdmListesi.veri?.find((bdm) => bdm.slug === slug)?.gorunen_ad ?? slug;

  const iptalEt = async () => {
    if (!iptalEdilen) return;
    setIptalEdiliyor(true);
    setIptalHatasi(null);
    try {
      await anahtarIptal(iptalEdilen.id);
      showToast(`${iptalEdilen.ad} anahtarı iptal edildi.`, "success");
      setIptalEdilen(null);
      liste.yenile();
    } catch (sebep) {
      setIptalHatasi(hataMesaji(sebep));
    } finally {
      setIptalEdiliyor(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold tracking-tight text-neutral-900">
            API Anahtarları
          </h1>
          <p className="text-sm text-neutral-500">
            Sohbet uçlarına programatik erişim; tam anahtar yalnızca oluşturmada görünür.
          </p>
        </div>
        <Button onClick={() => setOlusturAcik(true)}>
          <Plus aria-hidden className="size-4" />
          Yeni anahtar
        </Button>
      </header>

      <Card className="rounded-2xl">
        <VeriDurumu yukleniyor={liste.yukleniyor} hata={liste.hata} yenile={liste.yenile}>
          {liste.veri && liste.veri.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Ad</TableHead>
                  <TableHead>Anahtar</TableHead>
                  <TableHead>Durum</TableHead>
                  <TableHead>İzinli modeller</TableHead>
                  <TableHead>Son kullanım</TableHead>
                  <TableHead>Oluşturulma</TableHead>
                  <TableHead className="text-right">İşlem</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {liste.veri.map((anahtar) => (
                  <TableRow key={anahtar.id}>
                    <TableCell className="font-medium text-neutral-900">{anahtar.ad}</TableCell>
                    <TableCell className="font-mono text-xs">
                      {`${anahtar.onek}…${anahtar.son_dort}`}
                    </TableCell>
                    <TableCell>
                      <Badge tone={anahtar.durum === "aktif" ? "success" : "neutral"}>
                        {ANAHTAR_DURUMU_ETIKETI[anahtar.durum]}
                      </Badge>
                    </TableCell>
                    <TableCell className="max-w-xs">
                      {anahtar.izinli_modeller.length > 0 ? (
                        <span className="flex flex-wrap gap-1">
                          {anahtar.izinli_modeller.map((slug) => (
                            <Badge key={slug} tone="info">
                              {modelAdi(slug)}
                            </Badge>
                          ))}
                        </span>
                      ) : (
                        <span className="text-neutral-500">Tüm modeller</span>
                      )}
                    </TableCell>
                    <TableCell className="whitespace-nowrap">
                      {tarihSaatBicimle(anahtar.son_kullanim)}
                    </TableCell>
                    <TableCell className="whitespace-nowrap">
                      {tarihSaatBicimle(anahtar.olusturulma)}
                    </TableCell>
                    <TableCell className="text-right">
                      {anahtar.durum === "aktif" ? (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setIptalHatasi(null);
                            setIptalEdilen(anahtar);
                          }}
                        >
                          İptal et
                        </Button>
                      ) : (
                        <span className="text-neutral-400">—</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="p-4">
              <EmptyState
                icon={<KeyRound aria-hidden className="size-5" />}
                title="Henüz anahtar yok"
                description="Entegrasyonlar için ilk API anahtarını oluşturun."
              />
            </div>
          )}
        </VeriDurumu>
      </Card>

      <YeniAnahtarDiyalogu
        bdmler={bdmListesi.veri ?? []}
        acik={olusturAcik}
        onKapat={() => setOlusturAcik(false)}
        onOlusturuldu={(anahtar) => {
          setOlusan(anahtar);
          liste.yenile();
        }}
      />

      {olusan ? (
        <AnahtarSonucDiyalogu
          ad={olusan.ad}
          tamAnahtar={olusan.tam_anahtar}
          onKapat={() => setOlusan(null)}
        />
      ) : null}

      <Dialog
        open={iptalEdilen !== null}
        onClose={() => {
          if (!iptalEdiliyor) setIptalEdilen(null);
        }}
        title="Anahtarı iptal et"
        description="İptal edilen anahtar kimlik doğrulamada reddedilir; bu işlem geri alınamaz."
        footer={
          <>
            <Button variant="ghost" onClick={() => setIptalEdilen(null)} disabled={iptalEdiliyor}>
              Vazgeç
            </Button>
            <Button variant="danger" loading={iptalEdiliyor} onClick={() => void iptalEt()}>
              İptal et
            </Button>
          </>
        }
      >
        {iptalHatasi ? (
          <Alert tone="danger" title="İptal edilemedi">
            {iptalHatasi}
          </Alert>
        ) : (
          <p className="text-sm text-neutral-600">
            <span className="font-medium text-neutral-900">{iptalEdilen?.ad}</span> anahtarı
            iptal edilecek ve kullanan entegrasyonlar erişimini kaybedecek.
          </p>
        )}
      </Dialog>
    </div>
  );
}
