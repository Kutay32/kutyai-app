/**
 * Dalga 2 onuc yeteneklerinin regresyon testi.
 *
 * Kapsam: yeni SSE olayları (`arac_cagrisi`/`arac_sonucu`), akış `bitti` olayının
 * `kaynaklar`/`arac_cagrilari` alanları (API.md §19–20), araç kartlarının canlı
 * olaylarla birleşmesi, dosya yüklemenin multipart gövdesi (§18), medya
 * uçlarının gövdesi (§21) ve personel/yetki kapısı.
 */

import assert from "node:assert/strict";
import test from "node:test";

process.env.NEXT_PUBLIC_API_URL = "http://localhost:8107/api/v1";

// Statik import olamaz: `lib/api.ts` taban adresi modül yüklenirken okur.
// Uzantısız yol `testler/ts-kanca.mjs` çözümleyicisiyle `.ts` dosyasına bağlanır.
const sohbetModulu = import("../lib/sohbet");
const dosyalarModulu = import("../lib/dosyalar");
const medyaModulu = import("../lib/medya");
const tiplerModulu = import("../lib/tipler");
const bicimModulu = import("../lib/bicim");
const apiModulu = import("../lib/api");
const organizasyonlarModulu = import("../lib/organizasyonlar");
const oturumModulu = import("../lib/oturum");

type Cagri = { yol: string; yontem: string; govde: unknown; basliklar: Headers };

/** `fetch` çağrılarını kaydeden taklit; her yanıt sırayla `yanitlar`tan alınır. */
function fetchTaklidi(yanitlar: { durum?: number; govde?: unknown }[]): Cagri[] {
  const cagrilar: Cagri[] = [];
  globalThis.fetch = (async (girdi: string | URL | Request, secenekler?: RequestInit) => {
    const basliklar = new Headers(secenekler?.headers);
    cagrilar.push({
      yol: String(girdi).replace("http://localhost:8107/api/v1", ""),
      yontem: secenekler?.method ?? "GET",
      govde: secenekler?.body,
      basliklar,
    });
    const siradaki = yanitlar[Math.min(cagrilar.length - 1, yanitlar.length - 1)];
    const durum = siradaki?.durum ?? 200;
    // 204 gövde taşıyamaz; taklit de gövdesiz yanıt döndürür.
    if (durum === 204) return new Response(null, { status: 204 });
    return new Response(JSON.stringify(siradaki?.govde ?? {}), {
      status: durum,
      headers: { "Content-Type": "application/json" },
    });
  }) as typeof fetch;
  return cagrilar;
}

function kullanici(rol: "yonetici" | "operator" | "izleyici" | "son_kullanici") {
  return {
    id: 1,
    eposta: "personel@sirket.com",
    ad_soyad: "Personel",
    rol,
    durum: "aktif" as const,
    eposta_dogrulandi: true,
    olusturulma: "2026-09-01T00:00:00Z",
    son_giris: null,
  };
}

/* ------------------------------------------------------- yeni SSE olayları */

test("araç olayları ad, durum, özet ve argümanlarla çözülür", async () => {
  const { cerceveleriCoz } = await sohbetModulu;
  const akis = [
    'event: arac_cagrisi\ndata: {"ad":"hesap_makinesi","argumanlar":{"ifade":"2+2"}}\n\n',
    'event: arac_sonucu\ndata: {"ad":"hesap_makinesi","durum":"basarili","ozet":"Sonuç: 4"}\n\n',
    'event: bitti\ndata: {"arac_cagrilari":[{"ad":"hesap_makinesi","durum":"basarili"}]}\n\n',
  ].join("");

  const { olaylar, kalan } = cerceveleriCoz(akis);

  assert.deepEqual(olaylar, [
    { tur: "arac_cagrisi", ad: "hesap_makinesi", argumanlar: { ifade: "2+2" } },
    { tur: "arac_sonucu", ad: "hesap_makinesi", durum: "basarili", ozet: "Sonuç: 4" },
    { tur: "bitti", arac_cagrilari: [{ ad: "hesap_makinesi", durum: "basarili" }] },
  ]);
  assert.equal(kalan, "");
});

