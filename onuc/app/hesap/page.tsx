"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { Korumali } from "@/components/korumali";
import { BuyukKart, Kart } from "@/components/ui/kart";
import { YukleniyorDurumu } from "@/components/ui/yukleniyor";
import { ApiHatasi, apiFetch } from "@/lib/api";
import { tarihBicimle } from "@/lib/bicim";
import { DURUM_ETIKETLERI, ROL_ETIKETLERI, type Kullanici } from "@/lib/tipler";

type Satir = { etiket: string; deger: string };

function HesapIcerigi() {
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
          setHata("Hesap bilgisi bu sürümde kullanılamıyor.");
          return;
        }
        setHata(
          yakalanan instanceof ApiHatasi
            ? yakalanan.message
            : "Hesap bilgisi alınamadı. Lütfen tekrar deneyin.",
        );
      });
    return () => {
      iptal = true;
    };
  }, []);

  if (hata) {
    return (
      <div role="alert" className="rounded-lg border border-rose-200 p-4">
        <p className="text-[13px] text-rose-600">{hata}</p>
      </div>
    );
  }

  if (!kullanici) return <YukleniyorDurumu etiket="Hesap bilgisi yükleniyor" />;

  const satirlar: Satir[] = [
    { etiket: "Ad soyad", deger: kullanici.ad_soyad },
    { etiket: "E-posta", deger: kullanici.eposta },
    { etiket: "Rol", deger: ROL_ETIKETLERI[kullanici.rol] },
    { etiket: "Durum", deger: DURUM_ETIKETLERI[kullanici.durum] },
    {
      etiket: "E-posta doğrulaması",
      deger: kullanici.eposta_dogrulandi ? "Doğrulandı" : "Bekliyor",
    },
    { etiket: "Kayıt tarihi", deger: tarihBicimle(kullanici.olusturulma) },
    { etiket: "Son giriş", deger: tarihBicimle(kullanici.son_giris) },
  ];

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
          E-posta adresiniz doğrulanmadı.{" "}
          <Link href="/dogrula" className="text-neutral-900 underline underline-offset-2">
            Doğrulama sayfasına
          </Link>{" "}
          gidin.
        </p>
      ) : null}
    </Kart>
  );
}

export default function HesapSayfasi() {
  return (
    <Korumali>
      <div className="mx-auto w-full max-w-3xl p-4 md:p-8">
        <BuyukKart className="p-6">
          <h1 className="marka-serif text-2xl text-neutral-900">Hesabım</h1>
          <p className="mt-1 mb-6 text-sm text-neutral-500">
            Oturum bilgileriniz ve hesap ayrıntılarınız.
          </p>
          <HesapIcerigi />
        </BuyukKart>
      </div>
    </Korumali>
  );
}
