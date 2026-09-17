"""Kimlik dogrulama bagimliliklari (spec §9).

`gecerli_kullanici` yalniz JWT kabul eder; `gecerli_istemci` hem JWT hem
`kuty_` API anahtarini kabul eder (sohbet uclari icin).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from datetime import datetime, timezone

import sqlalchemy as sa
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek import guvenlik
from arkauc.app.cekirdek.hatalar import (
    AnahtarGecersiz,
    EpostaDogrulanmadi,
    JetonGecersiz,
    KimlikGerekli,
    YetkiYok,
)
from arkauc.app.cekirdek.organizasyon import (
    ORG_BASLIGI,
    organizasyon_coz,
    rol_yetkili_mi,
    uyelik_getir,
    uyelik_rolleri,
)
from bdm_veritabani.modeller import (
    PERSONEL_ROLLERI,
    PERSONEL_UYELIK_ROLLERI,
    AnahtarDurumu,
    ApiAnahtari,
    Kullanici,
    KullaniciDurumu,
    Organizasyon,
    Rol,
    UyelikDurumu,
    UyelikRolu,
)
from bdm_veritabani.oturum import oturum_uret

from fastapi import Request

_bearer = HTTPBearer(auto_error=False)

KimlikBilgisi = HTTPAuthorizationCredentials | None


@dataclass(slots=True)
class IstemciKimligi:
    """Sohbet uclarina erisen istemci: panel/kullanici ya da API anahtari."""

    tur: str
    kullanici: Kullanici | None = None
    anahtar: ApiAnahtari | None = None

    @property
    def kullanici_id(self) -> int | None:
        return self.kullanici.id if self.kullanici else None

    @property
    def anahtar_id(self) -> int | None:
        return self.anahtar.id if self.anahtar else None

    @property
    def etiket(self) -> str:
        if self.kullanici:
            return self.kullanici.eposta
        if self.anahtar:
            return self.anahtar.ad
        return "bilinmeyen"


async def veritabani_oturumu() -> AsyncIterator[AsyncSession]:
    async for oturum in oturum_uret():
        yield oturum


async def _jetonla_kullanici(jeton: str, oturum: AsyncSession) -> Kullanici:
    govde = guvenlik.jeton_coz(jeton)
    kullanici = await oturum.get(Kullanici, int(govde["sub"]))
    if kullanici is None:
        raise JetonGecersiz()
    if kullanici.durum == KullaniciDurumu.pasif:
        raise YetkiYok("Hesabınız devre dışı bırakılmış.")
    return kullanici


async def gecerli_kullanici(
    oturum: AsyncSession = Depends(veritabani_oturumu),
    kimlik: KimlikBilgisi = Depends(_bearer),
) -> Kullanici:
    if kimlik is None or not kimlik.credentials:
        raise KimlikGerekli()
    return await _jetonla_kullanici(kimlik.credentials, oturum)


def gecerli_personel(
    roller: tuple[Rol | UyelikRolu, ...] = PERSONEL_UYELIK_ROLLERI,
) -> Callable[..., Kullanici]:
    """Belirtilen organizasyon rollerinden birini zorunlu kilan bagimlilik.

    Yetki karari aktif organizasyondaki **uyelik** rolu uzerinden verilir;
    `sahip` her zaman yetkilidir. `Rol` degerleri geriye uyumluluk icin kabul
    edilir ve `UyelikRolu`ne cevrilir.
    """

    izinli = uyelik_rolleri(tuple(roller))

    async def _bagimlilik(
        kullanici: Kullanici = Depends(gecerli_kullanici),
        organizasyon: Organizasyon = Depends(aktif_organizasyon),
        oturum: AsyncSession = Depends(veritabani_oturumu),
    ) -> Kullanici:
        uyelik = await uyelik_getir(oturum, organizasyon.id, kullanici.id)
        if uyelik is None or uyelik.durum != UyelikDurumu.aktif:
            raise YetkiYok()
        if not rol_yetkili_mi(uyelik.rol, izinli):
            raise YetkiYok()
        return kullanici

    return _bagimlilik


async def _jeton_org(kimlik: KimlikBilgisi) -> int | None:
    """Erisim jetonundaki `org` claim'i (yoksa None)."""
    if kimlik is None or not kimlik.credentials:
        return None
    jeton = kimlik.credentials
    if jeton.startswith(guvenlik.API_ONEK):
        return None
    try:
        govde = guvenlik.jeton_coz(jeton)
    except Exception:
        return None
    deger = govde.get("org")
    return int(deger) if deger is not None else None


async def aktif_organizasyon(
    istek: Request,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    kullanici: Kullanici = Depends(gecerli_kullanici),
    kimlik: KimlikBilgisi = Depends(_bearer),
) -> Organizasyon:
    """Panel/kullanici uclari icin aktif organizasyon."""
    return await organizasyon_coz(
        oturum,
        baslik=istek.headers.get(ORG_BASLIGI),
        org_claim=await _jeton_org(kimlik),
        kullanici_id=kullanici.id,
        varsayilana_ekle=True,
    )


async def _anahtarla_istemci(jeton: str, oturum: AsyncSession) -> IstemciKimligi:
    from arkauc.app.cekirdek.denetim import islem_kaydet  # dongusel import onlemi

    anahtar = (
        await oturum.execute(
            sa.select(ApiAnahtari).where(ApiAnahtari.anahtar_hash == guvenlik.ozet(jeton))
        )
    ).scalar_one_or_none()
    if anahtar is None:
        raise AnahtarGecersiz()
    if anahtar.durum != AnahtarDurumu.aktif:
        raise AnahtarGecersiz("API anahtarı iptal edilmiş.")
    anahtar.son_kullanim = datetime.now(timezone.utc)
    await islem_kaydet(
        oturum,
        "api_anahtari.kullanildi",
        org_id=anahtar.org_id,
        hedef_tur="api_anahtari",
        hedef_id=anahtar.id,
    )
    return IstemciKimligi(tur="anahtar", anahtar=anahtar)


async def gecerli_istemci(
    oturum: AsyncSession = Depends(veritabani_oturumu),
    kimlik: KimlikBilgisi = Depends(_bearer),
) -> IstemciKimligi:
    if kimlik is None or not kimlik.credentials:
        raise KimlikGerekli()
    jeton = kimlik.credentials
    if jeton.startswith(guvenlik.API_ONEK):
        return await _anahtarla_istemci(jeton, oturum)
    kullanici = await _jetonla_kullanici(jeton, oturum)
    if kullanici.rol == Rol.son_kullanici and not kullanici.eposta_dogrulandi:
        raise EpostaDogrulanmadi()
    return IstemciKimligi(tur="kullanici", kullanici=kullanici)


async def istemci_organizasyonu(
    istek: Request,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    istemci: IstemciKimligi = Depends(gecerli_istemci),
    kimlik: KimlikBilgisi = Depends(_bearer),
) -> Organizasyon:
    """Sohbet uclari icin aktif organizasyon (JWT veya API anahtari)."""
    return await organizasyon_coz(
        oturum,
        baslik=istek.headers.get(ORG_BASLIGI),
        org_claim=await _jeton_org(kimlik),
        kullanici_id=istemci.kullanici_id,
        anahtar=istemci.anahtar,
        varsayilana_ekle=True,
    )
