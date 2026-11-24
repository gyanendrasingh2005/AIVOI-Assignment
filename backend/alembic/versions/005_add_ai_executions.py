"""005_add_ai_executions

Revision ID: 005_add_ai_executions
Revises: 004_enhance_documents_table
Create Date: 2026-11-24 18:32:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005_add_ai_executions'
down_revision: Union[str, None] = '004_enhance_documents_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ai_executions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workflow_id', sa.String(length=36), nullable=False),
        sa.Column('workflow_type', sa.String(length=50), nullable=False),
        sa.Column('investigation_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('prompt_version', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=30), server_default='PENDING', nullable=False),
        sa.Column('input_context_summary', sa.JSON(), nullable=True),
        sa.Column('structured_output', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('token_usage', sa.JSON(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['investigation_id'], ['investigations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_executions_investigation_id'), 'ai_executions', ['investigation_id'], unique=False)
    op.create_index(op.f('ix_ai_executions_started_at'), 'ai_executions', ['started_at'], unique=False)
    op.create_index(op.f('ix_ai_executions_status'), 'ai_executions', ['status'], unique=False)
    op.create_index(op.f('ix_ai_executions_user_id'), 'ai_executions', ['user_id'], unique=False)
    op.create_index(op.f('ix_ai_executions_workflow_id'), 'ai_executions', ['workflow_id'], unique=False)
    op.create_index(op.f('ix_ai_executions_workflow_type'), 'ai_executions', ['workflow_type'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_ai_executions_workflow_type'), table_name='ai_executions')
    op.drop_index(op.f('ix_ai_executions_workflow_id'), table_name='ai_executions')
    op.drop_index(op.f('ix_ai_executions_user_id'), table_name='ai_executions')
    op.drop_index(op.f('ix_ai_executions_status'), table_name='ai_executions')
    op.drop_index(op.f('ix_ai_executions_started_at'), table_name='ai_executions')
    op.drop_index(op.f('ix_ai_executions_investigation_id'), table_name='ai_executions')
    op.drop_table('ai_executions')

