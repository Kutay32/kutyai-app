"use client";

import { useEffect, useMemo, useState } from "react";

import { ApiHatasi } from "@/lib/api";
import { adresHatasi, zorunluHatasi } from "@/lib/dogrulama";
import { useUzakVeri } from "@/lib/kancalar";
import {
  bdmGuncelle,
  bdmOlustur,
  gpuGerekir,
  saglayicilariGetir,
  type BdmGirdisi,
  type BdmKaydi,
} from "@/lib/bdm";
import type { Saglayici, SaglayiciBilgisi } from "@/lib/tipler";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/toast";

type AlanAdi =
  | "gorunen_ad"
  | "slug"
  | "aciklama"
  | "saglayici"
  | "temel_url"
  | "upstream_model"
  | "api_anahtari"
  | "baglam_penceresi"
  | "maks_cikti"
  | "sicaklik_varsayilan"
  | "sistem_istemi";

type FormVerisi = Record<AlanAdi, string>;
type AlanHatalari = Partial<Record<AlanAdi, string>>;

const BOS_VERI: FormVerisi = {
  gorunen_ad: "",
  slug: "",
  aciklama: "",
  saglayici: "",
  temel_url: "",
  upstream_model: "",
  api_anahtari: "",
  baglam_penceresi: "8192",
  maks_cikti: "2048",
  sicaklik_varsayilan: "0.7",
  sistem_istemi: "",
};

export type BdmFormuProps = {
  /** `yeni`: POST /bdm, `duzenle`: PATCH /bdm/{id}. */
  mod: "yeni" | "duzenle";
  /** Düzenlemede mevcut kayıt. */
  baslangic?: BdmKaydi;
  onKaydedildi: (bdm: BdmKaydi) => void;
};

function sayiHatasi(deger: string, etiket: string, alt: number, ust: number): string | null {
  const sayi = Number(deger);
  if (!deger.trim() || !Number.isFinite(sayi)) return `${etiket} sayı olmalıdır.`;
  if (sayi < alt || sayi > ust) return `${etiket} ${alt} ile ${ust} arasında olmalıdır.`;
  return null;
}

