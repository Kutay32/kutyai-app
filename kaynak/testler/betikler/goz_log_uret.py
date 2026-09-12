"""Gözlem logunu (kaynak/testler/loglar-log.md) ham çıktılardan üretir.

Ham çıktılar /tmp altındaki gözlem koşularıdır; bu betik onları
`kaynak/testler/kanit/loglar/` altına kopyalar ve markdown'a gömer.
Bölümler kırpılabilir ama asla değiştirilmez.
"""

from __future__ import annotations

import pathlib
import shutil

KOK = pathlib.Path(__file__).resolve().parents[3]
KANIT = KOK / "kaynak" / "testler" / "kanit" / "loglar"
HEDEF = KOK / "kaynak" / "testler" / "loglar-log.md"

DOSYALAR = {
    "01": "goz01a.txt",
    "01b": "goz01b.txt",
    "02": "goz02.txt",
    "tohum": "goztohum.txt",
    "03": "goz03.txt",
    "04": "goz04.txt",
    "05": "goz05.txt",
    "06": "goz06.txt",
    "07": "goz07.txt",
}


def bolumleri_ayir(metin: str) -> list[str]:
    """'=== başlık ===' bloklarını başlıklarıyla birlikte döndürür."""
    bloklar: list[str] = []
    gecerli = False
    for satir in metin.splitlines():
        if satir.startswith("=== ") and satir.endswith(" ==="):
            gecerli = True
        if gecerli:
            bloklar.append(satir)
    return bloklar


def ham(anahtar: str, *, sinir: int = 1100, atla: tuple[str, ...] = ()) -> str:
    yol = KANIT / f"{anahtar}.txt"
    satirlar = bolumleri_ayir(yol.read_text(encoding="utf-8"))
    cikti: list[str] = []
    blok: list[str] = []
    baslik = ""

    def kapat() -> None:
        govde = "\n".join(blok).strip("\n")
        if not govde:
            return
        if any(baslik.startswith(a) for a in atla):
            return
        if len(govde) > sinir:
            govde = govde[:sinir] + f"\n... (kırpıldı; tam kayıt: kanit/loglar/{anahtar}.txt)"
        cikti.append(govde)

    for satir in satirlar:
        if satir.startswith("=== ") and satir.endswith(" ==="):
            kapat()
            baslik = satir[4:-4]
            blok = [satir]
        else:
            blok.append(satir)
    kapat()
    return "\n\n".join(cikti)


def kopyala() -> None:
    KANIT.mkdir(parents=True, exist_ok=True)
    for anahtar, dosya in DOSYALAR.items():
        shutil.copyfile(pathlib.Path("/tmp") / dosya, KANIT / f"{anahtar}.txt")


if __name__ == "__main__":
    kopyala()
    print("kopyalandı:", sorted(p.name for p in KANIT.glob("*.txt")))
