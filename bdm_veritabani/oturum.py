"""Async veritabani oturumu ve sema yardimcilari.

Motor tembel olusturulur; boylece testler ortam degiskenlerini import
oncesinde ayarlayabilir. SQLite icin NullPool kullanilir (testlerde her test
kendi olay dongusunu kurar).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from bdm_veritabani.modeller import Taban

_motor: Any = None
_uretici: async_sessionmaker[AsyncSession] | None = None


def motor() -> Any:
    """Tekil async motoru dondurur (gerekiyorsa olusturur)."""
    global _motor, _uretici
    if _motor is None:
        from arkauc.app.cekirdek.ayarlar import ayarlar

        url = ayarlar.veritabani_url_cozum()
        secenekler: dict[str, Any] = {"echo": False, "future": True}
        if url.startswith("sqlite"):
            secenekler["poolclass"] = NullPool
            secenekler["connect_args"] = {"timeout": 30}
        else:
            secenekler["pool_pre_ping"] = True
        _motor = create_async_engine(url, **secenekler)
        if url.startswith("sqlite"):
            _yabanci_anahtar_zorla(_motor.sync_engine)
        _uretici = async_sessionmaker(_motor, class_=AsyncSession, expire_on_commit=False)
    return _motor


def _yabanci_anahtar_zorla(senkron_motor: Any) -> None:
    """SQLite baglantilarinda FOREIGN KEY zorlamasini acar.

    SQLite varsayilan olarak yabanci anahtarlari yok sayar; bu olmadan
    `ON DELETE CASCADE`/`RESTRICT` kurallari sessizce devre disi kalir ve
    yetim kayitlar olusur.
    """
    from sqlalchemy import event

    @event.listens_for(senkron_motor, "connect")
    def _ac(dbapi_baglanti: Any, _kayit: Any) -> None:  # pragma: no cover - surucu kancasi
        imlec = dbapi_baglanti.cursor()
        imlec.execute("PRAGMA foreign_keys=ON")
        imlec.close()


def oturum_fabrikasi() -> async_sessionmaker[AsyncSession]:
    motor()
    assert _uretici is not None
    return _uretici


async def oturum_uret() -> AsyncIterator[AsyncSession]:
    """FastAPI bagimliligi: istek basina tek oturum."""
    async with oturum_fabrikasi()() as oturum:
        try:
            yield oturum
            await oturum.commit()
        except Exception:
            await oturum.rollback()
            raise


async def tablolari_olustur() -> None:
    """Sema yoksa olusturur (gelistirme/kurulum kolayligi)."""
    async with motor().begin() as baglanti:
        await baglanti.run_sync(Taban.metadata.create_all)


async def tablolari_sil() -> None:
    async with motor().begin() as baglanti:
        await baglanti.run_sync(Taban.metadata.drop_all)


async def motoru_sifirla() -> None:
    """Motoru kapatir ve unutur (testler arasi izolasyon)."""
    global _motor, _uretici
    if _motor is not None:
        await _motor.dispose()
    _motor = None
    _uretici = None
