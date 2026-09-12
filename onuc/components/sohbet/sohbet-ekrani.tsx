"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Menu, Plus } from "lucide-react";

import { Buton } from "@/components/ui/buton";
import { Yukleniyor } from "@/components/ui/yukleniyor";
import { ApiHatasi, apiFetch } from "@/lib/api";
import {
  seciliModeliAl,
  seciliModeliKaydet,
  sohbetAkisiniBaslat,
  type BdmOzet,
  type GorunumMesaji,
  type KonusmaDetayi,
  type KonusmaOzeti,
  type SohbetAkisiIstegi,
} from "@/lib/sohbet";

import { HataBandi, MesajIskeleti, SohbetBosDurumu } from "./durum-gorunumleri";
import { KonusmaListesi } from "./konusma-listesi";
import { MesajBaloncugu } from "./mesaj-baloncugu";
import { ModelSecici } from "./model-secici";
import { SohbetGirdisi } from "./sohbet-girdisi";

export type SohbetEkraniOzellikleri = {
  /** `/sohbet/[id]` rotasından gelen başlangıç konuşması. */
  baslangicKonusmaId?: number | null;
};

function hataMesaji(hata: unknown): string {
  if (hata instanceof ApiHatasi) return hata.message;
  return "Beklenmeyen bir hata oluştu. Lütfen tekrar deneyin.";
}

/** Yalnız `kullanici`/`asistan` rolleri gösterilir (API.md §9). */
function gorunumeCevir(detay: KonusmaDetayi): GorunumMesaji[] {
  const liste: GorunumMesaji[] = [];
  for (const mesaj of detay.mesajlar) {
    if (mesaj.rol !== "kullanici" && mesaj.rol !== "asistan") continue;
    liste.push({
      id: `kayit-${mesaj.id}`,
      rol: mesaj.rol,
      icerik: mesaj.icerik,
    });
  }
  return liste;
}

/** Yeniden üretmede kuyruktaki asistan mesajları atılır. */
function sonAsistaniKirp(liste: GorunumMesaji[]): GorunumMesaji[] {
  let son = liste.length;
  while (son > 0 && liste[son - 1].rol === "asistan") son -= 1;
  return son === liste.length ? liste : liste.slice(0, son);
}

function sonKullaniciMetni(liste: GorunumMesaji[]): string | null {
  for (let sira = liste.length - 1; sira >= 0; sira -= 1) {
    if (liste[sira].rol === "kullanici") return liste[sira].icerik;
  }
  return null;
}

/**
 * Sohbet ekranı: model seçimi, konuşma listesi, SSE akışı ve besteci.
 *
 * Ekran `/sohbet` ile `/sohbet/[id]` rotalarında aynı örneği kullanır; konuşma
 * değişiminde adres `history.replaceState` ile güncellenir, böylece akış
 * sırasında bileşen yeniden bağlanmaz.
 */
