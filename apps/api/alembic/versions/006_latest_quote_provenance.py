"""persist latest quote provenance snapshots

Revision ID: 006
Revises: 005
Create Date: 2026-07-26 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "latest_market_quotes",
        sa.Column("source_label", sa.String(128), nullable=True),
    )
    op.execute(
        "UPDATE latest_market_quotes SET source_label = provider_key WHERE source_label IS NULL",
    )
    op.alter_column("latest_market_quotes", "source_label", nullable=False)


def downgrade() -> None:
    op.drop_column("latest_market_quotes", "source_label")
