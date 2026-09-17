"use client";

import { useState } from "react";

import { useDil } from "@/lib/dil";
import { useUzakVeri } from "@/lib/kancalar";
import {
  aktifOrganizasyonRolu,
  organizasyonYonetebilirMi,
} from "@/lib/organizasyonlar";
import {
  VARSAYILAN_FATURA_SAYFA_BOYUTU,
  abonelikGetir,
  faturalariGetir,
  planlariGetir,
  type Abonelik,
  type Fatura,
  type Plan,
} from "@/lib/faturalama";
import type { Sayfa } from "@/lib/tipler";
import { AbonelikKarti } from "@/components/faturalama/abonelik-karti";
import { AboneOlDiyalogu } from "@/components/faturalama/faturalama-diyaloglari";
import { FaturaTablosu } from "@/components/faturalama/fatura-tablosu";
import { PlanKartlari } from "@/components/faturalama/plan-kartlari";
import { VeriDurumu } from "@/components/loglar/veri-durumu";

/** Faturalama sayfası: abonelik özeti, plan seçimi ve fatura listesi (spec §6). */
export default function FaturalamaSayfasi() {
  const { t } = useDil();
  const [sayfa, setSayfa] = useState(1);
  const [boyut, setBoyut] = useState<number>(VARSAYILAN_FATURA_SAYFA_BOYUTU);
  const [seciliPlan, setSeciliPlan] = useState<Plan | null>(null);

  const planlar = useUzakVeri<Plan[]>(() => planlariGetir());
  const abonelik = useUzakVeri<Abonelik | null>(() => abonelikGetir());
  const faturalar = useUzakVeri<Sayfa<Fatura>>(
    () => faturalariGetir(sayfa, boyut),
    [sayfa, boyut],
  );
  const rol = useUzakVeri(aktifOrganizasyonRolu);

  // Faturalama yazmaları sahip/yonetici ister; rol bilinmiyorsa düğmeler
  // gizlenmez, yetki kararı sunucuda kalır (403 → katalog mesajı).
  const duzenleyebilir = rol.veri === null || organizasyonYonetebilirMi(rol.veri ?? undefined);

  // Abonelik değişince ilk fatura da oluşur; ikisi birlikte tazelenir.
  const abonelikDegisti = () => {
    abonelik.yenile();
    faturalar.yenile();
  };

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight text-neutral-900">
          {t("faturalama.baslik")}
        </h1>
        <p className="text-sm text-neutral-500">{t("faturalama.aciklama")}</p>
      </header>

      <VeriDurumu
        yukleniyor={abonelik.yukleniyor}
        hata={abonelik.hata}
        yenile={abonelik.yenile}
      >
        <AbonelikKarti
          abonelik={abonelik.veri}
          duzenleyebilir={duzenleyebilir}
          onDegisti={abonelikDegisti}
        />
      </VeriDurumu>

      <VeriDurumu yukleniyor={planlar.yukleniyor} hata={planlar.hata} yenile={planlar.yenile}>
        <PlanKartlari
          planlar={planlar.veri ?? []}
          gecerliPlanId={abonelik.veri?.plan?.id ?? null}
          duzenleyebilir={duzenleyebilir}
          onSec={setSeciliPlan}
        />
      </VeriDurumu>

      <VeriDurumu
        yukleniyor={faturalar.yukleniyor}
        hata={faturalar.hata}
        yenile={faturalar.yenile}
      >
        {faturalar.veri ? (
          <FaturaTablosu
            sayfa={faturalar.veri}
            saglayici={abonelik.veri?.saglayici}
            duzenleyebilir={duzenleyebilir}
            onSayfa={setSayfa}
            onBoyut={(yeniBoyut) => {
              setBoyut(yeniBoyut);
              setSayfa(1);
            }}
            onDegisti={faturalar.yenile}
          />
        ) : null}
      </VeriDurumu>

      {seciliPlan ? (
        <AboneOlDiyalogu
          plan={seciliPlan}
          onKapat={() => setSeciliPlan(null)}
          onBaslatildi={abonelikDegisti}
        />
      ) : null}
    </div>
  );
}
