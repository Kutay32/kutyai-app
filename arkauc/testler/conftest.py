"""Ortak test altyapisi — DONDURULMUS.

Ortam degiskenleri, uygulama import edilmeden ONCE ayarlanir; boylece
`ayarlar` tekili test veritabanina baglanir. Her test kendi gecici SQLite
dosyasini sifirlar.
"""

from __future__ import annotations

import os
import pathlib
import sys
import tempfile

KOK = pathlib.Path(__file__).resolve().parents[2]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

_TMP = pathlib.Path(tempfile.mkdtemp(prefix="kutyai-test-"))
os.environ["KUTYAI_ORTAM"] = "test"
os.environ["KUTYAI_VERITABANI_URL"] = f"sqlite+aiosqlite:///{(_TMP / 'test.db').as_posix()}"
os.environ["KUTYAI_GIZLI_ANAHTAR"] = "test-gizli-anahtar-degeri-0123456789"
os.environ["KUTYAI_SIFRELEME_ANAHTARI"] = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
os.environ["KUTYAI_MASKELEME_AKTIF"] = "true"
# Oran sinirlayici testlerde devre disi sayilir: her test izole edilir ve
# limitler yuksek tutulur; sinirlayiciya ozel testler kendi limitini kurar.
os.environ["KUTYAI_ORAN_SINIRI_ISTEK_DK"] = "100000"
os.environ["KUTYAI_ORAN_SINIRI_KIMLIK_DK"] = "100000"

from datetime import datetime, timezone  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402

from arkauc.app.cekirdek import guvenlik  # noqa: E402
from arkauc.app.cekirdek.organizasyon import varsayilan_uyelik_ekle  # noqa: E402
from bdm_listesi.katalog import slug_uret  # noqa: E402
from bdm_veritabani.modeller import (  # noqa: E402
    AnahtarDurumu,
    ApiAnahtari,
    Kullanici,
    KullaniciDurumu,
    Organizasyon,
    Rol,
    Uyelik,
    UyelikDurumu,
    UyelikRolu,
)
from bdm_veritabani.oturum import (  # noqa: E402
    motoru_sifirla,
    oturum_fabrikasi,
    tablolari_olustur,
    tablolari_sil,
)
from bdm_veritabani.tohum import tohumla  # noqa: E402

VARSAYILAN_PAROLA = "Parola123!"


@pytest.fixture(autouse=True)
async def veritabani():
    """Her test icin temiz sema + tohum verisi."""
    from arkauc.app.cekirdek.oran_siniri import sinirlayiciyi_sifirla

    await motoru_sifirla()
    sinirlayiciyi_sifirla()
    await tablolari_olustur()
    await tohumla()
    yield
    sinirlayiciyi_sifirla()
    await tablolari_sil()
    await motoru_sifirla()


@pytest.fixture
def uygulama():
    from arkauc.app.main import uygulama_olustur

    return uygulama_olustur()


@pytest.fixture
async def istemci(uygulama, veritabani):
    tasima = httpx.ASGITransport(app=uygulama)
    async with httpx.AsyncClient(transport=tasima, base_url="http://test") as c:
        yield c


class Yardimci:
    """Testlerde kullanici, jeton ve API anahtari uretir."""

    def __init__(self) -> None:
        self.sayac = 0

    async def kullanici_ekle(
        self,
        eposta: str | None = None,
        *,
        parola: str = VARSAYILAN_PAROLA,
        rol: Rol = Rol.son_kullanici,
        durum: KullaniciDurumu = KullaniciDurumu.aktif,
        dogrulandi: bool = True,
        ad_soyad: str = "Test Kullanıcı",
    ) -> Kullanici:
        self.sayac += 1
        eposta = eposta or f"test{self.sayac}@kutyai.local"
        async with oturum_fabrikasi()() as oturum:
            kullanici = Kullanici(
                eposta=eposta.lower(),
                ad_soyad=ad_soyad,
                sifre_hash=guvenlik.sifre_hashle(parola),
                rol=rol,
                durum=durum,
                eposta_dogrulandi=dogrulandi,
            )
            oturum.add(kullanici)
            await oturum.flush()
            await varsayilan_uyelik_ekle(oturum, kullanici)
            await oturum.commit()
            await oturum.refresh(kullanici)
            return kullanici

    async def organizasyon(
        self, ad: str = "Test Organizasyon", *, sahibi: Kullanici | None = None
    ) -> Organizasyon:
        """Yeni organizasyon; `sahibi` verilmezse yeni bir sahip kullanicisi uretir."""
        async with oturum_fabrikasi()() as oturum:
            sahip = sahibi or await self.kullanici_ekle(rol=Rol.yonetici)
            organizasyon = Organizasyon(ad=ad, slug=slug_uret(ad))
            oturum.add(organizasyon)
            await oturum.flush()
            oturum.add(
                Uyelik(
                    organizasyon_id=organizasyon.id,
                    kullanici_id=sahip.id,
                    rol=UyelikRolu.sahip,
                    durum=UyelikDurumu.aktif,
                )
            )
            await oturum.commit()
            await oturum.refresh(organizasyon)
            return organizasyon

    async def uye_yap(
        self, organizasyon: Organizasyon, kullanici: Kullanici, rol: UyelikRolu = UyelikRolu.son_kullanici
    ) -> Uyelik:
        async with oturum_fabrikasi()() as oturum:
            uyelik = Uyelik(
                organizasyon_id=organizasyon.id,
                kullanici_id=kullanici.id,
                rol=rol,
                durum=UyelikDurumu.aktif,
            )
            oturum.add(uyelik)
            await oturum.commit()
            await oturum.refresh(uyelik)
            return uyelik

    async def yonetici(self, **kwargs) -> Kullanici:
        return await self.kullanici_ekle(rol=Rol.yonetici, **kwargs)

    async def anahtar_ekle(
        self,
        ad: str = "Test Anahtarı",
        *,
        izinli_modeller: list[str] | None = None,
        kullanici_id: int | None = None,
        durum: AnahtarDurumu = AnahtarDurumu.aktif,
    ) -> tuple[ApiAnahtari, str]:
        uretilen = guvenlik.api_anahtari_uret()
        async with oturum_fabrikasi()() as oturum:
            anahtar = ApiAnahtari(
                ad=ad,
                onek=uretilen["onek"],
                anahtar_hash=uretilen["hash"],
                son_dort=uretilen["son_dort"],
                kullanici_id=kullanici_id,
                durum=durum,
                izinli_modeller=izinli_modeller or [],
            )
            oturum.add(anahtar)
            await oturum.commit()
            await oturum.refresh(anahtar)
            return anahtar, uretilen["tam"]

    def jeton(self, kullanici: Kullanici) -> str:
        jeton, _ = guvenlik.erisim_jetonu_uret(kullanici.id, kullanici.rol.value)
        return jeton

    def basliklar(self, kullanici: Kullanici) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.jeton(kullanici)}"}

    def org_basliklari(self, kullanici: Kullanici, organizasyon: Organizasyon) -> dict[str, str]:
        """Jeton + `X-Organizasyon` basligi."""
        return {**self.basliklar(kullanici), "X-Organizasyon": organizasyon.slug}

    def anahtar_basliklari(self, tam_anahtar: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {tam_anahtar}"}


@pytest.fixture
def yardimci() -> Yardimci:
    return Yardimci()


@pytest.fixture
def simdi():
    return datetime.now(timezone.utc)
