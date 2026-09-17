"use client";

import { useState } from "react";

import { ExternalLink, TriangleAlert } from "lucide-react";

import { useDil } from "@/lib/dil";
import { sayiBicimle, tarihSaatBicimle } from "@/lib/bicim";
import {
  ABONELIK_DONEMLERI,
  FATURA_DURUMU_ANAHTARI,
  abonelikBaslat,
  abonelikIptal,
  faturaOdendi,
  faturalamaHatasi,
  type Abonelik,
  type AbonelikSonucu,
  type Fatura,
  type Plan,
} from "@/lib/faturalama";
import { cn } from "@/lib/cn";
import { FOCUS_RING } from "@/components/ui/stiller";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Select } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";

/** `POST /faturalama/abonelik` — plan ve dönem seçimi, ilk fatura ve ödeme bağlantısı. */
export function AboneOlDiyalogu({
  plan,
  onKapat,
  onBaslatildi,
}: {
  plan: Plan;
  onKapat: () => void;
  onBaslatildi: () => void;
}) {
  const { t } = useDil();
  const [donem, setDonem] = useState<number>(ABONELIK_DONEMLERI[0]);
  const [gonderiliyor, setGonderiliyor] = useState(false);
  const [hata, setHata] = useState<string | null>(null);
  const [sonuc, setSonuc] = useState<AbonelikSonucu | null>(null);

  const baslat = async () => {
    setGonderiliyor(true);
    setHata(null);
    try {
      const cevap = await abonelikBaslat({ plan_id: plan.id, donem_gun: donem });
      setSonuc(cevap);
      onBaslatildi();
    } catch (sebep) {
      setHata(faturalamaHatasi(sebep));
    } finally {
      setGonderiliyor(false);
    }
  };

  return (
    <Dialog
      open
      onClose={() => {
        if (!gonderiliyor) onKapat();
      }}
      title={t("faturalama.abone.baslik", { ad: plan.ad })}
      description={t("faturalama.abone.aciklama")}
      footer={
        sonuc ? (
          <Button onClick={onKapat}>{t("genel.kapat")}</Button>
        ) : (
          <>
            <Button variant="ghost" onClick={onKapat} disabled={gonderiliyor}>
              {t("genel.vazgec")}
            </Button>
            <Button loading={gonderiliyor} onClick={() => void baslat()}>
              {t("faturalama.abone.gonder")}
            </Button>
          </>
        )
      }
    >
      <div className="flex flex-col gap-4">
        {hata ? (
          <Alert tone="danger" title={t("faturalama.abone.hata.baslik")}>
            {hata}
          </Alert>
        ) : null}

        {sonuc ? (
          <>
            <Alert tone="success" title={t("faturalama.abone.basarili")}>
              {t("faturalama.fatura.no")}: #{sayiBicimle(sonuc.fatura.id)} ·{" "}
              {sonuc.fatura.tutar}
            </Alert>
            {sonuc.odeme_url ? (
              <div className="flex flex-col gap-2">
                <a
                  href={sonuc.odeme_url}
                  target="_blank"
                  rel="noreferrer"
                  className={cn(
                    "inline-flex h-10 items-center justify-center gap-2 rounded-md border border-neutral-900 bg-neutral-900 px-4 text-sm font-medium whitespace-nowrap text-white transition-colors hover:bg-neutral-800",
                    FOCUS_RING,
                  )}
                >
                  <ExternalLink aria-hidden className="size-4" />
                  {t("faturalama.abone.odeme")}
                </a>
                <p className="text-xs text-neutral-500">{t("faturalama.abone.odeme.ipucu")}</p>
              </div>
            ) : null}
          </>
        ) : (
          <>
            <Field label={t("faturalama.abone.donem")}>
              {({ id, ...erisim }) => (
                <Select
                  id={id}
                  {...erisim}
                  value={String(donem)}
                  onChange={(olay) => setDonem(Number(olay.target.value))}
                >
                  {ABONELIK_DONEMLERI.map((secenek) => (
                    <option key={secenek} value={secenek}>
                      {sayiBicimle(secenek)}
                    </option>
                  ))}
                </Select>
              )}
            </Field>

            <p className="text-sm text-neutral-500">
              {t("faturalama.abone.fatura")}:{" "}
              <span className="font-medium text-neutral-900">{plan.aylik_fiyat}</span>
            </p>
          </>
        )}
      </div>
    </Dialog>
  );
}

/** `POST /faturalama/abonelik/iptal`. */
export function AbonelikIptalDiyalogu({
  abonelik,
  onKapat,
  onIptalEdildi,
}: {
  abonelik: Abonelik;
  onKapat: () => void;
  onIptalEdildi: () => void;
}) {
  const { t } = useDil();
  const { showToast } = useToast();
  const [isleniyor, setIsleniyor] = useState(false);
  const [hata, setHata] = useState<string | null>(null);

  const iptalEt = async () => {
    setIsleniyor(true);
    setHata(null);
    try {
      await abonelikIptal();
      showToast(t("faturalama.abonelik.iptal.basarili"), "success");
      onIptalEdildi();
      onKapat();
    } catch (sebep) {
      setHata(faturalamaHatasi(sebep));
    } finally {
      setIsleniyor(false);
    }
  };

  const [once, sonra] = t("faturalama.abonelik.iptal.metin").split("{baglanti}");

  return (
    <Dialog
      open
      onClose={() => {
        if (!isleniyor) onKapat();
      }}
      title={t("faturalama.abonelik.iptal.baslik")}
      description={t("faturalama.abonelik.iptal.aciklama")}
      footer={
        <>
          <Button variant="ghost" onClick={onKapat} disabled={isleniyor}>
            {t("genel.vazgec")}
          </Button>
          <Button variant="danger" loading={isleniyor} onClick={() => void iptalEt()}>
            {t("faturalama.abonelik.iptal.onay")}
          </Button>
        </>
      }
    >
      {hata ? (
        <Alert tone="danger" title={t("faturalama.abonelik.iptal.hata.baslik")}>
          {hata}
        </Alert>
      ) : (
        <div className="flex items-start gap-2 text-sm text-neutral-600">
          <TriangleAlert aria-hidden className="mt-0.5 size-4 shrink-0 text-amber-600" />
          <p>
            {once}
            <span className="font-medium text-neutral-900">
              {abonelik.plan?.ad ?? "—"}
            </span>
            {sonra}
          </p>
        </div>
      )}
    </Dialog>
  );
}

