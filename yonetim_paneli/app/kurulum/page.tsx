"use client";

import { useEffect, useState } from "react";

import { useRouter } from "next/navigation";

import { Alert } from "@/components/ui/alert";
import { Brand } from "@/components/panel/brand";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import { AdimGostergesi } from "@/components/kurulum/adim-gostergesi";
import { ApiHatasi, istek } from "@/lib/api";
import {
  adresHatasi,
  epostaHatasi,
  parolaHatasi,
  parolaTekrarHatasi,
  zorunluHatasi,
} from "@/lib/dogrulama";
import { useUzakVeri } from "@/lib/kancalar";
import type {
  KurulumDurumu,
  KurulumIstegi,
  KurulumYaniti,
  Saglayici,
  SaglayiciBilgisi,
} from "@/lib/tipler";

const ADIMLAR = ["Şirket Bilgisi", "Yönetici Hesabı", "İlk BDM", "Özet"];

type AlanAdi =
  | "marka_adi"
  | "ad_soyad"
  | "eposta"
  | "parola"
  | "parola_tekrar"
  | "saglayici"
  | "gorunen_ad"
  | "temel_url"
  | "upstream_model"
  | "api_anahtari";

type FormVerisi = Record<AlanAdi, string>;

const BASLANGIC: FormVerisi = {
  marka_adi: "",
  ad_soyad: "",
  eposta: "",
  parola: "",
  parola_tekrar: "",
  saglayici: "",
  gorunen_ad: "",
  temel_url: "",
  upstream_model: "",
  api_anahtari: "",
};

function OzetSatiri({ etiket, deger }: { etiket: string; deger: string }) {
  return (
    <div className="flex justify-between gap-4 border-b border-neutral-100 py-2 text-sm last:border-b-0">
      <dt className="text-neutral-500">{etiket}</dt>
      <dd className="text-right font-medium text-neutral-900">{deger || "—"}</dd>
    </div>
  );
}

