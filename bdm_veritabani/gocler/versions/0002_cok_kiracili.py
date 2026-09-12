"""cok_kiracili

Revision ID: 0002_cok_kiracili

v1 semasini cok kiracili yapiya yukseltir:
- yeni tablolar (organizasyon, uyelik, plan, abonelik, fatura, dosya, vektor_*,
  arac, arac_cagrisi, sso_*, posta_sablonu)
- mevcut tablolara `org_id` (varsayilan organizasyona baglanir)
- mevcut kullanicilar icin uyelik kaydi

Idempotenttir: taze kurulumda (0001 guncel metadata ile tablolari zaten olusturur)
yalniz varsayilan organizasyon ve uyelikler eklenir.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

from bdm_veritabani.modeller import Taban

revision = "0002_cok_kiracili"
down_revision = "0001_ilk_sema"
branch_labels = None
depends_on = None

ORG_KOLONLU_TABLOLAR: tuple[str, ...] = (
    "bdm",
    "konusma",
    "api_anahtari",
    "islem_kaydi",
    "kullanim_kaydi",
)

YENI_TABLOLAR: tuple[str, ...] = (
    "organizasyon",
    "uyelik",
    "plan",
    "abonelik",
    "fatura",
    "dosya",
    "vektor_belgesi",
    "vektor_parcasi",
    "arac",
    "arac_cagrisi",
    "sso_saglayici",
    "sso_kimlik",
    "posta_sablonu",
)


def _tablolar(bind: sa.engine.Connection) -> set[str]:
    return set(inspect(bind).get_table_names())


def _kolonlar(bind: sa.engine.Connection, tablo: str) -> set[str]:
    return {kolon["name"] for kolon in inspect(bind).get_columns(tablo)}


def _varsayilan_organizasyon(bind: sa.engine.Connection) -> int:
    bind.execute(
        sa.text(
            """
            INSERT INTO organizasyon (ad, slug, durum, olusturulma, guncellenme)
            SELECT :ad, :slug, 'aktif', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            WHERE NOT EXISTS (SELECT 1 FROM organizasyon WHERE slug = :slug)
            """
        ),
        {"ad": "Varsayılan Organizasyon", "slug": "varsayilan"},
    )
    return int(
        bind.execute(
            sa.text("SELECT id FROM organizasyon WHERE slug = 'varsayilan'")
        ).scalar_one()
    )


def _uyelikleri_ekle(bind: sa.engine.Connection, org_id: int) -> None:
    bind.execute(
        sa.text(
            """
            INSERT INTO uyelik (organizasyon_id, kullanici_id, rol, durum, olusturulma)
            SELECT :org,
                   k.id,
                   CASE k.rol WHEN 'yonetici' THEN 'sahip' ELSE k.rol END,
                   CASE WHEN k.durum = 'pasif' THEN 'pasif' ELSE 'aktif' END,
                   CURRENT_TIMESTAMP
            FROM kullanici k
            WHERE NOT EXISTS (
                SELECT 1 FROM uyelik u
                WHERE u.organizasyon_id = :org AND u.kullanici_id = k.id
            )
            """
        ),
        {"org": org_id},
    )


def upgrade() -> None:
    bind = op.get_bind()
    mevcut = _tablolar(bind)

    # 1) Yeni tablolar (checkfirst: taze kurulumda zaten vardir)
    Taban.metadata.create_all(bind, checkfirst=True)

    eksik = [tablo for tablo in YENI_TABLOLAR if tablo not in _tablolar(bind)]
    if eksik:  # pragma: no cover - sema bozuksa
        raise RuntimeError(f"Şu tablolar oluşturulamadı: {', '.join(eksik)}")

    # 2) Varsayilan organizasyon ve mevcut kullanicilar icin uyelik
    org_id = _varsayilan_organizasyon(bind)
    if "kullanici" in _tablolar(bind):
        _uyelikleri_ekle(bind, org_id)

    # 3) org_id kolonlari (mevcut satirlar varsayilan organizasyona baglanir)
    for tablo in ORG_KOLONLU_TABLOLAR:
        if tablo not in mevcut:
            continue
        if "org_id" in _kolonlar(bind, tablo):
            continue
        op.add_column(
            tablo,
            sa.Column(
                "org_id",
                sa.Integer(),
                nullable=False,
                server_default=str(org_id),
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    mevcut = _tablolar(bind)

    # SQLite, foreign key taniminda gecen bir kolonu dogrudan DROP COLUMN ile
    # kaldiramaz; batch (tablo yeniden insa) modu her iki lehcede de calisir.
    for tablo in ORG_KOLONLU_TABLOLAR:
        if tablo in mevcut and "org_id" in _kolonlar(bind, tablo):
            # Batch reflection indeksleri de kopyalar; kolonu dusurmeden once
            # indeksi kaldirmazsak "no such column" hatasi alinir.
            bind.exec_driver_sql(f"DROP INDEX IF EXISTS ix_{tablo}_org_id")
            with op.batch_alter_table(tablo, recreate="always") as batch:
                batch.drop_column("org_id")

    for tablo in reversed(YENI_TABLOLAR):
        if tablo in _tablolar(bind):
            op.drop_table(tablo)
