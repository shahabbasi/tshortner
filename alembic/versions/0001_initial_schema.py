"""initial schema: short_urls and access_logs

Revision ID: 0001
Revises:
Create Date: 2026-09-13

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
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("original_url", sa.String(length=2048), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("click_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expired_short_code", sa.String(length=32), nullable=True),
    )
    op.create_index("ix_short_urls_short_code", "short_urls", ["short_code"], unique=True)
    op.create_index("ix_short_urls_user_id_original_url", "short_urls", ["user_id", "original_url"], unique=True)
    op.create_index("ix_short_urls_expired_short_code", "short_urls", ["expired_short_code"])

    op.create_table(
        "access_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("short_url_id", sa.Integer(), sa.ForeignKey("short_urls.id"), nullable=False),
        sa.Column("ip_address", sa.String(length=45), nullable=False),
        sa.Column("accessed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_access_logs_short_url_id", "access_logs", ["short_url_id"])


def downgrade() -> None:
    op.drop_table("access_logs")
    op.drop_table("short_urls")