test("parça sınırı araç olaylarını bölse de olaylar tek sefer çözülür", async () => {
  const { cerceveleriCoz } = await sohbetModulu;
  const akis =
    'event: arac_cagrisi\ndata: {"ad":"zaman","argumanlar":{}}\n\n' +
    'event: arac_sonucu\ndata: {"ad":"zaman","durum":"hata","ozet":"Zaman aşımı"}\n\n';

  for (let kesim = 1; kesim < akis.length; kesim += 1) {
    const ilk = cerceveleriCoz(akis.slice(0, kesim));
    const ikinci = cerceveleriCoz(ilk.kalan + akis.slice(kesim));
    assert.deepEqual(
      [...ilk.olaylar, ...ikinci.olaylar],
      [
        { tur: "arac_cagrisi", ad: "zaman", argumanlar: {} },
        { tur: "arac_sonucu", ad: "zaman", durum: "hata", ozet: "Zaman aşımı" },
      ],
      `kesim noktası ${kesim}`,
    );
  }
});

test("bitti olayı kaynakları taşır, ek alanlar boşken sade kalır", async () => {
  const { cerceveleriCoz } = await sohbetModulu;
  const kaynaklar = [{ belge_id: 7, belge_ad: "El Kitabı", sira: 2, skor: 0.8765 }];

  const dolu = cerceveleriCoz(
    `event: bitti\ndata: ${JSON.stringify({ kaynaklar })}\n\n`,
  );
  assert.deepEqual(dolu.olaylar, [{ tur: "bitti", kaynaklar }]);

  const sade = cerceveleriCoz("event: bitti\ndata: {}\n\n");
  assert.deepEqual(sade.olaylar, [{ tur: "bitti" }]);
});

test("bilinmeyen ve eksik alanlı olaylar gecersiz olarak işaretlenir", async () => {
  const { cerceveleriCoz } = await sohbetModulu;

  const bilinmeyen = cerceveleriCoz('event: yeni_olay\ndata: {"x":1}\n\n');
  assert.deepEqual(bilinmeyen.olaylar, [{ tur: "gecersiz", ad: "yeni_olay", ham: '{"x":1}' }]);

  const adsiz = cerceveleriCoz('event: arac_cagrisi\ndata: {"argumanlar":{}}\n\n');
  assert.deepEqual(adsiz.olaylar, [
    { tur: "gecersiz", ad: "arac_cagrisi", ham: '{"argumanlar":{}}' },
  ]);
});

/* --------------------------------------------- kaynak/araç dönüşümü */

test("kaynaklar dönüşümü eksik ve bozuk satırları atar, alanları sayıya çevirir", async () => {
  const { kaynaklariCoz, aracOzetleriniCoz } = await sohbetModulu;

  assert.deepEqual(
    kaynaklariCoz([
      { belge_id: "7", belge_ad: "El Kitabı", sira: "2", skor: "0.5" },
      { belge_ad: "Kimliksiz" },
      null,
      "metin",
    ]),
    [{ belge_id: 7, belge_ad: "El Kitabı", sira: 2, skor: 0.5 }],
  );
  assert.deepEqual(kaynaklariCoz(null), []);
  assert.deepEqual(kaynaklariCoz({ belge_id: 1 }), []);

  assert.deepEqual(
    aracOzetleriniCoz([
      { ad: "zaman", durum: "basarili" },
      { ad: "bozuk", durum: "bilinmeyen" },
      { durum: "basarili" },
    ]),
    [
      { ad: "zaman", durum: "basarili" },
      { ad: "bozuk", durum: "hata" },
    ],
  );
});

