"""fix_if_holiday_action_length

Amplía if_holiday_action de VARCHAR(20) a VARCHAR(30) para acomodar
"previous_business_day" (21 caracteres).

Revision ID: 004
Revises: 003
Create Date: 2026-05-07 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "recurring_templates",
        "if_holiday_action",
        existing_type=sa.String(20),
        type_=sa.String(30),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "recurring_templates",
        "if_holiday_action",
        existing_type=sa.String(30),
        type_=sa.String(20),
        existing_nullable=False,
    )
