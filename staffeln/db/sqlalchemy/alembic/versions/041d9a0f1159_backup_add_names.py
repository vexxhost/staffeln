"""Add volume_name and instance_name to queue_data

Revision ID: 041d9a0f1159
Revises:
Create Date: 2022-06-14 20:28:40

"""

# revision identifiers, used by Alembic.
from __future__ import annotations

revision = "041d9a0f1159"
down_revision = ""

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402


def upgrade():
    op.add_column(
        "queue_data",
        sa.Column("volume_name", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "queue_data",
        sa.Column("instance_name", sa.String(length=100), nullable=True),
    )
