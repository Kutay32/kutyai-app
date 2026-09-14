"use client";

import { useState } from "react";

import { Search, UserPlus, Users, X } from "lucide-react";

import { tarihSaatBicimle } from "@/lib/bicim";
import { useDil } from "@/lib/dil";
import { KULLANICI_DURUMU_ANAHTARI, KULLANICI_DURUMU_TONU, ROL_ANAHTARI } from "@/lib/etiketler";
import { useUzakVeri } from "@/lib/kancalar";
import {
  BASLANGIC_KULLANICI_FILTRESI,
  KULLANICI_DURUMLARI,
  KULLANICI_SAYFA_BOYUTLARI,
  ROLLER,
  kullaniciSorgusu,
  kullanicilariGetir,
  type KullaniciFiltresi,
} from "@/lib/kullanicilar";
import { kullaniciOku } from "@/lib/oturum";
import type { Kullanici, KullaniciDurumu, Rol, Sayfa } from "@/lib/tipler";
import { Sayfalama } from "@/components/loglar/sayfalama";
import { VeriDurumu } from "@/components/loglar/veri-durumu";
import { Badge } from "@/components/ui/badge";
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
import {
  KullaniciDuzenleDiyalogu,
  PasiflestirDiyalogu,
  PersonelEkleDiyalogu,
} from "./kullanici-diyaloglari";

function KullaniciFiltreCubugu({
  filtre,
  onUygula,
}: {
  filtre: KullaniciFiltresi;
  onUygula: (filtre: KullaniciFiltresi) => void;
}) {
  const { t } = useDil();
  const [taslak, setTaslak] = useState(filtre);

  return (
    <form
      aria-label={t("kullanicilar.filtre.aria")}
      className="grid gap-4 rounded-2xl border border-neutral-200 bg-white p-4 md:grid-cols-4"
      onSubmit={(olay) => {
        olay.preventDefault();
        onUygula({ ...taslak, sayfa: 1 });
      }}
    >
      <Field label={t("kullanicilar.rol")}>
        {({ id, ...erisim }) => (
          <Select
            id={id}
            {...erisim}
            value={taslak.rol}
            onChange={(olay) =>
              setTaslak((onceki) => ({ ...onceki, rol: olay.target.value as Rol | "" }))
            }
          >
            <option value="">{t("kullanicilar.filtre.rol.tumu")}</option>
            {ROLLER.map((rol) => (
              <option key={rol} value={rol}>
                {t(ROL_ANAHTARI[rol])}
              </option>
            ))}
          </Select>
        )}
      </Field>

      <Field label={t("kullanicilar.durum")}>
        {({ id, ...erisim }) => (
          <Select
            id={id}
            {...erisim}
            value={taslak.durum}
            onChange={(olay) =>
              setTaslak((onceki) => ({
                ...onceki,
                durum: olay.target.value as KullaniciDurumu | "",
              }))
            }
          >
            <option value="">{t("kullanicilar.filtre.durum.tumu")}</option>
            {KULLANICI_DURUMLARI.map((durum) => (
              <option key={durum} value={durum}>
                {t(KULLANICI_DURUMU_ANAHTARI[durum])}
              </option>
            ))}
          </Select>
        )}
      </Field>

      <Field label={t("kullanicilar.filtre.arama")} className="md:col-span-2">
        {({ id, ...erisim }) => (
          <div className="flex items-center gap-2">
            <Input
              id={id}
              {...erisim}
              type="search"
              placeholder={t("kullanicilar.filtre.arama.yer_tutucu")}
              value={taslak.arama}
              onChange={(olay) =>
                setTaslak((onceki) => ({ ...onceki, arama: olay.target.value }))
              }
            />
            <Button type="submit" className="shrink-0">
              <Search aria-hidden className="size-4" />
              {t("kullanicilar.filtre.uygula")}
            </Button>
            <Button
              type="button"
              variant="ghost"
              className="shrink-0"
              onClick={() => {
                setTaslak(BASLANGIC_KULLANICI_FILTRESI);
                onUygula(BASLANGIC_KULLANICI_FILTRESI);
              }}
            >
              <X aria-hidden className="size-4" />
              {t("kullanicilar.filtre.temizle")}
            </Button>
          </div>
        )}
      </Field>
    </form>
  );
}

