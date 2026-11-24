"""003_add_investigation_counters

Revision ID: 003_add_investigation_counters
Revises: 002_add_refresh_tokens
Create Date: 2026-11-24 17:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_add_investigation_counters'
down_revision: Union[str, None] = '002_add_refresh_tokens'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'investigation_counters',
        sa.Column('year', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('last_value', sa.Integer(), nullable=False, server_default=sa.text('0')),
    )


def downgrade() -> None:
    op.drop_table('investigation_counters')

