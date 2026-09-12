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
from bdm_veritabani.modeller import (
    PERSONEL_ROLLERI,
    AnahtarDurumu,
    ApiAnahtari,
    Kullanici,
    KullaniciDurumu,
    Rol,
)
from bdm_veritabani.oturum import oturum_uret

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
    roller: tuple[Rol, ...] = PERSONEL_ROLLERI,
) -> Callable[..., Kullanici]:
    """Belirtilen rollerden birini zorunlu kilan bagimlilik uretir."""

    async def _bagimlilik(
        kullanici: Kullanici = Depends(gecerli_kullanici),
    ) -> Kullanici:
        if kullanici.rol not in roller:
            raise YetkiYok()
        return kullanici

    return _bagimlilik


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
        oturum, "api_anahtari.kullanildi", hedef_tur="api_anahtari", hedef_id=anahtar.id
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
