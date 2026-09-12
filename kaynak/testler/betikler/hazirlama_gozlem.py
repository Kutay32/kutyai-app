"""`bdm_hazirlama_ucu` canli HTTP gozlemi (backend 8103, sahte upstream 8199).

Uctan uca: kurulum (ya da mevcut yonetici girisi) -> BDM olustur -> dogrula /
cek / manifest / on-kontrol. Her adim ham HTTP ciktisi olarak basilir.

Calistirma:
  ./.venv/Scripts/python.exe kaynak/testler/betikler/hazirlama_gozlem.py
"""

from __future__ import annotations

import json
import sqlite3
import sys
import time
from pathlib import Path

import httpx

TABAN = "http://127.0.0.1:8103/api/v1"
SAHTE = "http://127.0.0.1:8199/v1"
SAHTE_401 = "http://127.0.0.1:8199/modeller401/v1"
KAPALI = "http://127.0.0.1:8198/v1"
DB = Path("kaynak/testler/gecici/goz_hazirlama.db")

YONETICI = {"eposta": "goz-yp@gozlem.example.com", "ad_soyad": "Goz Yonetici", "parola": "GozlemParola1!"}
SON_KULLANICI = {"eposta": "goz-sk@gozlem.example.com", "ad_soyad": "Goz Son Kullanici", "parola": "GozlemParola2!"}

ISARET = str(int(time.time()))[-6:]

istemci = httpx.Client(base_url=TABAN, timeout=30.0)


def baslik(no: str, metin: str) -> None:
    print(f"\n===== [{no}] {metin} =====")


def goster(yanit: httpx.Response) -> dict | None:
    govde: object = yanit.text
    try:
        govde = yanit.json()
    except ValueError:
        pass
    print(f"HTTP {yanit.status_code} {yanit.headers.get('content-type', '')}")
    if isinstance(govde, str):
        print(govde[:3000])
    else:
        print(json.dumps(govde, ensure_ascii=False)[:3000])
    return govde if isinstance(govde, dict) else None


def bdm_olustur(jeton: str, ad: str, slug: str, saglayici: str, url: str,
                model: str = "", anahtar: str = "", zorunlu: bool = True) -> dict | None:
    yanit = istemci.post(
        "/bdm",
        headers={"Authorization": f"Bearer {jeton}"},
        json={"ad": ad, "gorunen_ad": ad, "slug": f"{slug}-{ISARET}", "saglayici": saglayici,
              "temel_url": url, "upstream_model": model, "api_anahtari": anahtar},
    )
    if yanit.status_code != 201:
        print(f"BDM OLUSTURULAMADI ({slug}): {yanit.status_code} {yanit.text[:400]}")
        if zorunlu:
            sys.exit(1)
        return None
    return yanit.json()


def durum_oku(jeton: str, bdm_id: int) -> str:
    yanit = istemci.get("/bdm", headers={"Authorization": f"Bearer {jeton}"})
    for kayit in yanit.json():
        if kayit["id"] == bdm_id:
            return str(kayit["durum"])
    return "?"


