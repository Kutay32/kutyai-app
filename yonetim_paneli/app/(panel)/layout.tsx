"use client";

import { useEffect, useState } from "react";

import { useRouter } from "next/navigation";

import { PanelShell } from "@/components/panel/shell";
import { Spinner } from "@/components/ui/spinner";
import { kullaniciOku, oturumDegisiminiDinle, oturumOku, oturumTemizle } from "@/lib/oturum";
import type { Kullanici } from "@/lib/tipler";

/** Panel oturum koruması: jeton veya kullanıcı kaydı yoksa `/giris`e yönlendirir. */
export default function PanelLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [kullanici, setKullanici] = useState<Kullanici | null>(null);

  useEffect(() => {
    const kontrol = () => {
      const erisim = oturumOku("erisim");
      const kayitli = erisim ? kullaniciOku() : null;
      if (erisim && !kayitli) {
        // Jeton duruyor ama kullanıcı kaydı yok/bozuk: yarım oturumla panele girilmez.
        oturumTemizle();
      }
      if (!erisim || !kayitli) {
        setKullanici(null);
        router.replace("/giris");
        return;
      }
      setKullanici(kayitli);
    };

    kontrol();
    return oturumDegisiminiDinle(kontrol);
  }, [router]);

  if (!kullanici) {
    return (
      <div className="flex min-h-screen items-center justify-center gap-2 text-sm text-neutral-500">
        <Spinner />
        Oturum kontrol ediliyor…
      </div>
    );
  }

  return <PanelShell kullanici={kullanici}>{children}</PanelShell>;
}
