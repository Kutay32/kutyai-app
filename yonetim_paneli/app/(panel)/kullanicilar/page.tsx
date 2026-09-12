"use client";

import { useState } from "react";

import { Search, UserPlus, Users, X } from "lucide-react";

import { kullaniciOku } from "@/lib/oturum";
import { KULLANICI_DURUMU_ETIKETI, KULLANICI_DURUMU_TONU, ROL_ETIKETI } from "@/lib/etiketler";
import { tarihSaatBicimle } from "@/lib/bicim";
import {
  BASLANGIC_KULLANICI_FILTRESI,
  KULLANICI_DURUMLARI,
  KULLANICI_SAYFA_BOYUTLARI,
  ROLLER,
  kullaniciSorgusu,
  kullanicilariGetir,
  type KullaniciFiltresi,
} from "@/lib/kullanicilar";
import { useUzakVeri } from "@/lib/kancalar";
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
  const [taslak, setTaslak] = useState(filtre);

  return (
    <form
      aria-label="Kullanıcı filtreleri"
      className="grid gap-4 rounded-2xl border border-neutral-200 bg-white p-4 md:grid-cols-4"
      onSubmit={(olay) => {
        olay.preventDefault();
        onUygula({ ...taslak, sayfa: 1 });
      }}
    >
      <Field label="Rol">
        {({ id, ...erisim }) => (
          <Select
            id={id}
            {...erisim}
            value={taslak.rol}
            onChange={(olay) =>
              setTaslak((onceki) => ({ ...onceki, rol: olay.target.value as Rol | "" }))
            }
          >
            <option value="">Tüm roller</option>
            {ROLLER.map((rol) => (
              <option key={rol} value={rol}>
                {ROL_ETIKETI[rol]}
              </option>
            ))}
          </Select>
        )}
      </Field>

      <Field label="Durum">
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
            <option value="">Tüm durumlar</option>
            {KULLANICI_DURUMLARI.map((durum) => (
              <option key={durum} value={durum}>
                {KULLANICI_DURUMU_ETIKETI[durum]}
              </option>
            ))}
          </Select>
        )}
      </Field>

      <Field label="Arama" className="md:col-span-2">
        {({ id, ...erisim }) => (
          <div className="flex items-center gap-2">
            <Input
              id={id}
              {...erisim}
              type="search"
              placeholder="E-posta veya ad soyad"
              value={taslak.arama}
              onChange={(olay) =>
                setTaslak((onceki) => ({ ...onceki, arama: olay.target.value }))
              }
            />
            <Button type="submit" className="shrink-0">
              <Search aria-hidden className="size-4" />
              Filtrele
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
              Temizle
            </Button>
          </div>
        )}
      </Field>
    </form>
  );
}

export default function KullanicilarSayfasi() {
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
            Kullanıcılar
          </h1>
          <p className="text-sm text-neutral-500">
            Personel ve son kullanıcı hesapları; rol ve durum yönetimi.
          </p>
        </div>
        <Button onClick={() => setEkleAcik(true)}>
          <UserPlus aria-hidden className="size-4" />
          Yeni personel
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
                    <TableHead>E-posta</TableHead>
                    <TableHead>Ad soyad</TableHead>
                    <TableHead>Rol</TableHead>
                    <TableHead>Durum</TableHead>
                    <TableHead>Doğrulandı</TableHead>
                    <TableHead>Son giriş</TableHead>
                    <TableHead className="text-right">İşlemler</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {liste.veri.kayitlar.map((kullanici) => (
                    <TableRow key={kullanici.id}>
                      <TableCell className="font-medium text-neutral-900">
                        <span className="flex flex-wrap items-center gap-2">
                          {kullanici.eposta}
                          {kullanici.id === oturumdakiKullanici?.id ? (
                            <Badge tone="info">Siz</Badge>
                          ) : null}
                        </span>
                      </TableCell>
                      <TableCell>{kullanici.ad_soyad || "—"}</TableCell>
                      <TableCell>{ROL_ETIKETI[kullanici.rol]}</TableCell>
                      <TableCell>
                        <Badge tone={KULLANICI_DURUMU_TONU[kullanici.durum]}>
                          {KULLANICI_DURUMU_ETIKETI[kullanici.durum]}
                        </Badge>
                      </TableCell>
                      <TableCell>{kullanici.eposta_dogrulandi ? "Evet" : "Hayır"}</TableCell>
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
                            Düzenle
                          </Button>
                          {kullanici.durum !== "pasif" ? (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setPasiflestirilen(kullanici)}
                            >
                              Pasifleştir
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
                title="Kullanıcı bulunamadı"
                description="Bu filtrelerle eşleşen hesap yok."
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
