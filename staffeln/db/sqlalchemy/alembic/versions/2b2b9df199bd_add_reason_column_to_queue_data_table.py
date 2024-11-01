"""Add reason column to queue_data table

Revision ID: 2b2b9df199bd
Revises: ebdbed01e9a7
Create Date: 2022-11-02 06:14:09.348932

"""

# revision identifiers, used by Alembic.
from __future__ import annotations

revision = "2b2b9df199bd"
down_revision = "ebdbed01e9a7"

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402


def upgrade():
    op.add_column(
        "queue_data", sa.Column("reason", sa.String(length=255), nullable=True)
    )
