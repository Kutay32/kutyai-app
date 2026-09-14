"use client";

import { useState } from "react";

import { Search, X } from "lucide-react";

import { useDil } from "@/lib/dil";
import type { LogFiltresi } from "@/lib/loglar";
import { BASLANGIC_LOG_FILTRESI } from "@/lib/loglar";
import type { Bdm, Kullanici } from "@/lib/tipler";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";

export type FiltreCubuguProps = {
  /** Uygulanmış filtre (sayfa ve boyut hariç tutulur). */
  filtre: LogFiltresi;
  /**
   * Kullanıcı listesi; `null` ise liste alınamamıştır (ör. izleyici/operatör için
   * `GET /kullanicilar` → `403`) ve kimlik ile filtreleme sunulur.
   */
  kullanicilar: Kullanici[] | null;
  bdmler: Bdm[];
  onUygula: (filtre: LogFiltresi) => void;
};

/** Kullanıcı, model, tarih aralığı ve tam metin filtrelerini tek satırda toplar. */
export function FiltreCubugu({ filtre, kullanicilar, bdmler, onUygula }: FiltreCubuguProps) {
  const { t } = useDil();
  const [taslak, setTaslak] = useState(filtre);

  const gonder = (olay: React.FormEvent<HTMLFormElement>) => {
    olay.preventDefault();
    onUygula({ ...taslak, sayfa: 1 });
  };

  const temizle = () => {
    setTaslak(BASLANGIC_LOG_FILTRESI);
    onUygula(BASLANGIC_LOG_FILTRESI);
  };

  return (
    <form
      onSubmit={gonder}
      className="grid gap-4 rounded-2xl border border-neutral-200 bg-white p-4 md:grid-cols-4"
      aria-label={t("kayit.filtre.aria")}
    >
      {kullanicilar ? (
        <Field label={t("kayit.filtre.kullanici")}>
          {({ id, ...erisim }) => (
            <Select
              id={id}
              {...erisim}
              value={taslak.kullanici_id === null ? "" : String(taslak.kullanici_id)}
              onChange={(olay) =>
                setTaslak((onceki) => ({
                  ...onceki,
                  kullanici_id: olay.target.value ? Number(olay.target.value) : null,
                }))
              }
            >
              <option value="">{t("kayit.filtre.tum_kullanicilar")}</option>
              {kullanicilar.map((kullanici) => (
                <option key={kullanici.id} value={kullanici.id}>
                  {kullanici.eposta}
                </option>
              ))}
            </Select>
          )}
        </Field>
      ) : (
        <Field
          label={t("kayit.filtre.kullanici_kimligi")}
          hint={t("kayit.filtre.kullanici_kimligi.ipucu")}
        >
          {({ id, ...erisim }) => (
            <Input
              id={id}
              {...erisim}
              type="number"
              min={1}
              inputMode="numeric"
              placeholder={t("kayit.filtre.ornek_kimlik")}
              value={taslak.kullanici_id ?? ""}
              onChange={(olay) =>
                setTaslak((onceki) => ({
                  ...onceki,
                  kullanici_id: olay.target.value ? Number(olay.target.value) : null,
                }))
              }
            />
          )}
        </Field>
      )}

      <Field label={t("kayit.filtre.model")}>
        {({ id, ...erisim }) => (
          <Select
            id={id}
            {...erisim}
            value={taslak.bdm_id === null ? "" : String(taslak.bdm_id)}
            onChange={(olay) =>
              setTaslak((onceki) => ({
                ...onceki,
                bdm_id: olay.target.value ? Number(olay.target.value) : null,
              }))
            }
          >
            <option value="">{t("kayit.filtre.tum_modeller")}</option>
            {bdmler.map((bdm) => (
              <option key={bdm.id} value={bdm.id}>
                {bdm.gorunen_ad}
              </option>
            ))}
          </Select>
        )}
      </Field>

      <Field label={t("kayit.filtre.baslangic")}>
        {({ id, ...erisim }) => (
          <Input
            id={id}
            {...erisim}
            type="date"
            value={taslak.baslangic}
            onChange={(olay) =>
              setTaslak((onceki) => ({ ...onceki, baslangic: olay.target.value }))
            }
          />
        )}
      </Field>

      <Field label={t("kayit.filtre.bitis")}>
        {({ id, ...erisim }) => (
          <Input
            id={id}
            {...erisim}
            type="date"
            value={taslak.bitis}
            onChange={(olay) => setTaslak((onceki) => ({ ...onceki, bitis: olay.target.value }))}
          />
        )}
      </Field>

      <Field label={t("kayit.filtre.arama")} className="md:col-span-2">
        {({ id, ...erisim }) => (
          <Input
            id={id}
            {...erisim}
            type="search"
            placeholder={t("kayit.filtre.arama.ipucu")}
            value={taslak.arama}
            onChange={(olay) => setTaslak((onceki) => ({ ...onceki, arama: olay.target.value }))}
          />
        )}
      </Field>

      <div className="flex items-end gap-2 md:col-span-2">
        <Button type="submit">
          <Search aria-hidden className="size-4" />
          {t("kayit.filtre.uygula")}
        </Button>
        <Button type="button" variant="ghost" onClick={temizle}>
          <X aria-hidden className="size-4" />
          {t("kayit.filtre.temizle")}
        </Button>
      </div>
    </form>
  );
}
