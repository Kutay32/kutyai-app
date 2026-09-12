"use client";

import Link from "next/link";
import { MessageSquare } from "lucide-react";

import { Korumali } from "@/components/korumali";
import { BuyukKart } from "@/components/ui/kart";

export default function SohbetSayfasi() {
  return (
    <Korumali>
      <div className="mx-auto w-full max-w-3xl p-4 md:p-8">
        <BuyukKart className="flex flex-col items-center gap-3 p-8 text-center">
          <MessageSquare aria-hidden className="size-6 text-neutral-400" />
          <h1 className="marka-serif text-2xl text-neutral-900">Sohbet yakında</h1>
          <p className="max-w-md text-sm text-neutral-500">
            Model seçimi, akışlı yanıtlar ve konuşma geçmişi sonraki sürümde bu ekranda
            açılacak. Bu sırada hesabınızı ve kullanım özetinizi inceleyebilirsiniz.
          </p>
          <div className="mt-2 flex flex-col gap-2 md:flex-row">
            <Link
              href="/kullanim"
              className="rounded-md border border-neutral-900 bg-neutral-900 px-4 py-2 text-sm text-white transition-colors hover:bg-neutral-800 focus:border-neutral-900 focus:ring-0"
            >
              Kullanımı görüntüle
            </Link>
            <Link
              href="/hesap"
              className="rounded-md border border-neutral-200 px-4 py-2 text-sm text-neutral-900 transition-colors hover:border-neutral-900 focus:border-neutral-900 focus:ring-0"
            >
              Hesabım
            </Link>
          </div>
        </BuyukKart>
      </div>
    </Korumali>
  );
}
