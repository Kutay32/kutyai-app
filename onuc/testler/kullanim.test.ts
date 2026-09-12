/**
 * `/kullanim` sayfasının veri yolunun regresyon testi.
 *
 * Gözlem bulgusu 1 (BLOCKER): sayfa personel uçlarını (`/kullanim/ozet`,
 * `/kullanim/zaman-serisi`) çağırdığı için son kullanıcı her zaman `403 yetki_yok`
 * alıyor ve hiç veri gösteremiyordu. Düzeltmeden sonra sayfa yalnız
 * `GET /kullanim/benim?gun=` ucunu çağırır (API.md §13).
 */

import assert from "node:assert/strict";
import test from "node:test";

process.env.NEXT_PUBLIC_API_URL = "http://localhost:8107/api/v1";

// Statik import olamaz: `lib/api.ts` taban adresi modül yüklenirken okur, bu yüzden
// yukarıdaki NEXT_PUBLIC_API_URL atamasından sonra dinamik olarak yüklenir.
// Uzantısız yol, `testler/ts-kanca.mjs` çözümleyicisiyle `.ts` dosyasına bağlanır.
const kullanimModulu = import("../lib/kullanim");

const ORNEK_YANIT = {
  gun: 30,
  toplam_istek: 12,
  toplam_token: 3456,
  girdi_token: 2100,
  cikti_token: 1356,
  ortalama_gecikme_ms: 480,
  kota: {
    gunluk_istek: 50,
    kullanilan_gunluk: 60,
    aylik_token: null,
    kullanilan_aylik: 3456,
    gun_sifirlanma: "2026-09-13T00:00:00Z",
    ay_sifirlanma: "2026-10-01T00:00:00Z",
  },
  seri: [
    { tarih: "2026-09-11", token: 1200 },
    { tarih: "2026-09-12", token: 2256 },
  ],
};

type Cagri = { url: string; yetki: string | null };

function fetchTaklidi(cagrilar: Cagri[], durum = 200, govde: unknown = ORNEK_YANIT) {
  globalThis.fetch = (async (girdi: string | URL | Request, secenekler?: RequestInit) => {
    const basliklar = new Headers(secenekler?.headers);
    cagrilar.push({ url: String(girdi), yetki: basliklar.get("Authorization") });
    return new Response(JSON.stringify(govde), {
      status: durum,
      headers: { "Content-Type": "application/json" },
    });
  }) as typeof fetch;
}

test("kişisel kullanım isteği /kullanim/benim ucuna gider, personel uçlarına değil", async () => {
  const cagrilar: Cagri[] = [];
  fetchTaklidi(cagrilar);
  const { kisiselKullanimGetir } = await kullanimModulu;

  const sonuc = await kisiselKullanimGetir(30);

  assert.deepEqual(
    cagrilar.map((cagri) => cagri.url),
    ["http://localhost:8107/api/v1/kullanim/benim?gun=30"],
  );
  assert.ok(
    !cagrilar.some(
      (cagri) => cagri.url.includes("/kullanim/ozet") || cagri.url.includes("/zaman-serisi"),
    ),
    "personel ucu çağrılmamalı",
  );
  assert.equal(sonuc.toplam_istek, 12);
  assert.equal(sonuc.toplam_token, 3456);
  assert.equal(sonuc.girdi_token, 2100);
  assert.equal(sonuc.cikti_token, 1356);
  assert.equal(sonuc.ortalama_gecikme_ms, 480);
  assert.equal(sonuc.kota?.gunluk_istek, 50);
  assert.deepEqual(sonuc.seri, ORNEK_YANIT.seri);
});

test("seçilen gün aralığı isteğe yansır", async () => {
  const cagrilar: Cagri[] = [];
  fetchTaklidi(cagrilar);
  const { kisiselKullanimGetir } = await kullanimModulu;

  await kisiselKullanimGetir(7);
  await kisiselKullanimGetir(90);

  assert.deepEqual(
    cagrilar.map((cagri) => cagri.url),
    [
      "http://localhost:8107/api/v1/kullanim/benim?gun=7",
      "http://localhost:8107/api/v1/kullanim/benim?gun=90",
    ],
  );
});

test("yetki hatası (403) kullanıcıya Türkçe mesajla döner", async () => {
  const cagrilar: Cagri[] = [];
  fetchTaklidi(cagrilar, 403, {
    hata: { kod: "yetki_yok", mesaj: "Bu işlem için yetkiniz yok.", ayrinti: {} },
  });
  const { kisiselKullanimGetir } = await kullanimModulu;

  await assert.rejects(kisiselKullanimGetir(30), (hata: unknown) => {
    assert.ok(hata instanceof Error);
    assert.equal(hata.message, "Bu işlem için yetkiniz yok.");
    return true;
  });
});

test("kota oranı sınırlıysa yüzde, sınırsızsa null döner", async () => {
  const { kotaYuzdesi } = await kullanimModulu;

  assert.equal(kotaYuzdesi(25, 50), 50);
  assert.equal(kotaYuzdesi(60, 50), 100, "sınır aşılırsa %100'de kırpılır");
  assert.equal(kotaYuzdesi(0, 50), 0);
  assert.equal(kotaYuzdesi(120, null), null);
  assert.equal(kotaYuzdesi(120, 0), null);
});

test("seri çubuk yükseklikleri en yüksek güne göre ölçeklenir", async () => {
  const { seriYukseklikleri } = await kullanimModulu;

  assert.deepEqual(seriYukseklikleri([{ token: 0 }, { token: 50 }, { token: 100 }]), [0, 50, 100]);
  assert.deepEqual(seriYukseklikleri([]), []);
  assert.deepEqual(seriYukseklikleri([{ token: 0 }, { token: 0 }]), [0, 0]);
  const kucuk = seriYukseklikleri([{ token: 10000 }, { token: 5 }]);
  assert.equal(kucuk[1], 2, "sıfırdan büyük gün görünür kalır");
});
