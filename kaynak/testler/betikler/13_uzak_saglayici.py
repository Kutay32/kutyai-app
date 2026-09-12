"""13 — Uzak sağlayıcıda `baslat`: hangi hata?"""

from __future__ import annotations

import pathlib
import sys

BETIKLER = pathlib.Path(__file__).resolve().parents[1] / "betikler"
sys.path.insert(0, str(BETIKLER))
sys.path.insert(0, str(BETIKLER.parents[2]))

import ortak  # noqa: E402

BASLIKLAR = ortak.basliklar(ortak.jeton_al())


def main() -> None:
    for bdm_id, etiket in ((4, "ozel (uzak)"), (3, "ollama (uzak adres)")):
        ortak.durum_yaz(bdm_id, "hazir")
        with ortak.istemci() as c:
            ortak.goster(f"POST {etiket} baslat", c.post(f"{ortak.UC}/{bdm_id}/baslat", headers=BASLIKLAR))
        db = ortak.bdm_satiri(bdm_id)
        print(f"  DB durum={db['durum']}")
        with ortak.istemci() as c:
            ortak.goster(f"POST {etiket} durdur", c.post(f"{ortak.UC}/{bdm_id}/durdur", headers=BASLIKLAR))


if __name__ == "__main__":
    main()
