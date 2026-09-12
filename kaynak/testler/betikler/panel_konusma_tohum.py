"""Kontrol paneli 'Son Konuşmalar' bloğunu gerçek veriyle sınamak için tohum kaydı.

Geçici gözlem veritabanına (kaynak/testler/gecici/panel.db) bir konuşma ve iki
mesaj yazar; ürün kodu değiştirilmez.

Kullanım: ./.venv/Scripts/python.exe kaynak/testler/betikler/panel_konusma_tohum.py
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone

YOL = "kaynak/testler/gecici/panel.db"


def main() -> int:
    zaman = datetime.now(timezone.utc).replace(tzinfo=None).isoformat(sep=" ", timespec="seconds")
    baglanti = sqlite3.connect(YOL)
    imlec = baglanti.execute(
        """
        INSERT INTO konusma (kullanici_id, api_anahtari_id, bdm_id, baslik, sistem_istemi,
                             token_girdi, token_cikti, arsivlendi, olusturulma, guncellenme)
        VALUES (1, NULL, 1, ?, '', 24, 61, 0, ?, ?)
        """,
        ("Gözlem konuşması [MASKELENDI:telefon]", zaman, zaman),
    )
    konusma_id = imlec.lastrowid
    baglanti.executemany(
        """
        INSERT INTO mesaj (konusma_id, rol, icerik, token_sayisi, gecikme_ms, model, hata, olusturulma)
        VALUES (?, ?, ?, ?, ?, ?, NULL, ?)
        """,
        [
            (konusma_id, "kullanici", "Merhaba, [MASKELENDI:telefon] numarasından yazıyorum.", 12, 0, "llama3", zaman),
            (konusma_id, "asistan", "Merhaba! Size nasıl yardımcı olabilirim?", 12, 812, "llama3", zaman),
        ],
    )
    baglanti.commit()
    satir = baglanti.execute(
        "SELECT id, baslik, token_girdi, token_cikti FROM konusma WHERE id = ?", (konusma_id,)
    ).fetchone()
    print(json.dumps({"konusma": satir, "mesaj_sayisi": 2}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
