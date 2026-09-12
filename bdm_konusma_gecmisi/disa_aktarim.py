"""Konusma disa aktarimi: json / md / csv (spec §7.7)."""

from __future__ import annotations

import csv
import io
import json

from bdm_veritabani.modeller import Konusma

BICIMLER = ("json", "md", "csv")
MEDYA_TURLERI = {
    "json": "application/json; charset=utf-8",
    "md": "text/markdown; charset=utf-8",
    "csv": "text/csv; charset=utf-8",
}


def dosya_adi_uret(konusma: Konusma, bicim: str) -> str:
    return f"konusma-{konusma.id}.{bicim}"


def json_disa_aktar(konusma: Konusma, detay: dict[str, object]) -> str:
    return json.dumps(detay, ensure_ascii=False, indent=2)


def markdown_disa_aktar(konusma: Konusma, detay: dict[str, object]) -> str:
    satirlar = [
        f"# {konusma.baslik}",
        "",
        f"- Konuşma no: {konusma.id}",
        f"- Model: {detay.get('bdm_ad') or '-'}",
        f"- Kullanıcı: {detay.get('kullanici_eposta') or '-'}",
        f"- Oluşturulma: {detay.get('olusturulma')}",
        "",
        "---",
        "",
    ]
    for mesaj in detay.get("mesajlar", []):  # type: ignore[union-attr]
        etiket = {
            "kullanici": "Kullanıcı",
            "asistan": "Asistan",
            "sistem": "Sistem",
            "arac": "Araç",
        }.get(mesaj["rol"], mesaj["rol"])
        satirlar.append(f"## {etiket}")
        satirlar.append("")
        satirlar.append(mesaj["icerik"] or "")
        satirlar.append("")
    return "\n".join(satirlar)


_FORMUL_ONEKLERI = ("=", "+", "-", "@", "\t", "\r")


def _hucre(deger: object) -> str:
    """CSV formül enjeksiyonunu etkisizleştirir (Excel/Sheets)."""
    metin = "" if deger is None else str(deger)
    if metin.startswith(_FORMUL_ONEKLERI):
        return "'" + metin
    return metin


def csv_disa_aktar(konusma: Konusma, detay: dict[str, object]) -> str:
    tampon = io.StringIO()
    yazici = csv.writer(tampon, lineterminator="\n")
    yazici.writerow(["mesaj_id", "rol", "icerik", "token", "gecikme_ms", "olusturulma"])
    for mesaj in detay.get("mesajlar", []):  # type: ignore[union-attr]
        yazici.writerow(
            [
                _hucre(mesaj["id"]),
                _hucre(mesaj["rol"]),
                _hucre(mesaj["icerik"]),
                _hucre(mesaj["token_sayisi"]),
                _hucre(mesaj["gecikme_ms"]),
                _hucre(mesaj["olusturulma"]),
            ]
        )
    return tampon.getvalue()


def disa_aktar(konusma: Konusma, detay: dict[str, object], bicim: str) -> tuple[str, str, str]:
    """(icerik, medya_turu, dosya_adi) dondurur."""
    bicim = (bicim or "json").lower()
    if bicim not in BICIMLER:
        from arkauc.app.cekirdek.hatalar import GecersizIstek

        raise GecersizIstek(
            f"Desteklenmeyen biçim: {bicim}", {"gecerli_bicimler": list(BICIMLER)}
        )
    uretici = {
        "json": json_disa_aktar,
        "md": markdown_disa_aktar,
        "csv": csv_disa_aktar,
    }[bicim]
    return uretici(konusma, detay), MEDYA_TURLERI[bicim], dosya_adi_uret(konusma, bicim)
