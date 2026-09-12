"""01 — Yaşam döngüsü durum makinesi: tüm geçişler canlı HTTP ile.

Her satır taze bir BDM kaydı kullanır; ön koşul durumu doğrudan veritabanına
yazılır (düzenleme), geçişin kendisi HTTP ile denenir.
"""

from __future__ import annotations

import json
import sys

sys.path.insert(0, __file__.rsplit("\\", 1)[0])
import ortak  # noqa: E402

JETON = ortak.jeton_al()
BASLIKLAR = ortak.basliklar(JETON)


def yeni_bdm(ad: str, saglayici: str = "ollama") -> int:
    kayit = ortak.bdm_olustur(
        ad,
        saglayici,
        temel_url="http://127.0.0.1:11435/v1",
        upstream_model="llama3",
        jeton=JETON,
    )
    return int(kayit["id"])


def dene(etiket: str, bdm_id: int, eylem: str, *, yol: str = "") -> tuple[int, str]:
    with ortak.istemci() as c:
        if yol:
            yanit = c.patch(f"{ortak.UC}/{bdm_id}/yol", json=json.loads(yol), headers=BASLIKLAR)
        else:
            yanit = c.post(f"{ortak.UC}/{bdm_id}/{eylem}", headers=BASLIKLAR)
    try:
        govde = yanit.json()
    except Exception:
        govde = {"ham": yanit.text[:200]}
    kod = govde.get("hata", {}).get("kod", "") if isinstance(govde, dict) else ""
    db = ortak.bdm_satiri(bdm_id)
    db_durum = db["durum"] if db else "kayıt yok"
    print(f"| {etiket:<28} | {yanit.status_code:<3} | {kod or '-':<18} | DB durum={db_durum:<11} | {str(govde)[:110]}")
    return yanit.status_code, kod


def main() -> None:
    ortak.baslik("Durum makinesi geçiş matrisi (canlı HTTP, port 8104)")
    print("| senaryo                     | kod | hata kodu          | sonuç                                   | yanıt özeti")
    print("|---|---|---|---|---|")

    # taslak
    b = yeni_bdm("Matris Taslak")
    dene("taslak→baslat", b, "baslat")
    dene("taslak→durdur", b, "durdur")
    dene("taslak→yeniden-baslat", b, "yeniden-baslat")

    # hazir → calisiyor
    b = yeni_bdm("Matris Hazir")
    ortak.durum_yaz(b, "hazir")
    dene("hazir→baslat", b, "baslat")
    dene("calisiyor→baslat", b, "baslat")
    dene("calisiyor→yeniden-baslat", b, "yeniden-baslat")
    dene("calisiyor→durdur", b, "durdur")
    dene("durdu→durdur", b, "durdur")
    dene("durdu→baslat", b, "baslat")

    # durdu → yeniden-baslat
    b = yeni_bdm("Matris Durdu")
    ortak.durum_yaz(b, "durdu")
    dene("durdu→yeniden-baslat", b, "yeniden-baslat")

    # hazir → yeniden-baslat
    b = yeni_bdm("Matris Hazir Yeniden")
    ortak.durum_yaz(b, "hazir")
    dene("hazir→yeniden-baslat", b, "yeniden-baslat")

    # hata
    b = yeni_bdm("Matris Hata")
    ortak.durum_yaz(b, "hata")
    dene("hata→baslat", b, "baslat")
    dene("hata→durdur", b, "durdur")
    dene("hata→yeniden-baslat", b, "yeniden-baslat")
    hata_id = b

    # hata'dan çıkış yolları
    ortak.baslik("hata durumundan çıkış denemeleri")
    with ortak.istemci() as c:
        yanit = c.patch(f"/bdm/{hata_id}", json={"durum": "hazir"}, headers=BASLIKLAR)
        ortak.goster("PATCH /bdm/{id} durum=hazir", yanit)
    print(f"  DB durum (PATCH sonrası) = {ortak.bdm_satiri(hata_id)['durum']}")
    with ortak.istemci() as c:
        yanit = c.post(f"/bdm/hazirlama/{hata_id}/dogrula", headers=BASLIKLAR)
        ortak.goster("POST /bdm/hazirlama/{id}/dogrula", yanit)
    print(f"  DB durum (doğrula sonrası) = {ortak.bdm_satiri(hata_id)['durum']}")

    # olmayan kayıt
    ortak.baslik("Olmayan BDM")
    dene("yok→baslat", 999999, "baslat")
    with ortak.istemci() as c:
        ortak.goster("GET yok/durum", c.get(f"{ortak.UC}/999999/durum", headers=BASLIKLAR))


if __name__ == "__main__":
    main()