export default function KullanicilarSayfasi() {
  const { t } = useDil();
  const [filtre, setFiltre] = useState<KullaniciFiltresi>(BASLANGIC_KULLANICI_FILTRESI);
  const [ekleAcik, setEkleAcik] = useState(false);
  const [duzenlenen, setDuzenlenen] = useState<Kullanici | null>(null);
  const [pasiflestirilen, setPasiflestirilen] = useState<Kullanici | null>(null);

  const liste = useUzakVeri<Sayfa<Kullanici>>(
    () => kullanicilariGetir(filtre),
    [kullaniciSorgusu(filtre)],
  );

  const oturumdakiKullanici = kullaniciOku();

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold tracking-tight text-neutral-900">
            {t("kullanicilar.baslik")}
          </h1>
          <p className="text-sm text-neutral-500">{t("kullanicilar.aciklama")}</p>
        </div>
        <Button onClick={() => setEkleAcik(true)}>
          <UserPlus aria-hidden className="size-4" />
          {t("kullanicilar.yeni")}
        </Button>
      </header>

      <KullaniciFiltreCubugu filtre={filtre} onUygula={setFiltre} />

      <Card className="rounded-2xl">
        <VeriDurumu yukleniyor={liste.yukleniyor} hata={liste.hata} yenile={liste.yenile}>
          {liste.veri && liste.veri.kayitlar.length > 0 ? (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t("kullanicilar.eposta")}</TableHead>
                    <TableHead>{t("kullanicilar.ad_soyad")}</TableHead>
                    <TableHead>{t("kullanicilar.rol")}</TableHead>
                    <TableHead>{t("kullanicilar.durum")}</TableHead>
                    <TableHead>{t("kullanicilar.tablo.dogrulandi")}</TableHead>
                    <TableHead>{t("kullanicilar.tablo.son_giris")}</TableHead>
                    <TableHead className="text-right">{t("kullanicilar.tablo.islemler")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {liste.veri.kayitlar.map((kullanici) => (
                    <TableRow key={kullanici.id}>
                      <TableCell className="font-medium text-neutral-900">
                        <span className="flex flex-wrap items-center gap-2">
                          {kullanici.eposta}
                          {kullanici.id === oturumdakiKullanici?.id ? (
                            <Badge tone="info">{t("kullanicilar.siz")}</Badge>
                          ) : null}
                        </span>
                      </TableCell>
                      <TableCell>{kullanici.ad_soyad || "—"}</TableCell>
                      <TableCell>{t(ROL_ANAHTARI[kullanici.rol])}</TableCell>
                      <TableCell>
                        <Badge tone={KULLANICI_DURUMU_TONU[kullanici.durum]}>
                          {t(KULLANICI_DURUMU_ANAHTARI[kullanici.durum])}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {kullanici.eposta_dogrulandi
                          ? t("kullanicilar.evet")
                          : t("kullanicilar.hayir")}
                      </TableCell>
                      <TableCell className="whitespace-nowrap">
                        {tarihSaatBicimle(kullanici.son_giris)}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => setDuzenlenen(kullanici)}
                          >
                            {t("kullanicilar.duzenle")}
                          </Button>
                          {kullanici.durum !== "pasif" ? (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setPasiflestirilen(kullanici)}
                            >
                              {t("kullanicilar.pasiflestir")}
                            </Button>
                          ) : null}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <div className="border-t border-neutral-200">
                <Sayfalama
                  toplam={liste.veri.toplam}
                  sayfa={liste.veri.sayfa}
                  boyut={liste.veri.boyut}
                  boyutlar={KULLANICI_SAYFA_BOYUTLARI}
                  onSayfa={(sayfa) => setFiltre((onceki) => ({ ...onceki, sayfa }))}
                  onBoyut={(boyut) => setFiltre((onceki) => ({ ...onceki, boyut, sayfa: 1 }))}
                />
              </div>
            </>
          ) : (
            <div className="p-4">
              <EmptyState
                icon={<Users aria-hidden className="size-5" />}
                title={t("kullanicilar.bos.baslik")}
                description={t("kullanicilar.bos.aciklama")}
              />
            </div>
          )}
        </VeriDurumu>
      </Card>

      <PersonelEkleDiyalogu
        acik={ekleAcik}
        onKapat={() => setEkleAcik(false)}
        onEklendi={liste.yenile}
      />

      {duzenlenen ? (
        <KullaniciDuzenleDiyalogu
          kullanici={duzenlenen}
          onKapat={() => setDuzenlenen(null)}
          onKaydedildi={liste.yenile}
        />
      ) : null}

      {pasiflestirilen ? (
        <PasiflestirDiyalogu
          kullanici={pasiflestirilen}
          onKapat={() => setPasiflestirilen(null)}
          onPasiflestirildi={liste.yenile}
        />
      ) : null}
    </div>
  );
}
