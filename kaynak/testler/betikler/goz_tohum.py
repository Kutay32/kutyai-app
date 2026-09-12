"""Log uçları için doğrudan SQL tohumu (yalnız geçici gözlem veritabanı).

3 konuşma + mesaj ekler; biri Türkçe karakterli başlık taşır.
"""

from __future__ import annotations

import sqlite3

YOL = "E:/kutyai-app/kaynak/testler/gecici/goz_loglar.db"

KONUSMALAR = [
    # (id, kullanici_id, api_anahtari_id, bdm_id, baslik, token_girdi, token_cikti, olusturulma)
    (1, 1, None, 1, "Öğle yemeği planı çığöşü", 11, 22, "2026-09-01 09:00:00.000000"),
    (2, 2, None, 2, "Sunucu kurulum notları", 33, 44, "2026-09-05 10:30:00.000000"),
    (3, None, 1, 1, "API anahtarıyla sohbet", 5, 6, "2026-09-11 23:00:00.000000"),
    (4, 1, None, 1, "Saklama süresi dolmuş eski kayıt", 1, 1, "2026-06-01 08:00:00.000000"),
]

MESAJLAR = [
    (1, 1, "kullanici", "Merhaba, öğle yemeği için Şişli'de buluşalım mı?", 8, 0, "llama3", None, "2026-09-01 09:00:00.000000"),
    (2, 1, "asistan", "Elbette, saat 12:30 uygun mu?", 3, 120, "llama3", None, "2026-09-01 09:00:01.000000"),
    (3, 2, "kullanici", "Docker port çakışması", 4, 0, "llama3", None, "2026-09-05 10:30:00.000000"),
    (4, 2, "asistan", "Konteyner portunu değiştirin.", 22, 340, "llama3", None, "2026-09-05 10:30:02.000000"),
    (5, 3, "kullanici", "Özel anahtar testi", 5, 0, "llama3", None, "2026-09-11 23:00:00.000000"),
    (6, 3, "asistan", "Anahtar geçerli.", 1, 90, "llama3", None, "2026-09-11 23:00:01.000000"),
]


def tohumla() -> None:
    baglanti = sqlite3.connect(YOL)
    baglanti.execute("DELETE FROM mesaj")
    baglanti.execute("DELETE FROM konusma")
    baglanti.executemany(
        "INSERT INTO konusma (id, kullanici_id, api_anahtari_id, bdm_id, baslik, "
        "sistem_istemi, token_girdi, token_cikti, arsivlendi, olusturulma, guncellenme) "
        "VALUES (?,?,?,?,?,'',?,?,0,?,?)",
        [(*k[:7], k[7], k[7]) for k in KONUSMALAR],
    )
    baglanti.executemany(
        "INSERT INTO mesaj (id, konusma_id, rol, icerik, token_sayisi, gecikme_ms, model, "
        "hata, olusturulma) VALUES (?,?,?,?,?,?,?,?,?)",
        MESAJLAR,
    )
    baglanti.commit()
    print("konusma:", baglanti.execute("SELECT id,baslik,olusturulma FROM konusma").fetchall())
    print("mesaj sayısı:", baglanti.execute("SELECT count(*) FROM mesaj").fetchone())
    baglanti.close()


if __name__ == "__main__":
    tohumla()
