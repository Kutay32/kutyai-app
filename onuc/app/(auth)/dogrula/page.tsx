"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { CheckCircle2 } from "lucide-react";

import { Alan } from "@/components/ui/alan";
import { Buton } from "@/components/ui/buton";
import { BuyukKart } from "@/components/ui/kart";
import { Yukleniyor } from "@/components/ui/yukleniyor";
import { ApiHatasi, apiFetch } from "@/lib/api";

type Durum = "bekliyor" | "gonderiliyor" | "basarili" | "hata";

function hataMesaji(yakalanan: unknown): string {
  if (yakalanan instanceof ApiHatasi) return yakalanan.message;
  return "Doğrulama tamamlanamadı. Lütfen tekrar deneyin.";
}

function DogrulamaIcerigi() {
  const aramaParametreleri = useSearchParams();
  const baglantiJetonu = aramaParametreleri.get("jeton") ?? "";
  const [jeton, setJeton] = useState(baglantiJetonu);
  const [durum, setDurum] = useState<Durum>(baglantiJetonu ? "gonderiliyor" : "bekliyor");
  const [mesaj, setMesaj] = useState<string | null>(null);

  useEffect(() => {
    if (!baglantiJetonu) return;
    let iptal = false;
    apiFetch<{ dogrulandi: boolean }>("/kimlik/dogrula", {
      method: "POST",
      govde: { jeton: baglantiJetonu },
      jeton: null,
      yenilemeDene: false,
    })
      .then(() => {
        if (iptal) return;
        setDurum("basarili");
        setMesaj("E-posta adresiniz doğrulandı. Artık giriş yapabilirsiniz.");
      })
      .catch((yakalanan: unknown) => {
        if (iptal) return;
        setDurum("hata");
        setMesaj(hataMesaji(yakalanan));
      });
    return () => {
      iptal = true;
    };
  }, [baglantiJetonu]);

  async function dogrula(olay: React.FormEvent<HTMLFormElement>) {
    olay.preventDefault();
    setMesaj(null);
    setDurum("gonderiliyor");
    try {
      await apiFetch<{ dogrulandi: boolean }>("/kimlik/dogrula", {
        method: "POST",
        govde: { jeton },
        jeton: null,
        yenilemeDene: false,
      });
      setDurum("basarili");
      setMesaj("E-posta adresiniz doğrulandı. Artık giriş yapabilirsiniz.");
    } catch (yakalanan) {
      setDurum("hata");
      setMesaj(hataMesaji(yakalanan));
    }
  }

  if (durum === "gonderiliyor") {
    return (
      <BuyukKart className="p-6">
        <h1 className="marka-serif text-2xl text-neutral-900">E-posta doğrulama</h1>
        <div className="py-6">
          <Yukleniyor etiket="Doğrulama bağlantısı denetleniyor" />
        </div>
      </BuyukKart>
    );
  }

  if (durum === "basarili") {
    return (
      <BuyukKart className="p-6">
        <div className="flex items-center gap-2">
          <CheckCircle2 aria-hidden className="size-5 text-green-700" />
          <h1 className="marka-serif text-2xl text-neutral-900">Doğrulandı</h1>
        </div>
        <p role="status" className="mt-2 text-sm text-neutral-600">
          {mesaj}
        </p>
        <div className="mt-6 border-t border-neutral-100 pt-4 text-[13px]">
          <Link href="/giris" className="text-neutral-900 underline underline-offset-2">
            Giriş yapın
          </Link>
        </div>
      </BuyukKart>
    );
  }

  return (
    <BuyukKart className="p-6">
      <h1 className="marka-serif text-2xl text-neutral-900">E-posta doğrulama</h1>
      <p className="mt-1 text-sm text-neutral-500">
        Doğrulama bağlantısındaki jetonu girin.
      </p>

      {durum === "hata" && mesaj ? (
        <div role="alert" className="mt-4 rounded-lg border border-rose-200 p-4">
          <p className="text-[13px] text-rose-600">{mesaj}</p>
        </div>
      ) : null}

      <form onSubmit={dogrula} className="mt-6 flex flex-col gap-4">
        <Alan
          etiket="Doğrulama jetonu"
          name="jeton"
          autoComplete="one-time-code"
          value={jeton}
          onChange={(olay) => setJeton(olay.target.value)}
          yardim="Bağlantıdaki jeton otomatik doldurulur."
          required
        />
        <Buton type="submit" className="mt-1 w-full">
          Doğrula
        </Buton>
      </form>

      <div className="mt-6 border-t border-neutral-100 pt-4 text-[13px] text-neutral-500">
        <Link href="/giris" className="rounded-md hover:text-neutral-900">
          Giriş sayfasına dön
        </Link>
      </div>
    </BuyukKart>
  );
}

export default function DogrulaSayfasi() {
  return (
    <Suspense
      fallback={
        <BuyukKart className="p-6">
          <Yukleniyor etiket="Yükleniyor" />
        </BuyukKart>
      }
    >
      <DogrulamaIcerigi />
    </Suspense>
  );
}
