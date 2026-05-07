"""recurring_due_days_and_month

Adds due_days (días para completar) and recurrence_month (para recurrencia anual)
to recurring_templates.

Revision ID: 003
Revises: 002
Create Date: 2026-05-07 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "recurring_templates",
        sa.Column("due_days", sa.Integer(), nullable=True),
    )
    op.add_column(
        "recurring_templates",
        sa.Column("recurrence_month", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("recurring_templates", "recurrence_month")
    op.drop_column("recurring_templates", "due_days")
