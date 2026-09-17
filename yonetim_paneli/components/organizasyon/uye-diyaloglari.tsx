"use client";

import { useState } from "react";

import { TriangleAlert } from "lucide-react";

import { useDil } from "@/lib/dil";
import { epostaHatasi } from "@/lib/dogrulama";
import { KULLANICI_DURUMU_ANAHTARI, UYELIK_ROL_ANAHTARI } from "@/lib/etiketler";
import {
  UYELIK_DURUMLARI,
  UYELIK_ROLLERI,
  organizasyonHatasi,
  sonSahipMi,
  uyeEkle,
  uyeGuncelle,
  uyeSil,
  type UyeGuncellemesi,
} from "@/lib/organizasyonlar";
import type { OrganizasyonUyesi, UyelikDurumu, UyelikRolu } from "@/lib/tipler";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";

function RolSecenegi({ rol }: { rol: UyelikRolu }) {
  const { t } = useDil();
  return <option value={rol}>{t(UYELIK_ROL_ANAHTARI[rol])}</option>;
}

/** `POST /organizasyonlar/{id}/uyeler` — e-posta ile üye ekleme. */
export function UyeEkleDiyalogu({
  organizasyonId,
  acik,
  onKapat,
  onEklendi,
}: {
  organizasyonId: number;
  acik: boolean;
  onKapat: () => void;
  onEklendi: () => void;
}) {
  const { t } = useDil();
  const { showToast } = useToast();
  const [eposta, setEposta] = useState("");
  const [rol, setRol] = useState<UyelikRolu>("son_kullanici");
  const [epostaHata, setEpostaHata] = useState<string | null>(null);
  const [gonderiliyor, setGonderiliyor] = useState(false);
  const [sunucuHatasi, setSunucuHatasi] = useState<string | null>(null);

  const kapat = () => {
    onKapat();
    setEposta("");
    setRol("son_kullanici");
    setEpostaHata(null);
    setSunucuHatasi(null);
  };

  const gonder = async (olay: React.FormEvent<HTMLFormElement>) => {
    olay.preventDefault();
    const dogrulama = epostaHatasi(eposta) ?? null;
    setEpostaHata(dogrulama);
    if (dogrulama) return;

    setGonderiliyor(true);
    setSunucuHatasi(null);
    try {
      await uyeEkle(organizasyonId, { eposta: eposta.trim(), rol });
      showToast(t("organizasyon.uye_ekle.basarili", { eposta: eposta.trim() }), "success");
      onEklendi();
      kapat();
    } catch (sebep) {
      setSunucuHatasi(organizasyonHatasi(sebep));
    } finally {
      setGonderiliyor(false);
    }
  };

  return (
    <Dialog
      open={acik}
      onClose={kapat}
      title={t("organizasyon.uye_ekle.baslik")}
      description={t("organizasyon.uye_ekle.aciklama")}
      footer={
        <>
          <Button variant="ghost" onClick={kapat} disabled={gonderiliyor}>
            {t("genel.vazgec")}
          </Button>
          <Button type="submit" form="uye-ekle-formu" loading={gonderiliyor}>
            {t("organizasyon.uye_ekle.gonder")}
          </Button>
        </>
      }
    >
      <form id="uye-ekle-formu" onSubmit={gonder} className="flex flex-col gap-4">
        {sunucuHatasi ? (
          <Alert tone="danger" title={t("organizasyon.uye_ekle.hata.baslik")}>
            {sunucuHatasi}
          </Alert>
        ) : null}

        <Field
          label={t("genel.eposta")}
          hint={t("organizasyon.uye_ekle.eposta.ipucu")}
          error={epostaHata}
          required
        >
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

        <Field label={t("organizasyon.uyeler.tablo.rol")}>
          {({ id, ...erisim }) => (
            <Select
              id={id}
              {...erisim}
              value={rol}
              onChange={(olay) => setRol(olay.target.value as UyelikRolu)}
            >
              {UYELIK_ROLLERI.map((secenek) => (
                <RolSecenegi key={secenek} rol={secenek} />
              ))}
            </Select>
          )}
        </Field>
      </form>
    </Dialog>
  );
}

