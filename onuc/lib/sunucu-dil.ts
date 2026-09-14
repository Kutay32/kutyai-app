import { cookies } from "next/headers";

import { dilGecerliMi, DIL_CEREZI, VARSAYILAN_DIL, type Dil } from "@/lib/sozluk";

/**
 * Sunucu bileşenleri için dil çözümü (spec §10.2): `kutyai.dil` çerezi okunur.
 * Çerez yoksa/geçersizse varsayılan dil döner.
 */
export async function dilOku(): Promise<Dil> {
  const cerez = await cookies();
  const deger = cerez.get(DIL_CEREZI)?.value;
  return dilGecerliMi(deger) ? deger : VARSAYILAN_DIL;
}
