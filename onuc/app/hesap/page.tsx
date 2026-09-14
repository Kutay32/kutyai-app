"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { DilSecici } from "@/components/dil-secici";
import { Korumali } from "@/components/korumali";
import { BuyukKart, Kart } from "@/components/ui/kart";
import { YukleniyorDurumu } from "@/components/ui/yukleniyor";
import { ApiHatasi, apiFetch } from "@/lib/api";
import { tarihBicimle } from "@/lib/bicim";
import { useDil } from "@/lib/dil";
import { DURUM_ANAHTARLARI, ROL_ANAHTARLARI, type Kullanici } from "@/lib/tipler";

type Satir = { etiket: string; deger: string };

function HesapIcerigi() {
  const { dil, t } = useDil();
  const [kullanici, setKullanici] = useState<Kullanici | null>(null);
  const [hata, setHata] = useState<string | null>(null);

  useEffect(() => {
    let iptal = false;
    apiFetch<Kullanici>("/kimlik/ben")
      .then((yanit) => {
        if (!iptal) setKullanici(yanit);
      })
      .catch((yakalanan: unknown) => {
        if (iptal) return;
        if (yakalanan instanceof ApiHatasi && yakalanan.durum === 404) {
          setHata(t("hesap.kullanilamiyor"));
          return;
        }
        setHata(
          yakalanan instanceof ApiHatasi ? yakalanan.message : t("hesap.hata"),
        );
      });
    return () => {
      iptal = true;
    };
  }, [t]);

  if (hata) {
    return (
      <div role="alert" className="rounded-lg border border-rose-200 p-4">
        <p className="text-[13px] text-rose-600">{hata}</p>
      </div>
    );
  }

  if (!kullanici) return <YukleniyorDurumu etiket={t("hesap.yukleniyor")} />;

  const satirlar: Satir[] = [
    { etiket: t("hesap.ad.soyad"), deger: kullanici.ad_soyad },
    { etiket: t("hesap.eposta"), deger: kullanici.eposta },
    { etiket: t("hesap.rol"), deger: t(ROL_ANAHTARLARI[kullanici.rol]) },
    { etiket: t("hesap.durum"), deger: t(DURUM_ANAHTARLARI[kullanici.durum]) },
    {
      etiket: t("hesap.eposta.dogrulama"),
      deger: kullanici.eposta_dogrulandi ? t("hesap.dogrulandi") : t("hesap.bekliyor"),
    },
    { etiket: t("hesap.kayit.tarihi"), deger: tarihBicimle(kullanici.olusturulma, dil) },
    { etiket: t("hesap.son.giris"), deger: tarihBicimle(kullanici.son_giris, dil) },
  ];

  const [dogrulamaOnce, dogrulamaSonra] = t("hesap.dogrulanmadi").split("{baglanti}");

  return (
    <Kart>
      <dl className="divide-y divide-neutral-100">
        {satirlar.map((satir) => (
          <div key={satir.etiket} className="flex flex-wrap items-center justify-between gap-2 py-3 first:pt-0 last:pb-0">
            <dt className="text-[13px] text-neutral-500">{satir.etiket}</dt>
            <dd className="text-[13px] font-medium text-neutral-900">{satir.deger}</dd>
          </div>
        ))}
      </dl>
      {!kullanici.eposta_dogrulandi ? (
        <p className="mt-4 border-t border-neutral-100 pt-4 text-[13px] text-neutral-600">
          {dogrulamaOnce}
          <Link href="/dogrula" className="text-neutral-900 underline underline-offset-2">
            {t("hesap.dogrulama.baglanti")}
          </Link>
          {dogrulamaSonra}
        </p>
      ) : null}
    </Kart>
  );
}

export default function HesapSayfasi() {
  const { t } = useDil();

  return (
    <Korumali>
      <div className="mx-auto w-full max-w-3xl p-4 md:p-8">
        <BuyukKart className="p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h1 className="marka-serif text-2xl text-neutral-900">{t("hesap.baslik")}</h1>
              <p className="mt-1 text-sm text-neutral-500">{t("hesap.aciklama")}</p>
            </div>
            <DilSecici />
          </div>
          <div className="mt-6">
            <HesapIcerigi />
          </div>
        </BuyukKart>
      </div>
    </Korumali>
  );
}
