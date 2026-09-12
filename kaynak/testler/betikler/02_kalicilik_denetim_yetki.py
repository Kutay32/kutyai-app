"""02 — Kalıcılık, denetim izi, PATCH /yol ve yetki matrisi (canlı HTTP + SQLite).

Docker bilinçli olarak devre dışı bırakılmadı; `ollama` sağlayıcısı için
`yerel` sürücü kullanılır ve sahte Ollama (127.0.0.1:11435) ayaktadır.
"""

from __future__ import annotations

import json
import sys

sys.path.insert(0, __file__.rsplit("\\", 1)[0])
import ortak  # noqa: E402

JETON = ortak.jeton_al()
BASLIKLAR = ortak.basliklar(JETON)


def yeni_bdm(ad: str, durum: str = "hazir") -> int:
    kayit = ortak.bdm_olustur(ad, "ollama", temel_url="http://127.0.0.1:11435/v1", upstream_model="llama3", jeton=JETON)
    ortak.durum_yaz(int(kayit["id"]), durum)
    return int(kayit["id"])


def main() -> None:
    # ---------------------------------------------------------------- A) kalıcılık
    ortak.baslik("A) baslat başarısı: konteyner_id yanıtta + DB'de kalıcı mı?")
    b = yeni_bdm("Kalicilik")
    with ortak.istemci() as c:
        yanit = c.post(f"{ortak.UC}/{b}/baslat", headers=BASLIKLAR)
    ortak.goster("POST baslat", yanit)
    yanit_id = yanit.json().get("konteyner_id")
    db = ortak.bdm_satiri(b)
    print(f"  yanıttaki konteyner_id = {yanit_id!r}")
    print(f"  DB durum={db['durum']} konteyner={json.dumps(db['konteyner'], ensure_ascii=False)}")
    print(f"  KALICI Mİ? {db['konteyner'] is not None and db['konteyner'].get('konteyner_id') == yanit_id}")
    with ortak.istemci() as c:
        ortak.goster("GET durum", c.get(f"{ortak.UC}/{b}/durum", headers=BASLIKLAR))

    ortak.baslik("A2) durdur sonrası konteyner_id korunuyor mu?")
    with ortak.istemci() as c:
        ortak.goster("POST durdur", c.post(f"{ortak.UC}/{b}/durdur", headers=BASLIKLAR))
    db = ortak.bdm_satiri(b)
    print(f"  DB durum={db['durum']} konteyner={json.dumps(db['konteyner'], ensure_ascii=False)}")
    print(f"  KORUNDU MU? {bool(db['konteyner'] and db['konteyner'].get('konteyner_id'))}")

    # ---------------------------------------------------------------- B) denetim
    ortak.baslik("B) Denetim izi: islem_kaydi satırları (doğrudan SQLite)")
    satirlar = ortak.sql(
        "SELECT id, kullanici_id, eylem, hedef_tur, hedef_id, ayrinti, ip, olusturulma "
        "FROM islem_kaydi WHERE hedef_tur='bdm' AND hedef_id=? ORDER BY id",
        (str(b),),
    )
    for satir in satirlar:
        print(f"  {satir}")
    print(f"  satır sayısı = {len(satirlar)}")
    eylemler = [s[2] for s in satirlar]
    print(f"  eylemler = {eylemler}")

    # ---------------------------------------------------------------- C) yol
    ortak.baslik("C) PATCH /{id}/yol: nerede saklanıyor, baslat koruyor mu?")
    b2 = yeni_bdm("Yol Testi")
    with ortak.istemci() as c:
        yanit = c.post(f"{ortak.UC}/{b2}/baslat", headers=BASLIKLAR)
    ilk_id = yanit.json()["konteyner_id"]
    with ortak.istemci() as c:
        yanit = c.patch(f"{ortak.UC}/{b2}/yol", json={"takma_ad": "hizli-model", "oncelik": 5}, headers=BASLIKLAR)
    ortak.goster("PATCH yol (yanıt)", yanit)
    govde = yanit.json()
    print(f"  yanıt anahtarları = {sorted(govde)}")
    print(f"  yanıt konteyner = {json.dumps(govde.get('konteyner'), ensure_ascii=False)}")
    db = ortak.bdm_satiri(b2)
    print(f"  DB konteyner = {json.dumps(db['konteyner'], ensure_ascii=False)}")
    with ortak.istemci() as c:
        ortak.goster("GET /bdm (kayıt)", c.get(f"/bdm/{b2}", headers=BASLIKLAR))

    with ortak.istemci() as c:
        ortak.goster("PATCH yol (boş gövde)", c.patch(f"{ortak.UC}/{b2}/yol", json={}, headers=BASLIKLAR))
        ortak.goster("PATCH yol (oncelik=9999)", c.patch(f"{ortak.UC}/{b2}/yol", json={"oncelik": 9999}, headers=BASLIKLAR))
        ortak.goster("PATCH yol (takma_ad='')", c.patch(f"{ortak.UC}/{b2}/yol", json={"takma_ad": ""}, headers=BASLIKLAR))

    ortak.baslik("C2) yeniden baslat sonrası yol korunuyor mu?")
    with ortak.istemci() as c:
        ortak.goster("POST yeniden-baslat", c.post(f"{ortak.UC}/{b2}/yeniden-baslat", headers=BASLIKLAR))
    db = ortak.bdm_satiri(b2)
    print(f"  DB konteyner = {json.dumps(db['konteyner'], ensure_ascii=False)}")
    print(f"  yol korundu mu? {bool(db['konteyner'] and db['konteyner'].get('yol'))} (ilk konteyner_id={ilk_id})")

    # ---------------------------------------------------------------- D) yetki
    ortak.baslik("D) Yetki matrisi: anonim / son_kullanici")
    uclar = [
        ("POST", f"{ortak.UC}/{b}/baslat"),
        ("POST", f"{ortak.UC}/{b}/durdur"),
        ("POST", f"{ortak.UC}/{b}/yeniden-baslat"),
        ("GET", f"{ortak.UC}/{b}/durum"),
        ("GET", f"{ortak.UC}/{b}/saglik"),
        ("GET", f"{ortak.UC}/{b}/gunlukler"),
        ("PATCH", f"{ortak.UC}/{b}/yol"),
        ("GET", f"{ortak.UC}/surucu/durum"),
    ]
    with ortak.istemci() as c:
        for yontem, yol in uclar:
            yanit = c.request(yontem, yol)
            kod = yanit.json().get("hata", {}).get("kod")
            print(f"  ANONİM {yontem:<6} {yol.split('/yonetim')[1]:<22} → {yanit.status_code} {kod}")

    # son_kullanici kullanıcısı
    with ortak.istemci() as c:
        yanit = c.post(
            "/kullanicilar",
            json={"eposta": "gozson@kutyai.example.com", "ad_soyad": "Gözlem Son", "parola": "Parola123!", "rol": "son_kullanici"},
            headers=BASLIKLAR,
        )
    print(f"  kullanıcı oluşturma → {yanit.status_code} {yanit.text[:160]}")
    sk_jeton = None
    if yanit.status_code == 201:
        kullanici_id = yanit.json()["id"]
        with ortak.istemci() as c:
            giris = c.post("/kimlik/giris", json={"eposta": "gozson@kutyai.example.com", "parola": "Parola123!"})
        print(f"  /kimlik/giris → {giris.status_code} {giris.text[:160]}")
        if giris.status_code == 200:
            sk_jeton = giris.json()["erisim_jetonu"]
        else:
            import os

            os.environ["KUTYAI_GIZLI_ANAHTAR"] = "gozlem-gizli-anahtar"
            sys.path.insert(0, str(ortak.KOK))
            from arkauc.app.cekirdek import guvenlik  # noqa: PLC0415

            sk_jeton = guvenlik.erisim_jetonu_uret(kullanici_id, "son_kullanici")[0]
            print("  (jeton doğrudan üretildi: kullanıcı id ile)")
    if sk_jeton:
        baslik = {"Authorization": f"Bearer {sk_jeton}"}
        with ortak.istemci() as c:
            for yontem, yol in uclar:
                yanit = c.request(yontem, yol, headers=baslik)
                kod = yanit.json().get("hata", {}).get("kod")
                print(f"  SON_KULLANICI {yontem:<6} {yol.split('/yonetim')[1]:<22} → {yanit.status_code} {kod}")


if __name__ == "__main__":
    main()
