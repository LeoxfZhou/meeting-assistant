from datetime import datetime
from uuid import UUID, uuid4
from pgvector.sqlalchemy import Vector
from sqlalchemy import String, Text, DateTime, func, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


class CompanyDocument(Base):
    __tablename__ = 'company_documents'
    id: Mapped[UUID] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class KnowledgeChunk(Base):
    __tablename__ = 'knowledge_chunks'
    __table_args__ = (
        UniqueConstraint('meeting_id','chunk_index'),
        UniqueConstraint('company_document_id','chunk_index'),
        CheckConstraint("(source_type = 'meeting' AND meeting_id IS NOT NULL AND company_document_id IS NULL) OR "
                        "(source_type = 'company_document' AND company_document_id IS NOT NULL AND meeting_id IS NULL)",
                        name='ck_chunks_source'),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source_type: Mapped[str] = mapped_column(String(30))
    meeting_id: Mapped[UUID | None] = mapped_column(ForeignKey('meetings.id', ondelete='CASCADE'), index=True)
    company_document_id: Mapped[UUID | None] = mapped_column(ForeignKey('company_documents.id', ondelete='CASCADE'), index=True)
    source_title: Mapped[str] = mapped_column(String(200))
    source_hash: Mapped[str] = mapped_column(String(64))
    content: Mapped[str] = mapped_column(Text)
    chunk_index: Mapped[int]
    char_start: Mapped[int]
    char_end: Mapped[int]
    embedding: Mapped[list[float]] = mapped_column(Vector(384))
    embedding_model: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    @property
    def source_id(self) -> UUID:
        return self.meeting_id or self.company_document_id
