"""04 — DockerSurucusu gerçek Docker ile: port eşleme, GPU device request,
sağlık sondası ve günlük akışı.

Küçük bir imaj (`nginx:alpine`) kullanılır; böylece gerçek konteyner yaşam
döngüsü hızlı kanıtlanır.
"""

from __future__ import annotations

import asyncio
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "betikler"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

import httpx  # noqa: E402

from arkauc.app.cekirdek.hatalar import SurucuYok  # noqa: E402
from arkauc.app.servisler.konteyner_docker import DockerSurucusu  # noqa: E402

IMGE = "nginx:alpine"
PORT = 18080


def bdm_sozlugu() -> dict[str, object]:
    return {"id": 0, "slug": "docker-gozlem", "temel_url": "http://127.0.0.1:18080/v1", "upstream_model": "x"}


def manifest(**ek: object) -> dict[str, object]:
    temel: dict[str, object] = {
        "image": IMGE,
        "komut": [],
        "port": PORT,
        "gpu": False,
        "bellek_gb": 1,
        "ortam": {"GOZLEM": "1"},
    }
    temel.update(ek)
    return temel


async def main() -> None:
    surucu = DockerSurucusu()

    print("== 1) durum() ==")
    durum = await surucu.durum()
    print(json.dumps(durum.__dict__ if hasattr(durum, "__dict__") else {
        "surucu": durum.surucu_adi, "docker": durum.docker_var, "gpu": durum.gpu_var,
        "gpu_listesi": durum.gpu_listesi, "image_onbellek": durum.image_onbellek,
        "surum": durum.surum, "mesaj": durum.mesaj}, ensure_ascii=False, indent=2))

    print("\n== 2) gerçek konteyner başlatma (port eşleme + etiket + env + bellek) ==")
    konteyner_id = await surucu.baslat(bdm_sozlugu(), manifest())
    print(f"konteyner_id = {konteyner_id}")

    istemci = surucu.istemci()
    ham = istemci.containers.get(konteyner_id)
    ham.reload()
    denetim = istemci.api.inspect_container(konteyner_id)
    print("PortBindings =", json.dumps(denetim["HostConfig"]["PortBindings"]))
    print("Ports        =", json.dumps(denetim["NetworkSettings"]["Ports"]))
    print("Labels       =", json.dumps(denetim["Config"]["Labels"]))
    print("Env          =", json.dumps(denetim["Config"]["Env"]))
    print("Memory       =", denetim["HostConfig"]["Memory"])
    print("DeviceRequests =", json.dumps(denetim["HostConfig"].get("DeviceRequests")))
    print("Cmd          =", json.dumps(denetim["Config"]["Cmd"]))
    print("Durum        =", denetim["State"]["Status"])

    print("\n== 3) sağlık sondası: manifest'te saglik_url YOK iken ==")
    saglik = await surucu.saglik(konteyner_id)
    print(json.dumps({"calisiyor": saglik.calisiyor, "hazir": saglik.hazir, "mesaj": saglik.mesaj, "ayrinti": saglik.ayrinti}, ensure_ascii=False))
    print("  ayrinti'da saglik_url var mı? ->", "saglik_url" in saglik.ayrinti)

    print("\n== 4) port gerçekten yayınlanıyor mu (HTTP 200 beklenir) ==")
    try:
        yanit = httpx.get(f"http://127.0.0.1:{PORT}/", timeout=10)
        print(f"HTTP {yanit.status_code}; sunucu başlığı={yanit.headers.get('server')}")
    except Exception as hata:
        print(f"ULAŞILAMADI: {hata}")

    print("\n== 5) günlük akışı (gerçek konteyner) ==")
    akis = surucu.gunlukler(konteyner_id, 20)
    satirlar: list[str] = []
    try:
        while len(satirlar) < 5:
            satirlar.append(await asyncio.wait_for(anext(akis), timeout=10))
    except (StopAsyncIteration, asyncio.TimeoutError) as hata:
        print(f"  akış kesildi: {type(hata).__name__}")
    finally:
        await akis.aclose()
    print(f"  okunan satır sayısı = {len(satirlar)}")
    for satir in satirlar[:6]:
        print(f"  | {satir[:120]}")

    print("\n== 6) saglik_url etiketi VAR iken sonda çalışıyor mu (bozuk adres) ==")
    konteyner2 = await surucu.baslat(
        {"id": 0, "slug": "docker-gozlem-2", "temel_url": "x", "upstream_model": "x"},
        manifest(port=18081, saglik_url="http://127.0.0.1:18081/health"),
    )
    saglik2 = await surucu.saglik(konteyner2)
    print(json.dumps({"calisiyor": saglik2.calisiyor, "hazir": saglik2.hazir, "mesaj": saglik2.mesaj, "ayrinti": saglik2.ayrinti}, ensure_ascii=False))

    print("\n== 7) GPU device request gerçekten gönderiliyor mu (gpu=True) ==")
    try:
        konteyner3 = await surucu.baslat(
            {"id": 0, "slug": "docker-gpu-gozlem", "temel_url": "x", "upstream_model": "x"},
            manifest(port=18082, gpu=True),
        )
        print(f"  gpu=True ile başlatıldı: {konteyner3}")
        denetim3 = istemci.api.inspect_container(konteyner3)
        print("  DeviceRequests =", json.dumps(denetim3["HostConfig"].get("DeviceRequests")))
        await surucu.durdur(konteyner3)
        await surucu.sil(konteyner3)
    except SurucuYok as hata:
        print(f"  SurucuYok: {hata.mesaj} / ayrinti={hata.ayrinti}")
    except Exception as hata:
        print(f"  {type(hata).__name__}: {hata}")

    print("\n== 8) durdur + sil ==")
    await surucu.durdur(konteyner_id)
    saglik3 = await surucu.saglik(konteyner_id)
    print("  durdur sonrası saglik:", json.dumps({"calisiyor": saglik3.calisiyor, "mesaj": saglik3.mesaj}, ensure_ascii=False))
    await surucu.durdur(konteyner2)
    await surucu.sil(konteyner_id)
    await surucu.sil(konteyner2)
    try:
        istemci.containers.get(konteyner_id)
        print("  HATA: konteyner hâlâ var")
    except Exception:
        print("  konteyner silindi (containers.get hata verdi)")

    print("\n== 9) olmayan konteyner kimliğiyle durdur/sil/saglik ==")
    await surucu.durdur("boyle-bir-konteyner-yok")
    await surucu.sil("boyle-bir-konteyner-yok")
    s = await surucu.saglik("boyle-bir-konteyner-yok")
    print("  saglik:", json.dumps({"calisiyor": s.calisiyor, "hazir": s.hazir, "mesaj": s.mesaj}, ensure_ascii=False))
    try:
        await anext(surucu.gunlukler("boyle-bir-konteyner-yok", 5))
        print("  gunlukler: beklenmedik şekilde veri döndü")
    except SurucuYok as hata:
        print(f"  gunlukler SurucuYok: {hata.mesaj}")


if __name__ == "__main__":
    asyncio.run(main())
