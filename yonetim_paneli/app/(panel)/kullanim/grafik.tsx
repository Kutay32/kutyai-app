"use client";

import { VARSAYILAN_KIRILIM_BOYUTU, type ZamanSerisiKaydi } from "@/lib/kullanim";
import { sayiBicimle } from "@/lib/bicim";

const SATIR_YUKSEKLIGI = 28;
const ETIKET_SUTUNU = 190;
const CUBUK_GENISLIGI = 390;
const CUBUK_YUKSEKLIGI = 14;
const GRAFIK_GENISLIGI = 640;
const EN_UZUN_ETIKET = 26;

export type CubukOlcusu = "istek" | "token";

export type CubukGrafikProps = {
  seri: ZamanSerisiKaydi[];
  olcu: CubukOlcusu;
};

/**
 * Kütüphanesiz yatay çubuk grafik. Erişilebilirlik için görsel öğe ekran
 * okuyuculardan gizlenir; aynı veri sayfadaki kırılım tablosunda sunulur.
 */
export function CubukGrafik({ seri, olcu }: CubukGrafikProps) {
  const gosterilen = seri.slice(0, VARSAYILAN_KIRILIM_BOYUTU);
  const enBuyuk = Math.max(0, ...gosterilen.map((kayit) => kayit[olcu]));
  const yukseklik = gosterilen.length * SATIR_YUKSEKLIGI + 8;
  const cubukAlani = ETIKET_SUTUNU + 10;

  return (
    <svg
      viewBox={`0 0 ${GRAFIK_GENISLIGI} ${yukseklik}`}
      className="h-auto w-full"
      aria-hidden
      focusable="false"
    >
      <line
        x1={cubukAlani}
        y1={0}
        x2={cubukAlani}
        y2={yukseklik}
        className="stroke-neutral-200"
        strokeWidth={1}
      />

      {gosterilen.map((kayit, indeks) => {
        const ust = indeks * SATIR_YUKSEKLIGI + 4;
        const orta = ust + SATIR_YUKSEKLIGI / 2;
        const deger = kayit[olcu];
        const genislik = enBuyuk > 0 ? (deger / enBuyuk) * CUBUK_GENISLIGI : 0;
        const etiket =
          kayit.etiket.length > EN_UZUN_ETIKET
            ? `${kayit.etiket.slice(0, EN_UZUN_ETIKET - 1)}…`
            : kayit.etiket;

        return (
          <g key={kayit.etiket}>
            <title>{`${kayit.etiket}: ${sayiBicimle(deger)}`}</title>
            <text
              x={ETIKET_SUTUNU}
              y={orta}
              textAnchor="end"
              dominantBaseline="middle"
              fontSize={12}
              className="fill-neutral-600"
            >
              {etiket}
            </text>

            {genislik > 0 ? (
              <rect
                x={cubukAlani}
                y={orta - CUBUK_YUKSEKLIGI / 2}
                width={genislik}
                height={CUBUK_YUKSEKLIGI}
                rx={3}
                className="fill-neutral-900"
              />
            ) : null}

            <text
              x={cubukAlani + genislik + 8}
              y={orta}
              dominantBaseline="middle"
              fontSize={12}
              className="fill-neutral-500"
            >
              {sayiBicimle(deger)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
