from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, String, Text, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Meeting(Base):
    __tablename__ = "meetings"
    __table_args__ = (
        CheckConstraint("source_type IN ('pasted_text', 'txt', 'markdown')", name="ck_meetings_source_type"),
        CheckConstraint("status = 'ready'", name="ck_meetings_status"),
        CheckConstraint("length(trim(title)) > 0", name="ck_meetings_title"),
        CheckConstraint("length(trim(content)) > 0", name="ck_meetings_content"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    creator_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", name="fk_meetings_creator_user_id", ondelete="RESTRICT"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(20), default="pasted_text")
    status: Mapped[str] = mapped_column(String(20), default="ready", server_default="ready")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
