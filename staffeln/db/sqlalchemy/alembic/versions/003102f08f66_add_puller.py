"""Add puller

Revision ID: 003102f08f66
Revises: 041d9a0f1159
Create Date: 2022-11-02 06:02:21.404596

"""

# revision identifiers, used by Alembic.
revision = '003102f08f66'
down_revision = '041d9a0f1159'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'puller',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('node_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True)
    )
