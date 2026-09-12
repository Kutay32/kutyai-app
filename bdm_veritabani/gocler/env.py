"""Alembic ortami — async motor, `ayarlar` tekili ile ayni URL'i kullanir."""

from __future__ import annotations

import asyncio
import pathlib
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

KOK = pathlib.Path(__file__).resolve().parents[2]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

from arkauc.app.cekirdek.ayarlar import ayarlar  # noqa: E402
from bdm_veritabani.modeller import Taban  # noqa: E402

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

hedef_metadata = Taban.metadata


def _url() -> str:
    return ayarlar.veritabani_url_cozum()


def run_migrations_offline() -> None:
    context.configure(
        url=_url(),
        target_metadata=hedef_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _calistir(baglanti) -> None:
    context.configure(
        connection=baglanti, target_metadata=hedef_metadata, render_as_batch=True
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    motor = create_async_engine(_url())
    async with motor.connect() as baglanti:
        await baglanti.run_sync(_calistir)
    await motor.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
