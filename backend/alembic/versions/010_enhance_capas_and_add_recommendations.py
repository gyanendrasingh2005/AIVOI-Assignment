"""010_enhance_capas_and_add_recommendations

Revision ID: 010_enhance_capas_and_add_recommendations
Revises: 009_add_evidence_gaps_and_completeness
Create Date: 2026-11-24 23:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '010_enhance_capas_and_add_recommendations'
down_revision: Union[str, None] = '009_add_evidence_gaps_and_completeness'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enhance capas table
    op.add_column('capas', sa.Column('capa_number', sa.String(length=50), nullable=True))
    op.add_column('capas', sa.Column('rca_analysis_id', sa.String(length=36), nullable=True))
    op.add_column('capas', sa.Column('problem_statement', sa.Text(), nullable=True))
    op.add_column('capas', sa.Column('root_cause_summary', sa.Text(), nullable=True))
    op.add_column('capas', sa.Column('corrective_action_summary', sa.Text(), nullable=True))
    op.add_column('capas', sa.Column('preventive_action_summary', sa.Text(), nullable=True))
    op.add_column('capas', sa.Column('responsible_department', sa.String(length=100), nullable=True))
    op.add_column('capas', sa.Column('initiated_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('capas', sa.Column('approval_status', sa.String(length=30), server_default='DRAFT', nullable=True))
    op.add_column('capas', sa.Column('approval_comments', sa.Text(), nullable=True))
    op.add_column('capas', sa.Column('approved_by', sa.String(length=36), nullable=True))
    op.add_column('capas', sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('capas', sa.Column('supporting_references', sa.JSON(), server_default='[]', nullable=False))

    op.create_foreign_key('fk_capas_rca_analysis_id', 'capas', 'rca_analyses', ['rca_analysis_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_capas_approved_by_users', 'capas', 'users', ['approved_by'], ['id'], ondelete='SET NULL')
    op.create_index('ix_capas_capa_number', 'capas', ['capa_number'], unique=True)
    op.create_index('ix_capas_rca_analysis_id', 'capas', ['rca_analysis_id'])

    # 2. Enhance capa_tasks table
    op.add_column('capa_tasks', sa.Column('action_type', sa.String(length=30), server_default='CORRECTIVE', nullable=False))
    op.add_column('capa_tasks', sa.Column('department', sa.String(length=100), nullable=True))
    op.add_column('capa_tasks', sa.Column('target_start_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('capa_tasks', sa.Column('priority', sa.String(length=20), server_default='MEDIUM', nullable=False))
    op.add_column('capa_tasks', sa.Column('dependencies', sa.JSON(), server_default='[]', nullable=False))
    op.add_column('capa_tasks', sa.Column('completion_criteria', sa.Text(), nullable=True))
    op.add_column('capa_tasks', sa.Column('required_evidence', sa.Text(), nullable=True))
    op.add_column('capa_tasks', sa.Column('submitted_evidence_references', sa.JSON(), server_default='[]', nullable=False))
    op.add_column('capa_tasks', sa.Column('reviewed_by', sa.String(length=36), nullable=True))
    op.add_column('capa_tasks', sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('capa_tasks', sa.Column('review_comments', sa.Text(), nullable=True))
    op.add_column('capa_tasks', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.add_column('capa_tasks', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))

    op.create_foreign_key('fk_capa_tasks_reviewed_by_users', 'capa_tasks', 'users', ['reviewed_by'], ['id'], ondelete='SET NULL')

    # 3. Create capa_recommendations table
    op.create_table(
        'capa_recommendations',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('investigation_id', sa.String(length=36), sa.ForeignKey('investigations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('ai_execution_id', sa.String(length=36), sa.ForeignKey('ai_executions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('recommendation_title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('action_type', sa.String(length=30), server_default='CORRECTIVE', nullable=False),
        sa.Column('root_cause_id', sa.String(length=36), sa.ForeignKey('root_causes.id', ondelete='SET NULL'), nullable=True),
        sa.Column('root_cause_title', sa.String(length=255), nullable=True),
        sa.Column('contributing_factor_ids', sa.JSON(), server_default='[]', nullable=False),
        sa.Column('evidence_gap_ids', sa.JSON(), server_default='[]', nullable=False),
        sa.Column('supporting_references', sa.JSON(), server_default='[]', nullable=False),
        sa.Column('rationale', sa.Text(), nullable=False),
        sa.Column('expected_outcome', sa.Text(), nullable=False),
        sa.Column('recurrence_risk_addressed', sa.Text(), nullable=True),
        sa.Column('priority', sa.String(length=20), server_default='MEDIUM', nullable=False),
        sa.Column('suggested_department', sa.String(length=100), nullable=True),
        sa.Column('suggested_role', sa.String(length=100), nullable=True),
        sa.Column('suggested_target_days', sa.Integer(), server_default='30', nullable=False),
        sa.Column('target_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('implementation_steps', sa.JSON(), server_default='[]', nullable=False),
        sa.Column('completion_criteria', sa.Text(), nullable=False),
        sa.Column('required_completion_evidence', sa.Text(), nullable=False),
        sa.Column('implementation_risks', sa.Text(), nullable=True),
        sa.Column('is_provisional', sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column('uncertainty_rationale', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=30), server_default='PENDING_REVIEW', nullable=False),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('reviewed_by', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_capa_id', sa.String(length=36), sa.ForeignKey('capas.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_capa_recommendations_id', 'capa_recommendations', ['id'])
    op.create_index('ix_capa_recommendations_investigation_id', 'capa_recommendations', ['investigation_id'])
    op.create_index('ix_capa_recommendations_status', 'capa_recommendations', ['status'])
    op.create_index('ix_capa_recommendations_action_type', 'capa_recommendations', ['action_type'])
    op.create_index('ix_capa_recommendations_root_cause_id', 'capa_recommendations', ['root_cause_id'])
    op.create_index('ix_capa_recommendations_created_capa_id', 'capa_recommendations', ['created_capa_id'])


def downgrade() -> None:
    op.drop_table('capa_recommendations')

    # Remove columns from capa_tasks
    op.drop_constraint('fk_capa_tasks_reviewed_by_users', 'capa_tasks', type_='foreignkey')
    op.drop_column('capa_tasks', 'updated_at')
    op.drop_column('capa_tasks', 'created_at')
    op.drop_column('capa_tasks', 'review_comments')
    op.drop_column('capa_tasks', 'reviewed_at')
    op.drop_column('capa_tasks', 'reviewed_by')
    op.drop_column('capa_tasks', 'submitted_evidence_references')
    op.drop_column('capa_tasks', 'required_evidence')
    op.drop_column('capa_tasks', 'completion_criteria')
    op.drop_column('capa_tasks', 'dependencies')
    op.drop_column('capa_tasks', 'priority')
    op.drop_column('capa_tasks', 'target_start_date')
    op.drop_column('capa_tasks', 'department')
    op.drop_column('capa_tasks', 'action_type')

    # Remove columns from capas
    op.drop_index('ix_capas_rca_analysis_id', table_name='capas')
    op.drop_index('ix_capas_capa_number', table_name='capas')
    op.drop_constraint('fk_capas_approved_by_users', 'capas', type_='foreignkey')
    op.drop_constraint('fk_capas_rca_analysis_id', 'capas', type_='foreignkey')
    op.drop_column('capas', 'supporting_references')
    op.drop_column('capas', 'approved_at')
    op.drop_column('capas', 'approved_by')
    op.drop_column('capas', 'approval_comments')
    op.drop_column('capas', 'approval_status')
    op.drop_column('capas', 'initiated_date')
    op.drop_column('capas', 'responsible_department')
    op.drop_column('capas', 'preventive_action_summary')
    op.drop_column('capas', 'corrective_action_summary')
    op.drop_column('capas', 'root_cause_summary')
    op.drop_column('capas', 'problem_statement')
    op.drop_column('capas', 'rca_analysis_id')
    op.drop_column('capas', 'capa_number')

