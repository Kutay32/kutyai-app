"""Fikstur kurulumu: kurulum ucu, girisler, BDM'ler, API anahtarlari, durumlar."""

from __future__ import annotations

import json
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _ortak import (  # noqa: E402
    ADMIN_EPOSTA,
    ADMIN_PAROLA,
    OPERATOR_EPOSTA,
    ORTAK_PAROLA,
    SON_EPOSTA,
    TOKEN_DOSYASI,
    UPSTREAM_ANAHTAR,
    istemci,
    sql,
    yaz,
)

c = istemci()

# 1) Kurulum: yonetici + anahtarli bir BDM
r = c.post(
    "/kurulum",
    json={
        "marka_adi": "Gozlem AI",
        "yonetici": {
            "eposta": ADMIN_EPOSTA,
            "ad_soyad": "Gozlem Yonetici",
            "parola": ADMIN_PAROLA,
        },
        "bdm": {
            "gorunen_ad": "Gozlem GPT",
            "saglayici": "openai",
            "temel_url": "https://api.openai.com/v1",
            "upstream_model": "gpt-4o-mini",
            "api_anahtari": UPSTREAM_ANAHTAR,
            "baglam_penceresi": 128000,
            "maks_cikti": 4096,
            "sicaklik_varsayilan": 0.7,
            "sistem_istemi": "",
            "yerel_mi": False,
        },
        "dogrula": False,
    },
)
yaz("POST /kurulum", r)

# 2) Yonetici girisi
g = c.post("/kimlik/panel-giris", json={"eposta": ADMIN_EPOSTA, "parola": ADMIN_PAROLA})
yaz("POST /kimlik/panel-giris (yonetici)", g)
admin_jeton = g.json()["erisim_jetonu"]
a = istemci(admin_jeton)

# 3) Ek BDM'ler
bdmler: dict[str, dict[str, object]] = {}
tanimlar = [
    ("musteri", "Müşteri Asistanı ÇĞİÖŞÜ", None),
    ("taslak", "Gozlem Taslak", "taslak-bdm"),
    ("durdu", "Gozlem Durdu", "durdu-bdm"),
    ("hata", "Gozlem Hata", "hata-bdm"),
    ("calisan", "Gozlem Calisan", None),
]
for anahtar, ad, slug in tanimlar:
    govde = {
        "gorunen_ad": ad,
        "aciklama": "",
        "saglayici": "openai",
        "temel_url": "https://api.openai.com/v1",
        "upstream_model": "gpt-4o-mini",
        "api_anahtari": UPSTREAM_ANAHTAR,
        "yerel_mi": False,
    }
    if slug:
        govde["slug"] = slug
    y = a.post("/bdm", json=govde)
    yaz(f"POST /bdm ({ad})", y)
    bdmler[anahtar] = y.json()

kurulum_bdm = r.json()["bdm"]
kimlikler = {
    "gozlem-gpt": kurulum_bdm["id"],
    "musteri": bdmler["musteri"]["id"],
    "taslak": bdmler["taslak"]["id"],
    "durdu": bdmler["durdu"]["id"],
    "hata": bdmler["hata"]["id"],
    "calisan": bdmler["calisan"]["id"],
}
print("--- BDM kimlik/slug haritasi")
print(json.dumps({k: {"id": v} for k, v in kimlikler.items()}, indent=2, ensure_ascii=False))
print(
    json.dumps(
        {
            "sluglar": {
                "gozlem-gpt": kurulum_bdm["slug"],
                "musteri": bdmler["musteri"]["slug"],
                "taslak": bdmler["taslak"]["slug"],
                "durdu": bdmler["durdu"]["slug"],
                "hata": bdmler["hata"]["slug"],
                "calisan": bdmler["calisan"]["slug"],
            }
        },
        indent=2,
        ensure_ascii=False,
    )
)
print()

# 4) Durumlari dogrudan veritabanindan ayarla (durum alani uclardan yazilamaz)
durumlar = {
    "hazir": (kimlikler["gozlem-gpt"], kimlikler["musteri"]),
    "calisiyor": (kimlikler["calisan"],),
    "durdu": (kimlikler["durdu"],),
    "hata": (kimlikler["hata"],),
    "taslak": (kimlikler["taslak"],),
}
for durum, idler in durumlar.items():
    for bdm_id in idler:
        sql("UPDATE bdm SET durum = ? WHERE id = ?", (durum, bdm_id))
print("--- bdm tablosu (id, slug, durum)")
print(json.dumps(sql("SELECT id, slug, durum FROM bdm ORDER BY id"), ensure_ascii=False, indent=2))
print()

# 5) Personel/kullanici hesaplari
for eposta, rol in ((OPERATOR_EPOSTA, "operator"), (SON_EPOSTA, "son_kullanici")):
    k = a.post(
        "/kullanicilar",
        json={"eposta": eposta, "ad_soyad": "Gozlem Kullanici", "parola": ORTAK_PAROLA, "rol": rol},
    )
    yaz(f"POST /kullanicilar ({rol})", k)

sql("UPDATE kullanici SET durum = 'aktif', eposta_dogrulandi = 1")
print("--- kullanici tablosu (eposta, rol, durum, eposta_dogrulandi)")
print(
    json.dumps(
        sql("SELECT eposta, rol, durum, eposta_dogrulandi FROM kullanici ORDER BY id"),
        ensure_ascii=False,
        indent=2,
    )
)
print()

op = c.post("/kimlik/panel-giris", json={"eposta": OPERATOR_EPOSTA, "parola": ORTAK_PAROLA})
yaz("POST /kimlik/panel-giris (operator)", op)
sn = c.post("/kimlik/giris", json={"eposta": SON_EPOSTA, "parola": ORTAK_PAROLA})
yaz("POST /kimlik/giris (son_kullanici)", sn)

# 6) API anahtarlari: bos liste, tek model (slug), tek model (id)
anahtarlar: dict[str, str] = {}
olusturmalar = [
    ("bos", {"ad": "Gozlem Bos Izin", "izinli_modeller": []}),
    ("tek_slug", {"ad": "Gozlem Tek Slug", "izinli_modeller": [bdmler["musteri"]["slug"]]}),
    ("tek_id", {"ad": "Gozlem Tek Id", "izinli_modeller": [str(kimlikler["calisan"])]}),
]
for anahtar_ad, govde in olusturmalar:
    y = a.post("/api-anahtarlari", json=govde)
    yaz(f"POST /api-anahtarlari ({govde['ad']})", y)
    anahtarlar[anahtar_ad] = y.json()["tam_anahtar"]

TOKEN_DOSYASI.write_text(
    json.dumps(
        {
            "admin": admin_jeton,
            "operator": op.json().get("erisim_jetonu", ""),
            "son_kullanici": sn.json().get("erisim_jetonu", ""),
            "anahtar_bos": anahtarlar["bos"],
            "anahtar_tek_slug": anahtarlar["tek_slug"],
            "anahtar_tek_id": anahtarlar["tek_id"],
            "bdm": kimlikler,
            "slug": {
                "gozlem-gpt": kurulum_bdm["slug"],
                "musteri": bdmler["musteri"]["slug"],
                "taslak": bdmler["taslak"]["slug"],
                "durdu": bdmler["durdu"]["slug"],
                "hata": bdmler["hata"]["slug"],
                "calisan": bdmler["calisan"]["slug"],
            },
        },
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
print(f"oturum dosyasi yazildi: {TOKEN_DOSYASI}")