/** BDM oluşturma/düzenleme formu; sağlayıcı seçimine göre alanları uyarlar (§8). */
export function BdmFormu({ mod, baslangic, onKaydedildi }: BdmFormuProps) {
  const { showToast } = useToast();
  const saglayicilar = useUzakVeri<SaglayiciBilgisi[]>(saglayicilariGetir, []);

  const [veri, setVeri] = useState<FormVerisi>(() =>
    baslangic
      ? {
          gorunen_ad: baslangic.gorunen_ad,
          slug: baslangic.slug,
          aciklama: baslangic.aciklama,
          saglayici: baslangic.saglayici,
          temel_url: baslangic.temel_url,
          upstream_model: baslangic.upstream_model,
          api_anahtari: "",
          baglam_penceresi: String(baslangic.baglam_penceresi),
          maks_cikti: String(baslangic.maks_cikti),
          sicaklik_varsayilan: String(baslangic.sicaklik_varsayilan),
          sistem_istemi: baslangic.sistem_istemi,
        }
      : BOS_VERI,
  );
  const [hatalar, setHatalar] = useState<AlanHatalari>({});
  const [genelHata, setGenelHata] = useState<string | null>(null);
  const [gonderiliyor, setGonderiliyor] = useState(false);

  const saglayiciListesi = useMemo(() => saglayicilar.veri ?? [], [saglayicilar.veri]);
  const secili =
    saglayiciListesi.find((bilgi) => bilgi.ad === veri.saglayici) ?? null;

  // Yeni kayıtta sağlayıcı listesi gelince CPU uyumlu varsayılanı seç.
  useEffect(() => {
    if (mod !== "yeni" || veri.saglayici || saglayiciListesi.length === 0) return;
    const varsayilan =
      saglayiciListesi.find((bilgi) => bilgi.ad === "ollama") ?? saglayiciListesi[0];
    setVeri((onceki) => ({
      ...onceki,
      saglayici: varsayilan.ad,
      temel_url: varsayilan.varsayilan_temel_url,
    }));
  }, [mod, veri.saglayici, saglayiciListesi]);

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

  function alanHatalari(): AlanHatalari {
    const bulunan: AlanHatalari = {};
    const ekle = (alan: AlanAdi, mesaj: string | null) => {
      if (mesaj) bulunan[alan] = mesaj;
    };

    const adHatasi = zorunluHatasi(veri.gorunen_ad, "Görünen ad");
    ekle(
      "gorunen_ad",
      adHatasi ?? (veri.gorunen_ad.trim().length < 2 ? "Görünen ad en az 2 karakter olmalıdır." : null),
    );
    ekle("saglayici", veri.saglayici ? null : "Sağlayıcı seçimi zorunludur.");
    ekle("upstream_model", zorunluHatasi(veri.upstream_model, "Upstream model"));

    const temel = veri.temel_url.trim();
    if (temel) ekle("temel_url", adresHatasi(temel));
    else if (secili && !secili.varsayilan_temel_url) {
      ekle("temel_url", "Bu sağlayıcı için temel adres zorunludur.");
    }

    if (mod === "yeni" && secili?.api_anahtari_gerekir) {
      ekle("api_anahtari", zorunluHatasi(veri.api_anahtari, "API anahtarı"));
    }

    ekle("baglam_penceresi", sayiHatasi(veri.baglam_penceresi, "Bağlam penceresi", 128, 2_000_000));
    ekle("maks_cikti", sayiHatasi(veri.maks_cikti, "Maksimum çıktı", 16, 200_000));
    ekle("sicaklik_varsayilan", sayiHatasi(veri.sicaklik_varsayilan, "Sıcaklık", 0, 2));

    return bulunan;
  }

  async function gonder(olay: React.FormEvent) {
    olay.preventDefault();
    const bulunan = alanHatalari();
    setHatalar(bulunan);
    if (Object.keys(bulunan).length > 0) {
      setGenelHata("Kaydetmek için işaretli alanları düzeltin.");
      return;
    }

    const govde: BdmGirdisi = {
      gorunen_ad: veri.gorunen_ad.trim(),
      aciklama: veri.aciklama.trim(),
      saglayici: veri.saglayici as Saglayici,
      temel_url: veri.temel_url.trim(),
      upstream_model: veri.upstream_model.trim(),
      api_anahtari: veri.api_anahtari,
      baglam_penceresi: Number(veri.baglam_penceresi),
      maks_cikti: Number(veri.maks_cikti),
      sicaklik_varsayilan: Number(veri.sicaklik_varsayilan),
      sistem_istemi: veri.sistem_istemi,
    };

    setGonderiliyor(true);
    setGenelHata(null);
    try {
      if (mod === "yeni") {
        const kayit = await bdmOlustur({ ...govde, slug: veri.slug.trim() || undefined });
        showToast("BDM oluşturuldu.", "success");
        onKaydedildi(kayit);
        return;
      }

      // Boş bırakılan anahtar mevcut anahtarı korur (§8 PATCH).
      const guncelleme: Partial<BdmGirdisi> = { ...govde };
      if (!govde.api_anahtari) delete guncelleme.api_anahtari;
      const kayit = await bdmGuncelle(baslangic?.id ?? 0, guncelleme);
      showToast("Değişiklikler kaydedildi.", "success");
      onKaydedildi(kayit);
    } catch (hata) {
      const mesaj =
        hata instanceof ApiHatasi && hata.kod === "cakisma"
          ? hata.message
          : hata instanceof Error
            ? hata.message
            : "Kayıt tamamlanamadı.";
      if (hata instanceof ApiHatasi && hata.kod === "cakisma") {
        setHatalar((onceki) => ({ ...onceki, slug: mesaj }));
      }
      setGenelHata(mesaj);
    } finally {
      setGonderiliyor(false);
    }
  }

  if (saglayicilar.yukleniyor) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Model bilgileri</CardTitle>
          <CardDescription>Sağlayıcı listesi yükleniyor…</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-2/3" />
        </CardContent>
      </Card>
    );
  }

  if (saglayicilar.hata) {
    return (
      <Alert tone="danger" title="Sağlayıcı listesi alınamadı">
        <p>{saglayicilar.hata}</p>
        <Button variant="secondary" size="sm" className="mt-2" onClick={saglayicilar.yenile}>
          Yeniden dene
        </Button>
      </Alert>
    );
  }

  const gpuUyarisi = secili ? gpuGerekir(secili.ad) : false;

  return (
    <form onSubmit={gonder} className="flex flex-col gap-4" noValidate>
      {genelHata ? <Alert tone="danger">{genelHata}</Alert> : null}

      {gpuUyarisi ? (
        <Alert tone="warning" title="GPU gerektiren sağlayıcı">
          <p>
            {secili?.gorunen_ad} GPU üzerinde çalışır. GPU çalışma zamanı yoksa hazırlama
            ve başlatma uçları <span className="font-medium">503 surucu_yok</span> döner.
          </p>
        </Alert>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Model bilgileri</CardTitle>
          <CardDescription>
            Görünen ad müşteriye gösterilir; slug boş bırakılırsa addan üretilir.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Field label="Görünen ad" required error={hatalar.gorunen_ad}>
            {(props) => (
              <Input
                {...props}
                invalid={props.invalid}
                value={veri.gorunen_ad}
                onChange={(olay) => guncelle("gorunen_ad", olay.target.value)}
                placeholder="Yerel Llama 3"
              />
            )}
          </Field>

          <Field
            label="Slug"
            hint={
              mod === "duzenle"
                ? "Slug oluşturulduktan sonra değiştirilemez."
                : "Boş bırakılırsa görünen addan üretilir."
            }
            error={hatalar.slug}
          >
            {(props) => (
              <Input
                {...props}
                invalid={props.invalid}
                value={veri.slug}
                disabled={mod === "duzenle"}
                onChange={(olay) => guncelle("slug", olay.target.value)}
                placeholder="yerel-llama-3"
              />
            )}
          </Field>

          <Field label="Sağlayıcı" required error={hatalar.saglayici}>
            {(props) => (
              <Select
                {...props}
                invalid={props.invalid}
                value={veri.saglayici}
                onChange={(olay) => saglayiciSec(olay.target.value)}
              >
                <option value="">Seçiniz…</option>
                {saglayiciListesi.map((bilgi) => (
                  <option key={bilgi.ad} value={bilgi.ad}>
                    {bilgi.gorunen_ad}
                  </option>
                ))}
              </Select>
            )}
          </Field>

          <Field label="Upstream model" required error={hatalar.upstream_model}>
            {(props) => (
              <Input
                {...props}
                invalid={props.invalid}
                value={veri.upstream_model}
                onChange={(olay) => guncelle("upstream_model", olay.target.value)}
                placeholder="gpt-4o-mini"
              />
            )}
          </Field>

          <Field
            label="Temel adres"
            hint={
              secili?.varsayilan_temel_url
                ? `Varsayılan: ${secili.varsayilan_temel_url}`
                : "Bu sağlayıcı için adresi siz girmelisiniz."
            }
            error={hatalar.temel_url}
            className="md:col-span-2"
          >
            {(props) => (
              <Input
                {...props}
                invalid={props.invalid}
                value={veri.temel_url}
                onChange={(olay) => guncelle("temel_url", olay.target.value)}
                placeholder={secili?.varsayilan_temel_url || "https://…"}
              />
            )}
          </Field>

          {secili?.api_anahtari_gerekir ? (
            <Field
              label="API anahtarı"
              required={mod === "yeni"}
              hint={
                mod === "duzenle"
                  ? `Boş bırakılırsa değişmez. Mevcut: ${baslangic?.api_anahtari_maskeli || "tanımsız"}`
                  : "Sağlayıcı anahtarı şifrelenerek saklanır."
              }
              error={hatalar.api_anahtari}
              className="md:col-span-2"
            >
              {(props) => (
                <Input
                  {...props}
                  invalid={props.invalid}
                  type="password"
                  autoComplete="off"
                  value={veri.api_anahtari}
                  onChange={(olay) => guncelle("api_anahtari", olay.target.value)}
                  placeholder={baslangic?.api_anahtari_maskeli || "sk-…"}
                />
              )}
            </Field>
          ) : null}

          <Field label="Açıklama" error={hatalar.aciklama} className="md:col-span-2">
            {(props) => (
              <Textarea
                {...props}
                invalid={props.invalid}
                rows={2}
                value={veri.aciklama}
                onChange={(olay) => guncelle("aciklama", olay.target.value)}
                placeholder="Kısa bir açıklama"
              />
            )}
          </Field>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Üretim parametreleri</CardTitle>
          <CardDescription>
            Varsayılanlar sohbet isteklerinde kullanılır; istek başına geçersiz kılınabilir.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <Field
            label="Bağlam penceresi"
            hint="128 – 2.000.000"
            error={hatalar.baglam_penceresi}
          >
            {(props) => (
              <Input
                {...props}
                invalid={props.invalid}
                type="number"
                value={veri.baglam_penceresi}
                onChange={(olay) => guncelle("baglam_penceresi", olay.target.value)}
              />
            )}
          </Field>

          <Field label="Maksimum çıktı" hint="16 – 200.000" error={hatalar.maks_cikti}>
            {(props) => (
              <Input
                {...props}
                invalid={props.invalid}
                type="number"
                value={veri.maks_cikti}
                onChange={(olay) => guncelle("maks_cikti", olay.target.value)}
              />
            )}
          </Field>

          <Field label="Sıcaklık" hint="0 – 2" error={hatalar.sicaklik_varsayilan}>
            {(props) => (
              <Input
                {...props}
                invalid={props.invalid}
                type="number"
                step="0.1"
                value={veri.sicaklik_varsayilan}
                onChange={(olay) => guncelle("sicaklik_varsayilan", olay.target.value)}
              />
            )}
          </Field>

          <Field label="Sistem istemi" className="md:col-span-3" error={hatalar.sistem_istemi}>
            {(props) => (
              <Textarea
                {...props}
                invalid={props.invalid}
                rows={4}
                value={veri.sistem_istemi}
                onChange={(olay) => guncelle("sistem_istemi", olay.target.value)}
                placeholder="Sen yardımcı bir asistansın…"
              />
            )}
          </Field>
        </CardContent>
      </Card>

      <div className="flex items-center gap-2">
        <Button type="submit" loading={gonderiliyor}>
          {mod === "yeni" ? "BDM oluştur" : "Değişiklikleri kaydet"}
        </Button>
      </div>
    </form>
  );
}
