"""create short_urls table

Revision ID: 0001
Revises:
Create Date: 2026-09-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "short_urls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("short_code", sa.String(length=32), nullable=True),
        sa.Column("long_url", sa.String(length=2048), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("click_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_short_urls_short_code", "short_urls", ["short_code"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_short_urls_short_code", table_name="short_urls")
    op.drop_table("short_urls")
