"""add user_id to short_urls

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("short_urls", sa.Column("user_id", sa.String(length=128), nullable=False))
    op.create_index("ix_short_urls_user_id", "short_urls", ["user_id"])
    op.create_unique_constraint(
        "uq_short_urls_user_id_long_url", "short_urls", ["user_id", "long_url"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_short_urls_user_id_long_url", "short_urls", type_="unique")
    op.drop_index("ix_short_urls_user_id", table_name="short_urls")
    op.drop_column("short_urls", "user_id")
