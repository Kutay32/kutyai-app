"use client";

import { useState } from "react";

import { TriangleAlert } from "lucide-react";

import { hataMesaji } from "@/lib/api";
import { epostaHatasi, parolaHatasi, zorunluHatasi } from "@/lib/dogrulama";
import { KULLANICI_DURUMU_ETIKETI, ROL_ETIKETI } from "@/lib/etiketler";
import {
  KULLANICI_DURUMLARI,
  ROLLER,
  geciciParolaUret,
  kullaniciGuncelle,
  kullaniciOlustur,
  kullaniciPasiflestir,
  type KullaniciGuncellemesi,
} from "@/lib/kullanicilar";
import type { Kullanici, KullaniciDurumu, Rol } from "@/lib/tipler";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";

type EkleHatalari = { eposta?: string; ad_soyad?: string; parola?: string };

export function PersonelEkleDiyalogu({
  acik,
  onKapat,
  onEklendi,
}: {
  acik: boolean;
  onKapat: () => void;
  onEklendi: () => void;
}) {
  const { showToast } = useToast();
  const [eposta, setEposta] = useState("");
  const [adSoyad, setAdSoyad] = useState("");
  const [parola, setParola] = useState("");
  const [rol, setRol] = useState<Rol>("izleyici");
  const [hatalar, setHatalar] = useState<EkleHatalari>({});
  const [gonderiliyor, setGonderiliyor] = useState(false);
  const [sunucuHatasi, setSunucuHatasi] = useState<string | null>(null);
  /** Oluşturma başarılıysa form yerine geçici parolayı gösteren durum. */
  const [olusan, setOlusan] = useState<{ eposta: string; parola: string } | null>(null);

  const kapat = () => {
    onKapat();
    setEposta("");
    setAdSoyad("");
    setParola("");
    setRol("izleyici");
    setHatalar({});
    setSunucuHatasi(null);
    setOlusan(null);
  };

  const gonder = async (olay: React.FormEvent<HTMLFormElement>) => {
    olay.preventDefault();
    const yeni: EkleHatalari = {
      eposta: epostaHatasi(eposta) ?? undefined,
      ad_soyad: zorunluHatasi(adSoyad, "Ad soyad") ?? undefined,
      parola: parolaHatasi(parola) ?? undefined,
    };
    setHatalar(yeni);
    if (yeni.eposta || yeni.ad_soyad || yeni.parola) return;

    setGonderiliyor(true);
    setSunucuHatasi(null);
    try {
      await kullaniciOlustur({
        eposta: eposta.trim(),
        ad_soyad: adSoyad.trim(),
        parola,
        rol,
      });
      setOlusan({ eposta: eposta.trim(), parola });
      onEklendi();
    } catch (sebep) {
      setSunucuHatasi(hataMesaji(sebep));
    } finally {
      setGonderiliyor(false);
    }
  };

  return (
    <Dialog
      open={acik}
      onClose={kapat}
      title={olusan ? "Personel eklendi" : "Yeni personel"}
      description={
        olusan
          ? "Geçici parolayı kullanıcıya iletin."
          : "Kullanıcı hemen aktif ve e-posta doğrulanmış olarak açılır."
      }
      footer={
        olusan ? (
          <Button onClick={kapat}>Anladım, kapat</Button>
        ) : (
          <>
            <Button variant="ghost" onClick={kapat} disabled={gonderiliyor}>
              Vazgeç
            </Button>
            <Button type="submit" form="personel-ekle-formu" loading={gonderiliyor}>
              Personel ekle
            </Button>
          </>
        )
      }
    >
      {olusan ? (
        <div className="flex flex-col gap-4">
          <Alert tone="warning" title="Bu parola bir daha gösterilmez">
            Parolayı şimdi kopyalayıp kullanıcıya iletin; bu pencere kapandıktan
            sonra yeniden görüntülenemez.
          </Alert>
          <dl className="flex flex-col gap-3">
            <div className="flex flex-col gap-1">
              <dt className="text-xs tracking-wide text-neutral-500 uppercase">E-posta</dt>
              <dd className="text-sm text-neutral-900">{olusan.eposta}</dd>
            </div>
            <div className="flex flex-col gap-1">
              <dt className="text-xs tracking-wide text-neutral-500 uppercase">
                Geçici parola
              </dt>
              <dd className="rounded-lg border border-neutral-200 bg-neutral-50 p-3 font-mono text-sm break-all text-neutral-900 select-all">
                {olusan.parola}
              </dd>
            </div>
          </dl>
        </div>
      ) : (
        <form id="personel-ekle-formu" onSubmit={gonder} className="flex flex-col gap-4">
          {sunucuHatasi ? (
            <Alert tone="danger" title="Personel eklenemedi">
              {sunucuHatasi}
            </Alert>
          ) : null}

          <Field label="E-posta" error={hatalar.eposta} required>
            {({ id, invalid, ...erisim }) => (
              <Input
                id={id}
                {...erisim}
                invalid={invalid}
                type="email"
                autoComplete="off"
                value={eposta}
                onChange={(olay) => setEposta(olay.target.value)}
              />
            )}
          </Field>

          <Field label="Ad soyad" error={hatalar.ad_soyad} required>
            {({ id, invalid, ...erisim }) => (
              <Input
                id={id}
                {...erisim}
                invalid={invalid}
                value={adSoyad}
                onChange={(olay) => setAdSoyad(olay.target.value)}
              />
            )}
          </Field>

          <Field
            label="Geçici parola"
            error={hatalar.parola}
            hint="En az 8 karakter; kullanıcı ilk girişten sonra değiştirebilir."
            required
          >
            {({ id, invalid, ...erisim }) => (
              <div className="flex items-center gap-2">
                <Input
                  id={id}
                  {...erisim}
                  invalid={invalid}
                  value={parola}
                  onChange={(olay) => setParola(olay.target.value)}
                />
                <Button
                  variant="secondary"
                  onClick={() => setParola(geciciParolaUret())}
                  className="shrink-0"
                >
                  Üret
                </Button>
              </div>
            )}
          </Field>

          <Field label="Rol">
            {({ id, ...erisim }) => (
              <Select
                id={id}
                {...erisim}
                value={rol}
                onChange={(olay) => setRol(olay.target.value as Rol)}
              >
                {ROLLER.map((secenek) => (
                  <option key={secenek} value={secenek}>
                    {ROL_ETIKETI[secenek]}
                  </option>
                ))}
              </Select>
            )}
          </Field>
        </form>
      )}
    </Dialog>
  );
}