test("araç kartları canlı olaylarla kapanır, bitti özeti kartları çiftlemez", async () => {
  const { aracCagrisiEkle, aracKartlariniBirlestir } = await sohbetModulu;

  const cagrili = aracCagrisiEkle([], { ad: "hesap_makinesi", argumanlar: { ifade: "2+2" } });
  assert.deepEqual(cagrili, [
    { ad: "hesap_makinesi", durum: "calisiyor", argumanlar: { ifade: "2+2" }, ozet: null },
  ]);

  const sonuclu = aracKartlariniBirlestir(cagrili, [
    { ad: "hesap_makinesi", durum: "basarili", ozet: "Sonuç: 4" },
  ]);
  assert.deepEqual(sonuclu, [
    { ad: "hesap_makinesi", durum: "basarili", argumanlar: { ifade: "2+2" }, ozet: "Sonuç: 4" },
  ]);

  const ozetli = aracKartlariniBirlestir(sonuclu, [{ ad: "hesap_makinesi", durum: "basarili" }]);
  assert.deepEqual(ozetli, sonuclu, "bitti özeti aynı kartı günceller, kopyasını eklemez");
});

test("aynı aracın ardışık çağrıları sırayla eşleşir, olaysız sonuç kendi kartını açar", async () => {
  const { aracCagrisiEkle, aracKartlariniBirlestir } = await sohbetModulu;

  const ikiCagri = aracCagrisiEkle(
    aracCagrisiEkle([], { ad: "zaman", argumanlar: { sira: 1 } }),
    { ad: "zaman", argumanlar: { sira: 2 } },
  );
  const kapali = aracKartlariniBirlestir(ikiCagri, [
    { ad: "zaman", durum: "basarili", ozet: "ilk" },
    { ad: "zaman", durum: "hata", ozet: "ikinci" },
  ]);

  assert.deepEqual(
    kapali.map((kart) => [kart.durum, kart.ozet]),
    [
      ["basarili", "ilk"],
      ["hata", "ikinci"],
    ],
  );

  const eksik = aracKartlariniBirlestir([], [{ ad: "zaman", durum: "hata" }]);
  assert.deepEqual(eksik, [{ ad: "zaman", durum: "hata", argumanlar: null, ozet: null }]);
});

/* ------------------------------------------------- dosya yükleme (§18) */

test("dosya yükleme multipart gövdesi kurar ve /dosyalar ucuna gider", async () => {
  const { dosyaFormu, dosyaYukle } = await dosyalarModulu;
  const dosya = new File(["merhaba"], "not.txt", { type: "text/plain" });

  const elle = dosyaFormu(dosya, "Notlar");
  assert.equal(elle.get("dosya"), dosya);
  assert.equal(elle.get("ad"), "Notlar");
  assert.equal(dosyaFormu(dosya).get("ad"), null, "ad verilmezse alan gönderilmez");

  const cagrilar = fetchTaklidi([
    {
      durum: 201,
      govde: {
        id: 3,
        ad: "not.txt",
        mime: "text/plain",
        boyut: 7,
        sha256: "abc",
        metin_uzunluk: 7,
        olusturulma: "2026-09-17T10:00:00Z",
      },
    },
  ]);
  const yuklenen = await dosyaYukle(dosya);

  assert.equal(cagrilar.length, 1);
  assert.equal(cagrilar[0].yol, "/dosyalar");
  assert.equal(cagrilar[0].yontem, "POST");
  const govde = cagrilar[0].govde;
  assert.ok(govde instanceof FormData, "gövde FormData olmalı");
  assert.equal(govde.get("dosya"), dosya);
  assert.equal(
    cagrilar[0].basliklar.get("Content-Type"),
    null,
    "Content-Type verilmez; sınırı tarayıcı üretir",
  );
  assert.equal(yuklenen.id, 3);
  assert.equal(yuklenen.metin_uzunluk, 7);
});

