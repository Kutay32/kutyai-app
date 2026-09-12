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

#: Tohumlama sirasinda ogrenilen varsayilan organizasyon kimligi.
_varsayilan_org_id: int | None = None


def varsayilan_org_id_ata(deger: int) -> None:
    global _varsayilan_org_id
    _varsayilan_org_id = int(deger)


def varsayilan_org_id() -> int | None:
    return _varsayilan_org_id


def _org_doldur(oturum: Any, *_argumanlar: Any, **_anahtar: Any) -> None:
    """`org_id` zorunlu tablolara dogrudan eklenen nesneleri varsayilana baglar.

    Uygulama kodunun tamami `org_id`yi acikca gecirir; bu kanca yalnizca test,
    tohum ve yardimci betiklerdeki dogrudan ORM eklemelerini guvenli kilar.
    """
    from bdm_veritabani.modeller import ORG_ZORUNLU_TABLOLAR

    for nesne in oturum.new:
        tablo = getattr(nesne, "__tablename__", None)
        if tablo not in ORG_ZORUNLU_TABLOLAR:
            continue
        if getattr(nesne, "org_id", None) is not None:
            continue
        if _varsayilan_org_id is None:  # pragma: no cover - tohumlama atlanirsa
            raise RuntimeError(
                "Varsayılan organizasyon bilinmiyor; org_id'yi açıkça verin "
                "ya da önce tohumlamayı çalıştırın."
            )
        nesne.org_id = _varsayilan_org_id


def _kancalari_kur() -> None:
    from sqlalchemy import event
    from sqlalchemy.orm import Session as SenkronOturum

    if not event.contains(SenkronOturum, "before_flush", _org_doldur):
        event.listen(SenkronOturum, "before_flush", _org_doldur)


_kancalari_kur()


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
