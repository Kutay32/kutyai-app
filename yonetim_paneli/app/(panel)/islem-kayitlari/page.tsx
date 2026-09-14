"use client";

import { useState } from "react";

import { Search, ScrollText, X } from "lucide-react";

import { tarihSaatBicimle } from "@/lib/bicim";
import { useDil } from "@/lib/dil";
import {
  BASLANGIC_ISLEM_FILTRESI,
  ISLEM_SAYFA_BOYUTLARI,
  islemKayitlariniGetir,
  islemSorgusu,
  type IslemFiltresi,
  type IslemKaydi,
} from "@/lib/islem-kayitlari";
import { BASLANGIC_KULLANICI_FILTRESI, kullanicilariGetir } from "@/lib/kullanicilar";
import { useUzakVeri } from "@/lib/kancalar";
import type { Kullanici, Sayfa } from "@/lib/tipler";
import { Sayfalama } from "@/components/loglar/sayfalama";
import { VeriDurumu } from "@/components/loglar/veri-durumu";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { AyrintiCekmecesi, EylemRozeti } from "./ayrinti-cekmecesi";

/** Filtre çubuğundaki kullanıcı seçimi için ilk 200 kullanıcı yeterlidir. */
const KULLANICI_SECIM_BOYUTU = 200;

/** Sunucudaki `islem_kaydet` çağrılarından bilinen eylem adları (öneri listesi). */
const BILINEN_EYLEMLER = [
  "api_anahtari.iptal_edildi",
  "api_anahtari.kullanildi",
  "api_anahtari.olusturuldu",
  "ayar.guncellendi",
  "bdm.dogrulandi",
  "bdm.guncellendi",
  "bdm.kopyalandi",
  "bdm.olusturuldu",
  "bdm.silindi",
  "bdm.yol_guncellendi",
  "kimlik.cikis",
  "kimlik.dogrula",
  "kimlik.giris",
  "kimlik.kayit",
  "kimlik.sifre_sifirla",
  "kimlik.sifre_sifirlama_iste",
  "kimlik.yenile",
  "konusma.silindi",
  "kullanici.guncelle",
  "kullanici.olustur",
  "kullanici.pasiflestir",
  "kurulum.tamamlandi",
  "loglar.temizlendi",
];