test("dosya listesi arama ve sayfalama parametreleriyle istenir", async () => {
  const { dosyaSorgusu, dosyalariGetir, dosyaSil } = await dosyalarModulu;

  assert.equal(
    dosyaSorgusu({ arama: " rapor ", sayfa: 2, boyut: 50 }),
    "arama=rapor&sayfa=2&boyut=50",
  );
  assert.equal(dosyaSorgusu({ arama: "   ", sayfa: 1, boyut: 25 }), "sayfa=1&boyut=25");

  const cagrilar = fetchTaklidi([
    { govde: { toplam: 0, sayfa: 1, boyut: 25, kayitlar: [] } },
    { durum: 204 },
  ]);
  const sayfa = await dosyalariGetir({ arama: "rapor", sayfa: 3, boyut: 25 });
  await dosyaSil(9);

  assert.deepEqual(
    cagrilar.map((cagri) => [cagri.yontem, cagri.yol]),
    [
      ["GET", "/dosyalar?arama=rapor&sayfa=3&boyut=25"],
      ["DELETE", "/dosyalar/9"],
    ],
  );
  assert.equal(sayfa.toplam, 0);
});

test("dosya yükleme hatası sunucunun mesajını taşır", async () => {
  const { dosyaYukle } = await dosyalarModulu;
  const { ApiHatasi } = await apiModulu;
  fetchTaklidi([
    {
      durum: 413,
      govde: {
        hata: { kod: "dosya_cok_buyuk", mesaj: "Dosya boyutu sınırı aştı.", ayrinti: {} },
      },
    },
  ]);

  await assert.rejects(dosyaYukle(new File(["x"], "buyuk.bin")), (hata: unknown) => {
    assert.ok(hata instanceof ApiHatasi);
    assert.equal(hata.kod, "dosya_cok_buyuk");
    assert.equal(hata.message, "Dosya boyutu sınırı aştı.");
    return true;
  });
});

/* ----------------------------------------------------- medya uçları (§21) */

test("görsel üretimi gövdesi ve sonucu sözleşmeye uyar", async () => {
  const { gorselUret } = await medyaModulu;
  const cagrilar = fetchTaklidi([
    { govde: [{ dosya_id: 12, ad: "gorsel-x-1.png", mime: "image/png", boyut: 2048 }] },
  ]);

  const gorseller = await gorselUret({ bdm_id: 4, istem: "Bir sahil", boyut: "1024x1024" });

  assert.equal(cagrilar[0].yol, "/medya/gorsel");
  assert.equal(cagrilar[0].yontem, "POST");
  assert.deepEqual(JSON.parse(String(cagrilar[0].govde)), {
    bdm_id: 4,
    istem: "Bir sahil",
    boyut: "1024x1024",
  });
  assert.deepEqual(gorseller, [
    { dosya_id: 12, ad: "gorsel-x-1.png", mime: "image/png", boyut: 2048 },
  ]);
});

test("yetenek kapalıysa sunucunun gerekçesi istemci hatasına taşınır", async () => {
  const { gorselUret } = await medyaModulu;
  const { ApiHatasi } = await apiModulu;
  fetchTaklidi([
    {
      durum: 400,
      govde: {
        hata: {
          kod: "medya_desteklenmiyor",
          mesaj: "Seçilen model görsel veya ses üretimini desteklemiyor.",
          ayrinti: {},
        },
      },
    },
  ]);

  await assert.rejects(
    gorselUret({ bdm_id: 4, istem: "Bir sahil" }),
    (hata: unknown) => {
      assert.ok(hata instanceof ApiHatasi);
      assert.equal(hata.kod, "medya_desteklenmiyor");
      assert.equal(hata.message, "Seçilen model görsel veya ses üretimini desteklemiyor.");
      return true;
    },
  );
});

test("ses üretimi dosya metasıyla tamamlanır", async () => {
  const { sesDosyasiUret } = await medyaModulu;
  const cagrilar = fetchTaklidi([
    { govde: { dosya_id: 42 } },
    {
      govde: {
        id: 42,
        ad: "ses-x.mp3",
        mime: "audio/mpeg",
        boyut: 1024,
        sha256: "abc",
        metin_uzunluk: 0,
        olusturulma: "2026-09-17T10:00:00Z",
      },
    },
  ]);

  const uretilen = await sesDosyasiUret({ bdm_id: 4, metin: "Merhaba", ses: "alloy", bicim: "mp3" });

  assert.deepEqual(
    cagrilar.map((cagri) => [cagri.yontem, cagri.yol]),
    [
      ["POST", "/medya/ses"],
      ["GET", "/dosyalar/42"],
    ],
  );
  assert.deepEqual(JSON.parse(String(cagrilar[0].govde)), {
    bdm_id: 4,
    metin: "Merhaba",
    ses: "alloy",
    bicim: "mp3",
  });
  assert.deepEqual(uretilen, {
    dosya_id: 42,
    ad: "ses-x.mp3",
    mime: "audio/mpeg",
    boyut: 1024,
  });
});

