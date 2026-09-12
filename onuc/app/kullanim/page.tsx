"use client";

import { useCallback, useEffect, useState } from "react";

import { Korumali } from "@/components/korumali";
import { BuyukKart, Kart } from "@/components/ui/kart";
import { YukleniyorDurumu } from "@/components/ui/yukleniyor";
import { cn } from "@/lib/cn";
import { ApiHatasi, apiFetch } from "@/lib/api";
import { sayiBicimle } from "@/lib/bicim";
import type { KullanimOzeti, KullanimSerisi } from "@/lib/tipler";

const GUN_SECENEKLERI = [7, 30, 90];

const OZET_ALANLARI: { anahtar: keyof KullanimOzeti; etiket: string }[] = [
  { anahtar: "toplam_istek", etiket: "Toplam istek" },
  { anahtar: "toplam_token", etiket: "Toplam token" },
  { anahtar: "basarili", etiket: "Başarılı" },
  { anahtar: "hatali", etiket: "Hatalı" },
  { anahtar: "kota_asimi", etiket: "Kota aşımı" },
  { anahtar: "ortalama_gecikme_ms", etiket: "Ortalama gecikme (ms)" },
];

function KullanimIcerigi() {
  const [gun, setGun] = useState(30);
  const [ozet, setOzet] = useState<KullanimOzeti | null>(null);
  const [seri, setSeri] = useState<KullanimSerisi["seri"]>([]);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [hata, setHata] = useState<string | null>(null);

  const yukle = useCallback(async (seciliGun: number) => {
    setYukleniyor(true);
    setHata(null);
    try {
      const [ozetYaniti, seriYaniti] = await Promise.all([
        apiFetch<KullanimOzeti>(`/kullanim/ozet?gun=${seciliGun}`),
        apiFetch<KullanimSerisi>(`/kullanim/zaman-serisi?gun=${seciliGun}&kirilim=bdm`),
      ]);
      setOzet(ozetYaniti);
      setSeri(seriYaniti.seri ?? []);
    } catch (yakalanan) {
      setOzet(null);
      setSeri([]);
      setHata(
        yakalanan instanceof ApiHatasi
          ? yakalanan.message
          : "Kullanım verileri alınamadı. Lütfen tekrar deneyin.",
      );
    } finally {
      setYukleniyor(false);
    }
  }, []);

  useEffect(() => {
    void yukle(gun);
  }, [gun, yukle]);

  const enYuksekIstek = seri.reduce((enBuyuk, kayit) => Math.max(enBuyuk, kayit.istek), 0);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center gap-1" role="group" aria-label="Zaman aralığı">
        {GUN_SECENEKLERI.map((secenek) => (
          <button
            key={secenek}
            type="button"
            aria-pressed={gun === secenek}
            onClick={() => setGun(secenek)}
            className={cn(
              "rounded-md border px-3 py-1.5 text-[13px] transition-colors focus:border-neutral-900 focus:ring-0",
              gun === secenek
                ? "border-neutral-900 text-neutral-900"
                : "border-neutral-200 text-neutral-500 hover:border-neutral-900 hover:text-neutral-900",
            )}
          >
            Son {secenek} gün
          </button>
        ))}
      </div>

      {hata ? (
        <div role="alert" className="rounded-lg border border-rose-200 p-4">
          <p className="text-[13px] text-rose-600">{hata}</p>
        </div>
      ) : null}

      {yukleniyor ? (
        <Kart>
          <YukleniyorDurumu etiket="Kullanım verileri yükleniyor" />
        </Kart>
      ) : ozet ? (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            {OZET_ALANLARI.map((alan) => (
              <Kart key={alan.anahtar}>
                <p className="text-[13px] text-neutral-500">{alan.etiket}</p>
                <p className="mt-1 text-2xl text-neutral-900">
                  {sayiBicimle(ozet[alan.anahtar])}
                </p>
              </Kart>
            ))}
          </div>

          <Kart className="p-0">
            <div className="border-b border-neutral-100 p-4">
              <h2 className="text-sm font-medium text-neutral-900">Modele göre dağılım</h2>
              <p className="mt-0.5 text-[13px] text-neutral-500">
                Seçilen aralıkta model başına istek ve token toplamı.
              </p>
            </div>
            {seri.length === 0 ? (
              <p className="p-4 text-[13px] text-neutral-500">
                Bu aralıkta kayıtlı kullanım yok.
              </p>
            ) : (
              <table className="w-full border-collapse text-left">
                <caption className="sr-only">Modele göre kullanım dağılımı</caption>
                <thead>
                  <tr className="border-b border-neutral-100 text-[13px] text-neutral-500">
                    <th scope="col" className="p-4 font-normal">
                      Etiket
                    </th>
                    <th scope="col" className="p-4 font-normal">
                      İstek
                    </th>
                    <th scope="col" className="p-4 font-normal">
                      Token
                    </th>
                    <th scope="col" className="hidden p-4 font-normal md:table-cell">
                      Dağılım
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {seri.map((kayit) => (
                    <tr key={kayit.etiket} className="border-b border-neutral-100 last:border-b-0">
                      <th scope="row" className="p-4 text-[13px] font-medium text-neutral-900">
                        {kayit.etiket}
                      </th>
                      <td className="p-4 text-[13px] text-neutral-600">
                        {sayiBicimle(kayit.istek)}
                      </td>
                      <td className="p-4 text-[13px] text-neutral-600">
                        {sayiBicimle(kayit.token)}
                      </td>
                      <td className="hidden p-4 md:table-cell">
                        <div className="h-2 w-full max-w-40 rounded-md border border-neutral-200">
                          <div
                            className="h-full rounded-md bg-neutral-900"
                            style={{
                              width: `${
                                enYuksekIstek > 0 ? Math.round((kayit.istek / enYuksekIstek) * 100) : 0
                              }%`,
                            }}
                          />
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Kart>
        </>
      ) : null}
    </div>
  );
}

export default function KullanimSayfasi() {
  return (
    <Korumali>
      <div className="mx-auto w-full max-w-5xl p-4 md:p-8">
        <div className="mb-6">
          <h1 className="marka-serif text-2xl text-neutral-900">Kullanım</h1>
          <p className="mt-1 text-sm text-neutral-500">
            İstek, token ve gecikme özetiniz.
          </p>
        </div>
        <KullanimIcerigi />
      </div>
    </Korumali>
  );
}