/** `PATCH /organizasyonlar/{id}/uyeler/{kullaniciId}` — rol ve durum. */
export function UyeDuzenleDiyalogu({
  organizasyonId,
  uye,
  uyeler,
  kendimId,
  onKapat,
  onKaydedildi,
}: {
  organizasyonId: number;
  uye: OrganizasyonUyesi;
  uyeler: OrganizasyonUyesi[];
  kendimId: number | undefined;
  onKapat: () => void;
  onKaydedildi: () => void;
}) {
  const { t } = useDil();
  const { showToast } = useToast();
  const [rol, setRol] = useState<UyelikRolu>(uye.rol);
  const [durum, setDurum] = useState<UyelikDurumu>(uye.durum);
  const [kaydediliyor, setKaydediliyor] = useState(false);
  const [hata, setHata] = useState<string | null>(null);

  const sonSahip = sonSahipMi(uye, uyeler);
  const kendiSahipligi = uye.kullanici_id === kendimId && uye.rol === "sahip";
  // Son sahip ve kendi sahip rolü sunucuda korunur (409 gecersiz_gecis); arayüz aynı kuralı uygular.
  const rolKilitli = sonSahip || kendiSahipligi;
  const durumKilitli = sonSahip || kendiSahipligi;

  const kaydet = async () => {
    const degisiklikler: UyeGuncellemesi = {};
    if (!rolKilitli && rol !== uye.rol) degisiklikler.rol = rol;
    if (!durumKilitli && durum !== uye.durum) degisiklikler.durum = durum;

    if (Object.keys(degisiklikler).length === 0) {
      showToast(t("organizasyon.uye_duzenle.degisiklik_yok"), "info");
      onKapat();
      return;
    }

    setKaydediliyor(true);
    setHata(null);
    try {
      await uyeGuncelle(organizasyonId, uye.kullanici_id, degisiklikler);
      showToast(t("organizasyon.uye_duzenle.basarili"), "success");
      onKaydedildi();
      onKapat();
    } catch (sebep) {
      setHata(organizasyonHatasi(sebep));
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
      title={t("organizasyon.uye_duzenle.baslik")}
      description={uye.eposta}
      footer={
        <>
          <Button variant="ghost" onClick={onKapat} disabled={kaydediliyor}>
            {t("genel.vazgec")}
          </Button>
          <Button loading={kaydediliyor} onClick={() => void kaydet()}>
            {t("organizasyon.bilgi.kaydet")}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {hata ? (
          <Alert tone="danger" title={t("organizasyon.uye_duzenle.hata.baslik")}>
            {hata}
          </Alert>
        ) : null}

        {rolKilitli ? (
          <Alert tone="warning">
            {t(
              sonSahip
                ? "organizasyon.uye_duzenle.son_sahip.ipucu"
                : "organizasyon.uye_duzenle.kendini_dusurme.ipucu",
            )}
          </Alert>
        ) : null}

        <Field label={t("organizasyon.uyeler.tablo.rol")}>
          {({ id, ...erisim }) => (
            <Select
              id={id}
              {...erisim}
              value={rol}
              disabled={rolKilitli}
              onChange={(olay) => setRol(olay.target.value as UyelikRolu)}
            >
              {UYELIK_ROLLERI.map((secenek) => (
                <RolSecenegi key={secenek} rol={secenek} />
              ))}
            </Select>
          )}
        </Field>

        <Field label={t("organizasyon.uyeler.tablo.durum")}>
          {({ id, ...erisim }) => (
            <Select
              id={id}
              {...erisim}
              value={durum}
              disabled={durumKilitli}
              onChange={(olay) => setDurum(olay.target.value as UyelikDurumu)}
            >
              {UYELIK_DURUMLARI.map((secenek) => (
                <option key={secenek} value={secenek}>
                  {t(KULLANICI_DURUMU_ANAHTARI[secenek])}
                </option>
              ))}
            </Select>
          )}
        </Field>
      </div>
    </Dialog>
  );
}

/** `DELETE /organizasyonlar/{id}/uyeler/{kullaniciId}`. */
export function UyeSilDiyalogu({
  organizasyonId,
  uye,
  onKapat,
  onSilindi,
}: {
  organizasyonId: number;
  uye: OrganizasyonUyesi;
  onKapat: () => void;
  onSilindi: () => void;
}) {
  const { t } = useDil();
  const { showToast } = useToast();
  const [isleniyor, setIsleniyor] = useState(false);
  const [hata, setHata] = useState<string | null>(null);

  const sil = async () => {
    setIsleniyor(true);
    setHata(null);
    try {
      await uyeSil(organizasyonId, uye.kullanici_id);
      showToast(t("organizasyon.uye_sil.basarili", { eposta: uye.eposta }), "success");
      onSilindi();
      onKapat();
    } catch (sebep) {
      setHata(organizasyonHatasi(sebep));
    } finally {
      setIsleniyor(false);
    }
  };

  const [once, sonra] = t("organizasyon.uye_sil.metin").split("{baglanti}");

  return (
    <Dialog
      open
      onClose={() => {
        if (!isleniyor) onKapat();
      }}
      title={t("organizasyon.uye_sil.baslik")}
      description={t("organizasyon.uye_sil.aciklama")}
      footer={
        <>
          <Button variant="ghost" onClick={onKapat} disabled={isleniyor}>
            {t("genel.vazgec")}
          </Button>
          <Button variant="danger" loading={isleniyor} onClick={() => void sil()}>
            {t("organizasyon.uye_sil.onay")}
          </Button>
        </>
      }
    >
      {hata ? (
        <Alert tone="danger" title={t("organizasyon.uye_sil.hata.baslik")}>
          {hata}
        </Alert>
      ) : (
        <div className="flex items-start gap-2 text-sm text-neutral-600">
          <TriangleAlert aria-hidden className="mt-0.5 size-4 shrink-0 text-amber-600" />
          <p>
            {once}
            <span className="font-medium text-neutral-900">{uye.eposta}</span>
            {sonra}
          </p>
        </div>
      )}
    </Dialog>
  );
}
