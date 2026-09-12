"""Uçtan uca duman testi: kurulum -> kayıt -> sohbet -> log -> panel verisi.

Gerçek servislere karşı koşar (varsayılan adresler):
  arkauc      : http://localhost:8000/api/v1
  sahte üst   : http://127.0.0.1:8190/v1   (onuc/testler/betikler/sahte_ust_saglayici.py)

Kullanım:
  ./.venv/Scripts/python.exe kaynak/testler/betikler/e2e_duman.py
"""

from __future__ import annotations

import json
import sys

import httpx

API = "http://localhost:8000/api/v1"
SAHTE_UST = "http://127.0.0.1:8190/v1"
MODEL = "sahte-bdm-1"

gecti: list[str] = []
kaldi: list[str] = []


def kontrol(ad: str, kosul: bool, ayrinti: object = "") -> None:
    (gecti if kosul else kaldi).append(ad)
    imza = "GEÇTİ" if kosul else "KALDI"
    print(f"[{imza}] {ad}" + (f" — {ayrinti}" if ayrinti else ""))


def sse_ayristir(govde: str) -> list[tuple[str, object]]:
    olaylar: list[tuple[str, object]] = []
    ad, veri = None, None
    for satir in govde.splitlines():
        if satir.startswith("event: "):
            ad = satir[7:].strip()
        elif satir.startswith("data: "):
            ham = satir[6:].strip()
            veri = json.loads(ham) if ham else {}
        elif satir == "" and ad is not None:
            olaylar.append((ad, veri))
            ad, veri = None, None
    if ad is not None:
        olaylar.append((ad, veri))
    return olaylar


