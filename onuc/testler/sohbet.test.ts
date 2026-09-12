/**
 * SSE çerçeve çözümlemesinin regresyon testi (API.md §9).
 *
 * Akış `response.body.getReader()` ile parça parça geldiği için çerçeve sınırı
 * çözümleyicinin kontrolünde değildir: aynı gövde farklı parça bölünmeleriyle
 * beslendiğinde olaylar birebir aynı olmalıdır. Ayrıca `hata` olayının hata
 * zarfını çözmesi (kullanıcıya gösterilen mesaj) sınanır.
 */

import assert from "node:assert/strict";
import test from "node:test";

import { cerceveleriCoz } from "../lib/sohbet";

const AKIS = [
  'event: baslangic\ndata: {"konusma_id":3,"mesaj_id":9}\n\n',
  'event: parca\ndata: {"icerik":"Mer"}\n\n',
  'event: parca\ndata: {"icerik":"haba"}\n\n',
  'event: kullanim\ndata: {"token_girdi":12,"token_cikti":34,"gecikme_ms":812}\n\n',
  "event: bitti\ndata: {}\n\n",
].join("");

const BEKLENEN = [
  { tur: "baslangic", konusma_id: 3, mesaj_id: 9 },
  { tur: "parca", icerik: "Mer" },
  { tur: "parca", icerik: "haba" },
  { tur: "kullanim", token_girdi: 12, token_cikti: 34, gecikme_ms: 812 },
  { tur: "bitti" },
];

function parcalarlaBesle(parcalar: string[]) {
  const olaylar: unknown[] = [];
  let tampon = "";
  for (const parca of parcalar) {
    tampon += parca;
    const sonuc = cerceveleriCoz(tampon);
    tampon = sonuc.kalan;
    olaylar.push(...sonuc.olaylar);
  }
  return { olaylar, kalan: tampon };
}

test("parça sınırı çerçeveye denk gelmese de olaylar sırayla ve tek sefer çözülür", () => {
  for (let kesim = 1; kesim < AKIS.length; kesim += 1) {
    const { olaylar, kalan } = parcalarlaBesle([AKIS.slice(0, kesim), AKIS.slice(kesim)]);
    assert.deepEqual(olaylar, BEKLENEN, `kesim noktası ${kesim}`);
    assert.equal(kalan, "", `kesim noktası ${kesim} sonrası artık kalmamalı`);
  }

  const tekTek = parcalarlaBesle([...AKIS]);
  assert.deepEqual(tekTek.olaylar, BEKLENEN);
  assert.equal(tekTek.kalan, "");
});

test("tamamlanmamış çerçeve erken yayınlanmaz", () => {
  const { olaylar, kalan } = parcalarlaBesle(['event: parca\ndata: {"icerik":"ya']);
  assert.deepEqual(olaylar, []);
  assert.equal(kalan, 'event: parca\ndata: {"icerik":"ya');
});

test("hata olayı hata zarfını kullanıcıya gösterilecek alanlara çevirir", () => {
  const govde =
    'event: hata\ndata: {"hata":{"kod":"kota_asildi","mesaj":"Kotanız doldu.","ayrinti":{"sifirlanma":"2026-09-13T00:00:00Z"}}}\n\n' +
    "event: bitti\ndata: {}\n\n";
  const { olaylar } = parcalarlaBesle([govde]);
  assert.deepEqual(olaylar, [
    {
      tur: "hata",
      kod: "kota_asildi",
      mesaj: "Kotanız doldu.",
      ayrinti: { sifirlanma: "2026-09-13T00:00:00Z" },
    },
    { tur: "bitti" },
  ]);
});

test("CRLF çerçeveleri desteklenir, bozuk JSON geçersiz olarak işaretlenir", () => {
  const sonuc = cerceveleriCoz(
    'event: parca\r\ndata: {"icerik":"a"}\r\n\r\nevent: parca\r\ndata: {bozuk\r\n\r\n',
  );
  assert.deepEqual(sonuc.olaylar, [
    { tur: "parca", icerik: "a" },
    { tur: "gecersiz", ad: "parca", ham: "{bozuk" },
  ]);
  assert.equal(sonuc.kalan, "");
});
