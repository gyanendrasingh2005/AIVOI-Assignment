"""001_initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-11-24 17:05:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. roles table
    op.create_table(
        'roles',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
    )
    op.create_index('ix_roles_id', 'roles', ['id'])
    op.create_index('ix_roles_name', 'roles', ['name'], unique=True)

    # 2. users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # 3. user_roles table
    op.create_table(
        'user_roles',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role_id', sa.String(length=36), sa.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False),
        sa.UniqueConstraint('user_id', 'role_id', name='uq_user_roles_user_id_role_id'),
    )
    op.create_index('ix_user_roles_id', 'user_roles', ['id'])
    op.create_index('ix_user_roles_user_id', 'user_roles', ['user_id'])
    op.create_index('ix_user_roles_role_id', 'user_roles', ['role_id'])

    # 4. investigations table
    op.create_table(
        'investigations',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('investigation_number', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='Draft'),
        sa.Column('priority', sa.String(length=20), nullable=False, server_default='Medium'),
        sa.Column('risk_level', sa.String(length=20), nullable=False, server_default='Major'),
        sa.Column('created_by', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('assigned_to', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_investigations_id', 'investigations', ['id'])
    op.create_index('ix_investigations_investigation_number', 'investigations', ['investigation_number'], unique=True)
    op.create_index('ix_investigations_status', 'investigations', ['status'])
    op.create_index('ix_investigations_created_by', 'investigations', ['created_by'])
    op.create_index('ix_investigations_assigned_to', 'investigations', ['assigned_to'])

    # 5. incidents table
    op.create_table(
        'incidents',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('investigation_id', sa.String(length=36), sa.ForeignKey('investigations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('api_product_name', sa.String(length=150), nullable=False),
        sa.Column('batch_number', sa.String(length=50), nullable=False),
        sa.Column('manufacturing_stage', sa.String(length=100), nullable=False),
        sa.Column('incident_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('incident_description', sa.Text(), nullable=False),
        sa.Column('equipment_id', sa.String(length=50), nullable=True),
        sa.Column('expected_parameter', sa.String(length=255), nullable=True),
        sa.Column('actual_parameter', sa.String(length=255), nullable=True),
        sa.Column('immediate_actions', sa.Text(), nullable=True),
        sa.Column('affected_batches', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
        sa.Column('potential_quality_impact', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_incidents_id', 'incidents', ['id'])
    op.create_index('ix_incidents_investigation_id', 'incidents', ['investigation_id'], unique=True)
    op.create_index('ix_incidents_api_product_name', 'incidents', ['api_product_name'])
    op.create_index('ix_incidents_batch_number', 'incidents', ['batch_number'])

    # 6. documents table
    op.create_table(
        'documents',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('investigation_id', sa.String(length=36), sa.ForeignKey('investigations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('stored_filename', sa.String(length=255), nullable=False),
        sa.Column('file_type', sa.String(length=100), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('storage_path', sa.String(length=500), nullable=False),
        sa.Column('extracted_text', sa.Text(), nullable=True),
        sa.Column('uploaded_by', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('processing_status', sa.String(length=30), nullable=False, server_default='Pending'),
    )
    op.create_index('ix_documents_id', 'documents', ['id'])
    op.create_index('ix_documents_investigation_id', 'documents', ['investigation_id'])
    op.create_index('ix_documents_stored_filename', 'documents', ['stored_filename'], unique=True)

    # 7. evidence table
    op.create_table(
        'evidence',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('investigation_id', sa.String(length=36), sa.ForeignKey('investigations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('document_id', sa.String(length=36), sa.ForeignKey('documents.id', ondelete='SET NULL'), nullable=True),
        sa.Column('evidence_type', sa.String(length=50), nullable=False, server_default='DocumentExcerpt'),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('source_reference', sa.String(length=255), nullable=True),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('excerpt', sa.Text(), nullable=True),
        sa.Column('verification_status', sa.String(length=30), nullable=False, server_default='Unverified'),
        sa.Column('uploaded_by', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_evidence_id', 'evidence', ['id'])
    op.create_index('ix_evidence_investigation_id', 'evidence', ['investigation_id'])
    op.create_index('ix_evidence_document_id', 'evidence', ['document_id'])

    # 8. rca_analyses table
    op.create_table(
        'rca_analyses',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('investigation_id', sa.String(length=36), sa.ForeignKey('investigations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('analysis_method', sa.String(length=50), nullable=False, server_default='5 Whys'),
        sa.Column('analysis_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='Draft'),
        sa.Column('created_by', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_rca_analyses_id', 'rca_analyses', ['id'])
    op.create_index('ix_rca_analyses_investigation_id', 'rca_analyses', ['investigation_id'])

    # 9. root_causes table
    op.create_table(
        'root_causes',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('rca_analysis_id', sa.String(length=36), sa.ForeignKey('rca_analyses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('evidence_strength', sa.String(length=30), nullable=False, server_default='Moderate'),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='Identified'),
        sa.Column('ai_generated', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('human_confirmed', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_root_causes_id', 'root_causes', ['id'])
    op.create_index('ix_root_causes_rca_analysis_id', 'root_causes', ['rca_analysis_id'])

    # 10. contributing_factors table
    op.create_table(
        'contributing_factors',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('root_cause_id', sa.String(length=36), sa.ForeignKey('root_causes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('evidence_reference', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='Active'),
    )
    op.create_index('ix_contributing_factors_id', 'contributing_factors', ['id'])
    op.create_index('ix_contributing_factors_root_cause_id', 'contributing_factors', ['root_cause_id'])

    # 11. why_analysis_steps table
    op.create_table(
        'why_analysis_steps',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('rca_analysis_id', sa.String(length=36), sa.ForeignKey('rca_analyses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('step_number', sa.Integer(), nullable=False),
        sa.Column('question', sa.String(length=500), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('evidence_reference', sa.String(length=255), nullable=True),
        sa.Column('is_root_cause', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index('ix_why_analysis_steps_id', 'why_analysis_steps', ['id'])
    op.create_index('ix_why_analysis_steps_rca_analysis_id', 'why_analysis_steps', ['rca_analysis_id'])

    # 12. fishbone_categories table
    op.create_table(
        'fishbone_categories',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('rca_analysis_id', sa.String(length=36), sa.ForeignKey('rca_analyses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
    )
    op.create_index('ix_fishbone_categories_id', 'fishbone_categories', ['id'])
    op.create_index('ix_fishbone_categories_rca_analysis_id', 'fishbone_categories', ['rca_analysis_id'])

    # 13. fishbone_causes table
    op.create_table(
        'fishbone_causes',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('category_id', sa.String(length=36), sa.ForeignKey('fishbone_categories.id', ondelete='CASCADE'), nullable=False),
        sa.Column('parent_cause_id', sa.String(length=36), sa.ForeignKey('fishbone_causes.id', ondelete='CASCADE'), nullable=True),
        sa.Column('cause_description', sa.Text(), nullable=False),
        sa.Column('evidence_reference', sa.String(length=255), nullable=True),
        sa.Column('is_significant', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index('ix_fishbone_causes_id', 'fishbone_causes', ['id'])
    op.create_index('ix_fishbone_causes_category_id', 'fishbone_causes', ['category_id'])
    op.create_index('ix_fishbone_causes_parent_cause_id', 'fishbone_causes', ['parent_cause_id'])

    # 14. evidence_gaps table
    op.create_table(
        'evidence_gaps',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('investigation_id', sa.String(length=36), sa.ForeignKey('investigations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('root_cause_id', sa.String(length=36), sa.ForeignKey('root_causes.id', ondelete='SET NULL'), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('priority', sa.String(length=20), nullable=False, server_default='Medium'),
        sa.Column('suggested_source', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='Open'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_evidence_gaps_id', 'evidence_gaps', ['id'])
    op.create_index('ix_evidence_gaps_investigation_id', 'evidence_gaps', ['investigation_id'])
    op.create_index('ix_evidence_gaps_root_cause_id', 'evidence_gaps', ['root_cause_id'])

    # 15. capas table
    op.create_table(
        'capas',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('investigation_id', sa.String(length=36), sa.ForeignKey('investigations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('root_cause_id', sa.String(length=36), sa.ForeignKey('root_causes.id', ondelete='SET NULL'), nullable=True),
        sa.Column('capa_type', sa.String(length=20), nullable=False, server_default='Corrective'),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('priority', sa.String(length=20), nullable=False, server_default='Medium'),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='Draft'),
        sa.Column('assigned_to', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_capas_id', 'capas', ['id'])
    op.create_index('ix_capas_investigation_id', 'capas', ['investigation_id'])
    op.create_index('ix_capas_root_cause_id', 'capas', ['root_cause_id'])

    # 16. capa_tasks table
    op.create_table(
        'capa_tasks',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('capa_id', sa.String(length=36), sa.ForeignKey('capas.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('assigned_to', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='Pending'),
        sa.Column('completion_notes', sa.Text(), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_capa_tasks_id', 'capa_tasks', ['id'])
    op.create_index('ix_capa_tasks_capa_id', 'capa_tasks', ['capa_id'])

    # 17. effectiveness_checks table
    op.create_table(
        'effectiveness_checks',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('capa_id', sa.String(length=36), sa.ForeignKey('capas.id', ondelete='CASCADE'), nullable=False),
        sa.Column('verification_method', sa.String(length=255), nullable=False),
        sa.Column('acceptance_criteria', sa.Text(), nullable=False),
        sa.Column('result', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='Scheduled'),
        sa.Column('verified_by', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_effectiveness_checks_id', 'effectiveness_checks', ['id'])
    op.create_index('ix_effectiveness_checks_capa_id', 'effectiveness_checks', ['capa_id'])

    # 18. approvals table
    op.create_table(
        'approvals',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('investigation_id', sa.String(length=36), sa.ForeignKey('investigations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('reviewer_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('approval_status', sa.String(length=30), nullable=False, server_default='Approved'),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_approvals_id', 'approvals', ['id'])
    op.create_index('ix_approvals_investigation_id', 'approvals', ['investigation_id'])
    op.create_index('ix_approvals_reviewer_id', 'approvals', ['reviewer_id'])

    # 19. audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('investigation_id', sa.String(length=36), sa.ForeignKey('investigations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.String(length=36), nullable=False),
        sa.Column('old_values', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
        sa.Column('new_values', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_audit_logs_id', 'audit_logs', ['id'])
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_investigation_id', 'audit_logs', ['investigation_id'])
    op.create_index('ix_audit_logs_entity_type', 'audit_logs', ['entity_type'])
    op.create_index('ix_audit_logs_entity_id', 'audit_logs', ['entity_id'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('approvals')
    op.drop_table('effectiveness_checks')
    op.drop_table('capa_tasks')
    op.drop_table('capas')
    op.drop_table('evidence_gaps')
    op.drop_table('fishbone_causes')
    op.drop_table('fishbone_categories')
    op.drop_table('why_analysis_steps')
    op.drop_table('contributing_factors')
    op.drop_table('root_causes')
    op.drop_table('rca_analyses')
    op.drop_table('evidence')
    op.drop_table('documents')
    op.drop_table('incidents')
    op.drop_table('investigations')
    op.drop_table('user_roles')
    op.drop_table('users')
    op.drop_table('roles')
