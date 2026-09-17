"use client";

import { useEffect, useState } from "react";
import { Download, Image as ImageIcon, Volume2 } from "lucide-react";

import { Korumali, useKullanici, useUyelikRolu } from "@/components/korumali";
import { GorselOnizleme, SesOynatici } from "@/components/medya/medya-onizleme";
import { Buton } from "@/components/ui/buton";
import { Kart } from "@/components/ui/kart";
import { YukleniyorDurumu } from "@/components/ui/yukleniyor";
import { useBildirim } from "@/components/ui/bildirim";
import { YetkiKarti } from "@/components/yetki-karti";
import { ApiHatasi, apiFetch } from "@/lib/api";
import { boyutBicimle } from "@/lib/bicim";
import { useDil } from "@/lib/dil";
import {
  GORSEL_BOYUTLARI,
  SES_ADLARI,
  SES_BICIMLERI,
  VARSAYILAN_BICIM,
  VARSAYILAN_GORSEL_BOYUTU,
  VARSAYILAN_SES,
  gorselUret,
  sesDosyasiUret,
  uretilenDosyayiIndir,
  type UretilenDosya,
} from "@/lib/medya";
import type { BdmOzet } from "@/lib/sohbet";
import { medyaYetkiliMi } from "@/lib/tipler";

/** Sunucunun `medya_desteklenmiyor` hatası da bu bantta Türkçe mesajıyla görünür. */
function HataBandi({ mesaj, onYenile }: { mesaj: string; onYenile: () => void }) {
  const { t } = useDil();
  return (
    <Kart role="alert" className="flex flex-wrap items-center justify-between gap-2 border-rose-200">
      <p className="text-[13px] text-rose-600">{mesaj}</p>
      <Buton tur="ikincil" boyut="kucuk" onClick={onYenile}>
        {t("medya.yenile")}
      </Buton>
    </Kart>
  );
}

type Secenek = { deger: string; etiket: string };

/** Etiketli seçim alanı; `Alan` yalnız metin girdisi sunduğu için ayrı tutulur. */
function Secim({
  id,
  etiket,
  deger,
  secenekler,
  yerTutucu,
  devreDisi,
  onSec,
}: {
  id: string;
  etiket: string;
  deger: string;
  secenekler: Secenek[];
  yerTutucu?: string;
  devreDisi: boolean;
  onSec: (deger: string) => void;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-[13px] font-medium text-neutral-900">
        {etiket}
      </label>
      <select
        id={id}
        value={deger}
        disabled={devreDisi}
        onChange={(olay) => onSec(olay.target.value)}
        className="h-10 w-full rounded-lg border border-neutral-200 bg-white px-3 text-sm text-neutral-900 transition-colors focus:border-neutral-900 focus:ring-0 focus:outline-none disabled:cursor-not-allowed disabled:bg-neutral-50"
      >
        {yerTutucu && deger === "" ? (
          <option value="" disabled>
            {yerTutucu}
          </option>
        ) : null}
        {secenekler.map((secenek) => (
          <option key={secenek.deger} value={secenek.deger}>
            {secenek.etiket}
          </option>
        ))}
      </select>
    </div>
  );
}

/** Çok satırlı istem alanı; `Alan` ile aynı yüzey sınıflarını taşır. */
function MetinAlani({
  id,
  etiket,
  ipucu,
  deger,
  devreDisi,
  onDegistir,
}: {
  id: string;
  etiket: string;
  ipucu: string;
  deger: string;
  devreDisi: boolean;
  onDegistir: (deger: string) => void;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-[13px] font-medium text-neutral-900">
        {etiket}
      </label>
      <textarea
        id={id}
        rows={4}
        value={deger}
        disabled={devreDisi}
        placeholder={ipucu}
        onChange={(olay) => onDegistir(olay.target.value)}
        className="min-h-24 w-full resize-y rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900 transition-colors placeholder:text-neutral-400 focus:border-neutral-900 focus:ring-0 focus:outline-none disabled:cursor-not-allowed disabled:bg-neutral-50"
      />
    </div>
  );
}

