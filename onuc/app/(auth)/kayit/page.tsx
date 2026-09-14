"use client";

import { useState } from "react";
import Link from "next/link";

import { Alan } from "@/components/ui/alan";
import { Buton } from "@/components/ui/buton";
import { BuyukKart } from "@/components/ui/kart";
import { useBildirim } from "@/components/ui/bildirim";
import { ApiHatasi, apiFetch } from "@/lib/api";
import { baglantidanJeton } from "@/lib/baglanti";
import { useDil } from "@/lib/dil";
import type { KayitYaniti } from "@/lib/tipler";

export default function KayitSayfasi() {
  const { goster } = useBildirim();
  const { t } = useDil();
  const [adSoyad, setAdSoyad] = useState("");
  const [eposta, setEposta] = useState("");
  const [parola, setParola] = useState("");
  const [parolaTekrar, setParolaTekrar] = useState("");
  const [hata, setHata] = useState<string | null>(null);
  const [gonderiliyor, setGonderiliyor] = useState(false);
  const [sonuc, setSonuc] = useState<{ mesaj: string; dogrulamaJetonu: string | null } | null>(null);

  async function kayitOl(olay: React.FormEvent<HTMLFormElement>) {
    olay.preventDefault();
    setHata(null);

    if (parola.length < 8) {
      setHata(t("kayit.parola.kisa"));
      return;
    }
    if (parola !== parolaTekrar) {
      setHata(t("kayit.parola.eslesmiyor"));
      return;
    }

    setGonderiliyor(true);
    try {
      const yanit = await apiFetch<KayitYaniti>("/kimlik/kayit", {
        method: "POST",
        govde: { eposta, ad_soyad: adSoyad, parola },
        jeton: null,
        yenilemeDene: false,
      });
      const dogrulamaJetonu = yanit.gelistirme_baglantisi
        ? baglantidanJeton(yanit.gelistirme_baglantisi)
        : null;
      setSonuc({
        mesaj: yanit.dogrulama_gerekli
          ? t("kayit.basarili.dogrulama")
          : t("kayit.basarili"),
        dogrulamaJetonu,
      });
      goster({ tur: "basari", mesaj: t("kayit.bildirim") });
    } catch (yakalanan) {
      setHata(
        yakalanan instanceof ApiHatasi ? yakalanan.message : t("kayit.hata"),
      );
    } finally {
      setGonderiliyor(false);
    }
  }

  if (sonuc) {
    return (
      <BuyukKart className="p-6">
        <h1 className="marka-serif text-2xl text-neutral-900">{t("kayit.tamamlandi.baslik")}</h1>
        <p className="mt-2 text-sm text-neutral-600">{sonuc.mesaj}</p>
        {sonuc.dogrulamaJetonu ? (
          <div className="mt-4 rounded-lg border border-neutral-200 bg-neutral-50 p-4">
            <p className="text-[13px] text-neutral-600">{t("kayit.gelistirme.notu")}</p>
            <Link
              href={`/dogrula?jeton=${encodeURIComponent(sonuc.dogrulamaJetonu)}`}
              className="mt-2 inline-block rounded-md border border-neutral-900 px-3 py-1.5 text-[13px] text-neutral-900 transition-colors hover:bg-neutral-50 focus:border-neutral-900 focus:ring-0"
            >
              {t("kayit.dogrula.dugme")}
            </Link>
          </div>
        ) : null}
        <div className="mt-6 border-t border-neutral-100 pt-4 text-[13px]">
          <Link href="/giris" className="text-neutral-900 underline underline-offset-2">
            {t("kayit.giris.don")}
          </Link>
        </div>
      </BuyukKart>
    );
  }

  return (
    <BuyukKart className="p-6">
      <h1 className="marka-serif text-2xl text-neutral-900">{t("kayit.baslik")}</h1>
      <p className="mt-1 text-sm text-neutral-500">{t("kayit.aciklama")}</p>

      {hata ? (
        <div role="alert" className="mt-4 rounded-lg border border-rose-200 p-4">
          <p className="text-[13px] text-rose-600">{hata}</p>
        </div>
      ) : null}

      <form onSubmit={kayitOl} className="mt-6 flex flex-col gap-4">
        <Alan
          etiket={t("kayit.ad.soyad")}
          name="ad_soyad"
          autoComplete="name"
          value={adSoyad}
          onChange={(olay) => setAdSoyad(olay.target.value)}
          required
        />
        <Alan
          etiket={t("kayit.eposta")}
          type="email"
          name="eposta"
          autoComplete="email"
          value={eposta}
          onChange={(olay) => setEposta(olay.target.value)}
          required
        />
        <Alan
          etiket={t("kayit.parola")}
          type="password"
          name="parola"
          autoComplete="new-password"
          yardim={t("kayit.parola.yardim")}
          value={parola}
          onChange={(olay) => setParola(olay.target.value)}
          required
        />
        <Alan
          etiket={t("kayit.parola.tekrar")}
          type="password"
          name="parola_tekrar"
          autoComplete="new-password"
          value={parolaTekrar}
          onChange={(olay) => setParolaTekrar(olay.target.value)}
          required
        />
        <Buton type="submit" yukleniyor={gonderiliyor} className="mt-1 w-full">
          {t("kayit.buton")}
        </Buton>
      </form>

      <div className="mt-6 border-t border-neutral-100 pt-4 text-[13px] text-neutral-500">
        {t("kayit.hesap.var")}{" "}
        <Link href="/giris" className="text-neutral-900 underline underline-offset-2">
          {t("kayit.giris.yap")}
        </Link>
      </div>
    </BuyukKart>
  );
}
