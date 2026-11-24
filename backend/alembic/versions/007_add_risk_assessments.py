"""007_add_risk_assessments

Revision ID: 007_add_risk_assessments
Revises: 006_add_incident_extractions
Create Date: 2026-11-24 19:08:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '007_add_risk_assessments'
down_revision: Union[str, None] = '006_add_incident_extractions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'risk_assessments',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('investigation_id', sa.String(length=36), nullable=False),
        sa.Column('ai_execution_id', sa.String(length=36), nullable=True),
        sa.Column('created_by', sa.String(length=36), nullable=True),
        sa.Column('framework_version', sa.String(length=20), server_default='1.0.0', nullable=False),
        sa.Column('incident_snapshot', sa.JSON(), nullable=False),
        sa.Column('quality_impact', sa.JSON(), nullable=False),
        sa.Column('patient_impact', sa.JSON(), nullable=False),
        sa.Column('batch_impact', sa.JSON(), nullable=False),
        sa.Column('process_impact', sa.JSON(), nullable=False),
        sa.Column('equipment_impact', sa.JSON(), nullable=False),
        sa.Column('data_integrity_impact', sa.JSON(), nullable=False),
        sa.Column('severity', sa.String(length=30), nullable=False),
        sa.Column('likelihood', sa.String(length=30), nullable=False),
        sa.Column('detectability', sa.String(length=30), nullable=True),
        sa.Column('overall_risk', sa.String(length=30), nullable=False),
        sa.Column('risk_rationale', sa.Text(), nullable=False),
        sa.Column('urgency_recommendation', sa.String(length=100), nullable=False),
        sa.Column('supporting_references', sa.JSON(), nullable=False),
        sa.Column('missing_information', sa.JSON(), nullable=False),
        sa.Column('conflicting_evidence', sa.JSON(), nullable=False),
        sa.Column('uncertainty_notes', sa.Text(), nullable=True),
        sa.Column('confidence_score', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('status', sa.String(length=30), server_default='PENDING', nullable=False),
        sa.Column('review_status', sa.String(length=30), server_default='PENDING_REVIEW', nullable=False),
        sa.Column('reviewer_notes', sa.Text(), nullable=True),
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
    op.create_index(op.f('ix_risk_assessments_ai_execution_id'), 'risk_assessments', ['ai_execution_id'], unique=False)
    op.create_index(op.f('ix_risk_assessments_created_by'), 'risk_assessments', ['created_by'], unique=False)
    op.create_index(op.f('ix_risk_assessments_investigation_id'), 'risk_assessments', ['investigation_id'], unique=False)
    op.create_index(op.f('ix_risk_assessments_overall_risk'), 'risk_assessments', ['overall_risk'], unique=False)
    op.create_index(op.f('ix_risk_assessments_review_status'), 'risk_assessments', ['review_status'], unique=False)
    op.create_index(op.f('ix_risk_assessments_reviewed_by'), 'risk_assessments', ['reviewed_by'], unique=False)
    op.create_index(op.f('ix_risk_assessments_status'), 'risk_assessments', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_risk_assessments_status'), table_name='risk_assessments')
    op.drop_index(op.f('ix_risk_assessments_reviewed_by'), table_name='risk_assessments')
    op.drop_index(op.f('ix_risk_assessments_review_status'), table_name='risk_assessments')
    op.drop_index(op.f('ix_risk_assessments_overall_risk'), table_name='risk_assessments')
    op.drop_index(op.f('ix_risk_assessments_investigation_id'), table_name='risk_assessments')
    op.drop_index(op.f('ix_risk_assessments_created_by'), table_name='risk_assessments')
    op.drop_index(op.f('ix_risk_assessments_ai_execution_id'), table_name='risk_assessments')
    op.drop_table('risk_assessments')
