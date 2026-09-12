"""ilk_sema

Revision ID: 0001_ilk_sema
Revizyon: spec §4'teki 12 tablo.
"""

from __future__ import annotations

from alembic import op

from bdm_veritabani.modeller import Taban

revision = "0001_ilk_sema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Taban.metadata.create_all(op.get_bind())


def downgrade() -> None:
    Taban.metadata.drop_all(op.get_bind())