export default function KurulumSayfasi() {
  const router = useRouter();

  const [adim, setAdim] = useState(0);
  const [veri, setVeri] = useState<FormVerisi>(BASLANGIC);
  const [hatalar, setHatalar] = useState<Partial<Record<AlanAdi, string>>>({});
  const [genelHata, setGenelHata] = useState<string | null>(null);
  const [uyari, setUyari] = useState<string | null>(null);
  const [gonderiliyor, setGonderiliyor] = useState(false);
  const [durumKontrol, setDurumKontrol] = useState(true);

  const saglayicilar = useUzakVeri<SaglayiciBilgisi[]>(
    () => istek<SaglayiciBilgisi[]>("/saglayicilar", { jeton: null }),
    [],
  );
  const saglayiciListesi = saglayicilar.veri ?? [];
  const seciliSaglayici = saglayiciListesi.find((bilgi) => bilgi.ad === veri.saglayici) ?? null;

  // Kurulum zaten tamamlandıysa giriş sayfasına yönlendir.
  useEffect(() => {
    let iptal = false;
    istek<KurulumDurumu>("/saglik/kurulum", { jeton: null })
      .then((durum) => {
        if (!iptal && durum.kurulum_tamam) router.replace("/giris");
      })
      .catch(() => {
        // Durum okunamazsa sihirbaz gösterilir; gönderim sırasında doğrulanır.
      })
      .finally(() => {
        if (!iptal) setDurumKontrol(false);
      });
    return () => {
      iptal = true;
    };
  }, [router]);

  // Sağlayıcı listesi gelince CPU uyumlu varsayılanı seç.
  useEffect(() => {
    if (veri.saglayici || saglayiciListesi.length === 0) return;
    const varsayilan =
      saglayiciListesi.find((bilgi) => bilgi.ad === "ollama") ?? saglayiciListesi[0];
    setVeri((onceki) => ({
      ...onceki,
      saglayici: varsayilan.ad,
      temel_url: varsayilan.varsayilan_temel_url,
    }));
  }, [saglayiciListesi, veri.saglayici]);

  function guncelle(alan: AlanAdi, deger: string) {
    setVeri((onceki) => ({ ...onceki, [alan]: deger }));
    setHatalar((onceki) => ({ ...onceki, [alan]: undefined }));
    setGenelHata(null);
  }

  function saglayiciSec(ad: string) {
    const bilgi = saglayiciListesi.find((secenek) => secenek.ad === ad);
    setVeri((onceki) => ({
      ...onceki,
      saglayici: ad,
      temel_url: bilgi?.varsayilan_temel_url ?? "",
      api_anahtari: "",
    }));
    setHatalar((onceki) => ({
      ...onceki,
      saglayici: undefined,
      temel_url: undefined,
      api_anahtari: undefined,
    }));
    setGenelHata(null);
  }

  function adimHatalari(sira: number): Partial<Record<AlanAdi, string>> {
    const bulunan: Partial<Record<AlanAdi, string>> = {};
    const ekle = (alan: AlanAdi, mesaj: string | null) => {
      if (mesaj) bulunan[alan] = mesaj;
    };

    if (sira === 0) {
      ekle("marka_adi", zorunluHatasi(veri.marka_adi, "Marka adı"));
    }

    if (sira === 1) {
      ekle("ad_soyad", zorunluHatasi(veri.ad_soyad, "Ad soyad"));
      ekle("eposta", epostaHatasi(veri.eposta));
      ekle("parola", parolaHatasi(veri.parola));
      ekle("parola_tekrar", parolaTekrarHatasi(veri.parola, veri.parola_tekrar));
    }

    if (sira === 2) {
      ekle("saglayici", veri.saglayici ? null : "Sağlayıcı seçimi zorunludur.");
      ekle("gorunen_ad", zorunluHatasi(veri.gorunen_ad, "Görünen ad"));
      ekle("temel_url", adresHatasi(veri.temel_url));
      ekle("upstream_model", zorunluHatasi(veri.upstream_model, "Upstream model"));
      if (seciliSaglayici?.api_anahtari_gerekir) {
        ekle("api_anahtari", zorunluHatasi(veri.api_anahtari, "API anahtarı"));
      }
    }

    return bulunan;
  }

  /**
   * Adım 3'te sağlayıcı listesi hazır değilse ilerlemeyi engelleyen görünür gerekçe.
   * Liste alınamadığında `<select>` hiç render edilmediği için alan hatası görünmez olurdu.
   */
  function saglayiciEngeli(): string | null {
    if (saglayicilar.yukleniyor) return "Sağlayıcı listesi yükleniyor, lütfen bekleyin.";
    if (saglayicilar.hata) {
      return "Sağlayıcı listesi alınamadı. “Yeniden dene” ile listeyi yükleyip tekrar deneyin.";
    }
    return null;
  }

  function ilerle() {
    if (adim === 2) {
      const engel = saglayiciEngeli();
      if (engel) {
        setGenelHata(engel);
        return;
      }
    }

    const bulunan = adimHatalari(adim);
    setHatalar(bulunan);
    if (Object.keys(bulunan).length > 0) return;
    setAdim((sira) => Math.min(sira + 1, ADIMLAR.length - 1));
  }

  function geri() {
    setGenelHata(null);
    setAdim((sira) => Math.max(sira - 1, 0));
  }

  async function bitir() {
    for (const sira of [0, 1, 2]) {
      if (sira === 2) {
        const engel = saglayiciEngeli();
        if (engel) {
          setAdim(2);
          setGenelHata(engel);
          return;
        }
      }
      const bulunan = adimHatalari(sira);
      if (Object.keys(bulunan).length > 0) {
        setHatalar(bulunan);
        setAdim(sira);
        setGenelHata("Kurulumu tamamlamak için işaretli alanları düzeltin.");
        return;
      }
    }

    setGonderiliyor(true);
    setGenelHata(null);
    setUyari(null);
    try {
      const govde: KurulumIstegi = {
        marka_adi: veri.marka_adi.trim(),
        yonetici: {
          eposta: veri.eposta.trim().toLowerCase(),
          ad_soyad: veri.ad_soyad.trim(),
          parola: veri.parola,
        },
        bdm: {
          gorunen_ad: veri.gorunen_ad.trim(),
          saglayici: veri.saglayici as Saglayici,
          temel_url: veri.temel_url.trim(),
          upstream_model: veri.upstream_model.trim(),
          api_anahtari: veri.api_anahtari,
          yerel_mi: seciliSaglayici?.yerel ?? false,
          sistem_istemi: "",
        },
        dogrula: true,
      };

      const yanit = await istek<KurulumYaniti>("/kurulum", { yontem: "POST", govde, jeton: null });
      if (yanit.dogrulama && !yanit.dogrulama.basarili) {
        // Hesap ve model oluşturuldu; bağlantı doğrulanamadı, kullanıcı bilgilendirilir.
        setUyari(
          yanit.dogrulama.mesaj.trim() ||
            "Sağlayıcı adresini, model kimliğini ve varsa API anahtarını denetleyin.",
        );
        return;
      }
      router.replace("/giris?kurulum=tamam");
    } catch (hata) {
      if (hata instanceof ApiHatasi && hata.kod === "kurulum_zaten_tamam") {
        router.replace("/giris");
        return;
      }
      setGenelHata(hata instanceof Error ? hata.message : "Kurulum tamamlanamadı.");
    } finally {
      setGonderiliyor(false);
    }
  }

  if (durumKontrol) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-neutral-50 p-4">
        <div className="flex items-center gap-2 text-sm text-neutral-500">
          <Spinner />
          Yükleniyor…
        </div>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen justify-center bg-neutral-50 p-4">
      <div className="flex w-full max-w-2xl flex-col gap-6 py-6">
        <header className="flex flex-col gap-1">
          <Brand markaAdi="KutyAI" className="text-3xl" />
          <h1 className="text-xl font-semibold tracking-tight text-neutral-900">
            Kurulum Sihirbazı
          </h1>
          <p className="text-sm text-neutral-500">
            Dört adımda platformu çalışır hâle getirin.
          </p>
        </header>

        <AdimGostergesi adimlar={ADIMLAR} aktif={adim} />

        {genelHata ? <Alert tone="danger">{genelHata}</Alert> : null}

        {uyari ? (
          <Alert tone="warning" title="Model bağlantısı doğrulanamadı">
            <p>{uyari}</p>
            <p>
              Yönetici hesabı ve model kaydı oluşturuldu; giriş yapıp model ayarlarını
              denetleyebilirsiniz.
            </p>
          </Alert>
        ) : null}

        <Card className="rounded-2xl">
          <div className="flex flex-col gap-4 p-4">
            {adim === 0 ? (
              <>
                <p className="text-sm text-neutral-500">
                  Panelde ve kullanıcı arayüzünde görünecek marka adını girin.
                </p>
                <Field label="Marka adı" required error={hatalar.marka_adi}>
                  {(alan) => (
                    <Input
                      {...alan}
                      value={veri.marka_adi}
                      onChange={(olay) => guncelle("marka_adi", olay.target.value)}
                      placeholder="Acme AI"
                    />
                  )}
                </Field>
              </>
            ) : null}

            {adim === 1 ? (
              <>
                <p className="text-sm text-neutral-500">
                  Bu hesap yönetici yetkisiyle oluşturulur ve panele giriş yapabilir.
                </p>
                <Field label="Ad soyad" required error={hatalar.ad_soyad}>
                  {(alan) => (
                    <Input
                      {...alan}
                      autoComplete="name"
                      value={veri.ad_soyad}
                      onChange={(olay) => guncelle("ad_soyad", olay.target.value)}
                      placeholder="Ayşe Yılmaz"
                    />
                  )}
                </Field>
                <Field label="E-posta" required error={hatalar.eposta}>
                  {(alan) => (
                    <Input
                      {...alan}
                      type="email"
                      autoComplete="username"
                      value={veri.eposta}
                      onChange={(olay) => guncelle("eposta", olay.target.value)}
                      placeholder="admin@sirket.com"
                    />
                  )}
                </Field>
                <Field
                  label="Parola"
                  required
                  hint="En az 8 karakter."
                  error={hatalar.parola}
                >
                  {(alan) => (
                    <Input
                      {...alan}
                      type="password"
                      autoComplete="new-password"
                      value={veri.parola}
                      onChange={(olay) => guncelle("parola", olay.target.value)}
                    />
                  )}
                </Field>
                <Field label="Parola tekrar" required error={hatalar.parola_tekrar}>
                  {(alan) => (
                    <Input
                      {...alan}
                      type="password"
                      autoComplete="new-password"
                      value={veri.parola_tekrar}
                      onChange={(olay) => guncelle("parola_tekrar", olay.target.value)}
                    />
                  )}
                </Field>
              </>
            ) : null}

            {adim === 2 ? (
              <>
                <p className="text-sm text-neutral-500">
                  Platformun ilk modelini tanımlayın. Kurulum sonunda bağlantı doğrulanır.
                </p>

                {saglayicilar.yukleniyor ? (
                  <div className="flex flex-col gap-2">
                    <Skeleton className="h-4 w-24" />
                    <Skeleton className="h-10 w-full" />
                  </div>
                ) : null}

                {saglayicilar.hata ? (
                  <Alert tone="danger" title="Sağlayıcı listesi alınamadı">
                    <p>Sağlayıcı listesi alınamadı. Sunucu ayakta mı?</p>
                    <Button
                      variant="secondary"
                      size="sm"
                      className="mt-2"
                      onClick={saglayicilar.yenile}
                    >
                      Yeniden dene
                    </Button>
                  </Alert>
                ) : null}

                {!saglayicilar.yukleniyor && !saglayicilar.hata ? (
                  <Field label="Sağlayıcı" required error={hatalar.saglayici}>
                    {(alan) => (
                      <Select
                        {...alan}
                        value={veri.saglayici}
                        onChange={(olay) => saglayiciSec(olay.target.value)}
                      >
                        {saglayiciListesi.map((bilgi) => (
                          <option key={bilgi.ad} value={bilgi.ad}>
                            {bilgi.gorunen_ad}
                          </option>
                        ))}
                      </Select>
                    )}
                  </Field>
                ) : null}

                {seciliSaglayici ? (
                  <p className="text-sm text-neutral-500">
                    {seciliSaglayici.aciklama}
                    {seciliSaglayici.gpu_gerekir
                      ? " Bu sağlayıcı GPU gerektirir; sunucuda GPU yoksa başlatma 503 surucu_yok ile başarısız olur."
                      : null}
                  </p>
                ) : null}

                <Field label="Görünen ad" required error={hatalar.gorunen_ad}>
                  {(alan) => (
                    <Input
                      {...alan}
                      value={veri.gorunen_ad}
                      onChange={(olay) => guncelle("gorunen_ad", olay.target.value)}
                      placeholder="Yerel Llama 3"
                    />
                  )}
                </Field>

                <Field label="Temel adres" required error={hatalar.temel_url}>
                  {(alan) => (
                    <Input
                      {...alan}
                      value={veri.temel_url}
                      onChange={(olay) => guncelle("temel_url", olay.target.value)}
                      placeholder="http://localhost:11434/v1"
                    />
                  )}
                </Field>

                <Field
                  label="Upstream model"
                  required
                  hint="Sağlayıcıdaki model kimliği (ör. llama3, gpt-4o-mini)."
                  error={hatalar.upstream_model}
                >
                  {(alan) => (
                    <Input
                      {...alan}
                      value={veri.upstream_model}
                      onChange={(olay) => guncelle("upstream_model", olay.target.value)}
                      placeholder="llama3"
                    />
                  )}
                </Field>

                {seciliSaglayici?.api_anahtari_gerekir ? (
                  <Field
                    label="API anahtarı"
                    required
                    hint="Anahtar şifrelenerek saklanır ve bir daha gösterilmez."
                    error={hatalar.api_anahtari}
                  >
                    {(alan) => (
                      <Input
                        {...alan}
                        type="password"
                        autoComplete="off"
                        value={veri.api_anahtari}
                        onChange={(olay) => guncelle("api_anahtari", olay.target.value)}
                      />
                    )}
                  </Field>
                ) : null}
              </>
            ) : null}

            {adim === 3 ? (
              <>
                <p className="text-sm text-neutral-500">
                  Bilgileri kontrol edin. Onayladığınızda yönetici hesabı ve ilk model
                  oluşturulur, ardından model bağlantısı doğrulanır.
                </p>
                <dl className="flex flex-col">
                  <OzetSatiri etiket="Marka adı" deger={veri.marka_adi} />
                  <OzetSatiri etiket="Yönetici" deger={veri.ad_soyad} />
                  <OzetSatiri etiket="E-posta" deger={veri.eposta} />
                  <OzetSatiri
                    etiket="Sağlayıcı"
                    deger={seciliSaglayici?.gorunen_ad ?? veri.saglayici}
                  />
                  <OzetSatiri etiket="Model adı" deger={veri.gorunen_ad} />
                  <OzetSatiri etiket="Temel adres" deger={veri.temel_url} />
                  <OzetSatiri etiket="Upstream model" deger={veri.upstream_model} />
                  <OzetSatiri
                    etiket="API anahtarı"
                    deger={seciliSaglayici?.api_anahtari_gerekir ? "Girildi" : "Gerekmiyor"}
                  />
                </dl>
              </>
            ) : null}
          </div>

          <div className="flex items-center justify-between gap-2 border-t border-neutral-200 p-4">
            <Button variant="secondary" onClick={geri} disabled={adim === 0 || gonderiliyor}>
              Geri
            </Button>
            {adim < ADIMLAR.length - 1 ? (
              <Button onClick={ilerle}>İleri</Button>
            ) : uyari ? (
              <Button onClick={() => router.replace("/giris?kurulum=tamam")}>
                Giriş sayfasına git
              </Button>
            ) : (
              <Button onClick={bitir} loading={gonderiliyor}>
                Kurulumu tamamla
              </Button>
            )}
          </div>
        </Card>
      </div>
    </main>
  );
}