/** Üretilen dosyaların ortak listesi: önizleme/oynatıcı ve indirme düğmesi. */
function SonucListesi({
  dosyalar,
  onIndir,
  onizleme,
}: {
  dosyalar: UretilenDosya[];
  onIndir: (dosya: UretilenDosya) => void;
  onizleme: (dosya: UretilenDosya) => React.ReactNode;
}) {
  const { dil, t } = useDil();
  return (
    <ul className="flex flex-col gap-4">
      {dosyalar.map((dosya) => (
        <li key={dosya.dosya_id} className="flex flex-col gap-2">
          {onizleme(dosya)}
          <div className="flex flex-wrap items-center gap-2">
            <span className="min-w-0 truncate text-[13px] text-neutral-600">{dosya.ad}</span>
            <span className="text-[13px] text-neutral-500">{boyutBicimle(dosya.boyut, dil)}</span>
            <Buton
              tur="ikincil"
              boyut="kucuk"
              onClick={() => onIndir(dosya)}
              aria-label={t("medya.indir.etiket", { ad: dosya.ad })}
            >
              <Download aria-hidden className="size-3.5" />
              {t("medya.indir")}
            </Buton>
          </div>
        </li>
      ))}
    </ul>
  );
}

function MedyaIcerigi() {
  const { t } = useDil();
  const { goster } = useBildirim();
  const [modeller, setModeller] = useState<BdmOzet[] | null>(null);
  const [modelHatasi, setModelHatasi] = useState<string | null>(null);

  const [gorselBdm, setGorselBdm] = useState<number | null>(null);
  const [istem, setIstem] = useState("");
  const [boyut, setBoyut] = useState<string>(VARSAYILAN_GORSEL_BOYUTU);
  const [gorseller, setGorseller] = useState<UretilenDosya[]>([]);
  const [gorselYukleniyor, setGorselYukleniyor] = useState(false);
  const [gorselHata, setGorselHata] = useState<string | null>(null);

  const [sesBdm, setSesBdm] = useState<number | null>(null);
  const [metin, setMetin] = useState("");
  const [ses, setSes] = useState<string>(VARSAYILAN_SES);
  const [bicim, setBicim] = useState<string>(VARSAYILAN_BICIM);
  const [sesler, setSesler] = useState<UretilenDosya[]>([]);
  const [sesYukleniyor, setSesYukleniyor] = useState(false);
  const [sesHata, setSesHata] = useState<string | null>(null);

  async function modelleriYukle() {
    setModelHatasi(null);
    try {
      const gelen = await apiFetch<BdmOzet[]>("/modeller");
      setModeller(gelen);
      setGorselBdm(gelen.find((model) => model.yetenekler.gorsel)?.id ?? null);
      setSesBdm(gelen.find((model) => model.yetenekler.ses)?.id ?? null);
    } catch (yakalanan) {
      setModeller([]);
      setModelHatasi(
        yakalanan instanceof ApiHatasi ? yakalanan.message : t("sohbet.hata.beklenmeyen"),
      );
    }
  }

  useEffect(() => {
    void modelleriYukle();
  }, []);

  const gorselModeller = (modeller ?? []).filter((model) => model.yetenekler.gorsel);
  const sesModeller = (modeller ?? []).filter((model) => model.yetenekler.ses);
  const gorselDevreDisi = gorselYukleniyor || gorselBdm === null;
  const sesDevreDisi = sesYukleniyor || sesBdm === null;

  async function gorselUretTikla() {
    if (gorselBdm === null || istem.trim().length === 0) return;
    setGorselYukleniyor(true);
    setGorselHata(null);
    try {
      const uretilenler = await gorselUret({ bdm_id: gorselBdm, istem: istem.trim(), boyut });
      setGorseller((onceki) => [...uretilenler, ...onceki]);
    } catch (yakalanan) {
      // Yetenek kapalıysa (`medya_desteklenmiyor`) mesaj sunucudan seçilen dilde gelir.
      setGorselHata(yakalanan instanceof ApiHatasi ? yakalanan.message : t("genel.hata.istek"));
    } finally {
      setGorselYukleniyor(false);
    }
  }

  async function sesUretTikla() {
    if (sesBdm === null || metin.trim().length === 0) return;
    setSesYukleniyor(true);
    setSesHata(null);
    try {
      const uretilen = await sesDosyasiUret({ bdm_id: sesBdm, metin: metin.trim(), ses, bicim });
      setSesler((onceki) => [uretilen, ...onceki]);
    } catch (yakalanan) {
      setSesHata(yakalanan instanceof ApiHatasi ? yakalanan.message : t("genel.hata.istek"));
    } finally {
      setSesYukleniyor(false);
    }
  }

  async function indir(dosya: UretilenDosya) {
    try {
      await uretilenDosyayiIndir(dosya);
      goster({ tur: "bilgi", mesaj: t("medya.indir.bildirim", { ad: dosya.ad }) });
    } catch (yakalanan) {
      goster({
        tur: "hata",
        mesaj: yakalanan instanceof ApiHatasi ? yakalanan.message : t("genel.hata.istek"),
      });
    }
  }

  if (modeller === null) {
    return <YukleniyorDurumu etiket={t("medya.model.yukleniyor")} />;
  }

  return (
    <div className="flex flex-col gap-6">
      {modelHatasi ? (
        <HataBandi mesaj={modelHatasi} onYenile={() => void modelleriYukle()} />
      ) : null}

      <Kart className="flex flex-col gap-4">
        <div>
          <h2 className="flex items-center gap-2 text-lg font-medium text-neutral-900">
            <ImageIcon aria-hidden className="size-4" />
            {t("medya.gorsel.baslik")}
          </h2>
          <p className="mt-1 text-sm text-neutral-500">{t("medya.gorsel.aciklama")}</p>
        </div>

        {gorselModeller.length === 0 ? (
          <p className="text-[13px] text-neutral-500">{t("medya.model.yok")}</p>
        ) : (
          <>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <Secim
                id="gorsel-model"
                etiket={t("medya.model.etiket")}
                deger={gorselBdm === null ? "" : String(gorselBdm)}
                yerTutucu={t("medya.model.secin")}
                secenekler={gorselModeller.map((model) => ({
                  deger: String(model.id),
                  etiket: model.gorunen_ad,
                }))}
                devreDisi={gorselDevreDisi}
                onSec={(deger) => setGorselBdm(Number(deger))}
              />
              <Secim
                id="gorsel-boyut"
                etiket={t("medya.gorsel.boyut")}
                deger={boyut}
                secenekler={GORSEL_BOYUTLARI.map((secenek) => ({
                  deger: secenek,
                  etiket: secenek,
                }))}
                devreDisi={gorselDevreDisi}
                onSec={setBoyut}
              />
            </div>
            <MetinAlani
              id="gorsel-istem"
              etiket={t("medya.gorsel.istem")}
              ipucu={t("medya.gorsel.istem.ipucu")}
              deger={istem}
              devreDisi={gorselDevreDisi}
              onDegistir={setIstem}
            />
            <div>
              <Buton
                yukleniyor={gorselYukleniyor}
                disabled={gorselBdm === null || istem.trim().length === 0}
                onClick={() => void gorselUretTikla()}
              >
                {gorselYukleniyor ? t("medya.gorsel.uretiyor") : t("medya.gorsel.uret")}
              </Buton>
            </div>
          </>
        )}

        {gorselHata ? (
          <HataBandi mesaj={gorselHata} onYenile={() => void gorselUretTikla()} />
        ) : null}

        <div className="border-t border-neutral-100 pt-4">
          <h3 className="text-sm font-medium text-neutral-900">{t("medya.gorsel.sonuc")}</h3>
          {gorseller.length === 0 ? (
            <p className="mt-2 text-[13px] text-neutral-500">{t("medya.gorsel.bos")}</p>
          ) : (
            <div className="mt-2">
              <SonucListesi
                dosyalar={gorseller}
                onIndir={(dosya) => void indir(dosya)}
                onizleme={(dosya) => <GorselOnizleme dosya={dosya} />}
              />
            </div>
          )}
        </div>
      </Kart>

      <Kart className="flex flex-col gap-4">
        <div>
          <h2 className="flex items-center gap-2 text-lg font-medium text-neutral-900">
            <Volume2 aria-hidden className="size-4" />
            {t("medya.ses.baslik")}
          </h2>
          <p className="mt-1 text-sm text-neutral-500">{t("medya.ses.aciklama")}</p>
        </div>

        {sesModeller.length === 0 ? (
          <p className="text-[13px] text-neutral-500">{t("medya.model.yok")}</p>
        ) : (
          <>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <Secim
                id="ses-model"
                etiket={t("medya.model.etiket")}
                deger={sesBdm === null ? "" : String(sesBdm)}
                yerTutucu={t("medya.model.secin")}
                secenekler={sesModeller.map((model) => ({
                  deger: String(model.id),
                  etiket: model.gorunen_ad,
                }))}
                devreDisi={sesDevreDisi}
                onSec={(deger) => setSesBdm(Number(deger))}
              />
              <Secim
                id="ses-ad"
                etiket={t("medya.ses.ad")}
                deger={ses}
                secenekler={SES_ADLARI.map((secenek) => ({ deger: secenek, etiket: secenek }))}
                devreDisi={sesDevreDisi}
                onSec={setSes}
              />
              <Secim
                id="ses-bicim"
                etiket={t("medya.ses.bicim")}
                deger={bicim}
                secenekler={SES_BICIMLERI.map((secenek) => ({
                  deger: secenek,
                  etiket: secenek,
                }))}
                devreDisi={sesDevreDisi}
                onSec={setBicim}
              />
            </div>
            <MetinAlani
              id="ses-metin"
              etiket={t("medya.ses.metin")}
              ipucu={t("medya.ses.metin.ipucu")}
              deger={metin}
              devreDisi={sesDevreDisi}
              onDegistir={setMetin}
            />
            <div>
              <Buton
                yukleniyor={sesYukleniyor}
                disabled={sesBdm === null || metin.trim().length === 0}
                onClick={() => void sesUretTikla()}
              >
                {sesYukleniyor ? t("medya.ses.uretiyor") : t("medya.ses.uret")}
              </Buton>
            </div>
          </>
        )}

        {sesHata ? <HataBandi mesaj={sesHata} onYenile={() => void sesUretTikla()} /> : null}

        <div className="border-t border-neutral-100 pt-4">
          <h3 className="text-sm font-medium text-neutral-900">{t("medya.ses.sonuc")}</h3>
          {sesler.length === 0 ? (
            <p className="mt-2 text-[13px] text-neutral-500">{t("medya.ses.bos")}</p>
          ) : (
            <div className="mt-2">
              <SonucListesi
                dosyalar={sesler}
                onIndir={(dosya) => void indir(dosya)}
                onizleme={(dosya) => <SesOynatici dosya={dosya} />}
              />
            </div>
          )}
        </div>
      </Kart>
    </div>
  );
}

function MedyaGovdesi() {
  const { t } = useDil();
  const kullanici = useKullanici();
  const uyelikRolu = useUyelikRolu();

  return (
    <div className="mx-auto w-full max-w-4xl p-4 md:p-8">
      <div className="mb-6">
        <h1 className="marka-serif text-2xl text-neutral-900">{t("medya.baslik")}</h1>
        <p className="mt-1 text-sm text-neutral-500">{t("medya.aciklama")}</p>
      </div>
      {medyaYetkiliMi(kullanici, uyelikRolu) ? (
        <MedyaIcerigi />
      ) : (
        <YetkiKarti baslik={t("medya.yetki.baslik")} metin={t("medya.yetki.metin")} />
      )}
    </div>
  );
}

export default function MedyaSayfasi() {
  return (
    <Korumali>
      <MedyaGovdesi />
    </Korumali>
  );
}
