"""`bdm_hazirlama_ucu` — surucu enjeksiyonlu (in-process ASGI) gozlem.

Neden ayri betik: bu makinede Docker calisiyor ve NVIDIA GPU var
(`docker info` -> Runtimes nvidia, `nvidia-smi` -> RTX 3080 Ti). Bu yuzden
"GPU yok" senaryosu canli ortamda uretilemez; spec §10'un kendi test kancasi
olan `SahteSurucu` + `surucu_ata()` ile ayni HTTP yuzeyi ASGI uzerinden
surulur (gercek router, gercek kimlik, gercek veritabani).

Calistirma:
  ./.venv/Scripts/python.exe kaynak/testler/betikler/hazirlama_asgi_gozlem.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(KOK))
os.chdir(KOK)

DB = KOK / "kaynak/testler/gecici/goz_hazirlama_asgi.db"
if DB.exists():
    DB.unlink()

os.environ["KUTYAI_VERITABANI_URL"] = f"sqlite+aiosqlite:///{DB.as_posix()}"
os.environ["KUTYAI_GIZLI_ANAHTAR"] = "gozlem-gizli-anahtar"
os.environ["KUTYAI_SIFRELEME_ANAHTARI"] = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="

import httpx  # noqa: E402

from arkauc.app.main import uygulama_olustur  # noqa: E402
from arkauc.app.servisler.konteyner import SahteSurucu, surucu_ata  # noqa: E402
from bdm_veritabani.oturum import motoru_sifirla, tablolari_olustur  # noqa: E402
from bdm_veritabani.tohum import tohumla  # noqa: E402

SAHTE = "http://127.0.0.1:8199/v1"
YONETICI = {"eposta": "asgi-yp@gozlem.example.com", "ad_soyad": "Asgi Yonetici", "parola": "GozlemParola1!"}


def baslik(no: str, metin: str) -> None:
    print(f"\n===== [{no}] {metin} =====")


def goster(yanit: httpx.Response) -> dict | None:
    govde: object = yanit.text
    try:
        govde = yanit.json()
    except ValueError:
        pass
    print(f"HTTP {yanit.status_code} {yanit.headers.get('content-type', '')}")
    print(json.dumps(govde, ensure_ascii=False)[:2500] if not isinstance(govde, str) else govde[:2500])
    return govde if isinstance(govde, dict) else None


async def bdm_olustur(istemci: httpx.AsyncClient, jeton: str, ad: str, slug: str, saglayici: str,
                      url: str, model: str = "", anahtar: str = "") -> dict:
    yanit = await istemci.post(
        "/api/v1/bdm",
        headers={"Authorization": f"Bearer {jeton}"},
        json={"ad": ad, "gorunen_ad": ad, "slug": slug, "saglayici": saglayici,
              "temel_url": url, "upstream_model": model, "api_anahtari": anahtar},
    )
    assert yanit.status_code == 201, yanit.text
    return yanit.json()


async def durum_oku(istemci: httpx.AsyncClient, y: dict, bdm_id: int) -> str:
    yanit = await istemci.get("/api/v1/bdm", headers=y)
    for kayit in yanit.json():
        if kayit["id"] == bdm_id:
            return str(kayit["durum"])
    return "?"


async def main() -> None:
    uygulama = uygulama_olustur()
    await tablolari_olustur()
    await tohumla()

    tasima = httpx.ASGITransport(app=uygulama, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=tasima, base_url="http://asgi", timeout=30.0) as istemci:
        baslik("A0", "Kurulum + panel girisi (ASGI)")
        yanit = await istemci.post(
            "/api/v1/kurulum",
            json={"marka_adi": "Gozlem", "yonetici": YONETICI,
                  "bdm": {"gorunen_ad": "Kurulum BDM", "saglayici": "ozel", "temel_url": SAHTE,
                          "upstream_model": "sahte-model-kucuk"}, "dogrula": False},
        )
        goster(yanit)
        yanit = await istemci.post("/api/v1/kimlik/panel-giris",
                                   json={"eposta": YONETICI["eposta"], "parola": YONETICI["parola"]})
        jeton = yanit.json()["erisim_jetonu"]
        Y = {"Authorization": f"Bearer {jeton}"}

        bdm_vllm = await bdm_olustur(istemci, jeton, "vLLM Yerel", "asgi-vllm", "vllm",
                                     "http://127.0.0.1:8000/v1", "Qwen/Qwen2.5-7B-Instruct",
                                     "hf-gizli-token-DEADBEEF")
        bdm_ollama = await bdm_olustur(istemci, jeton, "Ollama Yerel", "asgi-ollama", "ollama",
                                       SAHTE, "sahte-model-kucuk")
        bdm_tgi = await bdm_olustur(istemci, jeton, "TGI Yerel", "asgi-tgi", "tgi",
                                    "http://127.0.0.1:8080/v1", "mistralai/Mistral-7B-Instruct-v0.3")

        # ---------- GPU YOK senaryosu ----------
        surucu_ata(SahteSurucu(docker_var=False, gpu_var=False, image_onbellek=[]))
        baslik("B1", "GPU YOK: GET on-kontrol (vllm / tgi / ollama)")
        for etiket, bdm in (("vllm", bdm_vllm), ("tgi", bdm_tgi), ("ollama", bdm_ollama)):
            print(f"-- {etiket}:"); goster(await istemci.get(f"/api/v1/bdm/hazirlama/{bdm['id']}/on-kontrol", headers=Y))

        baslik("B2", "GPU YOK: POST manifest (vllm / tgi / ollama)")
        for etiket, bdm in (("vllm", bdm_vllm), ("tgi", bdm_tgi), ("ollama", bdm_ollama)):
            print(f"-- {etiket}:"); goster(await istemci.post(f"/api/v1/bdm/hazirlama/{bdm['id']}/manifest", headers=Y))

        baslik("B3", "GPU YOK: POST cek (vllm / tgi)")
        for etiket, bdm in (("vllm", bdm_vllm), ("tgi", bdm_tgi)):
            print(f"-- {etiket}:"); goster(await istemci.post(f"/api/v1/bdm/hazirlama/{bdm['id']}/cek", headers=Y))

        # ---------- GPU VAR senaryosu ----------
        surucu_ata(SahteSurucu(docker_var=True, gpu_var=True,
                               image_onbellek=["vllm/vllm-openai:latest", "ollama/ollama:latest"]))
        baslik("C1", "GPU VAR: GET on-kontrol (vllm / ollama)")
        for etiket, bdm in (("vllm", bdm_vllm), ("ollama", bdm_ollama)):
            print(f"-- {etiket}:"); goster(await istemci.get(f"/api/v1/bdm/hazirlama/{bdm['id']}/on-kontrol", headers=Y))

        baslik("C2", "GPU VAR: POST manifest (vllm — sir sizmasi kontrolu)")
        yanit = await istemci.post(f"/api/v1/bdm/hazirlama/{bdm_vllm['id']}/manifest", headers=Y)
        govde = goster(yanit)
        ham = yanit.text
        print("ham govdede 'DEADBEEF' var mi:", "DEADBEEF" in ham)
        print("ham govdede 'hf-gizli-token' var mi:", "hf-gizli-token" in ham)

        baslik("C3", "GPU VAR: POST manifest (tgi, vllm port override)")
        print("-- tgi:"); goster(await istemci.post(f"/api/v1/bdm/hazirlama/{bdm_tgi['id']}/manifest", headers=Y))

        # ---------- Durum makinesi: calisiyor iken dogrula ----------
        baslik("D1", "calisiyor BDM: baslat -> durum -> dogrula (BASARILI)")
        print("-- dogrula (hazir'a tasir):")
        goster(await istemci.post(f"/api/v1/bdm/hazirlama/{bdm_ollama['id']}/dogrula", headers=Y))
        print("-- durum:", await durum_oku(istemci, Y, bdm_ollama["id"]))
        print("-- yonetim/baslat:")
        goster(await istemci.post(f"/api/v1/bdm/yonetim/{bdm_ollama['id']}/baslat", headers=Y))
        print("-- yonetim/durum (konteyner calisiyor mu):")
        goster(await istemci.get(f"/api/v1/bdm/yonetim/{bdm_ollama['id']}/durum", headers=Y))
        print("-- tekrar dogrula (BASARILI):")
        goster(await istemci.post(f"/api/v1/bdm/hazirlama/{bdm_ollama['id']}/dogrula", headers=Y))
        print("-- dogrula sonrasi durum:", await durum_oku(istemci, Y, bdm_ollama["id"]))
        print("-- yonetim/durum (konteyner hala calisiyor mu):")
        goster(await istemci.get(f"/api/v1/bdm/yonetim/{bdm_ollama['id']}/durum", headers=Y))
        print("-- yonetim/durdur (calisan konteyner durdurulabiliyor mu):")
        goster(await istemci.post(f"/api/v1/bdm/yonetim/{bdm_ollama['id']}/durdur", headers=Y))
        print("-- durdur sonrasi dogrudan surucu sagligi:")
        goster(await istemci.get(f"/api/v1/bdm/yonetim/{bdm_ollama['id']}/saglik", headers=Y))

        baslik("D2", "calisiyor BDM: adres degisir -> dogrula (BASARISIZ)")
        bdm_kapali = await bdm_olustur(istemci, jeton, "Kapali Ollama", "asgi-kapali", "ollama",
                                       SAHTE, "sahte-model-kucuk")
        print("-- ilk dogrula (calisan upstream, hazir):")
        goster(await istemci.post(f"/api/v1/bdm/hazirlama/{bdm_kapali['id']}/dogrula", headers=Y))
        print("-- baslat:")
        goster(await istemci.post(f"/api/v1/bdm/yonetim/{bdm_kapali['id']}/baslat", headers=Y))
        print("-- durum:", await durum_oku(istemci, Y, bdm_kapali["id"]))
        print("-- PATCH temel_url -> kapali port (8198):")
        goster(await istemci.patch(f"/api/v1/bdm/{bdm_kapali['id']}", headers=Y,
                                   json={"temel_url": "http://127.0.0.1:8198/v1"}))
        print("-- dogrula (kapali port):")
        goster(await istemci.post(f"/api/v1/bdm/hazirlama/{bdm_kapali['id']}/dogrula", headers=Y))
        print("-- dogrula sonrasi durum:", await durum_oku(istemci, Y, bdm_kapali["id"]))
        print("-- yonetim/durum (konteyner hala calisiyor mu):")
        goster(await istemci.get(f"/api/v1/bdm/yonetim/{bdm_kapali['id']}/durum", headers=Y))
        print("-- yonetim/durdur (calisan konteyner durdurulabiliyor mu):")
        goster(await istemci.post(f"/api/v1/bdm/yonetim/{bdm_kapali['id']}/durdur", headers=Y))
        print("-- yonetim/baslat:"); goster(await istemci.post(f"/api/v1/bdm/yonetim/{bdm_kapali['id']}/baslat", headers=Y))
        print("-- yonetim/yeniden-baslat:"); goster(await istemci.post(f"/api/v1/bdm/yonetim/{bdm_kapali['id']}/yeniden-baslat", headers=Y))
        print("-- yonetim/durum (konteyner son durum):")
        goster(await istemci.get(f"/api/v1/bdm/yonetim/{bdm_kapali['id']}/durum", headers=Y))

        # ---------- SSE hata cercevesi ----------
        baslik("E1", "POST cek — upstream kapali (SSE hata cercevesi)")
        try:
            yanit = await istemci.post(f"/api/v1/bdm/hazirlama/{bdm_kapali['id']}/cek", headers=Y)
            print(f"HTTP {yanit.status_code} {yanit.headers.get('content-type', '')}")
            print("govde uzunlugu:", len(yanit.content))
            print(repr(yanit.text[:1500]))
        except Exception as hata:
            print(f"ISTEMCI ISTISNASI: {type(hata).__name__}: {hata}")

    surucu_ata(None)
    await motoru_sifirla()


if __name__ == "__main__":
    asyncio.run(main())
