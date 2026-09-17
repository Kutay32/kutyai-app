"use client";

import { useState } from "react";

import { Search } from "lucide-react";

import { hataMesaji } from "@/lib/api";
import type { BdmKaydi } from "@/lib/bdm";
import {
  EN_BUYUK_UST_K,
  ragAra,
  type AramaYaniti,
} from "@/lib/bilgi-tabani";
import { useDil } from "@/lib/dil";
import type { SozlukAnahtari } from "@/lib/sozluk";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";

/** Gömme üretebilecek durumlar (spec §5). */
const GOMME_DURUMLARI = ["hazir", "calisiyor"];

/** `ayrinti.yol` değerlerinin katalog karşılıkları. */
const YOL_ANAHTARI: Record<string, SozlukAnahtari> = {
  pgvector: "bilgi.arama.yol.pgvector",
  python: "bilgi.arama.yol.python",
};

export type AramaPaneliProps = {
  bdmler: BdmKaydi[];
};

/** RAG araması: sorgu gömülür, en benzer parçalar kaynak olarak listelenir. */
export function AramaPaneli({ bdmler }: AramaPaneliProps) {
  const { t } = useDil();
  const gommeModelleri = bdmler.filter((bdm) => GOMME_DURUMLARI.includes(bdm.durum));

  const [sorgu, setSorgu] = useState("");
  const [bdmId, setBdmId] = useState("");
  const [ustK, setUstK] = useState("");
  const [sorguHatasi, setSorguHatasi] = useState<string | null>(null);
  const [hata, setHata] = useState<string | null>(null);
  const [yanit, setYanit] = useState<AramaYaniti | null>(null);
  const [araniyor, setAraniyor] = useState(false);

  const ara = async (olay: React.FormEvent<HTMLFormElement>) => {
    olay.preventDefault();
    if (!sorgu.trim()) {
      setSorguHatasi(t("bilgi.arama.sorgu.zorunlu"));
      return;
    }
    setSorguHatasi(null);
    setHata(null);
    setAraniyor(true);
    try {
      const sonuc = await ragAra({
        sorgu: sorgu.trim(),
        ...(bdmId ? { bdm_id: Number(bdmId) } : {}),
        ...(ustK ? { ust_k: Number(ustK) } : {}),
      });
      setYanit(sonuc);
    } catch (sebep) {
      setYanit(null);
      setHata(hataMesaji(sebep));
    } finally {
      setAraniyor(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <form
        onSubmit={ara}
        className="grid grid-cols-1 gap-3 rounded-lg border border-neutral-200 bg-white p-4 md:grid-cols-[2fr_1fr_10rem_auto]"
      >
        <Field label={t("bilgi.arama.sorgu")} hint={t("bilgi.arama.sorgu.ipucu")} error={sorguHatasi}>
          {({ id, invalid, ...erisim }) => (
            <Input
              id={id}
              {...erisim}
              invalid={invalid}
              value={sorgu}
              onChange={(olay) => setSorgu(olay.target.value)}
            />
          )}
        </Field>

        <Field label={t("bilgi.arama.bdm")}>
          {({ id, invalid, ...erisim }) => (
            <Select
              id={id}
              {...erisim}
              invalid={invalid}
              value={bdmId}
              onChange={(olay) => setBdmId(olay.target.value)}
            >
              <option value="">{t("bilgi.arama.bdm.otomatik")}</option>
              {gommeModelleri.map((bdm) => (
                <option key={bdm.id} value={bdm.id}>
                  {bdm.gorunen_ad}
                </option>
              ))}
            </Select>
          )}
        </Field>

        <Field label={t("bilgi.arama.ust_k")} hint={t("bilgi.arama.ust_k.ipucu")}>
          {({ id, invalid, ...erisim }) => (
            <Input
              id={id}
              {...erisim}
              invalid={invalid}
              type="number"
              min={1}
              max={EN_BUYUK_UST_K}
              value={ustK}
              onChange={(olay) => setUstK(olay.target.value)}
            />
          )}
        </Field>

        <div className="flex items-end">
          <Button type="submit" loading={araniyor} className="w-full md:w-auto">
            <Search aria-hidden className="size-4" />
            {t("bilgi.arama.gonder")}
          </Button>
        </div>
      </form>

      {gommeModelleri.length === 0 ? (
        <Alert tone="warning">{t("bilgi.arama.baglam.ipucu")}</Alert>
      ) : null}

      {hata ? (
        <Alert tone="danger" title={t("bilgi.arama.hata.baslik")}>
          {hata}
        </Alert>
      ) : null}

      {araniyor ? (
        <div className="flex flex-col gap-2 rounded-lg border border-neutral-200 bg-white p-4">
          <Skeleton className="h-4 w-1/3" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      ) : null}

      {!araniyor && yanit ? (
        <div className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-base font-semibold text-neutral-900">
              {t("bilgi.arama.sonuc.baslik")}
            </h2>
            <Badge tone="neutral">
              {t("bilgi.arama.sonuc.sayi", { sayi: yanit.sonuclar.length })}
            </Badge>
            <Badge tone="info">
              {t("bilgi.arama.yol")}:{" "}
              {YOL_ANAHTARI[yanit.ayrinti.yol]
                ? t(YOL_ANAHTARI[yanit.ayrinti.yol])
                : yanit.ayrinti.yol}
            </Badge>
          </div>

          {yanit.sonuclar.length === 0 ? (
            <EmptyState
              title={t("bilgi.arama.bos.baslik")}
              description={t("bilgi.arama.bos.aciklama")}
            />
          ) : (
            <ol className="flex flex-col gap-3">
              {yanit.sonuclar.map((kaynak, indeks) => (
                <li
                  key={`${kaynak.belge_id}-${kaynak.sira}-${indeks}`}
                  className="flex flex-col gap-2 rounded-lg border border-neutral-200 bg-white p-4"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-medium text-neutral-900">
                        {kaynak.belge_ad}
                      </span>
                      <Badge tone="neutral">
                        {t("bilgi.arama.parca", { sira: kaynak.sira + 1 })}
                      </Badge>
                    </div>
                    <span className="text-xs text-neutral-500">
                      {t("bilgi.arama.skor")}:{" "}
                      <span className="font-mono text-neutral-700">
                        {kaynak.skor.toFixed(3)}
                      </span>
                    </span>
                  </div>
                  <p className="text-sm break-words whitespace-pre-wrap text-neutral-700">
                    {kaynak.icerik}
                  </p>
                </li>
              ))}
            </ol>
          )}
        </div>
      ) : null}
    </div>
  );
}
