#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
"""Add volume_name and instance_name to queue_data

Revision ID: 041d9a0f1159
Revises:
Create Date: 2022-06-14 20:28:40

"""

# revision identifiers, used by Alembic.
revision = "041d9a0f1159"
down_revision = ""

import sqlalchemy as sa  # noqa: E402
from alembic import op  # noqa: E402


def upgrade():
    op.add_column(
        "queue_data", sa.Column("volume_name", sa.String(length=100), nullable=True)
    )
    op.add_column(
        "queue_data", sa.Column("instance_name", sa.String(length=100), nullable=True)
    )
