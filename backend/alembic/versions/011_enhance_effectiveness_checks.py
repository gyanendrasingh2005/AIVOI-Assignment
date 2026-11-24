"""011_enhance_effectiveness_checks

Revision ID: 011_enhance_effectiveness_checks
Revises: 010_enhance_capas_and_add_recommendations
Create Date: 2026-11-25 00:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '011_enhance_effectiveness_checks'
down_revision: Union[str, None] = '010_enhance_capas_and_add_recommendations'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enhance effectiveness_checks table
    op.add_column('effectiveness_checks', sa.Column('check_title', sa.String(length=255), server_default='CAPA Effectiveness Verification', nullable=False))
    op.add_column('effectiveness_checks', sa.Column('verification_type', sa.String(length=50), server_default='PROCESS_MONITORING', nullable=False))
    op.add_column('effectiveness_checks', sa.Column('objective', sa.Text(), nullable=True))
    op.add_column('effectiveness_checks', sa.Column('measurement_method', sa.Text(), nullable=True))
    op.add_column('effectiveness_checks', sa.Column('baseline_data', sa.Text(), nullable=True))
    op.add_column('effectiveness_checks', sa.Column('expected_outcome', sa.Text(), nullable=True))
    op.add_column('effectiveness_checks', sa.Column('observation_period_days', sa.Integer(), server_default='30', nullable=False))
    op.add_column('effectiveness_checks', sa.Column('planned_start_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('effectiveness_checks', sa.Column('planned_completion_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('effectiveness_checks', sa.Column('actual_completion_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('effectiveness_checks', sa.Column('responsible_reviewer_id', sa.String(length=36), nullable=True))
    op.add_column('effectiveness_checks', sa.Column('required_evidence', sa.Text(), nullable=True))
    op.add_column('effectiveness_checks', sa.Column('associated_evidence_ids', sa.JSON(), server_default='[]', nullable=False))
    op.add_column('effectiveness_checks', sa.Column('sampling_approach', sa.Text(), nullable=True))
    op.add_column('effectiveness_checks', sa.Column('check_frequency', sa.String(length=100), nullable=True))
    op.add_column('effectiveness_checks', sa.Column('conclusion', sa.Text(), nullable=True))
    op.add_column('effectiveness_checks', sa.Column('reviewer_comments', sa.Text(), nullable=True))
    op.add_column('effectiveness_checks', sa.Column('effectiveness_decision', sa.String(length=50), nullable=True))
    op.add_column('effectiveness_checks', sa.Column('decision_reason', sa.Text(), nullable=True))
    op.add_column('effectiveness_checks', sa.Column('decision_by', sa.String(length=36), nullable=True))
    op.add_column('effectiveness_checks', sa.Column('decision_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('effectiveness_checks', sa.Column('ai_assessment_summary', sa.JSON(), nullable=True))
    op.add_column('effectiveness_checks', sa.Column('ai_execution_id', sa.String(length=36), nullable=True))
    op.add_column('effectiveness_checks', sa.Column('recurrence_observed', sa.Boolean(), server_default='0', nullable=False))
    op.add_column('effectiveness_checks', sa.Column('followup_investigation_id', sa.String(length=36), nullable=True))
    op.add_column('effectiveness_checks', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.add_column('effectiveness_checks', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))

    op.create_foreign_key('fk_eff_checks_reviewer_users', 'effectiveness_checks', 'users', ['responsible_reviewer_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_eff_checks_decision_by_users', 'effectiveness_checks', 'users', ['decision_by'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_eff_checks_ai_execution_id', 'effectiveness_checks', 'ai_executions', ['ai_execution_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_eff_checks_followup_inv_id', 'effectiveness_checks', 'investigations', ['followup_investigation_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint('fk_eff_checks_followup_inv_id', 'effectiveness_checks', type_='foreignkey')
    op.drop_constraint('fk_eff_checks_ai_execution_id', 'effectiveness_checks', type_='foreignkey')
    op.drop_constraint('fk_eff_checks_decision_by_users', 'effectiveness_checks', type_='foreignkey')
    op.drop_constraint('fk_eff_checks_reviewer_users', 'effectiveness_checks', type_='foreignkey')

    op.drop_column('effectiveness_checks', 'updated_at')
    op.drop_column('effectiveness_checks', 'created_at')
    op.drop_column('effectiveness_checks', 'followup_investigation_id')
    op.drop_column('effectiveness_checks', 'recurrence_observed')
    op.drop_column('effectiveness_checks', 'ai_execution_id')
    op.drop_column('effectiveness_checks', 'ai_assessment_summary')
    op.drop_column('effectiveness_checks', 'decision_at')
    op.drop_column('effectiveness_checks', 'decision_by')
    op.drop_column('effectiveness_checks', 'decision_reason')
    op.drop_column('effectiveness_checks', 'effectiveness_decision')
    op.drop_column('effectiveness_checks', 'reviewer_comments')
    op.drop_column('effectiveness_checks', 'conclusion')
    op.drop_column('effectiveness_checks', 'check_frequency')
    op.drop_column('effectiveness_checks', 'sampling_approach')
    op.drop_column('effectiveness_checks', 'associated_evidence_ids')
    op.drop_column('effectiveness_checks', 'required_evidence')
    op.drop_column('effectiveness_checks', 'responsible_reviewer_id')
    op.drop_column('effectiveness_checks', 'actual_completion_date')
    op.drop_column('effectiveness_checks', 'planned_completion_date')
    op.drop_column('effectiveness_checks', 'planned_start_date')
    op.drop_column('effectiveness_checks', 'observation_period_days')
    op.drop_column('effectiveness_checks', 'expected_outcome')
    op.drop_column('effectiveness_checks', 'baseline_data')
    op.drop_column('effectiveness_checks', 'measurement_method')
    op.drop_column('effectiveness_checks', 'objective')
    op.drop_column('effectiveness_checks', 'verification_type')
    op.drop_column('effectiveness_checks', 'check_title')