export function SohbetEkrani({ baslangicKonusmaId = null }: SohbetEkraniOzellikleri) {
  const [modeller, setModeller] = useState<BdmOzet[] | null>(null);
  const [seciliModelId, setSeciliModelId] = useState<number | null>(null);
  const [konusmalar, setKonusmalar] = useState<KonusmaOzeti[]>([]);
  const [konusmalarYukleniyor, setKonusmalarYukleniyor] = useState(true);
  const [konusmaId, setKonusmaId] = useState<number | null>(baslangicKonusmaId);
  const [mesajlar, setMesajlar] = useState<GorunumMesaji[]>([]);
  const [gecmisYukleniyor, setGecmisYukleniyor] = useState(false);
  const [gonderiliyor, setGonderiliyor] = useState(false);
  const [arama, setArama] = useState("");
  const [cekimAcik, setCekimAcik] = useState(false);
  const [hata, setHata] = useState<{ mesaj: string; yenidenDene: (() => void) | null } | null>(
    null,
  );

  const kaydirmaRef = useRef<HTMLDivElement>(null);
  const dibeYakinRef = useRef(true);
  const iptalRef = useRef<AbortController | null>(null);
  const sayacRef = useRef(0);

  /* ----------------------------------------------------------- veri yükleme */

  async function konusmalariTazele() {
    try {
      const liste = await apiFetch<{ kayitlar: KonusmaOzeti[] }>("/sohbet/konusmalar");
      setKonusmalar(liste.kayitlar ?? []);
    } catch {
      // Liste tazeleme hatası sohbeti kesmez; bir sonraki açılışta yeniden denenir.
    } finally {
      setKonusmalarYukleniyor(false);
    }
  }

  async function modelleriYukle() {
    try {
      const gelen = await apiFetch<BdmOzet[]>("/modeller");
      setModeller(gelen);
      const kayitli = seciliModeliAl();
      const secili = gelen.find((model) => model.id === kayitli) ?? gelen[0] ?? null;
      setSeciliModelId(secili?.id ?? null);
    } catch (yakalanan) {
      setModeller([]);
      setHata({
        mesaj: hataMesaji(yakalanan),
        yenidenDene: () => void modelleriYukle(),
      });
    }
  }

  useEffect(() => {
    void (async () => {
      await modelleriYukle();
      await konusmalariTazele();
    })();
    // Yalnız ilk bağlanışta çalışır; konuşma listesi akış sonunda ayrıca tazelenir.
  }, []);

  /* -------------------------------------------------------- konuşma yönetimi */

  async function konusmayiAc(id: number) {
    iptalRef.current?.abort();
    iptalRef.current = null;
    setGonderiliyor(false);
    setKonusmaId(id);
    setCekimAcik(false);
    setHata(null);
    setGecmisYukleniyor(true);
    dibeYakinRef.current = true;
    window.history.replaceState(null, "", `/sohbet/${id}`);
    try {
      const detay = await apiFetch<KonusmaDetayi>(`/sohbet/konusmalar/${id}`);
      setMesajlar(gorunumeCevir(detay));
      setSeciliModelId(detay.bdm_id);
      seciliModeliKaydet(detay.bdm_id);
    } catch (yakalanan) {
      setMesajlar([]);
      setHata({
        mesaj: hataMesaji(yakalanan),
        yenidenDene: () => void konusmayiAc(id),
      });
    } finally {
      setGecmisYukleniyor(false);
    }
  }

  useEffect(() => {
    if (baslangicKonusmaId === null) return;
    void konusmayiAc(baslangicKonusmaId);
  }, [baslangicKonusmaId]);

  function yeniSohbet() {
    iptalRef.current?.abort();
    iptalRef.current = null;
    setGonderiliyor(false);
    setKonusmaId(null);
    setMesajlar([]);
    setHata(null);
    setCekimAcik(false);
    setArama("");
    window.history.replaceState(null, "", "/sohbet");
  }

  function modelSec(bdmId: number) {
    setSeciliModelId(bdmId);
    seciliModeliKaydet(bdmId);
    // Sunucu konuşmayı tek bir modele bağlar: model değişince yeni konuşma açılır.
    if (konusmaId !== null) yeniSohbet();
  }

  /* ------------------------------------------------------------- akış */

  function asistaniGuncelle(id: string, yama: Partial<GorunumMesaji>) {
    setMesajlar((onceki) => {
      const sonraki: GorunumMesaji[] = [];
      for (const mesaj of onceki) {
        if (mesaj.id !== id) {
          sonraki.push(mesaj);
          continue;
        }
        const guncel = { ...mesaj, ...yama };
        // Boş kalan yer tutucu, hata/durdurma sonrası ekranda kalmaz.
        if (guncel.icerik.length === 0 && guncel.akisHalinde !== true) continue;
        sonraki.push(guncel);
      }
      return sonraki;
    });
  }

  async function gonder(metin: string, secenekler: { yenidenUret?: boolean } = {}) {
    const temiz = metin.trim();
    if (!temiz || iptalRef.current || seciliModelId === null) {
      if (seciliModelId === null) {
        setHata({ mesaj: "Sohbet için önce bir model seçin.", yenidenDene: null });
      }
      return;
    }

    const iptal = new AbortController();
    iptalRef.current = iptal;
    dibeYakinRef.current = true;
    setGonderiliyor(true);
    setHata(null);

    sayacRef.current += 1;
    const asistanId = `yerel-asistan-${sayacRef.current}`;
    const kullaniciId = `yerel-kullanici-${sayacRef.current}`;
    const istek: SohbetAkisiIstegi = {
      bdm_id: seciliModelId,
      konusma_id: konusmaId,
      mesaj: temiz,
    };

    setMesajlar((onceki) => {
      const temel = secenekler.yenidenUret ? sonAsistaniKirp(onceki) : onceki;
      const eklenecek: GorunumMesaji[] = secenekler.yenidenUret
        ? []
        : [{ id: kullaniciId, rol: "kullanici", icerik: temiz }];
      return [...temel, ...eklenecek, { id: asistanId, rol: "asistan", icerik: "", akisHalinde: true }];
    });

    try {
      await sohbetAkisiniBaslat(
        istek,
        (olay) => {
          if (olay.tur === "parca") {
            setMesajlar((onceki) =>
              onceki.map((mesaj) =>
                mesaj.id === asistanId ? { ...mesaj, icerik: mesaj.icerik + olay.icerik } : mesaj,
              ),
            );
            return;
          }
          if (olay.tur === "baslangic") {
            setKonusmaId(olay.konusma_id);
            window.history.replaceState(null, "", `/sohbet/${olay.konusma_id}`);
            return;
          }
          if (olay.tur === "hata") {
            setHata({
              mesaj: olay.mesaj,
              yenidenDene: () => void gonder(temiz, { yenidenUret: true }),
            });
            asistaniGuncelle(asistanId, { akisHalinde: false, hatali: true });
          }
        },
        iptal.signal,
      );
    } catch (yakalanan) {
      if (iptal.signal.aborted) {
        asistaniGuncelle(asistanId, { akisHalinde: false, durduruldu: true });
      } else {
        const mesaj = hataMesaji(yakalanan);
        setHata({ mesaj, yenidenDene: () => void gonder(temiz, { yenidenUret: true }) });
        asistaniGuncelle(asistanId, { akisHalinde: false, hatali: true });
      }
    } finally {
      iptalRef.current = null;
      setGonderiliyor(false);
      asistaniGuncelle(asistanId, { akisHalinde: false });
      void konusmalariTazele();
    }
  }

  function durdur() {
    iptalRef.current?.abort();
  }

  function yenidenUret() {
    const metin = sonKullaniciMetni(mesajlar);
    if (metin) void gonder(metin, { yenidenUret: true });
  }

  /* -------------------------------------------------------- kaydırma & klavye */

  function kaydirmaDinle() {
    const alan = kaydirmaRef.current;
    if (!alan) return;
    dibeYakinRef.current = alan.scrollHeight - alan.scrollTop - alan.clientHeight < 96;
  }

  useEffect(() => {
    if (!dibeYakinRef.current) return;
    const alan = kaydirmaRef.current;
    if (alan) alan.scrollTop = alan.scrollHeight;
  }, [mesajlar, gecmisYukleniyor]);

  useEffect(() => {
    function tusaBasildi(olay: KeyboardEvent) {
      if (olay.key !== "Escape") return;
      if (cekimAcik) {
        setCekimAcik(false);
        return;
      }
      if (gonderiliyor) durdur();
    }
    window.addEventListener("keydown", tusaBasildi);
    return () => window.removeEventListener("keydown", tusaBasildi);
  }, [cekimAcik, gonderiliyor]);

  /* ------------------------------------------------------------------ görünüm */

  const suzulmus = useMemo(() => {
    const terim = arama.trim().toLocaleLowerCase("tr");
    if (!terim) return konusmalar;
    return konusmalar.filter((konusma) =>
      `${konusma.baslik} ${konusma.bdm_ad}`.toLocaleLowerCase("tr").includes(terim),
    );
  }, [konusmalar, arama]);

  const modelVar = (modeller?.length ?? 0) > 0;
  const icerikIskeleti = modeller === null || gecmisYukleniyor;

  const liste = (
    <KonusmaListesi
      konusmalar={suzulmus}
      toplam={konusmalar.length}
      seciliId={konusmaId}
      arama={arama}
      yukleniyor={konusmalarYukleniyor}
      onArama={setArama}
      onSec={(id) => void konusmayiAc(id)}
      onYeni={yeniSohbet}
    />
  );

  return (
    <div className="flex h-full min-h-0">
      <aside className="hidden w-72 shrink-0 border-r border-neutral-100 md:flex md:flex-col">
        {liste}
      </aside>

      <section className="flex min-w-0 flex-1 flex-col">
        <header className="flex flex-wrap items-center justify-between gap-2 border-b border-neutral-100 p-3">
          <div className="flex min-w-0 items-center gap-2">
            <Buton
              tur="ikincil"
              boyut="kucuk"
              className="md:hidden"
              onClick={() => setCekimAcik(true)}
              aria-label="Konuşma listesini aç"
            >
              <Menu aria-hidden className="size-3.5" />
              Konuşmalar
            </Buton>
            <ModelSecici
              modeller={modeller ?? []}
              seciliId={seciliModelId}
              devreDisi={gonderiliyor || !modelVar}
              onSec={modelSec}
            />
          </div>
          <div className="flex items-center gap-2">
            {gonderiliyor ? <Yukleniyor etiket="Yanıt üretiliyor" boyut="kucuk" /> : null}
            <Buton tur="ikincil" boyut="kucuk" className="hidden md:inline-flex" onClick={yeniSohbet}>
              <Plus aria-hidden className="size-3.5" />
              Yeni sohbet
            </Buton>
          </div>
        </header>

        {hata ? (
          <div className="px-3 pt-3">
            <HataBandi mesaj={hata.mesaj} onYenidenDene={hata.yenidenDene} />
          </div>
        ) : null}

        <div
          ref={kaydirmaRef}
          onScroll={kaydirmaDinle}
          role="log"
          aria-busy={gonderiliyor || undefined}
          aria-label="Konuşma"
          className="min-h-0 flex-1 overflow-y-auto"
        >
          {icerikIskeleti ? (
            <div className="p-4">
              <MesajIskeleti />
            </div>
          ) : mesajlar.length === 0 ? (
            <div className="flex h-full items-center justify-center p-4">
              <SohbetBosDurumu modelVar={modelVar} onYenile={() => void modelleriYukle()} />
            </div>
          ) : (
            <div className="mx-auto flex w-full max-w-3xl flex-col gap-4 p-4">
              {mesajlar.map((mesaj, sira) => (
                <MesajBaloncugu
                  key={mesaj.id}
                  mesaj={mesaj}
                  sonMu={sira === mesajlar.length - 1}
                  gonderiliyor={gonderiliyor}
                  onYenidenUret={yenidenUret}
                />
              ))}
            </div>
          )}
        </div>

        <footer className="border-t border-neutral-100 p-3">
          <div className="mx-auto w-full max-w-3xl">
            <SohbetGirdisi
              gonderiliyor={gonderiliyor}
              gonderilebilir={seciliModelId !== null}
              onGonder={(metin) => void gonder(metin)}
              onDurdur={durdur}
            />
          </div>
        </footer>
      </section>

      {cekimAcik ? (
        <div className="fixed inset-0 z-50 flex md:hidden">
          <button
            type="button"
            aria-label="Konuşma listesini kapat"
            onClick={() => setCekimAcik(false)}
            className="absolute inset-0 cursor-default bg-neutral-900/40"
          />
          <aside
            role="dialog"
            aria-modal="true"
            aria-label="Konuşmalar"
            className="relative z-10 flex h-full w-80 max-w-[85%] flex-col border-r border-neutral-200 bg-white"
          >
            {liste}
          </aside>
        </div>
      ) : null}
    </div>
  );
}