/* ---------------------------------------------------- yetki kapısı */

test("personel kapısı üyelik rolüne bakar, hesap rolüne değil", async () => {
  const { personelMi } = await tiplerModulu;

  assert.ok(personelMi(kullanici("yonetici"), "sahip"));
  assert.ok(personelMi(kullanici("izleyici"), "izleyici"));
  assert.ok(personelMi(kullanici("operator"), "operator"));
  assert.equal(personelMi(kullanici("son_kullanici"), "son_kullanici"), false);

  // Hesap rolü personel ama aktif organizasyondaki üyelik `son_kullanici`: uçlar 403 verir.
  assert.equal(personelMi(kullanici("yonetici"), "son_kullanici"), false);
  // Tersi: hesap rolü son kullanıcı, üyelik operatör → yetenekler görünür.
  assert.ok(personelMi(kullanici("son_kullanici"), "operator"));
});

test("üyelik çözülemezse hesabın varsayılan rolüne düşülür", async () => {
  const { personelMi } = await tiplerModulu;

  assert.ok(personelMi(kullanici("operator"), null));
  assert.equal(personelMi(kullanici("son_kullanici"), null), false);
  assert.equal(personelMi(null, null), false, "rol çözülemezse yetenek gösterilmez");
  assert.equal(personelMi(null, "izleyici"), true, "üyelik varsa hesap kaydı gerekmez");
});

test("medya üretimi izleyiciye ve son kullanıcıya kapalıdır", async () => {
  const { medyaYetkiliMi } = await tiplerModulu;

  assert.ok(medyaYetkiliMi(kullanici("yonetici"), "yonetici"));
  assert.ok(medyaYetkiliMi(kullanici("operator"), "operator"));
  assert.ok(medyaYetkiliMi(kullanici("son_kullanici"), "sahip"), "sahip üyelik her zaman yetkili");
  assert.equal(medyaYetkiliMi(kullanici("izleyici"), "izleyici"), false);
  assert.equal(medyaYetkiliMi(kullanici("yonetici"), "son_kullanici"), false);
  assert.equal(medyaYetkiliMi(kullanici("izleyici"), null), false);
  assert.equal(medyaYetkiliMi(null, null), false);
});

/* ------------------------------------------------------- biçimleme */

test("boyut biçimleyici baytı okunur birime çevirir", async () => {
  const { boyutBicimle } = await bicimModulu;

  assert.equal(boyutBicimle(512, "tr"), "512 B");
  assert.equal(boyutBicimle(1536, "tr"), "1,5 KB");
  assert.equal(boyutBicimle(1536, "en"), "1.5 KB");
  assert.equal(boyutBicimle(2 * 1024 * 1024, "tr"), "2 MB");
  assert.equal(boyutBicimle(null), "—");
  assert.equal(boyutBicimle(Number.NaN), "—");
});

/* ------------------------------------- sohbet isteği yetenek alanları */

test("akış isteği ekleri, bilgi tabanını ve araçları taşır", async () => {
  const { sohbetAkisiniBaslat } = await sohbetModulu;
  const cagrilar = fetchTaklidi([{ govde: {} }]);

  await sohbetAkisiniBaslat(
    {
      bdm_id: 4,
      konusma_id: null,
      mesaj: "Özetle",
      dosya_idleri: [3, 5],
      rag: true,
      rag_belge_idleri: [7],
      arac_sluglari: ["hesap_makinesi"],
    },
    () => undefined,
  );

  assert.equal(cagrilar[0].yol, "/sohbet/akis");
  assert.deepEqual(JSON.parse(String(cagrilar[0].govde)), {
    bdm_id: 4,
    konusma_id: null,
    mesaj: "Özetle",
    dosya_idleri: [3, 5],
    rag: true,
    rag_belge_idleri: [7],
    arac_sluglari: ["hesap_makinesi"],
  });
});

