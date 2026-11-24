"""004_enhance_documents_table

Revision ID: 004_enhance_documents_table
Revises: 003_add_investigation_counters
Create Date: 2026-11-24 18:05:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004_enhance_documents_table'
down_revision: Union[str, None] = '003_add_investigation_counters'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add enhanced columns to documents table
    op.add_column('documents', sa.Column('checksum', sa.String(length=64), nullable=False, server_default=''))
    op.add_column('documents', sa.Column('file_extension', sa.String(length=20), nullable=True))
    op.add_column('documents', sa.Column('document_category', sa.String(length=50), nullable=True))
    op.add_column('documents', sa.Column('extracted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('documents', sa.Column('extraction_error', sa.Text(), nullable=True))
    op.add_column('documents', sa.Column('page_count', sa.Integer(), nullable=True))
    op.add_column('documents', sa.Column('character_count', sa.Integer(), nullable=True))
    op.add_column('documents', sa.Column('source_type', sa.String(length=50), nullable=False, server_default='file_upload'))
    op.add_column('documents', sa.Column('metadata_json', sa.JSON(), nullable=True))
    op.add_column('documents', sa.Column('is_archived', sa.Boolean(), nullable=False, server_default=sa.text('false')))

    # Add indexes
    op.create_index('ix_documents_checksum', 'documents', ['checksum'])
    op.create_index('ix_documents_uploaded_by', 'documents', ['uploaded_by'])
    op.create_index('ix_documents_uploaded_at', 'documents', ['uploaded_at'])
    op.create_index('ix_documents_processing_status', 'documents', ['processing_status'])
    op.create_index('ix_documents_is_archived', 'documents', ['is_archived'])


def downgrade() -> None:
    op.drop_index('ix_documents_is_archived', table_name='documents')
    op.drop_index('ix_documents_processing_status', table_name='documents')
    op.drop_index('ix_documents_uploaded_at', table_name='documents')
    op.drop_index('ix_documents_uploaded_by', table_name='documents')
    op.drop_index('ix_documents_checksum', table_name='documents')

    op.drop_column('documents', 'is_archived')
    op.drop_column('documents', 'metadata_json')
    op.drop_column('documents', 'source_type')
    op.drop_column('documents', 'character_count')
    op.drop_column('documents', 'page_count')
    op.drop_column('documents', 'extraction_error')
    op.drop_column('documents', 'extracted_at')
    op.drop_column('documents', 'document_category')
    op.drop_column('documents', 'file_extension')
    op.drop_column('documents', 'checksum')
