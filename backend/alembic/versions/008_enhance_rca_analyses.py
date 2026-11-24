"""008_enhance_rca_analyses

Revision ID: 008_enhance_rca_analyses
Revises: 007_add_risk_assessments
Create Date: 2026-11-24 19:42:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '008_enhance_rca_analyses'
down_revision: Union[str, None] = '007_add_risk_assessments'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enhance rca_analyses
    op.add_column('rca_analyses', sa.Column('ai_execution_id', sa.String(length=36), nullable=True))
    op.add_column('rca_analyses', sa.Column('prompt_version', sa.String(length=20), server_default='1.0.0', nullable=False))
    op.add_column('rca_analyses', sa.Column('problem_statement', sa.Text(), nullable=True))
    op.add_column('rca_analyses', sa.Column('incident_summary', sa.Text(), nullable=True))
    op.add_column('rca_analyses', sa.Column('five_whys_data', sa.JSON(), server_default='[]', nullable=False))
    op.add_column('rca_analyses', sa.Column('fishbone_data', sa.JSON(), server_default='{}', nullable=False))
    op.add_column('rca_analyses', sa.Column('root_causes_data', sa.JSON(), server_default='[]', nullable=False))
    op.add_column('rca_analyses', sa.Column('contributing_factors_data', sa.JSON(), server_default='[]', nullable=False))
    op.add_column('rca_analyses', sa.Column('rejected_hypotheses_data', sa.JSON(), server_default='[]', nullable=False))
    op.add_column('rca_analyses', sa.Column('evidence_gaps_data', sa.JSON(), server_default='[]', nullable=False))
    op.add_column('rca_analyses', sa.Column('reviewer_notes', sa.Text(), nullable=True))
    op.add_column('rca_analyses', sa.Column('reviewed_by', sa.String(length=36), nullable=True))
    op.add_column('rca_analyses', sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True))

    op.create_foreign_key('fk_rca_analyses_ai_execution_id', 'rca_analyses', 'ai_executions', ['ai_execution_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_rca_analyses_reviewed_by', 'rca_analyses', 'users', ['reviewed_by'], ['id'], ondelete='SET NULL')
    op.create_index(op.f('ix_rca_analyses_ai_execution_id'), 'rca_analyses', ['ai_execution_id'], unique=False)
    op.create_index(op.f('ix_rca_analyses_reviewed_by'), 'rca_analyses', ['reviewed_by'], unique=False)

    # 2. Enhance why_analysis_steps
    op.add_column('why_analysis_steps', sa.Column('explanation', sa.Text(), nullable=True))
    op.add_column('why_analysis_steps', sa.Column('confidence_score', sa.Float(), server_default='0.8', nullable=False))
    op.add_column('why_analysis_steps', sa.Column('verification_status', sa.String(length=30), server_default='PROPOSED', nullable=False))
    op.add_column('why_analysis_steps', sa.Column('assumptions', sa.JSON(), server_default='[]', nullable=False))
    op.add_column('why_analysis_steps', sa.Column('supporting_references', sa.JSON(), server_default='[]', nullable=False))

    # 3. Enhance fishbone_causes
    op.add_column('fishbone_causes', sa.Column('cause_title', sa.String(length=255), nullable=True))
    op.add_column('fishbone_causes', sa.Column('confidence_score', sa.Float(), server_default='0.8', nullable=False))
    op.add_column('fishbone_causes', sa.Column('verification_status', sa.String(length=30), server_default='PROPOSED', nullable=False))
    op.add_column('fishbone_causes', sa.Column('potential_impact', sa.Text(), nullable=True))
    op.add_column('fishbone_causes', sa.Column('supporting_references', sa.JSON(), server_default='[]', nullable=False))

    # 4. Enhance root_causes
    op.add_column('root_causes', sa.Column('confidence_score', sa.Float(), server_default='0.8', nullable=False))
    op.add_column('root_causes', sa.Column('supporting_references', sa.JSON(), server_default='[]', nullable=False))
    op.add_column('root_causes', sa.Column('rejection_reason', sa.Text(), nullable=True))


def downgrade() -> None:
    # 4. Revert root_causes
    op.drop_column('root_causes', 'rejection_reason')
    op.drop_column('root_causes', 'supporting_references')
    op.drop_column('root_causes', 'confidence_score')

    # 3. Revert fishbone_causes
    op.drop_column('fishbone_causes', 'supporting_references')
    op.drop_column('fishbone_causes', 'potential_impact')
    op.drop_column('fishbone_causes', 'verification_status')
    op.drop_column('fishbone_causes', 'confidence_score')
    op.drop_column('fishbone_causes', 'cause_title')

    # 2. Revert why_analysis_steps
    op.drop_column('why_analysis_steps', 'supporting_references')
    op.drop_column('why_analysis_steps', 'assumptions')
    op.drop_column('why_analysis_steps', 'verification_status')
    op.drop_column('why_analysis_steps', 'confidence_score')
    op.drop_column('why_analysis_steps', 'explanation')

    # 1. Revert rca_analyses
    op.drop_index(op.f('ix_rca_analyses_reviewed_by'), table_name='rca_analyses')
    op.drop_index(op.f('ix_rca_analyses_ai_execution_id'), table_name='rca_analyses')
    op.drop_constraint('fk_rca_analyses_reviewed_by', 'rca_analyses', type_='foreignkey')
    op.drop_constraint('fk_rca_analyses_ai_execution_id', 'rca_analyses', type_='foreignkey')

    op.drop_column('rca_analyses', 'reviewed_at')
    op.drop_column('rca_analyses', 'reviewed_by')
    op.drop_column('rca_analyses', 'reviewer_notes')
    op.drop_column('rca_analyses', 'evidence_gaps_data')
    op.drop_column('rca_analyses', 'rejected_hypotheses_data')
    op.drop_column('rca_analyses', 'contributing_factors_data')
    op.drop_column('rca_analyses', 'root_causes_data')
    op.drop_column('rca_analyses', 'fishbone_data')
    op.drop_column('rca_analyses', 'five_whys_data')
    op.drop_column('rca_analyses', 'incident_summary')
    op.drop_column('rca_analyses', 'problem_statement')
    op.drop_column('rca_analyses', 'prompt_version')
    op.drop_column('rca_analyses', 'ai_execution_id')