test("akış isteği hata mesajları için dil başlığı gönderir", async () => {
  const { sohbetAkisiniBaslat } = await sohbetModulu;
  const cagrilar = fetchTaklidi([{ govde: {} }]);

  await sohbetAkisiniBaslat({ bdm_id: 4, konusma_id: null, mesaj: "Merhaba" }, () => undefined);

  // Test ortamında `document` yok; `tarayiciDili` varsayılan dile düşer (spec §10.1).
  assert.equal(cagrilar[0].basliklar.get("Accept-Language"), "tr");
  assert.equal(cagrilar[0].basliklar.get("Accept"), "text/event-stream");
});

/* --------------------------------------------- yetki kapısı (üyelik rolü) */

test("aktif organizasyonun üyelik rolü jeton claim'i ile çözülür", async () => {
  const { aktifUyelikRolu } = await organizasyonlarModulu;

  const uyelikler = [
    { id: 1, ad: "Varsayılan", slug: "varsayilan", durum: "aktif", rol: "izleyici", olusturulma: null },
    { id: 2, ad: "Acme", slug: "acme", durum: "aktif", rol: "son_kullanici", olusturulma: null },
  ] as const;

  assert.equal(aktifUyelikRolu([...uyelikler], 2), "son_kullanici", "jeton claim'i kazanır");
  assert.equal(aktifUyelikRolu([...uyelikler], 9), "izleyici", "claim eşleşmezse ilk aktif üyelik");
  assert.equal(aktifUyelikRolu([...uyelikler], null), "izleyici");
  assert.equal(
    aktifUyelikRolu(
      [
        { id: 3, ad: "Askıda", slug: "askida", durum: "askida", rol: "yonetici", olusturulma: null },
        { id: 4, ad: "Aktif", slug: "aktif", durum: "aktif", rol: "operator", olusturulma: null },
      ],
      null,
    ),
    "operator",
    "askıdaki organizasyon atlanır",
  );
  assert.equal(aktifUyelikRolu([], 1), null);
  assert.equal(aktifUyelikRolu([{ ...uyelikler[0], rol: null }], null), null);
});

test("jeton org claim'i erişim jetonundan okunur", async () => {
  const { jetonOrganizasyonId } = await oturumModulu;
  const govde = (kayit: object) => Buffer.from(JSON.stringify(kayit)).toString("base64url");
  const depo = new Map([
    ["kutyai.erisim_jetonu", `${govde({ alg: "HS256" })}.${govde({ sub: "1", org: 7 })}.imza`],
    ["kutyai.yenileme_jetonu", "yenileme"],
  ]);
  // Node test ortamında `window` yok; `oturumAl` tarayıcı deposunu okuduğu için
  // asgari bir taklit kurulur (taklit yalnız bu test boyunca yaşar).
  const globalPencere = globalThis as { window?: unknown };
  globalPencere.window = {
    localStorage: {
      getItem: (anahtar: string) => depo.get(anahtar) ?? null,
      setItem: (anahtar: string, deger: string) => void depo.set(anahtar, deger),
      removeItem: (anahtar: string) => void depo.delete(anahtar),
    },
  };
  try {
    assert.equal(jetonOrganizasyonId(), 7);

    depo.set("kutyai.erisim_jetonu", "gecersiz-jeton");
    assert.equal(jetonOrganizasyonId(), null, "çözülemeyen jeton null döner");

    depo.set("kutyai.erisim_jetonu", `${govde({ sub: "1" })}.${govde({ sub: "1" })}.imza`);
    assert.equal(jetonOrganizasyonId(), null, "org claim'i yoksa null döner");
  } finally {
    delete globalPencere.window;
  }
});
