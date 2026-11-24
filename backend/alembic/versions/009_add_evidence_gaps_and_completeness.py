"""009_add_evidence_gaps_and_completeness

Revision ID: 009_add_evidence_gaps_and_completeness
Revises: 008_enhance_rca_analyses
Create Date: 2026-11-24 22:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '009_add_evidence_gaps_and_completeness'
down_revision: Union[str, None] = '008_enhance_rca_analyses'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enhance evidence_gaps table with classification, assignment, and resolution attributes
    op.add_column('evidence_gaps', sa.Column('gap_title', sa.String(length=255), nullable=True))
    op.add_column('evidence_gaps', sa.Column('category', sa.String(length=50), server_default='OTHER', nullable=False))
    op.add_column('evidence_gaps', sa.Column('detection_type', sa.String(length=50), server_default='MISSING_EVIDENCE', nullable=False))
    op.add_column('evidence_gaps', sa.Column('affected_area', sa.String(length=100), nullable=True))
    op.add_column('evidence_gaps', sa.Column('recommended_evidence_type', sa.String(length=100), nullable=True))
    op.add_column('evidence_gaps', sa.Column('recommended_action', sa.Text(), nullable=True))
    op.add_column('evidence_gaps', sa.Column('detection_source', sa.String(length=50), server_default='AI_ASSESSMENT', nullable=False))
    op.add_column('evidence_gaps', sa.Column('ai_confidence', sa.Float(), nullable=True))
    op.add_column('evidence_gaps', sa.Column('assigned_to', sa.String(length=36), nullable=True))
    op.add_column('evidence_gaps', sa.Column('due_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('evidence_gaps', sa.Column('resolution_justification', sa.Text(), nullable=True))
    op.add_column('evidence_gaps', sa.Column('resolved_by', sa.String(length=36), nullable=True))
    op.add_column('evidence_gaps', sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('evidence_gaps', sa.Column('requirement_profile_version', sa.String(length=20), server_default='1.0.0', nullable=True))
    op.add_column('evidence_gaps', sa.Column('assessment_version', sa.Integer(), server_default='1', nullable=False))
    op.add_column('evidence_gaps', sa.Column('associated_evidence_ids', sa.JSON(), server_default='[]', nullable=False))
    op.add_column('evidence_gaps', sa.Column('supporting_references', sa.JSON(), server_default='[]', nullable=False))

    op.create_foreign_key('fk_evidence_gaps_assigned_to_users', 'evidence_gaps', 'users', ['assigned_to'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_evidence_gaps_resolved_by_users', 'evidence_gaps', 'users', ['resolved_by'], ['id'], ondelete='SET NULL')

    op.create_index('ix_evidence_gaps_category', 'evidence_gaps', ['category'])
    op.create_index('ix_evidence_gaps_assigned_to', 'evidence_gaps', ['assigned_to'])

    # 2. Create completeness_assessments table
    op.create_table(
        'completeness_assessments',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('investigation_id', sa.String(length=36), sa.ForeignKey('investigations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('assessment_version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('overall_status', sa.String(length=30), nullable=False),
        sa.Column('completeness_score', sa.Float(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('dimension_results', sa.JSON(), nullable=False),
        sa.Column('critical_unresolved_gaps', sa.Integer(), server_default='0', nullable=False),
        sa.Column('high_priority_unresolved_gaps', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_unresolved_gaps', sa.Integer(), server_default='0', nullable=False),
        sa.Column('conflicting_evidence_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('unverified_causal_claims_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('pending_reviews_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('recommended_activities', sa.JSON(), server_default='[]', nullable=False),
        sa.Column('requirement_profile_version', sa.String(length=20), server_default='1.0.0', nullable=False),
        sa.Column('ai_execution_id', sa.String(length=36), sa.ForeignKey('ai_executions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_by', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_completeness_assessments_investigation_id', 'completeness_assessments', ['investigation_id'])
    op.create_index('ix_completeness_assessments_version', 'completeness_assessments', ['investigation_id', 'assessment_version'])


def downgrade() -> None:
    op.drop_table('completeness_assessments')

    op.drop_index('ix_evidence_gaps_assigned_to', table_name='evidence_gaps')
    op.drop_index('ix_evidence_gaps_category', table_name='evidence_gaps')
    op.drop_constraint('fk_evidence_gaps_resolved_by_users', 'evidence_gaps', type_='foreignkey')
    op.drop_constraint('fk_evidence_gaps_assigned_to_users', 'evidence_gaps', type_='foreignkey')

    op.drop_column('evidence_gaps', 'supporting_references')
    op.drop_column('evidence_gaps', 'associated_evidence_ids')
    op.drop_column('evidence_gaps', 'assessment_version')
    op.drop_column('evidence_gaps', 'requirement_profile_version')
    op.drop_column('evidence_gaps', 'resolved_at')
    op.drop_column('evidence_gaps', 'resolved_by')
    op.drop_column('evidence_gaps', 'resolution_justification')
    op.drop_column('evidence_gaps', 'due_date')
    op.drop_column('evidence_gaps', 'assigned_to')
    op.drop_column('evidence_gaps', 'ai_confidence')
    op.drop_column('evidence_gaps', 'detection_source')
    op.drop_column('evidence_gaps', 'recommended_action')
    op.drop_column('evidence_gaps', 'recommended_evidence_type')
    op.drop_column('evidence_gaps', 'affected_area')
    op.drop_column('evidence_gaps', 'detection_type')
    op.drop_column('evidence_gaps', 'category')
    op.drop_column('evidence_gaps', 'gap_title')
