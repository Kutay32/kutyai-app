"use client";

import { useState } from "react";

import { Trash2 } from "lucide-react";

import { hataMesaji } from "@/lib/api";
import { loglariTemizle } from "@/lib/loglar";
import { TEHLIKELI_GUN_SECENEKLERI } from "@/lib/ayarlar";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Select } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";

export type LogTemizlemeKartiProps = {
  /** Ayarlardaki saklama süresi; "varsayılan" seçeneğinde kullanılır. */
  saklamaGunu: number;
  onTemizlendi: () => void;
};

/** Saklama süresini aşan kayıtları silen tehlikeli işlem (yalnız yönetici). */
export function LogTemizlemeKarti({ saklamaGunu, onTemizlendi }: LogTemizlemeKartiProps) {
  const { showToast } = useToast();
  const [gun, setGun] = useState("");
  const [onayAcik, setOnayAcik] = useState(false);
  const [siliniyor, setSiliniyor] = useState(false);
  const [hata, setHata] = useState<string | null>(null);

  const temizle = async () => {
    setSiliniyor(true);
    setHata(null);
    try {
      const sonuc = await loglariTemizle(gun ? Number(gun) : null);
      showToast(`${sonuc.silinen} konuşma kaydı silindi.`, "success");
      setOnayAcik(false);
      onTemizlendi();
    } catch (sebep) {
      setHata(hataMesaji(sebep));
    } finally {
      setSiliniyor(false);
    }
  };

  const hedef =
    gun === ""
      ? `saklama süresini (${saklamaGunu} gün) aşan tüm kayıtlar`
      : `${gun} günden eski tüm kayıtlar`;

  return (
    <>
      <Card className="rounded-2xl border-rose-200">
        <CardHeader>
          <CardTitle className="text-rose-900">Tehlikeli bölge</CardTitle>
          <CardDescription>
            Saklama süresini aşan konuşma kayıtlarını kalıcı olarak siler. İşlem
            geri alınamaz ve yalnız yönetici tarafından yürütülebilir.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-4">
          <Field label="Silinecek kayıt yaşı" className="w-full md:w-64">
            {({ id, ...erisim }) => (
              <Select
                id={id}
                {...erisim}
                value={gun}
                onChange={(olay) => setGun(olay.target.value)}
              >
                <option value="">Saklama süresi ({saklamaGunu} gün)</option>
                {TEHLIKELI_GUN_SECENEKLERI.map((secenek) => (
                  <option key={secenek} value={secenek}>
                    {secenek} günden eski
                  </option>
                ))}
              </Select>
            )}
          </Field>

          <Button
            variant="danger"
            onClick={() => {
              setHata(null);
              setOnayAcik(true);
            }}
          >
            <Trash2 aria-hidden className="size-4" />
            Kayıtları temizle
          </Button>
        </CardContent>
      </Card>

      <Dialog
        open={onayAcik}
        onClose={() => {
          if (!siliniyor) setOnayAcik(false);
        }}
        title="Kayıtları temizle"
        description="Silinen kayıtlar geri getirilemez."
        footer={
          <>
            <Button variant="ghost" onClick={() => setOnayAcik(false)} disabled={siliniyor}>
              Vazgeç
            </Button>
            <Button variant="danger" loading={siliniyor} onClick={() => void temizle()}>
              Kalıcı olarak sil
            </Button>
          </>
        }
      >
        {hata ? (
          <Alert tone="danger" title="Temizlenemedi">
            {hata}
          </Alert>
        ) : (
          <p className="text-sm text-neutral-600">{hedef} silinecek.</p>
        )}
      </Dialog>
    </>
  );
}