def main() -> int:
    with httpx.Client(timeout=60.0) as istemci:
        # 1) Kurulum sihirbazi
        kurulum = istemci.get(f"{API}/saglik/kurulum").json()
        kontrol("kurulum öncesi durum", kurulum["kurulum_tamam"] is False, kurulum)

        yanit = istemci.post(
            f"{API}/kurulum",
            json={
                "marka_adi": "E2E Anonim Şirketi",
                "yonetici": {
                    "eposta": "yonetici@e2e-test.com",
                    "ad_soyad": "E2E Yönetici",
                    "parola": "Parola123!",
                },
                "bdm": {
                    "gorunen_ad": "E2E Sahte Model",
                    "saglayici": "ozel",
                    "temel_url": SAHTE_UST,
                    "upstream_model": MODEL,
                    "yerel_mi": False,
                },
                "dogrula": True,
            },
        )
        kontrol("POST /kurulum", yanit.status_code == 201, yanit.status_code)
        kurulum_govde = yanit.json()
        bdm_id = kurulum_govde["bdm"]["id"]
        kontrol(
            "kurulum doğrulaması başarılı",
            bool((kurulum_govde.get("dogrulama") or {}).get("basarili")),
            kurulum_govde.get("dogrulama"),
        )
        kontrol("kurulum_tamam işaretlendi", kurulum_govde["kurulum_tamam"] is True)

        # 2) Son kullanici kaydi + dogrulama
        kayit = istemci.post(
            f"{API}/kimlik/kayit",
            json={
                "eposta": "son.kullanici@e2e-test.com",
                "ad_soyad": "Son Kullanıcı",
                "parola": "Parola123!",
            },
        )
        kontrol("POST /kimlik/kayit", kayit.status_code == 201, kayit.status_code)
        baglanti = kayit.json().get("gelistirme_baglantisi") or ""
        jeton = baglanti.split("jeton=")[-1] if "jeton=" in baglanti else ""
        kontrol("doğrulama bağlantısı döndü (geliştirme)", bool(jeton))

        dogrula = istemci.post(f"{API}/kimlik/dogrula", json={"jeton": jeton})
        kontrol("POST /kimlik/dogrula", dogrula.status_code == 200, dogrula.status_code)

        giris = istemci.post(
            f"{API}/kimlik/giris",
            json={"eposta": "son.kullanici@e2e-test.com", "parola": "Parola123!"},
        )
        kontrol("POST /kimlik/giris", giris.status_code == 200, giris.status_code)
        kullanici_jetonu = giris.json()["erisim_jetonu"]
        kullanici_baslik = {"Authorization": f"Bearer {kullanici_jetonu}"}

        # 3) Akisli sohbet (mesajda kisisel veri var -> logda maskelenmeli)
        mesaj = "Merhaba, beni ayse.yilmaz@acme.com adresinden veya 0532 123 45 67 numarasından arayın."
        with istemci.stream(
            "POST",
            f"{API}/sohbet/akis",
            json={"bdm_id": bdm_id, "mesaj": mesaj},
            headers=kullanici_baslik,
        ) as akis:
            kontrol("POST /sohbet/akis", akis.status_code == 200, akis.status_code)
            kontrol(
                "içerik tipi SSE",
                akis.headers.get("content-type", "").startswith("text/event-stream"),
                akis.headers.get("content-type"),
            )
            govde = "".join(akis.iter_text())

        olaylar = sse_ayristir(govde)
        adlar = [ad for ad, _ in olaylar]
        kontrol("akış olay sırası", adlar[:1] == ["baslangic"] and adlar[-1] == "bitti", adlar)
        kontrol("parça olayları aktı", adlar.count("parca") > 3, adlar.count("parca"))
        kontrol("kullanım olayı geldi", "kullanim" in adlar)
        birlesik = "".join(
            str(veri.get("icerik", "")) for ad, veri in olaylar if ad == "parca"
        )
        kontrol("yanıt metni oluştu", len(birlesik) > 50, len(birlesik))

        # 4) Konusma kaydi ve maskeleme
        konusmalar = istemci.get(f"{API}/sohbet/konusmalar", headers=kullanici_baslik)
        kontrol("GET /sohbet/konusmalar", konusmalar.status_code == 200)
        kayitlar = konusmalar.json()["kayitlar"]
        kontrol("konuşma kaydedildi", len(kayitlar) == 1, len(kayitlar))
        konusma_id = kayitlar[0]["id"]

        detay = istemci.get(f"{API}/sohbet/konusmalar/{konusma_id}", headers=kullanici_baslik)
        ham_detay = detay.text
        kontrol("konuşma detayı maskeli", "ayse.yilmaz@acme.com" not in ham_detay)
        kontrol("maskelenmiş iz var", "[MASKELENDI:eposta]" in ham_detay)

        # 5) Yonetim paneli verileri
        panel_giris = istemci.post(
            f"{API}/kimlik/panel-giris",
            json={"eposta": "yonetici@e2e-test.com", "parola": "Parola123!"},
        )
        kontrol("POST /kimlik/panel-giris", panel_giris.status_code == 200)
        panel_baslik = {"Authorization": f"Bearer {panel_giris.json()['erisim_jetonu']}"}

        loglar = istemci.get(f"{API}/loglar/konusmalar", headers=panel_baslik).json()
        kontrol("panel log listesi", loglar["toplam"] == 1, loglar["toplam"])
        kontrol("log satırında model adı", loglar["kayitlar"][0]["bdm_ad"] == "E2E Sahte Model")

        for bicim, ipucu in (("json", "{"), ("md", "# "), ("csv", "mesaj_id")):
            disa = istemci.get(
                f"{API}/loglar/konusmalar/{konusma_id}/disa-aktar",
                params={"bicim": bicim},
                headers=panel_baslik,
            )
            kontrol(
                f"dışa aktarım {bicim}",
                disa.status_code == 200 and ipucu in disa.text,
                disa.headers.get("content-disposition"),
            )

        ozet = istemci.get(f"{API}/kullanim/ozet", headers=panel_baslik).json()
        kontrol("kullanım özeti istek sayısı", ozet["toplam_istek"] == 1, ozet["toplam_istek"])
        kontrol("kullanım özeti token", ozet["toplam_token"] > 0, ozet["toplam_token"])

        kisisel = istemci.get(f"{API}/kullanim/benim", headers=kullanici_baslik)
        kontrol("GET /kullanim/benim", kisisel.status_code == 200, kisisel.status_code)
        kontrol("kişisel kullanım kaydı", kisisel.json()["toplam_istek"] == 1)

        denetim = istemci.get(f"{API}/islem-kayitlari", headers=panel_baslik).json()
        eylemler = {satir["eylem"] for satir in denetim["kayitlar"]}
        kontrol("denetim izi okunabilir", denetim["toplam"] > 0, denetim["toplam"])
        kontrol(
            "kurulum ve sohbet denetimde",
            "kurulum.tamamlandi" in eylemler and "kimlik.giris" in eylemler,
            sorted(eylemler),
        )

        # 6) Modeller listesi (son kullanıcı görebilmeli)
        modeller = istemci.get(f"{API}/modeller", headers=kullanici_baslik)
        kontrol("GET /modeller", modeller.status_code == 200, modeller.status_code)
        kontrol("model listede", len(modeller.json()) == 1, modeller.json())

    print()
    print(f"SONUÇ: {len(gecti)} geçti, {len(kaldi)} kaldı")
    for ad in kaldi:
        print(f"  KALAN: {ad}")
    return 1 if kaldi else 0


if __name__ == "__main__":
    sys.exit(main())
