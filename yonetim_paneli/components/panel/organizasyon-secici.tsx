"use client";

import { useEffect, useState } from "react";

import { ChevronDown, Building2 } from "lucide-react";

import { aktifOrganizasyonKaydet, aktifOrganizasyonOku } from "@/lib/aktif-organizasyon";
import { istek } from "@/lib/api";
import { cn } from "@/lib/cn";
import { useDil } from "@/lib/dil";
import { kullaniciOku, oturumKaydet, oturumOku } from "@/lib/oturum";
import type { Organizasyon, OrganizasyonSecimi } from "@/lib/tipler";

/**
 * Üst bardaki organizasyon değiştirici (spec §15, plan Dalga 2: "org değiştirici").
 *
 * Seçim iki yolla uygulanır: `/kimlik/organizasyon-sec` ile erişim jetonundaki
 * `org` claim'i tazelenir ve slug `lib/aktif-organizasyon.ts`'e yazılır (her
 * istek `X-Organizasyon` başlığını taşır). Ardından sayfa yenilenir ki tüm
 * veriler yeni organizasyon kapsamıyla gelsin.
 */
export function OrganizasyonSecici({ className }: { className?: string }) {
  const { t } = useDil();
  const [organizasyonlar, setOrganizasyonlar] = useState<Organizasyon[]>([]);
  const [slug, setSlug] = useState<string>("");
  const [degisiyor, setDegisiyor] = useState(false);

  useEffect(() => {
    let iptal = false;
    istek<Organizasyon[]>("/organizasyonlar")
      .then((liste) => {
        if (iptal) return;
        setOrganizasyonlar(liste);
        const kayitli = aktifOrganizasyonOku();
        const bulunan = liste.find((o) => o.slug === kayitli) ?? liste[0];
        setSlug(bulunan?.slug ?? "");
        if (bulunan && bulunan.slug !== kayitli) aktifOrganizasyonKaydet(bulunan.slug);
      })
      .catch(() => {
        // Organizasyon listesi alınamazsa değiştirici gizli kalır.
      });
    return () => {
      iptal = true;
    };
  }, []);

  async function sec(yeniSlug: string) {
    const hedef = organizasyonlar.find((o) => o.slug === yeniSlug);
    if (!hedef || hedef.slug === slug) return;
    setDegisiyor(true);
    try {
      const yanit = await istek<OrganizasyonSecimi>("/kimlik/organizasyon-sec", {
        yontem: "POST",
        govde: { organizasyon_id: hedef.id },
      });
      const kullanici = kullaniciOku();
      const yenileme = oturumOku("yenileme");
      if (kullanici && yenileme) {
        oturumKaydet({
          erisim_jetonu: yanit.erisim_jetonu,
          yenileme_jetonu: yenileme,
          kullanici,
        });
      }
      aktifOrganizasyonKaydet(hedef.slug);
      setSlug(hedef.slug);
      // Tüm veriler yeni kapsamla gelsin diye tam yenileme.
      window.location.reload();
    } catch {
      setDegisiyor(false);
    }
  }

  if (organizasyonlar.length <= 1) return null;

  return (
    <div className={cn("flex items-center gap-1.5", className)}>
      <Building2 aria-hidden className="size-4 shrink-0 text-neutral-500" />
      <label htmlFor="organizasyon-secici" className="sr-only">
        {t("organizasyon.aktif")}
      </label>
      <div className="relative">
        <select
          id="organizasyon-secici"
          value={slug}
          disabled={degisiyor}
          onChange={(olay) => void sec(olay.target.value)}
          className={cn(
            "h-8 max-w-[12rem] appearance-none rounded-md border border-neutral-300 bg-white pr-7 pl-2 text-sm text-neutral-800 transition-colors",
            "focus:border-neutral-900 focus:ring-0 focus:outline-none disabled:opacity-50",
          )}
        >
          {organizasyonlar.map((organizasyon) => (
            <option key={organizasyon.id} value={organizasyon.slug}>
              {organizasyon.ad}
            </option>
          ))}
        </select>
        <ChevronDown
          aria-hidden
          className="pointer-events-none absolute top-1/2 right-1.5 size-3.5 -translate-y-1/2 text-neutral-500"
        />
      </div>
    </div>
  );
}
