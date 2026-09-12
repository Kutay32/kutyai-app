"use client";

import { useEffect, useRef, useState } from "react";

import { Copy, Download, FileCode2, PlugZap, Server } from "lucide-react";

import {
  cekAkisi,
  hazirlamaDogrula,
  hazirlamaManifest,
  hazirlamaOnKontrol,
  type BdmKaydi,
  type DogrulamaSonucu,
  type Manifest,
  type OnKontrolSonucu,
} from "@/lib/bdm";
import { gecikmeBicimle, sayiBicimle } from "@/lib/bicim";
import { hataMesaji } from "@/lib/api";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { IlerlemeCubugu } from "@/components/bdm/ilerleme-cubugu";
import { StatCard } from "@/components/ui/stat-card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";

export type SekmeHazirlamaProps = { bdm: BdmKaydi };

/** Hazırlama sekmesi: doğrulama, ön kontrol, manifest ve model indirme (§10). */
export function SekmeHazirlama({ bdm }: SekmeHazirlamaProps) {
  const { showToast } = useToast();

  const [dogrulama, setDogrulama] = useState<DogrulamaSonucu | null>(null);
  const [dogrulamaHatasi, setDogrulamaHatasi] = useState<string | null>(null);
  const [dogrulaniyor, setDogrulaniyor] = useState(false);

  const [onKontrol, setOnKontrol] = useState<OnKontrolSonucu | null>(null);
  const [onKontrolHatasi, setOnKontrolHatasi] = useState<string | null>(null);
  const [onKontrolYukleniyor, setOnKontrolYukleniyor] = useState(false);

  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [manifestHatasi, setManifestHatasi] = useState<string | null>(null);
  const [manifestYukleniyor, setManifestYukleniyor] = useState(false);

  const [yuzde, setYuzde] = useState(0);
  const [cekMesaji, setCekMesaji] = useState("");
  const [cekHatasi, setCekHatasi] = useState<string | null>(null);
  const [cekiliyor, setCekiliyor] = useState(false);
  const cekIptal = useRef<AbortController | null>(null);

  // Sekmeden çıkılınca indirme akışı kapatılır.
  useEffect(() => () => cekIptal.current?.abort(), []);

  async function dogrula() {
    setDogrulaniyor(true);
    setDogrulamaHatasi(null);
    try {
      setDogrulama(await hazirlamaDogrula(bdm.id));
    } catch (hata) {
      setDogrulamaHatasi(hataMesaji(hata));
    } finally {
      setDogrulaniyor(false);
    }
  }

  async function onKontrolCalistir() {
    setOnKontrolYukleniyor(true);
    setOnKontrolHatasi(null);
    try {
      setOnKontrol(await hazirlamaOnKontrol(bdm.id));
    } catch (hata) {
      setOnKontrolHatasi(hataMesaji(hata));
    } finally {
      setOnKontrolYukleniyor(false);
    }
  }

  async function manifestCalistir() {
    setManifestYukleniyor(true);
    setManifestHatasi(null);
    try {
      setManifest(await hazirlamaManifest(bdm.id));
    } catch (hata) {
      setManifest(null);
      setManifestHatasi(hataMesaji(hata));
    } finally {
      setManifestYukleniyor(false);
    }
  }

  async function cekBaslat() {
    cekIptal.current?.abort();
    const denetleyici = new AbortController();
    cekIptal.current = denetleyici;
    setCekiliyor(true);
    setCekHatasi(null);
    setYuzde(0);
    setCekMesaji("Bağlantı kuruluyor…");
    try {
      for await (const olay of cekAkisi(bdm.id, denetleyici.signal)) {
        setYuzde(olay.yuzde);
        setCekMesaji(olay.mesaj);
      }
      showToast("Model indirme akışı tamamlandı.", "success");
    } catch (hata) {
      if (hata instanceof DOMException && hata.name === "AbortError") return;
      setCekHatasi(hataMesaji(hata));
    } finally {
      setCekiliyor(false);
      cekIptal.current = null;
    }
  }

  const cekEngeli =
    bdm.saglayici === "ollama"
      ? null
      : "Model indirme yalnızca Ollama sağlayıcısında desteklenir.";

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle>Bağlantı doğrulama</CardTitle>
          <CardDescription>
            Sağlayıcı adresine erişim ve model listesi sınanır; gecikme ölçülür.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div>
            <Button loading={dogrulaniyor} onClick={() => void dogrula()}>
              <PlugZap aria-hidden className="size-4" />
              Bağlantıyı doğrula
            </Button>
          </div>

          {dogrulamaHatasi ? <Alert tone="danger">{dogrulamaHatasi}</Alert> : null}

          {dogrulama ? (
            <Alert
              tone={dogrulama.basarili ? "success" : "danger"}
              title={dogrulama.basarili ? "Bağlantı başarılı" : "Bağlantı doğrulanamadı"}
            >
              <p>{dogrulama.mesaj}</p>
              <p className="text-xs">
                Gecikme: {gecikmeBicimle(dogrulama.gecikme_ms)} ·{" "}
                {sayiBicimle(dogrulama.modeller.length)} model
              </p>
              {dogrulama.modeller.length > 0 ? (
                <ul className="mt-2 flex max-h-32 flex-col gap-1 overflow-y-auto font-mono text-xs">
                  {dogrulama.modeller.map((model) => (
                    <li key={model}>{model}</li>
                  ))}
                </ul>
              ) : null}
            </Alert>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Ön kontrol</CardTitle>
          <CardDescription>
            Docker, GPU, boş disk alanı ve imaj önbelleği denetlenir.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div>
            <Button
              variant="secondary"
              loading={onKontrolYukleniyor}
              onClick={() => void onKontrolCalistir()}
            >
              <Server aria-hidden className="size-4" />
              Ön kontrolü çalıştır
            </Button>
          </div>

          {onKontrolHatasi ? <Alert tone="danger">{onKontrolHatasi}</Alert> : null}

          {onKontrol ? (
            <>
              <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
                <StatCard label="Docker" value={onKontrol.docker ? "Var" : "Yok"} />
                <StatCard label="GPU" value={onKontrol.gpu ? "Var" : "Yok"} />
                <StatCard label="Boş disk" value={`${sayiBicimle(onKontrol.disk_gb)} GB`} />
                <StatCard label="İmaj" value={onKontrol.image_var ? "Önbellekte" : "Yok"} />
              </div>

              <div className="flex items-center gap-2 text-sm text-neutral-700">
                <span>Uygunluk:</span>
                <Badge tone={onKontrol.uygun ? "success" : "warning"}>
                  {onKontrol.uygun ? "Hazırlamaya uygun" : "Uygun değil"}
                </Badge>
              </div>

              {onKontrol.uyarilar.length > 0 ? (
                <Alert tone="warning" title="Uyarılar">
                  <ul className="flex list-disc flex-col gap-1 pl-4">
                    {onKontrol.uyarilar.map((uyari) => (
                      <li key={uyari}>{uyari}</li>
                    ))}
                  </ul>
                </Alert>
              ) : (
                <Alert tone="success">Ön kontrol uyarısı yok.</Alert>
              )}
            </>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Konteyner manifesti</CardTitle>
          <CardDescription>
            Çalıştırma komutu, port, GPU bayrağı, bellek tahmini ve ortam değişkenleri.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div>
            <Button
              variant="secondary"
              loading={manifestYukleniyor}
              onClick={() => void manifestCalistir()}
            >
              <FileCode2 aria-hidden className="size-4" />
              Manifest üret
            </Button>
          </div>

          {manifestHatasi ? <Alert tone="danger">{manifestHatasi}</Alert> : null}

          {manifest ? (
            <div className="flex flex-col gap-3">
              <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
                <StatCard label="İmaj" value={manifest.image.split("/").pop() ?? manifest.image} />
                <StatCard label="Port" value={String(manifest.port)} />
                <StatCard label="GPU" value={manifest.gpu ? "Gerekli" : "Gerekmez"} />
                <StatCard label="Bellek" value={`${sayiBicimle(manifest.bellek_gb)} GB`} />
              </div>

              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium text-neutral-800">Komut</p>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      void navigator.clipboard
                        .writeText(manifest.komut.join(" "))
                        .then(() => showToast("Komut kopyalandı.", "success"))
                        .catch(() => showToast("Komut kopyalanamadı.", "danger"));
                    }}
                  >
                    <Copy aria-hidden className="size-4" />
                    Kopyala
                  </Button>
                </div>
                <pre className="overflow-x-auto rounded-lg border border-neutral-200 bg-neutral-50 p-4 font-mono text-xs text-neutral-800">
                  {manifest.komut.join(" ")}
                </pre>
                <p className="font-mono text-xs text-neutral-500">{manifest.image}</p>
              </div>

              <div className="flex flex-col gap-2">
                <p className="text-sm font-medium text-neutral-800">Ortam değişkenleri</p>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Ad</TableHead>
                      <TableHead>Değer</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {Object.entries(manifest.ortam).length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={2} className="text-neutral-500">
                          Ortam değişkeni yok.
                        </TableCell>
                      </TableRow>
                    ) : (
                      Object.entries(manifest.ortam).map(([ad, deger]) => (
                        <TableRow key={ad}>
                          <TableCell className="font-mono text-xs">{ad}</TableCell>
                          <TableCell className="font-mono text-xs">{deger}</TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
                <p className="text-xs text-neutral-500">
                  Gizli değerler maskelenmiş olarak gösterilir.
                </p>
              </div>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Modeli indir</CardTitle>
          <CardDescription>
            Ollama model indirmesi ilerleme akışı olarak izlenir (SSE).
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {cekEngeli ? (
            <Alert tone="info" title="Bu sağlayıcıda indirme yok">
              <p>{cekEngeli}</p>
            </Alert>
          ) : null}

          <div className="flex items-center gap-2">
            <Button
              loading={cekiliyor}
              disabled={cekEngeli !== null}
              title={cekEngeli ?? undefined}
              onClick={() => void cekBaslat()}
            >
              <Download aria-hidden className="size-4" />
              Modeli indir
            </Button>
            {cekiliyor ? (
              <Button
                variant="secondary"
                onClick={() => {
                  cekIptal.current?.abort();
                  setCekMesaji("İndirme durduruldu.");
                }}
              >
                Durdur
              </Button>
            ) : null}
          </div>

          {cekHatasi ? <Alert tone="danger">{cekHatasi}</Alert> : null}

          {cekiliyor || yuzde > 0 || cekMesaji ? (
            <IlerlemeCubugu yuzde={yuzde} mesaj={cekMesaji} />
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
