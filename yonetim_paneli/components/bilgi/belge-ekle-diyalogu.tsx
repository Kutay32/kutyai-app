"use client";

import { useState } from "react";

import { Plus } from "lucide-react";

import { hataMesaji } from "@/lib/api";
import { belgeEkle, type BelgeOzeti } from "@/lib/bilgi-tabani";
import type { BdmKaydi } from "@/lib/bdm";
import { useDil } from "@/lib/dil";
import type { DosyaOzeti } from "@/lib/dosyalar";
import { boyutBicimle } from "@/lib/dosyalar";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

/** Gömme üretebilecek durumlar (spec §5: hazır ya da çalışıyor olmalı). */
const GOMME_DURUMLARI = ["hazir", "calisiyor"];

export type BelgeEkleDiyaloguProps = {
  acik: boolean;
  bdmler: BdmKaydi[];
  dosyalar: DosyaOzeti[];
  onKapat: () => void;
  onEklendi: (belge: BelgeOzeti) => void;
};

type KaynakTuru = "metin" | "dosya";

/** Yeni belge: metin ya da yüklenmiş dosyadan parçalama + gömme yapar. */
export function BelgeEkleDiyalogu({
  acik,
  bdmler,
  dosyalar,
  onKapat,
  onEklendi,
}: BelgeEkleDiyaloguProps) {
  const { t } = useDil();
  const gommeModelleri = bdmler.filter((bdm) => GOMME_DURUMLARI.includes(bdm.durum));

  const [ad, setAd] = useState("");
  const [bdmId, setBdmId] = useState("");
  const [kaynakTuru, setKaynakTuru] = useState<KaynakTuru>("metin");
  const [metin, setMetin] = useState("");
  const [dosyaId, setDosyaId] = useState("");
  const [hatalar, setHatalar] = useState<Record<string, string | null>>({});
  const [sunucuHatasi, setSunucuHatasi] = useState<string | null>(null);
  const [gonderiliyor, setGonderiliyor] = useState(false);

  const kapat = () => {
    onKapat();
    setAd("");
    setBdmId("");
    setKaynakTuru("metin");
    setMetin("");
    setDosyaId("");
    setHatalar({});
    setSunucuHatasi(null);
  };

  const gonder = async (olay: React.FormEvent<HTMLFormElement>) => {
    olay.preventDefault();
    const bulunan: Record<string, string | null> = {};
    if (!ad.trim()) bulunan.ad = t("bilgi.ekle.ad.zorunlu");
    if (!bdmId) bulunan.bdm = t("bilgi.ekle.bdm.zorunlu");
    if (kaynakTuru === "metin" && !metin.trim()) {
      bulunan.metin = t("bilgi.ekle.metin.zorunlu");
    }
    if (kaynakTuru === "dosya" && !dosyaId) {
      bulunan.dosya = t("bilgi.ekle.dosya.zorunlu");
    }
    setHatalar(bulunan);
    if (Object.values(bulunan).some(Boolean)) return;

    setSunucuHatasi(null);
    setGonderiliyor(true);
    try {
      const belge = await belgeEkle({
        ad: ad.trim(),
        bdm_id: Number(bdmId),
        ...(kaynakTuru === "metin"
          ? { metin }
          : { dosya_id: Number(dosyaId) }),
      });
      onEklendi(belge);
      kapat();
    } catch (sebep) {
      setSunucuHatasi(hataMesaji(sebep));
    } finally {
      setGonderiliyor(false);
    }
  };

  return (
    <Dialog
      open={acik}
      onClose={kapat}
      className="max-h-[90vh] overflow-y-auto"
      title={t("bilgi.ekle.baslik")}
      description={t("bilgi.ekle.aciklama")}
      footer={
        <>
          <Button variant="ghost" onClick={kapat} disabled={gonderiliyor}>
            {t("bilgi.vazgec")}
          </Button>
          <Button
            type="submit"
            form="belge-ekle-formu"
            loading={gonderiliyor}
            disabled={gommeModelleri.length === 0}
          >
            <Plus aria-hidden className="size-4" />
            {t("bilgi.ekle.gonder")}
          </Button>
        </>
      }
    >
      <form id="belge-ekle-formu" onSubmit={gonder} className="flex flex-col gap-4">
        {sunucuHatasi ? (
          <Alert tone="danger" title={t("bilgi.ekle.hata.baslik")}>
            {sunucuHatasi}
          </Alert>
        ) : null}

        {gommeModelleri.length === 0 ? (
          <Alert tone="warning" title={t("bilgi.ekle.bdm")}>
            {t("bilgi.ekle.bdm.bos")}
          </Alert>
        ) : null}

        <Field label={t("bilgi.ekle.ad")} error={hatalar.ad} required>
          {({ id, invalid, ...erisim }) => (
            <Input
              id={id}
              {...erisim}
              invalid={invalid}
              value={ad}
              onChange={(olay) => setAd(olay.target.value)}
            />
          )}
        </Field>

        <Field label={t("bilgi.ekle.bdm")} hint={t("bilgi.ekle.bdm.ipucu")} error={hatalar.bdm} required>
          {({ id, invalid, ...erisim }) => (
            <Select
              id={id}
              {...erisim}
              invalid={invalid}
              value={bdmId}
              onChange={(olay) => setBdmId(olay.target.value)}
            >
              <option value="">{t("bilgi.ekle.secin")}</option>
              {gommeModelleri.map((bdm) => (
                <option key={bdm.id} value={bdm.id}>
                  {bdm.gorunen_ad}
                </option>
              ))}
            </Select>
          )}
        </Field>

        <Field label={t("bilgi.ekle.kaynak_turu")}>
          {({ id, invalid, ...erisim }) => (
            <Select
              id={id}
              {...erisim}
              invalid={invalid}
              value={kaynakTuru}
              onChange={(olay) => setKaynakTuru(olay.target.value as KaynakTuru)}
            >
              <option value="metin">{t("bilgi.ekle.metin")}</option>
              <option value="dosya">{t("bilgi.ekle.dosya")}</option>
            </Select>
          )}
        </Field>

        {kaynakTuru === "metin" ? (
          <Field
            label={t("bilgi.ekle.metin.alan")}
            hint={t("bilgi.ekle.metin.ipucu")}
            error={hatalar.metin}
            required
          >
            {({ id, invalid, ...erisim }) => (
              <Textarea
                id={id}
                {...erisim}
                invalid={invalid}
                rows={10}
                value={metin}
                onChange={(olay) => setMetin(olay.target.value)}
              />
            )}
          </Field>
        ) : (
          <Field label={t("bilgi.ekle.dosya.alan")} error={hatalar.dosya} required>
            {({ id, invalid, ...erisim }) => (
              <>
                <Select
                  id={id}
                  {...erisim}
                  invalid={invalid}
                  value={dosyaId}
                  onChange={(olay) => setDosyaId(olay.target.value)}
                >
                  <option value="">{t("bilgi.ekle.dosya.secin")}</option>
                  {dosyalar.map((dosya) => (
                    <option key={dosya.id} value={dosya.id}>
                      {`${dosya.ad} · ${boyutBicimle(dosya.boyut)}`}
                    </option>
                  ))}
                </Select>
                {dosyalar.length === 0 ? (
                  <p className="text-xs text-neutral-500">{t("bilgi.ekle.dosya.bos")}</p>
                ) : null}
              </>
            )}
          </Field>
        )}
      </form>
    </Dialog>
  );
}
