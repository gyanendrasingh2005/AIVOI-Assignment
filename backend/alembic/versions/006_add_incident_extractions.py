"""006_add_incident_extractions

Revision ID: 006_add_incident_extractions
Revises: 005_add_ai_executions
Create Date: 2026-11-24 18:47:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '006_add_incident_extractions'
down_revision: Union[str, None] = '005_add_ai_executions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'incident_extractions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('investigation_id', sa.String(length=36), nullable=False),
        sa.Column('ai_execution_id', sa.String(length=36), nullable=True),
        sa.Column('created_by', sa.String(length=36), nullable=True),
        sa.Column('source_document_ids', sa.JSON(), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('prompt_version', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=30), server_default='PENDING', nullable=False),
        sa.Column('review_status', sa.String(length=30), server_default='PENDING_REVIEW', nullable=False),
        sa.Column('extracted_fields', sa.JSON(), nullable=False),
        sa.Column('missing_information', sa.JSON(), nullable=False),
        sa.Column('conflicting_information', sa.JSON(), nullable=False),
        sa.Column('document_summaries', sa.JSON(), nullable=False),
        sa.Column('reviewed_by', sa.String(length=36), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['ai_execution_id'], ['ai_executions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['investigation_id'], ['investigations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_incident_extractions_ai_execution_id'), 'incident_extractions', ['ai_execution_id'], unique=False)
    op.create_index(op.f('ix_incident_extractions_created_by'), 'incident_extractions', ['created_by'], unique=False)
    op.create_index(op.f('ix_incident_extractions_investigation_id'), 'incident_extractions', ['investigation_id'], unique=False)
    op.create_index(op.f('ix_incident_extractions_review_status'), 'incident_extractions', ['review_status'], unique=False)
    op.create_index(op.f('ix_incident_extractions_reviewed_by'), 'incident_extractions', ['reviewed_by'], unique=False)
    op.create_index(op.f('ix_incident_extractions_status'), 'incident_extractions', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_incident_extractions_status'), table_name='incident_extractions')
    op.drop_index(op.f('ix_incident_extractions_reviewed_by'), table_name='incident_extractions')
    op.drop_index(op.f('ix_incident_extractions_review_status'), table_name='incident_extractions')
    op.drop_index(op.f('ix_incident_extractions_investigation_id'), table_name='incident_extractions')
    op.drop_index(op.f('ix_incident_extractions_created_by'), table_name='incident_extractions')
    op.drop_index(op.f('ix_incident_extractions_ai_execution_id'), table_name='incident_extractions')
    op.drop_table('incident_extractions')

