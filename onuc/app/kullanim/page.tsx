"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { Korumali } from "@/components/korumali";
import { Buton } from "@/components/ui/buton";
import { Kart } from "@/components/ui/kart";
import { cn } from "@/lib/cn";
import { ApiHatasi } from "@/lib/api";
import { kisaTarihBicimle, sayiBicimle, tarihBicimle } from "@/lib/bicim";
import { useDil } from "@/lib/dil";
import {
  GUN_SECENEKLERI,
  VARSAYILAN_GUN,
  kisiselKullanimGetir,
  kotaYuzdesi,
  seriYukseklikleri,
} from "@/lib/kullanim";
import type { SozlukAnahtari } from "@/lib/sozluk";
import type { KisiselKullanim } from "@/lib/tipler";

type OlcuAnahtari =
  | "toplam_istek"
  | "toplam_token"
  | "girdi_token"
  | "cikti_token"
  | "ortalama_gecikme_ms";

const OLCULER: { anahtar: OlcuAnahtari; etiket: SozlukAnahtari }[] = [
  { anahtar: "toplam_istek", etiket: "kullanim.olcu.toplam_istek" },
  { anahtar: "toplam_token", etiket: "kullanim.olcu.toplam_token" },
  { anahtar: "girdi_token", etiket: "kullanim.olcu.girdi_token" },
  { anahtar: "cikti_token", etiket: "kullanim.olcu.cikti_token" },
  { anahtar: "ortalama_gecikme_ms", etiket: "kullanim.olcu.ortalama_gecikme" },
];

/** Ölçü kartları ve grafik yerine geçen yükleme iskeleti. */
function Iskelet() {
  const { t } = useDil();

  return (
    <div role="status" aria-live="polite" className="flex flex-col gap-6">
      <span className="sr-only">{t("kullanim.veri.yukleniyor")}</span>
      <div aria-hidden className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {OLCULER.map((olcu) => (
          <Kart key={olcu.anahtar}>
            <div className="h-3 w-20 animate-pulse rounded-md bg-neutral-100" />
            <div className="mt-3 h-7 w-28 animate-pulse rounded-md bg-neutral-100" />
          </Kart>
        ))}
      </div>
      <Kart aria-hidden className="flex flex-col gap-5">
        <div className="h-3 w-32 animate-pulse rounded-md bg-neutral-100" />
        <div className="h-2 w-full animate-pulse rounded-md bg-neutral-100" />
        <div className="h-2 w-full animate-pulse rounded-md bg-neutral-100" />
      </Kart>
      <Kart aria-hidden className="flex flex-col gap-4">
        <div className="h-3 w-40 animate-pulse rounded-md bg-neutral-100" />
        <div className="h-40 w-full animate-pulse rounded-md bg-neutral-100" />
      </Kart>
    </div>
  );
}

type KotaCubuguOzellikleri = {
  etiket: string;
  kullanilan: number;
  /** `null` sınır sınırsız demektir; ilerleme çubuğu yerine yalnız sıfırlanma tarihi yazılır. */
  sinir: number | null;
  birim: string;
  sifirlanma: string;
  sifirlanmaEtiketi: string;
};

function KotaCubugu({
  etiket,
  kullanilan,
  sinir,
  birim,
  sifirlanma,
  sifirlanmaEtiketi,
}: KotaCubuguOzellikleri) {
  const { dil, t } = useDil();
  const yuzde = kotaYuzdesi(kullanilan, sinir);
  const doldu = yuzde !== null && yuzde >= 100;
  const olcu = birim
    ? `${sayiBicimle(kullanilan, dil)} ${birim}`
    : sayiBicimle(kullanilan, dil);
  const sinirMetni =
    sinir === null
      ? t("kullanim.kota.sinirsiz")
      : birim
        ? `${sayiBicimle(sinir, dil)} ${birim}`
        : sayiBicimle(sinir, dil);

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <span className="text-[13px] text-neutral-900">{etiket}</span>
        <span className="text-[13px] text-neutral-500">
          {olcu} / {sinirMetni}
        </span>
      </div>
      {yuzde !== null ? (
        <div
          role="progressbar"
          aria-label={t("kullanim.kota.kullanim.etiket", { etiket })}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={yuzde}
          className="h-2 w-full overflow-hidden rounded-md border border-neutral-200"
        >
          <div
            className={cn("h-full rounded-md", doldu ? "bg-rose-600" : "bg-neutral-900")}
            style={{ width: `${yuzde}%` }}
          />
        </div>
      ) : null}
      <p className="text-[13px] text-neutral-500">
        {t("kullanim.kota.sifirlanma", {
          etiket: sifirlanmaEtiketi,
          tarih: tarihBicimle(sifirlanma, dil),
        })}
      </p>
    </div>
  );
}

