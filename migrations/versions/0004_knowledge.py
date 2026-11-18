"""Fixed-dimension pgvector chunks for company documents and authorized meetings."""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
revision='0004_knowledge'
down_revision='0003_actions_tasks'
branch_labels=None
depends_on=None


def upgrade():
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.create_table('company_documents',
        sa.Column('id',sa.Uuid(),primary_key=True),
        sa.Column('slug',sa.String(100),nullable=False,unique=True),
        sa.Column('title',sa.String(200),nullable=False),
        sa.Column('content',sa.Text(),nullable=False),
        sa.Column('content_hash',sa.String(64),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table('knowledge_chunks',
        sa.Column('id',sa.Uuid(),primary_key=True),
        sa.Column('source_type',sa.String(30),nullable=False),
        sa.Column('meeting_id',sa.Uuid(),sa.ForeignKey('meetings.id',ondelete='CASCADE')),
        sa.Column('company_document_id',sa.Uuid(),sa.ForeignKey('company_documents.id',ondelete='CASCADE')),
        sa.Column('source_title',sa.String(200),nullable=False),
        sa.Column('source_hash',sa.String(64),nullable=False),
        sa.Column('content',sa.Text(),nullable=False),
        sa.Column('chunk_index',sa.Integer(),nullable=False),
        sa.Column('char_start',sa.Integer(),nullable=False),
        sa.Column('char_end',sa.Integer(),nullable=False),
        sa.Column('embedding',Vector(384),nullable=False),
        sa.Column('embedding_model',sa.String(200),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
        sa.UniqueConstraint('meeting_id','chunk_index'),sa.UniqueConstraint('company_document_id','chunk_index'),
        sa.CheckConstraint("(source_type = 'meeting' AND meeting_id IS NOT NULL AND company_document_id IS NULL) OR "
                           "(source_type = 'company_document' AND company_document_id IS NOT NULL AND meeting_id IS NULL)",name='ck_chunks_source'))
    op.create_index('ix_knowledge_chunks_meeting_id','knowledge_chunks',['meeting_id'])
    op.create_index('ix_knowledge_chunks_company_document_id','knowledge_chunks',['company_document_id'])


def downgrade():
    op.drop_table('knowledge_chunks')
    op.drop_table('company_documents')
    # 不删除共享 extension，避免影响数据库内其他使用者。
