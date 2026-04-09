"""notification_scheduled_email

Revision ID: 002
Revises: 001
Create Date: 2026-04-05 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "notifications",
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "notifications",
        sa.Column("email_sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_notifications_scheduled_for",
        "notifications",
        ["scheduled_for"],
        postgresql_where=sa.text("scheduled_for IS NOT NULL AND email_sent_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_scheduled_for", table_name="notifications")
    op.drop_column("notifications", "email_sent_at")
    op.drop_column("notifications", "scheduled_for")
