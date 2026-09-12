"use client";

import { useEffect, useState } from "react";

import { useRouter } from "next/navigation";

import { PanelShell } from "@/components/panel/shell";
import { Spinner } from "@/components/ui/spinner";
import { kullaniciOku, oturumDegisiminiDinle, oturumOku } from "@/lib/oturum";
import type { Kullanici } from "@/lib/tipler";

/** Panel oturum koruması: jeton yoksa `/giris`e yönlendirir. */
export default function PanelLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [kullanici, setKullanici] = useState<Kullanici | null>(null);

  useEffect(() => {
    const kontrol = () => {
      if (!oturumOku("erisim")) {
        setKullanici(null);
        router.replace("/giris");
        return;
      }
      setKullanici(kullaniciOku());
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
