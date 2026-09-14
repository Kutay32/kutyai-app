"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { Alan } from "@/components/ui/alan";
import { Buton } from "@/components/ui/buton";
import { BuyukKart } from "@/components/ui/kart";
import { ApiHatasi, apiFetch } from "@/lib/api";
import { useDil } from "@/lib/dil";
import { oturumAl, oturumKaydet } from "@/lib/oturum";
import type { GirisYaniti } from "@/lib/tipler";

export default function GirisSayfasi() {
  const yonlendirici = useRouter();
  const { t } = useDil();
  const [eposta, setEposta] = useState("");
  const [parola, setParola] = useState("");
  const [hata, setHata] = useState<string | null>(null);
  const [dogrulamaGerekli, setDogrulamaGerekli] = useState(false);
  const [gonderiliyor, setGonderiliyor] = useState(false);

  useEffect(() => {
    if (oturumAl()) yonlendirici.replace("/sohbet");
  }, [yonlendirici]);

  async function girisYap(olay: React.FormEvent<HTMLFormElement>) {
    olay.preventDefault();
    setHata(null);
    setDogrulamaGerekli(false);
    setGonderiliyor(true);
    try {
      const yanit = await apiFetch<GirisYaniti>("/kimlik/giris", {
        method: "POST",
        govde: { eposta, parola },
        jeton: null,
        yenilemeDene: false,
      });
      oturumKaydet({
        erisim_jetonu: yanit.erisim_jetonu,
        yenileme_jetonu: yanit.yenileme_jetonu,
      });
      yonlendirici.replace("/sohbet");
    } catch (yakalanan) {
      if (yakalanan instanceof ApiHatasi) {
        setHata(yakalanan.message);
        setDogrulamaGerekli(
          yakalanan.kod === "eposta_dogrulanmadi" || yakalanan.kod === "yetki_yok",
        );
      } else {
        setHata(t("giris.hata"));
      }
      setGonderiliyor(false);
    }
  }

  const [dogrulamaOnce, dogrulamaSonra] = t("giris.dogrulama.metin").split("{baglanti}");

  return (
    <BuyukKart className="p-6">
      <h1 className="marka-serif text-2xl text-neutral-900">{t("giris.baslik")}</h1>
      <p className="mt-1 text-sm text-neutral-500">{t("giris.aciklama")}</p>

      {hata ? (
        <div role="alert" className="mt-4 rounded-lg border border-rose-200 bg-white p-4">
          <p className="text-[13px] text-rose-600">{hata}</p>
          {dogrulamaGerekli ? (
            <p className="mt-1 text-[13px] text-neutral-600">
              {dogrulamaOnce}
              <Link href="/dogrula" className="underline underline-offset-2 hover:text-neutral-900">
                {t("giris.dogrulama.baglanti")}
              </Link>
              {dogrulamaSonra}
            </p>
          ) : null}
        </div>
      ) : null}

      <form onSubmit={girisYap} className="mt-6 flex flex-col gap-4">
        <Alan
          etiket={t("giris.eposta")}
          type="email"
          name="eposta"
          autoComplete="email"
          placeholder={t("giris.eposta.ornek")}
          value={eposta}
          onChange={(olay) => setEposta(olay.target.value)}
          required
        />
        <Alan
          etiket={t("giris.parola")}
          type="password"
          name="parola"
          autoComplete="current-password"
          value={parola}
          onChange={(olay) => setParola(olay.target.value)}
          required
        />
        <Buton type="submit" yukleniyor={gonderiliyor} className="mt-1 w-full">
          {t("giris.baslik")}
        </Buton>
      </form>

      <div className="mt-6 flex flex-col gap-2 border-t border-neutral-100 pt-4 text-[13px] text-neutral-500">
        <Link href="/sifre-sifirla" className="rounded-md hover:text-neutral-900">
          {t("giris.parolami.unuttum")}
        </Link>
        <p>
          {t("giris.hesap.yok")}{" "}
          <Link href="/kayit" className="text-neutral-900 underline underline-offset-2">
            {t("giris.kayit.ol")}
          </Link>
        </p>
      </div>
    </BuyukKart>
  );
}