def main() -> None:
    # -- 0) Kurulum ve oturumlar -------------------------------------------
    baslik("0", "Kurulum + panel girisi")
    yanit = istemci.post(
        "/kurulum",
        json={
            "marka_adi": "Gozlem",
            "yonetici": YONETICI,
            "bdm": {"gorunen_ad": "Kurulum BDM", "saglayici": "ozel", "temel_url": SAHTE,
                    "upstream_model": "sahte-model-kucuk"},
            "dogrula": False,
        },
    )
    goster(yanit)
    yanit = istemci.post("/kimlik/panel-giris", json={"eposta": YONETICI["eposta"], "parola": YONETICI["parola"]})
    goster(yanit)
    yonetici = yanit.json()["erisim_jetonu"]
    Y = {"Authorization": f"Bearer {yonetici}"}

    # -- 1) Gercek OpenAI-uyumlu sunucuya dogrulama -------------------------
    baslik("1", "POST /{id}/dogrula -> GERCEK sahte upstream (/v1/models 200)")
    bdm_sahte = bdm_olustur(yonetici, "Sahte Ozel", "goz-sahte", "ozel", SAHTE, "sahte-model-kucuk")
    yanit = istemci.post(f"/bdm/hazirlama/{bdm_sahte['id']}/dogrula", headers=Y)
    goster(yanit)
    print("durum (GET /bdm):", durum_oku(yonetici, bdm_sahte["id"]))
    print("sahte upstream vurus sayaci:", httpx.get("http://127.0.0.1:8199/_vuruslar").text)

    # -- 1b) /models 401 -> sohbet yedek yolu -------------------------------
    baslik("1b", "POST /{id}/dogrula -> /v1/models 401, sohbet yedegi")
    bdm_401 = bdm_olustur(yonetici, "Modeller401 Ozel", "goz-401", "ozel", SAHTE_401, "sahte-model-kucuk")
    yanit = istemci.post(f"/bdm/hazirlama/{bdm_401['id']}/dogrula", headers=Y)
    goster(yanit)
    print("durum (GET /bdm):", durum_oku(yonetici, bdm_401["id"]))
    print("sahte upstream vurus sayaci:", httpx.get("http://127.0.0.1:8199/_vuruslar").text)

    # -- 1c) Adres tanimsiz -------------------------------------------------
    baslik("1c", "POST /{id}/dogrula -> temel_url bos")
    bdm_bos = bdm_olustur(yonetici, "Adres Bos", "goz-bos", "ozel", "", "sahte-model-kucuk", zorunlu=False)
    if bdm_bos is None:
        print("(bos temel_url ile BDM olusturma reddedildi — ayri bir gozlem)")
    else:
        yanit = istemci.post(f"/bdm/hazirlama/{bdm_bos['id']}/dogrula", headers=Y)
        goster(yanit)
        print("durum (GET /bdm):", durum_oku(yonetici, bdm_bos["id"]))

    # -- 2) Kapali porta dogrulama ------------------------------------------
    baslik("2", "POST /{id}/dogrula -> KAPALI port (8198)")
    bdm_kapali = bdm_olustur(yonetici, "Kapali Port", "goz-kapali", "ozel", KAPALI, "yok")
    yanit = istemci.post(f"/bdm/hazirlama/{bdm_kapali['id']}/dogrula", headers=Y)
    goster(yanit)
    print("durum (GET /bdm):", durum_oku(yonetici, bdm_kapali["id"]))

    # -- 2b) Bozuk URL -------------------------------------------------------
    baslik("2b", "POST /{id}/dogrula -> gecersiz port iceren URL (99999)")
    bdm_bozuk = bdm_olustur(yonetici, "Bozuk Adres", "goz-bozuk", "ozel", "http://127.0.0.1:99999/v1")
    yanit = istemci.post(f"/bdm/hazirlama/{bdm_bozuk['id']}/dogrula", headers=Y)
    goster(yanit)

    # -- 2c) Cozulemeyen ana makine -----------------------------------------
    baslik("2c", "POST /{id}/dogrula -> cozulemeyen ana makine (IDNA gecersiz)")
    bdm_idna = bdm_olustur(yonetici, "Bozuk Ana Makine", "goz-idna", "ozel", "http://[::1/v1")
    yanit = istemci.post(f"/bdm/hazirlama/{bdm_idna['id']}/dogrula", headers=Y)
    goster(yanit)

    # -- 3) calisiyor -> dogrula -------------------------------------------
    baslik("3", "calisiyor durumundaki BDM'e POST /{id}/dogrula (basarisiz dogrulama)")
    baglanti = sqlite3.connect(DB)
    baglanti.execute("UPDATE bdm SET durum='calisiyor' WHERE id=?", (bdm_kapali["id"],))
    baglanti.commit()
    baglanti.close()
    print("dogrulama oncesi durum:", durum_oku(yonetici, bdm_kapali["id"]))
    yanit = istemci.post(f"/bdm/hazirlama/{bdm_kapali['id']}/dogrula", headers=Y)
    goster(yanit)
    print("dogrulama sonrasi durum:", durum_oku(yonetici, bdm_kapali["id"]))

    # -- BDM'ler ------------------------------------------------------------
    bdm_vllm = bdm_olustur(yonetici, "vLLM Yerel", "goz-vllm", "vllm", "http://127.0.0.1:8000/v1",
                           "Qwen/Qwen2.5-7B-Instruct", "hf-gizli-token-DEADBEEF")
    bdm_ollama = bdm_olustur(yonetici, "Ollama Yerel", "goz-ollama", "ollama", SAHTE, "sahte-model-kucuk")
    bdm_openai = bdm_olustur(yonetici, "OpenAI Uzak", "goz-openai", "openai", SAHTE, "gpt-4o-mini",
                             "sk-gizli-anahtar-DEADBEEF")

    # -- 4) on-kontrol ------------------------------------------------------
    baslik("4", "GET /{id}/on-kontrol (vllm ve ollama) — bu makinede Docker+GPU VAR")
    print("-- vllm:"); goster(istemci.get(f"/bdm/hazirlama/{bdm_vllm['id']}/on-kontrol", headers=Y))
    print("-- ollama:"); goster(istemci.get(f"/bdm/hazirlama/{bdm_ollama['id']}/on-kontrol", headers=Y))
    print("-- surucu durumu (yonetim):")
    goster(istemci.get("/bdm/yonetim/surucu/durum", headers=Y))

    # -- 5) manifest --------------------------------------------------------
    baslik("5", "POST /{id}/manifest (vllm, openai, ollama)")
    for etiket, bdm in (("vllm", bdm_vllm), ("openai", bdm_openai), ("ollama", bdm_ollama)):
        print(f"-- {etiket}:")
        yanit = istemci.post(f"/bdm/hazirlama/{bdm['id']}/manifest", headers=Y)
        goster(yanit)
        print("   ham govdede 'DEADBEEF' var mi:", "DEADBEEF" in yanit.text)

    # -- 6) GPU yok -> 503 (bu makinede GPU oldugu icin 503 beklenmez) -------
    baslik("6", "vllm icin POST /cek ve /manifest (canli: GPU VAR)")
    print("-- vllm /cek:"); goster(istemci.post(f"/bdm/hazirlama/{bdm_vllm['id']}/cek", headers=Y))
    print("-- vllm /manifest:"); goster(istemci.post(f"/bdm/hazirlama/{bdm_vllm['id']}/manifest", headers=Y))

    # -- 7) cek SSE ---------------------------------------------------------
    baslik("7", "POST /{id}/cek (openai -> 400, ollama -> SSE)")
    print("-- openai:"); goster(istemci.post(f"/bdm/hazirlama/{bdm_openai['id']}/cek", headers=Y))
    print("-- ollama / vllm:")
    for etiket, bdm in (("ollama", bdm_ollama), ("vllm", bdm_vllm)):
        yanit = istemci.post(f"/bdm/hazirlama/{bdm['id']}/cek", headers=Y)
        print(f"   {etiket}:"); goster(yanit)

    # -- 7b) Kapali upstream -> SSE hata yolu -------------------------------
    baslik("7b", "POST /{id}/cek -> upstream kapali (SSE hata cercevesi)")
    bdm_kapali_cek = bdm_olustur(yonetici, "Kapali Ollama", "goz-kapali-cek", "ollama", KAPALI, "sahte-model-kucuk")
    try:
        yanit = istemci.post(f"/bdm/hazirlama/{bdm_kapali_cek['id']}/cek", headers=Y)
        print(f"HTTP {yanit.status_code} {yanit.headers.get('content-type', '')}")
        print("govde uzunlugu:", len(yanit.content))
        print("ham govde:", repr(yanit.text))
    except Exception as hata:
        print(f"ISTEMCI ISTISNASI: {type(hata).__name__}: {hata}")

    # -- 8) Yetki -----------------------------------------------------------
    baslik("8", "Anonim 401 / son_kullanici 403")
    for etiket, istek in (
        ("anonim on-kontrol", istemci.get(f"/bdm/hazirlama/{bdm_ollama['id']}/on-kontrol")),
        ("anonim manifest", istemci.post(f"/bdm/hazirlama/{bdm_ollama['id']}/manifest")),
        ("anonim cek", istemci.post(f"/bdm/hazirlama/{bdm_ollama['id']}/cek")),
        ("anonim dogrula", istemci.post(f"/bdm/hazirlama/{bdm_ollama['id']}/dogrula")),
    ):
        print(f"-- {etiket}:"); goster(istek)
    yanit = istemci.post("/kimlik/kayit", json=SON_KULLANICI)
    print("-- kayit (ilk calistirmada 201, sonra 409):", yanit.status_code)
    baglanti = sqlite3.connect(DB)
    baglanti.execute("UPDATE kullanici SET eposta_dogrulandi=1, durum='aktif' WHERE eposta=?",
                     (SON_KULLANICI["eposta"],))
    baglanti.commit()
    baglanti.close()
    giris = istemci.post("/kimlik/giris", json={"eposta": SON_KULLANICI["eposta"], "parola": SON_KULLANICI["parola"]})
    print("-- son kullanici giris:", giris.status_code)
    SK = {"Authorization": f"Bearer {giris.json()['erisim_jetonu']}"}
    print("-- son_kullanici on-kontrol:"); goster(istemci.get(f"/bdm/hazirlama/{bdm_ollama['id']}/on-kontrol", headers=SK))
    print("-- son_kullanici manifest:"); goster(istemci.post(f"/bdm/hazirlama/{bdm_ollama['id']}/manifest", headers=SK))
    print("-- son_kullanici dogrula:"); goster(istemci.post(f"/bdm/hazirlama/{bdm_ollama['id']}/dogrula", headers=SK))
    print("-- son_kullanici cek:"); goster(istemci.post(f"/bdm/hazirlama/{bdm_ollama['id']}/cek", headers=SK))

    print(f"\n[ozet] vllm={bdm_vllm['id']} ollama={bdm_ollama['id']} openai={bdm_openai['id']} "
          f"kapali={bdm_kapali['id']} kapali_cek={bdm_kapali_cek['id']}")


if __name__ == "__main__":
    main()