/** `POST /faturalama/faturalar/{id}/odendi` — yalnız yerel sağlayıcıda gösterilir. */
export function FaturaOdendiDiyalogu({
  fatura,
  onKapat,
  onIsaretlendi,
}: {
  fatura: Fatura;
  onKapat: () => void;
  onIsaretlendi: () => void;
}) {
  const { t } = useDil();
  const { showToast } = useToast();
  const [isleniyor, setIsleniyor] = useState(false);
  const [hata, setHata] = useState<string | null>(null);

  const isaretle = async () => {
    setIsleniyor(true);
    setHata(null);
    try {
      await faturaOdendi(fatura.id);
      showToast(t("faturalama.fatura.odendi.basarili"), "success");
      onIsaretlendi();
      onKapat();
    } catch (sebep) {
      setHata(faturalamaHatasi(sebep));
    } finally {
      setIsleniyor(false);
    }
  };

  return (
    <Dialog
      open
      onClose={() => {
        if (!isleniyor) onKapat();
      }}
      title={t("faturalama.fatura.odendi.baslik")}
      description={t("faturalama.fatura.odendi.aciklama")}
      footer={
        <>
          <Button variant="ghost" onClick={onKapat} disabled={isleniyor}>
            {t("genel.vazgec")}
          </Button>
          <Button loading={isleniyor} onClick={() => void isaretle()}>
            {t("faturalama.fatura.odendi.onay")}
          </Button>
        </>
      }
    >
      {hata ? (
        <Alert tone="danger" title={t("faturalama.fatura.odendi.hata.baslik")}>
          {hata}
        </Alert>
      ) : (
        <div className="flex flex-col gap-2 text-sm text-neutral-600">
          <p>
            #{sayiBicimle(fatura.id)} · {fatura.tutar}
          </p>
          <Badge tone="warning">{t(FATURA_DURUMU_ANAHTARI[fatura.durum])}</Badge>
        </div>
      )}
    </Dialog>
  );
}

/** Fatura kalemleri ve durum bilgisi. */
export function FaturaDetayDiyalogu({
  fatura,
  onKapat,
}: {
  fatura: Fatura;
  onKapat: () => void;
}) {
  const { t, dil } = useDil();

  /** Kalem tutarı: para birimi kodunu da taşıyan yerel biçim. */
  const tutarBicimle = (kurus: number): string => {
    try {
      return new Intl.NumberFormat(dil === "tr" ? "tr-TR" : "en-US", {
        style: "currency",
        currency: fatura.para,
      }).format(kurus / 100);
    } catch {
      return `${(kurus / 100).toFixed(2)} ${fatura.para}`;
    }
  };

  return (
    <Dialog
      open
      onClose={onKapat}
      title={t("faturalama.fatura.detay.baslik", { id: sayiBicimle(fatura.id) })}
      footer={<Button onClick={onKapat}>{t("genel.kapat")}</Button>}
    >
      <div className="flex flex-col gap-4">
        <p className="text-sm text-neutral-500">{fatura.tutar}</p>

        <dl className="flex flex-col gap-3">
          <div className="flex flex-col gap-1">
            <dt className="text-xs tracking-wide text-neutral-500 uppercase">
              {t("faturalama.fatura.durum")}
            </dt>
            <dd className="text-sm text-neutral-900">
              {t(FATURA_DURUMU_ANAHTARI[fatura.durum])}
            </dd>
          </div>
          <div className="flex flex-col gap-1">
            <dt className="text-xs tracking-wide text-neutral-500 uppercase">
              {t("faturalama.fatura.olusturulma")}
            </dt>
            <dd className="text-sm text-neutral-900">
              {tarihSaatBicimle(fatura.olusturulma)}
            </dd>
          </div>
          <div className="flex flex-col gap-1">
            <dt className="text-xs tracking-wide text-neutral-500 uppercase">
              {t("faturalama.fatura.odeme_tarihi")}
            </dt>
            <dd className="text-sm text-neutral-900">
              {fatura.odeme_tarihi
                ? tarihSaatBicimle(fatura.odeme_tarihi)
                : t("genel.yok")}
            </dd>
          </div>
        </dl>

        <div className="flex flex-col gap-2">
          <p className="text-xs tracking-wide text-neutral-500 uppercase">
            {t("faturalama.fatura.kalemler")}
          </p>
          {fatura.kalemler.length > 0 ? (
            <ul className="flex flex-col divide-y divide-neutral-100 rounded-lg border border-neutral-200">
              {fatura.kalemler.map((kalem, sira) => (
                <li
                  key={`${kalem.aciklama}-${sira}`}
                  className="flex items-start justify-between gap-3 p-3 text-sm"
                >
                  <span className="text-neutral-700">{kalem.aciklama}</span>
                  <span className="shrink-0 font-medium text-neutral-900">
                    {tutarBicimle(kalem.tutar_kurus)}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-neutral-500">{t("faturalama.fatura.kalemler_yok")}</p>
          )}
        </div>
      </div>
    </Dialog>
  );
}
