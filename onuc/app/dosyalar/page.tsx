"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Download, FolderOpen, Trash2, Upload } from "lucide-react";

import { Korumali, useKullanici, useUyelikRolu } from "@/components/korumali";
import { Buton } from "@/components/ui/buton";
import { Alan } from "@/components/ui/alan";
import { Kart } from "@/components/ui/kart";
import { Yukleniyor, YukleniyorDurumu } from "@/components/ui/yukleniyor";
import { useBildirim } from "@/components/ui/bildirim";
import { YetkiKarti } from "@/components/yetki-karti";
import { ApiHatasi } from "@/lib/api";
import { boyutBicimle, tarihBicimle } from "@/lib/bicim";
import { useDil } from "@/lib/dil";
import {
  BASLANGIC_DOSYA_FILTRESI,
  DOSYA_SAYFA_BOYUTLARI,
  dosyaIcerikIndir,
  dosyaSil,
  dosyalariGetir,
  dosyaYukle,
  type DosyaFiltresi,
  type DosyaOzeti,
} from "@/lib/dosyalar";
import { personelMi, type Sayfa } from "@/lib/tipler";

/** Dosya listesi: arama, yükleme, indirme, silme ve sayfalama. */
function DosyaListesi() {
  const { dil, t } = useDil();
  const { goster } = useBildirim();
  const [filtre, setFiltre] = useState<DosyaFiltresi>(BASLANGIC_DOSYA_FILTRESI);
  const [arama, setArama] = useState("");
  const [veri, setVeri] = useState<Sayfa<DosyaOzeti> | null>(null);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [hata, setHata] = useState<string | null>(null);
  const [yuklenenAd, setYuklenenAd] = useState<string | null>(null);
  const [silinecek, setSilinecek] = useState<number | null>(null);
  const [siliniyor, setSiliniyor] = useState<number | null>(null);
  const [indirilen, setIndirilen] = useState<number | null>(null);
  const sonIstek = useRef(0);
  const girdiRef = useRef<HTMLInputElement>(null);

  // Her tuşta istek atmamak için arama 300 ms geciktirilir (panel deseni).
  useEffect(() => {
    const zamanlayici = window.setTimeout(() => {
      setFiltre((onceki) =>
        onceki.arama === arama ? onceki : { ...onceki, arama, sayfa: 1 },
      );
    }, 300);
    return () => window.clearTimeout(zamanlayici);
  }, [arama]);

  const yukle = useCallback(
    async (secili: DosyaFiltresi) => {
      const sira = ++sonIstek.current;
      setYukleniyor(true);
      setHata(null);
      try {
        const yanit = await dosyalariGetir(secili);
        if (sira !== sonIstek.current) return;
        setVeri(yanit);
      } catch (yakalanan) {
        if (sira !== sonIstek.current) return;
        setVeri(null);
        setHata(
          yakalanan instanceof ApiHatasi ? yakalanan.message : t("dosya.liste.alinamadi"),
        );
      } finally {
        if (sira === sonIstek.current) setYukleniyor(false);
      }
    },
    [t],
  );

  useEffect(() => {
    void yukle(filtre);
  }, [filtre, yukle]);

  async function yukleSecilen(dosya: File) {
    setYuklenenAd(dosya.name);
    try {
      const yuklenen = await dosyaYukle(dosya);
      goster({ tur: "basari", mesaj: t("dosya.yukle.bildirim", { ad: yuklenen.ad }) });
      await yukle(filtre);
    } catch (yakalanan) {
      goster({
        tur: "hata",
        mesaj: yakalanan instanceof ApiHatasi ? yakalanan.message : t("genel.hata.istek"),
      });
    } finally {
      setYuklenenAd(null);
      const girdi = girdiRef.current;
      if (girdi) girdi.value = "";
    }
  }

  async function indir(dosya: DosyaOzeti) {
    setIndirilen(dosya.id);
    try {
      await dosyaIcerikIndir(dosya);
    } catch (yakalanan) {
      goster({
        tur: "hata",
        mesaj: yakalanan instanceof ApiHatasi ? yakalanan.message : t("genel.hata.istek"),
      });
    } finally {
      setIndirilen(null);
    }
  }

  async function sil(dosya: DosyaOzeti) {
    setSiliniyor(dosya.id);
    try {
      await dosyaSil(dosya.id);
      goster({ tur: "basari", mesaj: t("dosya.sil.bildirim") });
      setSilinecek(null);
      // Son kayıt silindiyse boş sayfada kalınmasın.
      const sonSayfaMi = (veri?.kayitlar.length ?? 0) === 1 && filtre.sayfa > 1;
      if (sonSayfaMi) {
        setFiltre((onceki) => ({ ...onceki, sayfa: onceki.sayfa - 1 }));
      } else {
        await yukle(filtre);
      }
    } catch (yakalanan) {
      // Başka organizasyonun kaydı `404` döner: bilgi olarak gösterilir.
      if (yakalanan instanceof ApiHatasi && yakalanan.durum === 404) {
        goster({ tur: "bilgi", mesaj: t("dosya.sil.bulunamadi") });
        setSilinecek(null);
        await yukle(filtre);
      } else {
        goster({
          tur: "hata",
          mesaj: yakalanan instanceof ApiHatasi ? yakalanan.message : t("genel.hata.istek"),
        });
      }
    } finally {
      setSiliniyor(null);
    }
  }

  const kayitlar = veri?.kayitlar ?? [];
  const toplam = veri?.toplam ?? 0;
  const toplamSayfa = Math.max(1, Math.ceil(toplam / filtre.boyut));

  return (
    <div className="flex flex-col gap-4">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="marka-serif text-2xl text-neutral-900">{t("dosya.baslik")}</h1>
          <p className="mt-1 max-w-2xl text-sm text-neutral-500">{t("dosya.aciklama")}</p>
        </div>
        <div className="flex items-center gap-2">
          {yuklenenAd ? <Yukleniyor etiket={t("dosya.yukleniyor")} boyut="kucuk" /> : null}
          <input
            ref={girdiRef}
            id="dosya-yukleme"
            type="file"
            className="peer sr-only"
            disabled={yuklenenAd !== null}
            onChange={(olay) => {
              const dosya = olay.target.files?.[0];
              if (dosya) void yukleSecilen(dosya);
            }}
          />
          <label
            htmlFor="dosya-yukleme"
            className="inline-flex h-10 cursor-pointer items-center gap-2 rounded-md border border-neutral-900 bg-neutral-900 px-4 text-sm font-medium text-white transition-colors hover:bg-neutral-800 peer-focus-visible:border-neutral-900 peer-disabled:cursor-not-allowed peer-disabled:opacity-50"
          >
            <Upload aria-hidden className="size-4" />
            {t("dosya.yukle")}
          </label>
        </div>
      </header>

      <p className="text-[13px] text-neutral-500">{t("dosya.yukle.ipucu")}</p>

      <Alan
        etiket={t("dosya.ara.etiket")}
        type="search"
        placeholder={t("dosya.ara.ipucu")}
        value={arama}
        onChange={(olay) => setArama(olay.target.value)}
      />

      {hata ? (
        <Kart role="alert" className="flex flex-col items-start gap-3 border-rose-200">
          <p className="text-[13px] text-rose-600">{hata}</p>
          <Buton tur="ikincil" boyut="kucuk" onClick={() => void yukle(filtre)}>
            {t("dosya.yenile")}
          </Buton>
        </Kart>
      ) : yukleniyor && !veri ? (
        <Kart>
          <YukleniyorDurumu etiket={t("dosya.liste.yukleniyor")} />
        </Kart>
      ) : kayitlar.length === 0 ? (
        <Kart className="flex flex-col items-center gap-2 py-10 text-center">
          <FolderOpen aria-hidden className="size-6 text-neutral-400" />
          <p className="text-sm text-neutral-500">
            {filtre.arama.trim() ? t("dosya.liste.eslesme.yok") : t("dosya.liste.bos")}
          </p>
        </Kart>
      ) : (
        <Kart className="p-0">
          <h2 className="sr-only">{t("dosya.liste.baslik")}</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[13px]">
              <thead className="border-b border-neutral-100 text-neutral-500">
                <tr>
                  <th scope="col" className="px-4 py-2 font-medium">
                    {t("dosya.sutun.ad")}
                  </th>
                  <th scope="col" className="px-4 py-2 font-medium">
                    {t("dosya.sutun.tur")}
                  </th>
                  <th scope="col" className="px-4 py-2 font-medium">
                    {t("dosya.sutun.boyut")}
                  </th>
                  <th scope="col" className="px-4 py-2 font-medium">
                    {t("dosya.sutun.tarih")}
                  </th>
                  <th scope="col" className="px-4 py-2 text-right font-medium">
                    {t("dosya.sutun.islem")}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100">
                {kayitlar.map((dosya) => (
                  <tr key={dosya.id}>
                    <td className="max-w-[20rem] truncate px-4 py-2 text-neutral-900">
                      {dosya.ad}
                    </td>
                    <td className="px-4 py-2 font-mono text-[11px] text-neutral-500">
                      {dosya.mime}
                    </td>
                    <td className="px-4 py-2 text-neutral-600">
                      {boyutBicimle(dosya.boyut, dil)}
                    </td>
                    <td className="px-4 py-2 text-neutral-600">
                      {tarihBicimle(dosya.olusturulma, dil)}
                    </td>
                    <td className="px-4 py-2">
                      {silinecek === dosya.id ? (
                        <div className="flex flex-wrap items-center justify-end gap-2">
                          <p className="text-neutral-600">
                            {t("dosya.sil.soru", { ad: dosya.ad })}
                          </p>
                          <Buton
                            tur="tehlike"
                            boyut="kucuk"
                            yukleniyor={siliniyor === dosya.id}
                            onClick={() => void sil(dosya)}
                          >
                            {t("dosya.sil.onayla")}
                          </Buton>
                          <Buton tur="hayalet" boyut="kucuk" onClick={() => setSilinecek(null)}>
                            {t("dosya.sil.vazgec")}
                          </Buton>
                        </div>
                      ) : (
                        <div className="flex items-center justify-end gap-1">
                          <Buton
                            tur="ikincil"
                            boyut="kucuk"
                            yukleniyor={indirilen === dosya.id}
                            onClick={() => void indir(dosya)}
                            aria-label={t("dosya.indir.etiket", { ad: dosya.ad })}
                          >
                            <Download aria-hidden className="size-3.5" />
                            {t("dosya.indir")}
                          </Buton>
                          <Buton
                            tur="tehlike"
                            boyut="kucuk"
                            onClick={() => setSilinecek(dosya.id)}
                            aria-label={t("dosya.sil.etiket", { ad: dosya.ad })}
                          >
                            <Trash2 aria-hidden className="size-3.5" />
                            {t("dosya.sil")}
                          </Buton>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-neutral-100 px-4 py-3">
            <p className="text-[13px] text-neutral-500">
              {t("dosya.sayfa.bilgi", { sayfa: filtre.sayfa, toplam: toplamSayfa })}
            </p>
            <div className="flex items-center gap-2">
              <label htmlFor="dosya-sayfa-boyutu" className="text-[13px] text-neutral-500">
                {t("dosya.sayfa.boyut")}
              </label>
              <select
                id="dosya-sayfa-boyutu"
                value={filtre.boyut}
                onChange={(olay) =>
                  setFiltre((onceki) => ({ ...onceki, boyut: Number(olay.target.value), sayfa: 1 }))
                }
                className="h-8 rounded-lg border border-neutral-200 bg-white px-2 text-[13px] text-neutral-900 focus:border-neutral-900 focus:ring-0 focus:outline-none"
              >
                {DOSYA_SAYFA_BOYUTLARI.map((boyut) => (
                  <option key={boyut} value={boyut}>
                    {boyut}
                  </option>
                ))}
              </select>
              <Buton
                tur="ikincil"
                boyut="kucuk"
                disabled={filtre.sayfa <= 1}
                onClick={() => setFiltre((onceki) => ({ ...onceki, sayfa: onceki.sayfa - 1 }))}
              >
                {t("dosya.sayfa.onceki")}
              </Buton>
              <Buton
                tur="ikincil"
                boyut="kucuk"
                disabled={filtre.sayfa >= toplamSayfa}
                onClick={() => setFiltre((onceki) => ({ ...onceki, sayfa: onceki.sayfa + 1 }))}
              >
                {t("dosya.sayfa.sonraki")}
              </Buton>
            </div>
          </div>
        </Kart>
      )}
    </div>
  );
}

function DosyaIcerigi() {
  const { t } = useDil();
  const kullanici = useKullanici();
  const uyelikRolu = useUyelikRolu();

  return (
    <div className="mx-auto w-full max-w-5xl p-4 md:p-8">
      {personelMi(kullanici, uyelikRolu) ? (
        <DosyaListesi />
      ) : (
        <YetkiKarti baslik={t("dosya.yetki.baslik")} metin={t("dosya.yetki.metin")} />
      )}
    </div>
  );
}

export default function DosyalarSayfasi() {
  return (
    <Korumali>
      <DosyaIcerigi />
    </Korumali>
  );
}
