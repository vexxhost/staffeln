from __future__ import annotations

from alembic import op
from oslo_log import log
import sqlalchemy as sa

"""add report timestamp

Revision ID: 5b2e78435231
Revises: 2b2b9df199bd
Create Date: 2023-03-20 12:24:58.084135

"""

# revision identifiers, used by Alembic.
revision = "5b2e78435231"
down_revision = "2b2b9df199bd"

LOG = log.getLogger(__name__)


def upgrade():
    op.create_table(
        "report_timestamp",
        sa.Column(
            "id",
            sa.String(36),
            primary_key=True,
            nullable=False,
            autoincrement=True,
        ),
        sa.Column("created_at", sa.DateTime),
        sa.Column("updated_at", sa.DateTime),
        sa.Column("sender", sa.String(length=255), nullable=True),
        mysql_engine="InnoDB",
        mysql_charset="utf8",
    )


def downgrade():
    try:
        op.drop_table("report_timestamp")
    except Exception:
        LOG.exception("Error Dropping 'report_timestamp' table.")