function KullanimIcerigi() {
  const { dil, t } = useDil();
  const [gun, setGun] = useState(VARSAYILAN_GUN);
  const [kullanim, setKullanim] = useState<KisiselKullanim | null>(null);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [hata, setHata] = useState<string | null>(null);
  const sonIstek = useRef(0);

  const yukle = useCallback(
    async (seciliGun: number) => {
      const sira = ++sonIstek.current;
      setYukleniyor(true);
      setHata(null);
      try {
        const yanit = await kisiselKullanimGetir(seciliGun);
        if (sira !== sonIstek.current) return;
        setKullanim(yanit);
      } catch (yakalanan) {
        if (sira !== sonIstek.current) return;
        setKullanim(null);
        setHata(
          yakalanan instanceof ApiHatasi ? yakalanan.message : t("kullanim.veri.hata"),
        );
      } finally {
        if (sira === sonIstek.current) setYukleniyor(false);
      }
    },
    [t],
  );

  useEffect(() => {
    void yukle(gun);
  }, [gun, yukle]);

  const seri = kullanim?.seri ?? [];
  const yukseklikler = seriYukseklikleri(seri);
  const enYuksekToken = seri.reduce((enBuyuk, nokta) => Math.max(enBuyuk, nokta.token), 0);

  return (
    <div className="flex flex-col gap-6">
      <div
        className="flex flex-wrap items-center gap-1"
        role="group"
        aria-label={t("kullanim.aralik")}
      >
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
            {t("kullanim.gun", { gun: secenek })}
          </button>
        ))}
      </div>

      {hata ? (
        <Kart role="alert" className="flex flex-col items-start gap-3 border-rose-200">
          <p className="text-[13px] text-rose-600">{hata}</p>
          <Buton tur="ikincil" boyut="kucuk" onClick={() => void yukle(gun)}>
            {t("kullanim.yeniden.dene")}
          </Buton>
        </Kart>
      ) : yukleniyor ? (
        <Iskelet />
      ) : kullanim ? (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            {OLCULER.map((olcu) => (
              <Kart key={olcu.anahtar}>
                <p className="text-[13px] text-neutral-500">{t(olcu.etiket)}</p>
                <p className="mt-1 text-2xl text-neutral-900">
                  {sayiBicimle(kullanim[olcu.anahtar], dil)}
                </p>
              </Kart>
            ))}
          </div>

          <Kart className="flex flex-col gap-5">
            <div>
              <h2 className="text-sm font-medium text-neutral-900">{t("kullanim.kota.baslik")}</h2>
              <p className="mt-0.5 text-[13px] text-neutral-500">
                {t("kullanim.kota.aciklama")}
              </p>
            </div>
            {kullanim.kota ? (
              <>
                <KotaCubugu
                  etiket={t("kullanim.kota.gunluk")}
                  kullanilan={kullanim.kota.kullanilan_gunluk}
                  sinir={kullanim.kota.gunluk_istek}
                  birim=""
                  sifirlanma={kullanim.kota.gun_sifirlanma}
                  sifirlanmaEtiketi={t("kullanim.kota.gunluk.sinir")}
                />
                <KotaCubugu
                  etiket={t("kullanim.kota.aylik")}
                  kullanilan={kullanim.kota.kullanilan_aylik}
                  sinir={kullanim.kota.aylik_token}
                  birim={t("kullanim.birim.token")}
                  sifirlanma={kullanim.kota.ay_sifirlanma}
                  sifirlanmaEtiketi={t("kullanim.kota.aylik.sinir")}
                />
              </>
            ) : (
              <p className="text-[13px] text-neutral-500">{t("kullanim.kota.yok")}</p>
            )}
          </Kart>

          <Kart className="flex flex-col gap-4">
            <div>
              <h2 className="text-sm font-medium text-neutral-900">{t("kullanim.seri.baslik")}</h2>
              <p className="mt-0.5 text-[13px] text-neutral-500">
                {t("kullanim.seri.aciklama", { gun })}
              </p>
            </div>
            {seri.length === 0 ? (
              <p className="text-[13px] text-neutral-500">{t("kullanim.seri.bos")}</p>
            ) : (
              <div className="flex flex-col gap-2">
                <div
                  role="img"
                  aria-label={t("kullanim.grafik.etiket", {
                    gun: seri.length,
                    token: sayiBicimle(enYuksekToken, dil),
                  })}
                  className="flex h-40 items-end gap-1"
                >
                  {seri.map((nokta, sira) => (
                    <div
                      key={nokta.tarih}
                      title={t("kullanim.grafik.nokta", {
                        tarih: nokta.tarih,
                        token: sayiBicimle(nokta.token, dil),
                      })}
                      className="min-w-0 flex-1 rounded-t-md bg-neutral-900"
                      style={{ height: `${yukseklikler[sira]}%` }}
                    />
                  ))}
                </div>
                <div className="flex justify-between text-[13px] text-neutral-500">
                  <span>{kisaTarihBicimle(seri[0]?.tarih, dil)}</span>
                  <span>{kisaTarihBicimle(seri[seri.length - 1]?.tarih, dil)}</span>
                </div>
              </div>
            )}
          </Kart>
        </>
      ) : null}
    </div>
  );
}

export default function KullanimSayfasi() {
  const { t } = useDil();

  return (
    <Korumali>
      <div className="mx-auto w-full max-w-5xl p-4 md:p-8">
        <div className="mb-6">
          <h1 className="marka-serif text-2xl text-neutral-900">{t("kullanim.baslik")}</h1>
          <p className="mt-1 text-sm text-neutral-500">{t("kullanim.aciklama")}</p>
        </div>
        <KullanimIcerigi />
      </div>
    </Korumali>
  );
}
