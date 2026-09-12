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
import type { MesajYaniti } from "@/lib/tipler";

type Mod = "istek" | "sifirla";

function hataMesaji(yakalanan: unknown, varsayilan: string): string {
  if (yakalanan instanceof ApiHatasi) return yakalanan.message;
  return varsayilan;
}

function SifirlamaIcerigi() {
  const aramaParametreleri = useSearchParams();
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
      setHata(hataMesaji(yakalanan, "İstek gönderilemedi. Lütfen tekrar deneyin."));
    } finally {
      setGonderiliyor(false);
    }
  }

  async function sifirla(olay: React.FormEvent<HTMLFormElement>) {
    olay.preventDefault();
    setHata(null);
    setBasari(null);
    if (yeniParola.length < 8) {
      setHata("Parola en az 8 karakter olmalı.");
      return;
    }
    if (yeniParola !== yeniParolaTekrar) {
      setHata("Parolalar birbiriyle eşleşmiyor.");
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
      setHata(hataMesaji(yakalanan, "Parola sıfırlanamadı. Lütfen tekrar deneyin."));
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
      <h1 className="marka-serif text-2xl text-neutral-900">Parola sıfırlama</h1>
      <p className="mt-1 text-sm text-neutral-500">
        E-posta ile sıfırlama bağlantısı isteyin veya elinizdeki jetonla yeni parola belirleyin.
      </p>

      <div role="tablist" aria-label="Parola sıfırlama yöntemi" className="mt-5 flex gap-1 border-b border-neutral-100">
        <button
          type="button"
          role="tab"
          id="sekme-istek"
          aria-selected={mod === "istek"}
          aria-controls="panel-istek"
          onClick={() => modDegistir("istek")}
          className={`-mb-px rounded-md border-b-2 px-3 py-2 text-[13px] transition-colors focus:border-neutral-900 focus:ring-0 ${sekmeSinifi(mod === "istek")}`}
        >
          Bağlantı iste
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
          Jetonla sıfırla
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
            etiket="E-posta"
            type="email"
            name="eposta"
            autoComplete="email"
            value={eposta}
            onChange={(olay) => setEposta(olay.target.value)}
            required
          />
          <Buton type="submit" yukleniyor={gonderiliyor} className="mt-1 w-full">
            <Mail aria-hidden className="size-4" />
            Sıfırlama bağlantısı gönder
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
            etiket="Sıfırlama jetonu"
            name="jeton"
            autoComplete="one-time-code"
            value={jeton}
            onChange={(olay) => setJeton(olay.target.value)}
            yardim="Bağlantıdaki jeton otomatik doldurulur."
            required
          />
          <Alan
            etiket="Yeni parola"
            type="password"
            name="yeni_parola"
            autoComplete="new-password"
            yardim="En az 8 karakter."
            value={yeniParola}
            onChange={(olay) => setYeniParola(olay.target.value)}
            required
          />
          <Alan
            etiket="Yeni parola (tekrar)"
            type="password"
            name="yeni_parola_tekrar"
            autoComplete="new-password"
            value={yeniParolaTekrar}
            onChange={(olay) => setYeniParolaTekrar(olay.target.value)}
            required
          />
          <Buton type="submit" yukleniyor={gonderiliyor} className="mt-1 w-full">
            Parolayı sıfırla
          </Buton>
        </form>
      )}

      <div className="mt-6 border-t border-neutral-100 pt-4 text-[13px] text-neutral-500">
        <Link href="/giris" className="rounded-md hover:text-neutral-900">
          Giriş sayfasına dön
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
          <Yukleniyor etiket="Yükleniyor" />
        </BuyukKart>
      }
    >
      <SifirlamaIcerigi />
    </Suspense>
  );
}
