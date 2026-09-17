"use client";

import { useState } from "react";

import { Copy } from "lucide-react";

import { useDil } from "@/lib/dil";
import { SSO_TURU_ANAHTARI, girisAdresi, type SsoSaglayici } from "@/lib/sso";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";

/**
 * Sağlayıcının giriş adresi (`GET /sso/{org}/{saglayici}/baslat`).
 * Adres `giris_yolu` şablonundaki `{org}` yerine aktif organizasyon slug'ı yazılarak kurulur.
 */
export function GirisAdresiDiyalogu({
  saglayici,
  organizasyonSlug,
  onKapat,
}: {
  saglayici: SsoSaglayici;
  organizasyonSlug: string | null;
  onKapat: () => void;
}) {
  const { t } = useDil();
  const { showToast } = useToast();
  const [kopyalandi, setKopyalandi] = useState(false);

  const adres = organizasyonSlug ? girisAdresi(saglayici, organizasyonSlug) : "";

  const kopyala = async () => {
    if (!navigator.clipboard?.writeText) {
      showToast(t("sso.kopyalanamadi"), "danger");
      return;
    }
    try {
      await navigator.clipboard.writeText(adres);
      setKopyalandi(true);
      showToast(t("sso.kopyalandi"), "success");
    } catch {
      showToast(t("sso.kopyalanamadi"), "danger");
    }
  };

  return (
    <Dialog
      open
      onClose={onKapat}
      title={t("sso.giris_yolu")}
      description={`${saglayici.ad} · ${t(SSO_TURU_ANAHTARI[saglayici.tur])}`}
      footer={<Button onClick={onKapat}>{t("genel.kapat")}</Button>}
    >
      <div className="flex flex-col gap-4">
        {organizasyonSlug ? (
          <>
            <Field label={t("sso.giris_yolu")} hint={t("sso.giris_yolu.ipucu")}>
              {({ id }) => (
                <div className="flex items-center gap-2">
                  <Input id={id} readOnly value={adres} className="font-mono text-xs" />
                  <Button
                    variant="secondary"
                    className="shrink-0"
                    onClick={() => void kopyala()}
                  >
                    <Copy aria-hidden className="size-4" />
                    {t("sso.kopyala")}
                  </Button>
                </div>
              )}
            </Field>
            {kopyalandi ? <Alert tone="success">{t("sso.kopyalandi")}</Alert> : null}
          </>
        ) : (
          <Alert tone="warning">{t("sso.giris.organizasyon_yok")}</Alert>
        )}
      </div>
    </Dialog>
  );
}
