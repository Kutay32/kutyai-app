"use client";

import { Suspense, useEffect, useState } from "react";

import { useRouter, useSearchParams } from "next/navigation";

import { ApiHatasi, istek } from "@/lib/api";
import { useDil } from "@/lib/dil";
import { epostaHatasi } from "@/lib/dogrulama";
import { oturumKaydet } from "@/lib/oturum";
import type { KurulumDurumu, OturumYaniti } from "@/lib/tipler";
import { Alert } from "@/components/ui/alert";
import { Brand } from "@/components/panel/brand";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";

type Alanlar = {
  eposta: string;
  parola: string;
};

function GirisFormu() {
  const router = useRouter();
  const aramaParametreleri = useSearchParams();
  const { t } = useDil();
  const kurulumTamam = aramaParametreleri.get("kurulum") === "tamam";

  const [alanlar, setAlanlar] = useState<Alanlar>({ eposta: "", parola: "" });
  const [hatalar, setHatalar] = useState<Partial<Alanlar>>({});
  const [genelHata, setGenelHata] = useState<string | null>(null);
  const [gonderiliyor, setGonderiliyor] = useState(false);
  const [durumKontrol, setDurumKontrol] = useState(true);

  // Kurulum tamamlanmadıysa sihirbaza yönlendir.
  useEffect(() => {
    let iptal = false;
    istek<KurulumDurumu>("/saglik/kurulum", { jeton: null })
      .then((durum) => {
        if (!iptal && !durum.kurulum_tamam) router.replace("/kurulum");
      })
      .catch(() => {
        // Kurulum durumu okunamazsa giriş denenebilir.
      })
      .finally(() => {
        if (!iptal) setDurumKontrol(false);
      });
    return () => {
      iptal = true;
    };
  }, [router]);

  function guncelle(alan: keyof Alanlar, deger: string) {
    setAlanlar((onceki) => ({ ...onceki, [alan]: deger }));
    setHatalar((onceki) => ({ ...onceki, [alan]: undefined }));
    setGenelHata(null);
  }

  async function gonder(olay: React.FormEvent) {
    olay.preventDefault();

    const yeniHatalar: Partial<Alanlar> = {
      eposta: epostaHatasi(alanlar.eposta) ?? undefined,
      parola: alanlar.parola ? undefined : t("dogrulama.parola.zorunlu"),
    };
    setHatalar(yeniHatalar);
    if (yeniHatalar.eposta || yeniHatalar.parola) return;

    setGonderiliyor(true);
    setGenelHata(null);
    try {
      const oturum = await istek<OturumYaniti>("/kimlik/panel-giris", {
        yontem: "POST",
        govde: { eposta: alanlar.eposta.trim().toLowerCase(), parola: alanlar.parola },
        jeton: null,
      });
      oturumKaydet(oturum);
      router.replace("/");
    } catch (hata) {
      if (hata instanceof ApiHatasi && hata.kod === "yetki_yok") {
        setGenelHata(t("giris.hata.rol"));
      } else if (hata instanceof ApiHatasi && hata.durum === 401) {
        setGenelHata(t("giris.hata.kimlik"));
      } else {
        setGenelHata(hata instanceof Error ? hata.message : t("giris.hata.genel"));
      }
    } finally {
      setGonderiliyor(false);
    }
  }

  if (durumKontrol) {
    return (
      <div className="flex items-center gap-2 text-sm text-neutral-500">
        <Spinner />
        {t("genel.yukleniyor")}
      </div>
    );
  }

  return (
    <div className="flex w-full max-w-sm flex-col gap-6">
      <div className="flex flex-col items-center gap-1 text-center">
        <Brand markaAdi="KutyAI" className="text-3xl" />
        <p className="text-sm text-neutral-500">{t("giris.aciklama")}</p>
      </div>

      {kurulumTamam ? (
        <Alert tone="success" title={t("giris.kurulum.baslik")}>
          {t("giris.kurulum.metin")}
        </Alert>
      ) : null}

      {genelHata ? <Alert tone="danger">{genelHata}</Alert> : null}

      <Card className="rounded-2xl">
        <form onSubmit={gonder} noValidate className="flex flex-col gap-4 p-4">
          <Field label={t("genel.eposta")} required error={hatalar.eposta}>
            {(alan) => (
              <Input
                {...alan}
                type="email"
                autoComplete="username"
                value={alanlar.eposta}
                onChange={(olay) => guncelle("eposta", olay.target.value)}
                placeholder={t("giris.eposta.ornek")}
              />
            )}
          </Field>

          <Field label={t("genel.parola")} required error={hatalar.parola}>
            {(alan) => (
              <Input
                {...alan}
                type="password"
                autoComplete="current-password"
                value={alanlar.parola}
                onChange={(olay) => guncelle("parola", olay.target.value)}
              />
            )}
          </Field>

          <Button type="submit" loading={gonderiliyor} className="w-full">
            {t("giris.giris_yap")}
          </Button>
        </form>
      </Card>
    </div>
  );
}

export default function GirisSayfasi() {
  const { t } = useDil();

  return (
    <main className="flex min-h-screen items-center justify-center bg-neutral-50 p-4">
      <Suspense
        fallback={
          <div className="flex items-center gap-2 text-sm text-neutral-500">
            <Spinner />
            {t("genel.yukleniyor")}
          </div>
        }
      >
        <GirisFormu />
      </Suspense>
    </main>
  );
}