function IslemFiltreCubugu({
  filtre,
  kullanicilar,
  onUygula,
}: {
  filtre: IslemFiltresi;
  /** `null` ise kullanıcı listesi alınamamıştır; kimlik ile süzülür. */
  kullanicilar: Kullanici[] | null;
  onUygula: (filtre: IslemFiltresi) => void;
}) {
  const { t } = useDil();
  const [taslak, setTaslak] = useState(filtre);

  return (
    <form
      aria-label={t("islem.filtre.aria")}
      className="grid gap-4 rounded-2xl border border-neutral-200 bg-white p-4 md:grid-cols-4"
      onSubmit={(olay) => {
        olay.preventDefault();
        onUygula({ ...taslak, sayfa: 1 });
      }}
    >
      <Field label={t("islem.filtre.eylem")} hint={t("islem.filtre.eylem.ipucu")}>
        {({ id, ...erisim }) => (
          <>
            <Input
              id={id}
              {...erisim}
              type="search"
              list="bilinen-eylemler"
              autoComplete="off"
              value={taslak.eylem}
              onChange={(olay) => setTaslak((onceki) => ({ ...onceki, eylem: olay.target.value }))}
            />
            <datalist id="bilinen-eylemler">
              {BILINEN_EYLEMLER.map((eylem) => (
                <option key={eylem} value={eylem} />
              ))}
            </datalist>
          </>
        )}
      </Field>

      {kullanicilar ? (
        <Field label={t("islem.filtre.kullanici")}>
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
              <option value="">{t("islem.filtre.tum_kullanicilar")}</option>
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
          label={t("islem.filtre.kullanici_kimligi")}
          hint={t("islem.filtre.kullanici_kimligi.ipucu")}
        >
          {({ id, ...erisim }) => (
            <Input
              id={id}
              {...erisim}
              type="number"
              min={1}
              inputMode="numeric"
              placeholder={t("islem.filtre.ornek_kimlik")}
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

      <Field label={t("islem.filtre.baslangic")}>
        {({ id, ...erisim }) => (
          <Input
            id={id}
            {...erisim}
            type="date"
            value={taslak.baslangic}
            onChange={(olay) => setTaslak((onceki) => ({ ...onceki, baslangic: olay.target.value }))}
          />
        )}
      </Field>

      <Field label={t("islem.filtre.bitis")}>
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

      <div className="flex items-end gap-2 md:col-span-4">
        <Button type="submit">
          <Search aria-hidden className="size-4" />
          {t("islem.filtre.uygula")}
        </Button>
        <Button
          type="button"
          variant="ghost"
          onClick={() => {
            setTaslak(BASLANGIC_ISLEM_FILTRESI);
            onUygula(BASLANGIC_ISLEM_FILTRESI);
          }}
        >
          <X aria-hidden className="size-4" />
          {t("islem.filtre.temizle")}
        </Button>
      </div>
    </form>
  );
}

export default function IslemKayitlariSayfasi() {
  const { t } = useDil();
  const [filtre, setFiltre] = useState<IslemFiltresi>(BASLANGIC_ISLEM_FILTRESI);
  const [secilen, setSecilen] = useState<IslemKaydi | null>(null);

  const kayitlar = useUzakVeri<Sayfa<IslemKaydi>>(
    () => islemKayitlariniGetir(filtre),
    [islemSorgusu(filtre)],
  );

  // `GET /kullanicilar` yalnız yöneticiye açıktır; hata alınırsa kimlik ile süzülür.
  const kullaniciListesi = useUzakVeri<Kullanici[]>(
    async () =>
      (await kullanicilariGetir({ ...BASLANGIC_KULLANICI_FILTRESI, boyut: KULLANICI_SECIM_BOYUTU }))
        .kayitlar,
    [],
  );

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight text-neutral-900">
          {t("islem.baslik")}
        </h1>
        <p className="text-sm text-neutral-500">{t("islem.aciklama")}</p>
      </header>

      <IslemFiltreCubugu
        filtre={filtre}
        kullanicilar={kullaniciListesi.hata ? null : (kullaniciListesi.veri ?? [])}
        onUygula={setFiltre}
      />

      <Card className="rounded-2xl">
        <VeriDurumu
          yukleniyor={kayitlar.yukleniyor}
          hata={kayitlar.hata}
          yenile={kayitlar.yenile}
        >
          {kayitlar.veri && kayitlar.veri.kayitlar.length > 0 ? (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t("islem.tablo.tarih")}</TableHead>
                    <TableHead>{t("islem.tablo.eylem")}</TableHead>
                    <TableHead>{t("islem.tablo.kullanici")}</TableHead>
                    <TableHead>{t("islem.tablo.hedef")}</TableHead>
                    <TableHead>{t("islem.tablo.ip")}</TableHead>
                    <TableHead className="text-right">{t("islem.tablo.ayrinti")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {kayitlar.veri.kayitlar.map((kayit) => (
                    <TableRow
                      key={kayit.id}
                      className="cursor-pointer"
                      onClick={(olay) => {
                        if ((olay.target as HTMLElement).closest("button")) return;
                        setSecilen(kayit);
                      }}
                    >
                      <TableCell className="whitespace-nowrap">
                        {tarihSaatBicimle(kayit.olusturulma)}
                      </TableCell>
                      <TableCell>
                        <EylemRozeti eylem={kayit.eylem} />
                      </TableCell>
                      <TableCell>{kayit.kullanici_eposta ?? "—"}</TableCell>
                      <TableCell className="whitespace-nowrap">
                        {kayit.hedef_tur
                          ? `${kayit.hedef_tur}${kayit.hedef_id ? ` #${kayit.hedef_id}` : ""}`
                          : "—"}
                      </TableCell>
                      <TableCell>{kayit.ip || "—"}</TableCell>
                      <TableCell className="text-right">
                        <Button variant="secondary" size="sm" onClick={() => setSecilen(kayit)}>
                          {t("islem.goruntule")}
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <div className="border-t border-neutral-200">
                <Sayfalama
                  toplam={kayitlar.veri.toplam}
                  sayfa={kayitlar.veri.sayfa}
                  boyut={kayitlar.veri.boyut}
                  boyutlar={ISLEM_SAYFA_BOYUTLARI}
                  onSayfa={(sayfa) => setFiltre((onceki) => ({ ...onceki, sayfa }))}
                  onBoyut={(boyut) => setFiltre((onceki) => ({ ...onceki, boyut, sayfa: 1 }))}
                />
              </div>
            </>
          ) : (
            <div className="p-4">
              <EmptyState
                icon={<ScrollText aria-hidden className="size-5" />}
                title={t("islem.bos.baslik")}
                description={t("islem.bos.aciklama")}
              />
            </div>
          )}
        </VeriDurumu>
      </Card>

      <AyrintiCekmecesi kayit={secilen} onKapat={() => setSecilen(null)} />
    </div>
  );
}
