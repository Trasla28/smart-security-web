"""add_google_sub_to_users

Adds google_sub (TEXT NULL) to users for Google OAuth identity linking.

Revision ID: 005
Revises: 004
Create Date: 2026-05-07 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("google_sub", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "google_sub")