export function KullaniciDuzenleDiyalogu({
  kullanici,
  onKapat,
  onKaydedildi,
}: {
  kullanici: Kullanici;
  onKapat: () => void;
  onKaydedildi: () => void;
}) {
  const { showToast } = useToast();
  const [adSoyad, setAdSoyad] = useState(kullanici.ad_soyad);
  const [rol, setRol] = useState<Rol>(kullanici.rol);
  const [durum, setDurum] = useState<KullaniciDurumu>(kullanici.durum);
  const [kaydediliyor, setKaydediliyor] = useState(false);
  const [hata, setHata] = useState<string | null>(null);

  const kaydet = async () => {
    const degisiklikler: KullaniciGuncellemesi = {};
    if (adSoyad.trim() !== kullanici.ad_soyad) degisiklikler.ad_soyad = adSoyad.trim();
    if (rol !== kullanici.rol) degisiklikler.rol = rol;
    if (durum !== kullanici.durum) degisiklikler.durum = durum;

    if (Object.keys(degisiklikler).length === 0) {
      showToast("Değişiklik yok.", "info");
      onKapat();
      return;
    }

    setKaydediliyor(true);
    setHata(null);
    try {
      await kullaniciGuncelle(kullanici.id, degisiklikler);
      showToast("Kullanıcı güncellendi.", "success");
      onKaydedildi();
      onKapat();
    } catch (sebep) {
      setHata(hataMesaji(sebep));
    } finally {
      setKaydediliyor(false);
    }
  };

  return (
    <Dialog
      open
      onClose={() => {
        if (!kaydediliyor) onKapat();
      }}
      title="Kullanıcıyı düzenle"
      description={kullanici.eposta}
      footer={
        <>
          <Button variant="ghost" onClick={onKapat} disabled={kaydediliyor}>
            Vazgeç
          </Button>
          <Button loading={kaydediliyor} onClick={() => void kaydet()}>
            Kaydet
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {hata ? (
          <Alert tone="danger" title="Güncellenemedi">
            {hata}
          </Alert>
        ) : null}

        <Field label="Ad soyad">
          {({ id, ...erisim }) => (
            <Input
              id={id}
              {...erisim}
              value={adSoyad}
              onChange={(olay) => setAdSoyad(olay.target.value)}
            />
          )}
        </Field>

        <Field label="Rol">
          {({ id, ...erisim }) => (
            <Select
              id={id}
              {...erisim}
              value={rol}
              onChange={(olay) => setRol(olay.target.value as Rol)}
            >
              {ROLLER.map((secenek) => (
                <option key={secenek} value={secenek}>
                  {ROL_ETIKETI[secenek]}
                </option>
              ))}
            </Select>
          )}
        </Field>

        <Field label="Durum">
          {({ id, ...erisim }) => (
            <Select
              id={id}
              {...erisim}
              value={durum}
              onChange={(olay) => setDurum(olay.target.value as KullaniciDurumu)}
            >
              {KULLANICI_DURUMLARI.map((secenek) => (
                <option key={secenek} value={secenek}>
                  {KULLANICI_DURUMU_ETIKETI[secenek]}
                </option>
              ))}
            </Select>
          )}
        </Field>
      </div>
    </Dialog>
  );
}

export function PasiflestirDiyalogu({
  kullanici,
  onKapat,
  onPasiflestirildi,
}: {
  kullanici: Kullanici;
  onKapat: () => void;
  onPasiflestirildi: () => void;
}) {
  const { showToast } = useToast();
  const [isleniyor, setIsleniyor] = useState(false);
  const [hata, setHata] = useState<string | null>(null);

  const pasiflestir = async () => {
    setIsleniyor(true);
    setHata(null);
    try {
      await kullaniciPasiflestir(kullanici.id);
      showToast(`${kullanici.eposta} pasifleştirildi.`, "success");
      onPasiflestirildi();
      onKapat();
    } catch (sebep) {
      // Ör. kendi hesabını pasifleştirme denemesi → 409; sunucu mesajı gösterilir.
      setHata(hataMesaji(sebep));
    } finally {
      setIsleniyor(false);
    }
  };

  return (
    <Dialog
      open
      onClose={() => {
        if (!isleniyor) onKapat();
      }}
      title="Kullanıcıyı pasifleştir"
      description="Kayıt silinmez; açık oturumlar iptal edilir."
      footer={
        <>
          <Button variant="ghost" onClick={onKapat} disabled={isleniyor}>
            Vazgeç
          </Button>
          <Button variant="danger" loading={isleniyor} onClick={() => void pasiflestir()}>
            Pasifleştir
          </Button>
        </>
      }
    >
      {hata ? (
        <Alert tone="danger" title="Pasifleştirilemedi">
          {hata}
        </Alert>
      ) : (
        <div className="flex items-start gap-2 text-sm text-neutral-600">
          <TriangleAlert aria-hidden className="mt-0.5 size-4 shrink-0 text-amber-600" />
          <p>
            <span className="font-medium text-neutral-900">{kullanici.eposta}</span> hesabı
            pasifleştirilecek ve mevcut oturumları kapatılacak.
          </p>
        </div>
      )}
    </Dialog>
  );
}
