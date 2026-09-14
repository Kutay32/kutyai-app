"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { CheckCircle2, Mail } from "lucide-react";

import { Alan } from "@/components/ui/alan";
import { Buton } from "@/components/ui/buton";
import { BuyukKart } from "@/components/ui/kart";
import { Yukleniyor } from "@/components/ui/yukleniyor";
import { ApiHatasi, apiFetch } from "@/lib/api";
import { baglantidanJeton } from "@/lib/baglanti";
import { useDil } from "@/lib/dil";
import type { MesajYaniti } from "@/lib/tipler";

type Mod = "istek" | "sifirla";

function hataMesaji(yakalanan: unknown, varsayilan: string): string {
  if (yakalanan instanceof ApiHatasi) return yakalanan.message;
  return varsayilan;
}

function SifirlamaIcerigi() {
  const aramaParametreleri = useSearchParams();
  const { t } = useDil();
  const baglantiJetonu = aramaParametreleri.get("jeton") ?? "";
  const [mod, setMod] = useState<Mod>(baglantiJetonu ? "sifirla" : "istek");
  const [eposta, setEposta] = useState("");
  const [jeton, setJeton] = useState(baglantiJetonu);
  const [yeniParola, setYeniParola] = useState("");
  const [yeniParolaTekrar, setYeniParolaTekrar] = useState("");
  const [hata, setHata] = useState<string | null>(null);
  const [basari, setBasari] = useState<string | null>(null);
  const [gonderiliyor, setGonderiliyor] = useState(false);

  function modDegistir(yeni: Mod) {
    setMod(yeni);
    setHata(null);
    setBasari(null);
  }

  async function istekGonder(olay: React.FormEvent<HTMLFormElement>) {
    olay.preventDefault();
    setHata(null);
    setBasari(null);
    setGonderiliyor(true);
    try {
      const yanit = await apiFetch<MesajYaniti>("/kimlik/sifre-sifirlama-iste", {
        method: "POST",
        govde: { eposta },
        jeton: null,
        yenilemeDene: false,
      });
      const jetonCevap = baglantidanJeton(yanit.gelistirme_baglantisi);
      if (jetonCevap) setJeton(jetonCevap);
      setBasari(yanit.mesaj);
    } catch (yakalanan) {
      setHata(hataMesaji(yakalanan, t("sifre.istek.hata")));
    } finally {
      setGonderiliyor(false);
    }
  }

  async function sifirla(olay: React.FormEvent<HTMLFormElement>) {
    olay.preventDefault();
    setHata(null);
    setBasari(null);
    if (yeniParola.length < 8) {
      setHata(t("kayit.parola.kisa"));
      return;
    }
    if (yeniParola !== yeniParolaTekrar) {
      setHata(t("kayit.parola.eslesmiyor"));
      return;
    }
    setGonderiliyor(true);
    try {
      const yanit = await apiFetch<MesajYaniti>("/kimlik/sifre-sifirla", {
        method: "POST",
        govde: { jeton, yeni_parola: yeniParola },
        jeton: null,
        yenilemeDene: false,
      });
      setBasari(yanit.mesaj);
    } catch (yakalanan) {
      setHata(hataMesaji(yakalanan, t("sifre.sifirlama.hata")));
    } finally {
      setGonderiliyor(false);
    }
  }

  const sekmeSinifi = (etkin: boolean) =>
    etkin
      ? "border-neutral-900 text-neutral-900"
      : "border-transparent text-neutral-500 hover:text-neutral-900";

  return (
    <BuyukKart className="p-6">
      <h1 className="marka-serif text-2xl text-neutral-900">{t("sifre.baslik")}</h1>
      <p className="mt-1 text-sm text-neutral-500">{t("sifre.aciklama")}</p>

      <div
        role="tablist"
        aria-label={t("sifre.yontem")}
        className="mt-5 flex gap-1 border-b border-neutral-100"
      >
        <button
          type="button"
          role="tab"
          id="sekme-istek"
          aria-selected={mod === "istek"}
          aria-controls="panel-istek"
          onClick={() => modDegistir("istek")}
          className={`-mb-px rounded-md border-b-2 px-3 py-2 text-[13px] transition-colors focus:border-neutral-900 focus:ring-0 ${sekmeSinifi(mod === "istek")}`}
        >
          {t("sifre.sekme.istek")}
        </button>
        <button
          type="button"
          role="tab"
          id="sekme-sifirla"
          aria-selected={mod === "sifirla"}
          aria-controls="panel-sifirla"
          onClick={() => modDegistir("sifirla")}
          className={`-mb-px rounded-md border-b-2 px-3 py-2 text-[13px] transition-colors focus:border-neutral-900 focus:ring-0 ${sekmeSinifi(mod === "sifirla")}`}
        >
          {t("sifre.sekme.sifirla")}
        </button>
      </div>

      {hata ? (
        <div role="alert" className="mt-4 rounded-lg border border-rose-200 p-4">
          <p className="text-[13px] text-rose-600">{hata}</p>
        </div>
      ) : null}

      {basari ? (
        <div role="status" className="mt-4 flex items-start gap-2 rounded-lg border border-green-200 p-4">
          <CheckCircle2 aria-hidden className="mt-0.5 size-4 shrink-0 text-green-700" />
          <p className="text-[13px] text-neutral-600">{basari}</p>
        </div>
      ) : null}

      {mod === "istek" ? (
        <form
          id="panel-istek"
          role="tabpanel"
          aria-labelledby="sekme-istek"
          onSubmit={istekGonder}
          className="mt-6 flex flex-col gap-4"
        >
          <Alan
            etiket={t("kayit.eposta")}
            type="email"
            name="eposta"
            autoComplete="email"
            value={eposta}
            onChange={(olay) => setEposta(olay.target.value)}
            required
          />
          <Buton type="submit" yukleniyor={gonderiliyor} className="mt-1 w-full">
            <Mail aria-hidden className="size-4" />
            {t("sifre.baglanti.gonder")}
          </Buton>
        </form>
      ) : (
        <form
          id="panel-sifirla"
          role="tabpanel"
          aria-labelledby="sekme-sifirla"
          onSubmit={sifirla}
          className="mt-6 flex flex-col gap-4"
        >
          <Alan
            etiket={t("sifre.jeton")}
            name="jeton"
            autoComplete="one-time-code"
            value={jeton}
            onChange={(olay) => setJeton(olay.target.value)}
            yardim={t("sifre.jeton.yardim")}
            required
          />
          <Alan
            etiket={t("sifre.yeni.parola")}
            type="password"
            name="yeni_parola"
            autoComplete="new-password"
            yardim={t("kayit.parola.yardim")}
            value={yeniParola}
            onChange={(olay) => setYeniParola(olay.target.value)}
            required
          />
          <Alan
            etiket={t("sifre.yeni.parola.tekrar")}
            type="password"
            name="yeni_parola_tekrar"
            autoComplete="new-password"
            value={yeniParolaTekrar}
            onChange={(olay) => setYeniParolaTekrar(olay.target.value)}
            required
          />
          <Buton type="submit" yukleniyor={gonderiliyor} className="mt-1 w-full">
            {t("sifre.buton")}
          </Buton>
        </form>
      )}

      <div className="mt-6 border-t border-neutral-100 pt-4 text-[13px] text-neutral-500">
        <Link href="/giris" className="rounded-md hover:text-neutral-900">
          {t("sifre.giris.don")}
        </Link>
      </div>
    </BuyukKart>
  );
}

export default function SifreSifirlaSayfasi() {
  return (
    <Suspense
      fallback={
        <BuyukKart className="p-6">
          <Yukleniyor />
        </BuyukKart>
      }
    >
      <SifirlamaIcerigi />
    </Suspense>
  );
}
