"use client";

import { useState } from "react";

import { MessageSquare } from "lucide-react";

import { istek } from "@/lib/api";
import {
  BASLANGIC_LOG_FILTRESI,
  LOG_SAYFA_BOYUTLARI,
  loglariGetir,
  logSorgusu,
  type LogFiltresi,
} from "@/lib/loglar";
import { BASLANGIC_KULLANICI_FILTRESI, kullanicilariGetir } from "@/lib/kullanicilar";
import { useUzakVeri } from "@/lib/kancalar";
import type { Bdm, Kullanici, LogKonusmasi, Sayfa } from "@/lib/tipler";
import { FiltreCubugu } from "@/components/loglar/filtre-cubugu";
import { LogTablosu } from "@/components/loglar/tablo";
import { Sayfalama } from "@/components/loglar/sayfalama";
import { VeriDurumu } from "@/components/loglar/veri-durumu";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";

/** Filtre çubuğundaki kullanıcı seçimi için ilk 200 kullanıcı yeterlidir. */
const KULLANICI_SECIM_BOYUTU = 200;

export default function LoglarSayfasi() {
  const [filtre, setFiltre] = useState<LogFiltresi>(BASLANGIC_LOG_FILTRESI);

  const kayitlar = useUzakVeri<Sayfa<LogKonusmasi>>(
    () => loglariGetir(filtre),
    [logSorgusu(filtre)],
  );

  // `GET /kullanicilar` yalnız yöneticiye açıktır; hata alınırsa kimlik ile süzülür.
  const kullaniciListesi = useUzakVeri<Kullanici[]>(
    async () =>
      (await kullanicilariGetir({ ...BASLANGIC_KULLANICI_FILTRESI, boyut: KULLANICI_SECIM_BOYUTU }))
        .kayitlar,
    [],
  );
  const bdmListesi = useUzakVeri<Bdm[]>(() => istek<Bdm[]>("/bdm"), []);

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight text-neutral-900">
          Konuşma Kayıtları
        </h1>
        <p className="text-sm text-neutral-500">
          Kayıtlar maskelenmiş olarak saklanır; filtreleyin, indirin ve yönetin.
        </p>
      </header>

      <FiltreCubugu
        filtre={filtre}
        kullanicilar={kullaniciListesi.hata ? null : (kullaniciListesi.veri ?? [])}
        bdmler={bdmListesi.veri ?? []}
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
              <LogTablosu kayitlar={kayitlar.veri.kayitlar} />
              <div className="border-t border-neutral-200">
                <Sayfalama
                  toplam={kayitlar.veri.toplam}
                  sayfa={kayitlar.veri.sayfa}
                  boyut={kayitlar.veri.boyut}
                  boyutlar={LOG_SAYFA_BOYUTLARI}
                  onSayfa={(sayfa) => setFiltre((onceki) => ({ ...onceki, sayfa }))}
                  onBoyut={(boyut) =>
                    setFiltre((onceki) => ({ ...onceki, boyut, sayfa: 1 }))
                  }
                />
              </div>
            </>
          ) : (
            <div className="p-4">
              <EmptyState
                icon={<MessageSquare aria-hidden className="size-5" />}
                title="Kayıt bulunamadı"
                description="Bu filtrelerle eşleşen konuşma yok. Filtreleri gevşetmeyi deneyin."
              />
            </div>
          )}
        </VeriDurumu>
      </Card>
    </div>
  );
}
