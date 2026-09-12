"""Docker konteyner surucusu (spec §10).

Senkron `docker` SDK'si `asyncio.to_thread` ile sarmalanir; boylece FastAPI
olay dongusu bloklanmaz. Surucu, `konteyner.py` icindeki `KonteynerSurucusu`
sozlesmesini uygular.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
from collections.abc import AsyncIterator
from typing import Any

import httpx

from arkauc.app.cekirdek.ayarlar import ayarlar
from arkauc.app.cekirdek.hatalar import GecersizIstek, SurucuYok
from arkauc.app.servisler.konteyner import SaglikDurumu, SurucuDurumu

logger = logging.getLogger("kutyai.konteyner.docker")

SAGLIK_ZAMAN_ASIMI = 5.0
DURDURMA_ZAMAN_ASIMI = 10


class DockerSurucusu:
    """Docker SDK tabanli surucu: imaj cekme, port/GPU eslemesi, saglik sondasi."""

    ad = "docker"

    def __init__(self) -> None:
        self._istemci: Any = None
        # konteyner kimliği → manifest'teki sağlık adresi (etiket yoksa yedek)
        self._saglik_adresleri: dict[str, str] = {}

    # -- altyapi -------------------------------------------------------------

    def istemci(self) -> Any:
        """Docker istemcisini dondurur; erisilemiyorsa `SurucuYok` firlatir.

        `KUTYAI_DOCKER_SOKETI` tanimliysa istemci o adrese baglanir (uretimde
        soket bir vekil arkasinda olabilir); bos ise ortam varsayilanlari kullanilir.
        """
        if self._istemci is None:
            try:
                import docker
            except ImportError as hata:
                raise SurucuYok(
                    "Docker SDK kurulu değil. `pip install docker` ile kurup tekrar deneyin."
                ) from hata
            try:
                soket = str(ayarlar.docker_soketi or "").strip()
                if soket:
                    self._istemci = docker.DockerClient(base_url=soket)
                else:
                    self._istemci = docker.from_env()
            except Exception as hata:
                raise SurucuYok(
                    "Docker çalışma zamanına ulaşılamadı. Docker kurulu ve çalışır durumda olmalıdır."
                ) from hata
        return self._istemci

    def _konteyner(self, konteyner_id: str, *, zorunlu: bool = True) -> Any:
        istemci = self.istemci()
        try:
            return istemci.containers.get(konteyner_id)
        except Exception as hata:
            if not zorunlu:
                return None
            raise SurucuYok("Konteyner bulunamadı.", {"konteyner_id": konteyner_id}) from hata

    # -- yetenekler ----------------------------------------------------------

    async def durum(self) -> SurucuDurumu:
        return await asyncio.to_thread(self._durum)

    def _durum(self) -> SurucuDurumu:
        istemci = self.istemci()
        try:
            istemci.ping()
        except SurucuYok:
            raise
        except Exception as hata:
            raise SurucuYok(
                "Docker çalışma zamanına ulaşılamadı. Docker kurulu ve çalışır durumda olmalıdır."
            ) from hata
        bilgi = istemci.info()
        gpu_var, gpu_listesi = self._gpu_bilgisi(bilgi)
        surum = ""
        try:
            surum = str(istemci.version().get("Version", ""))
        except Exception:  # pragma: no cover - surum okunamazsa bos kalir
            surum = ""
        return SurucuDurumu(
            surucu_adi=self.ad,
            docker_var=True,
            gpu_var=gpu_var,
            gpu_listesi=gpu_listesi,
            image_onbellek=self._image_adlari(istemci),
            surum=surum,
            mesaj="" if gpu_var else "GPU çalışma zamanı bulunamadı; vLLM/TGI gibi GPU gerektiren sağlayıcılar başlatılamaz.",
        )

    @staticmethod
    def _gpu_bilgisi(bilgi: dict[str, Any]) -> tuple[bool, list[str]]:
        """nvidia-smi ciktisi ve Docker nvidia calisma zamani ile GPU tespiti."""
        adlar = DockerSurucusu._nvidia_gpu_adlari()
        calisma_zamanlari = bilgi.get("Runtimes") or {}
        nvidia_var = any("nvidia" in str(ad).lower() for ad in calisma_zamanlari)
        return bool(adlar) or nvidia_var, adlar

    @staticmethod
    def _nvidia_gpu_adlari() -> list[str]:
        try:
            cikti = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return []
        if cikti.returncode != 0:
            return []
        return [satir.strip() for satir in cikti.stdout.splitlines() if satir.strip()]

    @staticmethod
    def _image_adlari(istemci: Any) -> list[str]:
        try:
            imajlar = istemci.images.list()
        except Exception:  # pragma: no cover - altyapi arizasi
            return []
        adlar: list[str] = []
        for imaj in imajlar:
            for etiket in getattr(imaj, "tags", None) or []:
                if etiket and etiket not in adlar:
                    adlar.append(str(etiket))
        return sorted(adlar)

    # -- konteyner islemleri -------------------------------------------------

    async def baslat(self, bdm: dict[str, Any], manifest: dict[str, Any]) -> str:
        return await asyncio.to_thread(self._baslat, bdm, manifest)

    def _baslat(self, bdm: dict[str, Any], manifest: dict[str, Any]) -> str:
        istemci = self.istemci()
        image = str(manifest.get("image") or "").strip()
        if not image:
            raise GecersizIstek("Manifest konteyner imajı içermiyor.", {"alan": "image"})
        if not self._image_var_mi(istemci, image):
            try:
                istemci.images.pull(image)
            except Exception as hata:
                logger.exception("'%s' imajı çekilemedi.", image)
                raise SurucuYok("Konteyner imajı çekilemedi.", {"image": image}) from hata

        ayarlar: dict[str, Any] = {
            "detach": True,
            "environment": {str(a): str(b) for a, b in (manifest.get("ortam") or {}).items()},
            "labels": self._etiketler(bdm, manifest),
            "name": self._konteyner_adi(bdm),
        }
        port = manifest.get("port")
        if port:
            ayarlar["ports"] = {f"{int(port)}/tcp": int(port)}
        komut = manifest.get("komut")
        if komut:
            ayarlar["command"] = [str(parca) for parca in komut] if isinstance(komut, (list, tuple)) else [str(komut)]
        bellek_gb = manifest.get("bellek_gb")
        if bellek_gb:
            ayarlar["mem_limit"] = f"{int(bellek_gb)}g"
        birimler = self._birimler(manifest)
        if birimler:
            ayarlar["volumes"] = birimler
        if manifest.get("gpu"):
            from docker.types import DeviceRequest

            ayarlar["device_requests"] = [DeviceRequest(capabilities=[["gpu"]], count=-1)]

        try:
            konteyner = istemci.containers.run(image, **ayarlar)
        except Exception as hata:
            if not self._ad_cakismasi_mi(hata):
                logger.exception("Konteyner başlatılamadı (%s).", ayarlar["name"])
                raise SurucuYok(
                    "Konteyner başlatılamadı.", {"image": image, "ad": ayarlar["name"]}
                ) from hata
            logger.warning("Aynı adlı konteyner kaldırılıp yeniden oluşturuluyor: %s", ayarlar["name"])
            self._ad_cakismasini_gider(istemci, ayarlar["name"])
            try:
                konteyner = istemci.containers.run(image, **ayarlar)
            except Exception as hata:
                logger.exception("Konteyner yeniden oluşturulamadı (%s).", ayarlar["name"])
                raise SurucuYok(
                    "Konteyner başlatılamadı.", {"image": image, "ad": ayarlar["name"]}
                ) from hata
        kimlik = str(konteyner.id)
        saglik_url = str(manifest.get("saglik_url") or "")
        if saglik_url:
            self._saglik_adresleri[kimlik] = saglik_url
        return kimlik

    async def durdur(self, konteyner_id: str) -> None:
        await asyncio.to_thread(self._durdur, konteyner_id)

    def _durdur(self, konteyner_id: str) -> None:
        konteyner = self._konteyner(konteyner_id, zorunlu=False)
        if konteyner is None:
            logger.warning("Durdurulacak konteyner bulunamadı: %s", konteyner_id)
            return
        try:
            konteyner.stop(timeout=DURDURMA_ZAMAN_ASIMI)
        except Exception as hata:
            logger.exception("Konteyner durdurulamadı (%s).", konteyner_id)
            raise SurucuYok(
                "Konteyner durdurulamadı.", {"konteyner_id": konteyner_id}
            ) from hata

    async def sil(self, konteyner_id: str) -> None:
        await asyncio.to_thread(self._sil, konteyner_id)

    def _sil(self, konteyner_id: str) -> None:
        self._saglik_adresleri.pop(konteyner_id, None)
        konteyner = self._konteyner(konteyner_id, zorunlu=False)
        if konteyner is None:
            return
        try:
            konteyner.remove(force=True)
        except Exception as hata:
            logger.exception("Konteyner silinemedi (%s).", konteyner_id)
            raise SurucuYok("Konteyner silinemedi.", {"konteyner_id": konteyner_id}) from hata

    async def saglik(self, konteyner_id: str) -> SaglikDurumu:
        return await asyncio.to_thread(self._saglik, konteyner_id)

    def _saglik(self, konteyner_id: str) -> SaglikDurumu:
        konteyner = self._konteyner(konteyner_id, zorunlu=False)
        if konteyner is None:
            return SaglikDurumu(
                calisiyor=False,
                hazir=False,
                mesaj="Konteyner bulunamadı.",
                ayrinti={"konteyner_id": konteyner_id},
            )
        try:
            konteyner.reload()
            durum = str(konteyner.status or "")
        except Exception as hata:
            logger.exception("Konteyner durumu okunamadı (%s).", konteyner_id)
            return SaglikDurumu(
                calisiyor=False,
                hazir=False,
                mesaj="Konteyner durumu okunamadı.",
                ayrinti={"konteyner_id": konteyner_id},
            )
        calisiyor = durum == "running"
        ayrinti: dict[str, Any] = {"konteyner_id": konteyner_id, "durum": durum}
        saglik_url = str((getattr(konteyner, "labels", None) or {}).get("kutyai.saglik_url", "") or "")
        if not saglik_url:
            # Eski ya da etiketsiz konteynerler için manifest'ten hatırlanan adres.
            saglik_url = self._saglik_adresleri.get(konteyner_id, "")
        if saglik_url:
            ayrinti["saglik_url"] = saglik_url
        if saglik_url and calisiyor:
            hazir, mesaj = self._http_sondasi(saglik_url)
            ayrinti["saglik_kaynagi"] = "saglik_url"
            return SaglikDurumu(calisiyor=calisiyor, hazir=hazir, mesaj=mesaj, ayrinti=ayrinti)
        # Sağlık adresi yoksa `hazir` yalnızca konteyner durumundan türetilir.
        ayrinti["saglik_kaynagi"] = "konteyner_durumu"
        if not saglik_url:
            ayrinti["saglik_url_yok"] = True
        return SaglikDurumu(
            calisiyor=calisiyor,
            hazir=calisiyor,
            mesaj="Çalışıyor." if calisiyor else "Durduruldu.",
            ayrinti=ayrinti,
        )

    @staticmethod
    def _http_sondasi(url: str) -> tuple[bool, str]:
        try:
            yanit = httpx.get(url, timeout=SAGLIK_ZAMAN_ASIMI)
        except Exception:
            logger.exception("Sağlık adresine ulaşılamadı (%s).", url)
            return False, "Sağlık adresine ulaşılamadı."
        if yanit.status_code < 400:
            return True, "Çalışıyor."
        return False, f"Sağlık adresi {yanit.status_code} döndü."

    async def gunlukler(self, konteyner_id: str, satir: int = 200) -> AsyncIterator[str]:
        konteyner = await asyncio.to_thread(self._konteyner, konteyner_id)
        akis = await asyncio.to_thread(
            lambda: konteyner.logs(stream=True, tail=max(1, int(satir)))
        )
        try:
            while True:
                parca = await asyncio.to_thread(next, akis, None)
                if parca is None:
                    break
                yield parca.decode("utf-8", errors="replace").rstrip("\r\n")
        finally:
            kapat = getattr(akis, "close", None)
            if kapat is not None:
                await asyncio.to_thread(kapat)

    # -- yardimcilar ---------------------------------------------------------

    @staticmethod
    def _birimler(manifest: dict[str, Any]) -> dict[str, dict[str, str]]:
        """Manifest `birimler` alanını `containers.run(volumes=...)` sözlüğüne çevirir.

        Kaynak yollar Docker'a **olduğu gibi** geçirilir: Windows biçimli yollar
        (`E:/...` ya da `E:\\...`) Docker Desktop'ın kendi yol eşlemesiyle
        çözülür, bu yüzden burada yol dönüşümü/normalizasyonu yapılmaz. `hedef`
        ya da `kaynak` taşımayan girdiler atlanır (uyarı loglanır).
        """
        birimler: dict[str, dict[str, str]] = {}
        for birim in manifest.get("birimler") or []:
            if not isinstance(birim, dict):
                logger.warning("Manifest birim girdisi sözlük değil, atlandı: %r", birim)
                continue
            kaynak = str(birim.get("kaynak") or "").strip()
            hedef = str(birim.get("hedef") or "").strip()
            if not kaynak or not hedef:
                logger.warning("Manifest birimi kaynak/hedef içermiyor, atlandı: %r", birim)
                continue
            birimler[kaynak] = {"bind": hedef, "mode": str(birim.get("mod") or "rw")}
        return birimler

    @staticmethod
    def _konteyner_adi(bdm: dict[str, Any]) -> str:
        return f"kutyai-{bdm.get('slug') or 'bdm'}"

    @staticmethod
    def _etiketler(bdm: dict[str, Any], manifest: dict[str, Any]) -> dict[str, str]:
        etiketler = {"kutyai.bdm": str(bdm.get("slug") or "")}
        if manifest.get("saglik_url"):
            etiketler["kutyai.saglik_url"] = str(manifest["saglik_url"])
        return etiketler

    @staticmethod
    def _image_var_mi(istemci: Any, image: str) -> bool:
        try:
            istemci.images.get(image)
        except Exception:
            return False
        return True

    @staticmethod
    def _ad_cakismasi_mi(hata: Exception) -> bool:
        metin = f"{getattr(hata, 'explanation', '') or ''} {hata}".lower()
        return "conflict" in metin or "already in use" in metin

    @staticmethod
    def _ad_cakismasini_gider(istemci: Any, ad: str) -> None:
        try:
            eski = istemci.containers.get(ad)
            eski.remove(force=True)
        except Exception as hata:  # pragma: no cover - temizlik en iyi caba
            logger.warning("Eski konteyner kaldırılamadı (%s): %s", ad, hata)
