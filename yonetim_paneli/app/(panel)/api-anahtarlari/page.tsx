"use client";

import { useState } from "react";

import { KeyRound, Plus } from "lucide-react";

import { hataMesaji, istek } from "@/lib/api";
import { tarihSaatBicimle } from "@/lib/bicim";
import { useDil } from "@/lib/dil";
import {
  ANAHTAR_DURUMU_ANAHTARI,
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
  const { t } = useDil();
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
        ? t("anahtar.olustur.ad.zorunlu")
        : temizAd.length < EN_KISA_AD
          ? t("anahtar.olustur.ad.kisa", { uzunluk: EN_KISA_AD })
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
      title={t("anahtar.olustur.baslik")}
      description={t("anahtar.olustur.aciklama")}
      footer={
        <>
          <Button variant="ghost" onClick={kapat} disabled={olusturuluyor}>
            {t("anahtar.vazgec")}
          </Button>
          <Button type="submit" form="anahtar-formu" loading={olusturuluyor}>
            {t("anahtar.olustur.gonder")}
          </Button>
        </>
      }
    >
      <form id="anahtar-formu" onSubmit={gonder} className="flex flex-col gap-4">
        {sunucuHatasi ? (
          <Alert tone="danger" title={t("anahtar.olustur.hata.baslik")}>
            {sunucuHatasi}
          </Alert>
        ) : null}

        <Field label={t("anahtar.olustur.ad")} error={adHatasi} required>
          {({ id, invalid, ...erisim }) => (
            <Input
              id={id}
              {...erisim}
              invalid={invalid}
              placeholder={t("anahtar.olustur.ad.yer_tutucu")}
              value={ad}
              onChange={(olay) => setAd(olay.target.value)}
            />
          )}
        </Field>

        <div className="flex flex-col gap-1.5">
          <p className="text-sm font-medium text-neutral-800">{t("anahtar.izinli_modeller")}</p>
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
                  ? t("anahtar.olustur.secili", { sayi: secililer.length })
                  : t("anahtar.olustur.tum_modeller.ipucu")}
              </p>
            </>
          ) : (
            <p className="text-xs text-neutral-500">{t("anahtar.olustur.katalog_bos")}</p>
          )}
        </div>
      </form>
    </Dialog>
  );
}

export default function ApiAnahtarlariSayfasi() {
  const { t } = useDil();
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

  const [iptalOnce, iptalSonra] = t("anahtar.iptal.metin").split("{baglanti}");

  const iptalEt = async () => {
    if (!iptalEdilen) return;
    setIptalEdiliyor(true);
    setIptalHatasi(null);
    try {
      await anahtarIptal(iptalEdilen.id);
      showToast(t("anahtar.iptal.basarili", { ad: iptalEdilen.ad }), "success");
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
            {t("anahtar.baslik")}
          </h1>
          <p className="text-sm text-neutral-500">{t("anahtar.aciklama")}</p>
        </div>
        <Button onClick={() => setOlusturAcik(true)}>
          <Plus aria-hidden className="size-4" />
          {t("anahtar.yeni")}
        </Button>
      </header>

      <Card className="rounded-2xl">
        <VeriDurumu yukleniyor={liste.yukleniyor} hata={liste.hata} yenile={liste.yenile}>
          {liste.veri && liste.veri.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("anahtar.tablo.ad")}</TableHead>
                  <TableHead>{t("anahtar.tablo.anahtar")}</TableHead>
                  <TableHead>{t("anahtar.tablo.durum")}</TableHead>
                  <TableHead>{t("anahtar.izinli_modeller")}</TableHead>
                  <TableHead>{t("anahtar.tablo.son_kullanim")}</TableHead>
                  <TableHead>{t("anahtar.tablo.olusturulma")}</TableHead>
                  <TableHead className="text-right">{t("anahtar.tablo.islem")}</TableHead>
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
                        {t(ANAHTAR_DURUMU_ANAHTARI[anahtar.durum])}
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
                        <span className="text-neutral-500">{t("anahtar.tum_modeller")}</span>
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
                          {t("anahtar.iptal")}
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
                title={t("anahtar.bos.baslik")}
                description={t("anahtar.bos.aciklama")}
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
        title={t("anahtar.iptal.baslik")}
        description={t("anahtar.iptal.aciklama")}
        footer={
          <>
            <Button variant="ghost" onClick={() => setIptalEdilen(null)} disabled={iptalEdiliyor}>
              {t("anahtar.vazgec")}
            </Button>
            <Button variant="danger" loading={iptalEdiliyor} onClick={() => void iptalEt()}>
              {t("anahtar.iptal")}
            </Button>
          </>
        }
      >
        {iptalHatasi ? (
          <Alert tone="danger" title={t("anahtar.iptal.hata.baslik")}>
            {iptalHatasi}
          </Alert>
        ) : (
          <p className="text-sm text-neutral-600">
            {iptalOnce}
            <span className="font-medium text-neutral-900">{iptalEdilen?.ad}</span>
            {iptalSonra}
          </p>
        )}
      </Dialog>
    </div>
  );
}
