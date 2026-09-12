"""Derlenmiş CSS taraması: yasak tasarım desenleri (sm:, gradyan, purple/violet/indigo, blur).

Kullanım:
    python kaynak/testler/betikler/css_tara.py <css_url_veya_dosya> [...]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import httpx

DESENLER = {
    "sm_breakpoint_40rem": re.compile(r"min-width:\s*40rem"),
    "sm_onekli_sinif": re.compile(r"\.sm\\?:|sm\\:"),
    "gradyan": re.compile(r"gradient", re.I),
    "purple_violet_indigo": re.compile(r"purple|violet|indigo", re.I),
    "blur_backdrop": re.compile(r"backdrop-filter|blur\(", re.I),
    "md_breakpoint_48rem": re.compile(r"min-width:\s*48rem"),
    "medya_sorgulari": re.compile(r"@media[^{]*"),
}


def css_metni(kaynak: str) -> str:
    if kaynak.startswith("http"):
        return httpx.get(kaynak, timeout=30.0).text
    return Path(kaynak).read_text(encoding="utf-8")


def main() -> int:
    for kaynak in sys.argv[1:]:
        metin = css_metni(kaynak)
        print(f"=== {kaynak} ({len(metin)} bayt) ===")
        for ad, desen in DESENLER.items():
            if ad == "medya_sorgulari":
                bulunan = sorted(set(m.group(0).strip() for m in desen.finditer(metin)))
                print(f"  {ad}: {bulunan}")
                continue
            eslesen = desen.findall(metin)
            print(f"  {ad}: {len(eslesen)} eslesme" + (f" -> {eslesen[:5]}" if eslesen else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
