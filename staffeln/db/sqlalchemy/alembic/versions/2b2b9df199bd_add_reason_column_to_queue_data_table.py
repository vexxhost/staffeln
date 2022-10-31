"""Add reason column to queue_data table

Revision ID: 2b2b9df199bd
Revises: 003102f08f66
Create Date: 2022-11-02 06:14:09.348932

"""

# revision identifiers, used by Alembic.
revision = '2b2b9df199bd'
down_revision = '003102f08f66'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column(
        "queue_data",
        sa.Column("reason", sa.String(length=255), nullable=True)
    )
