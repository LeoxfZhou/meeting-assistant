from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import String, Text, ForeignKey, CheckConstraint, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


class ActionItem(Base):
    __tablename__ = "action_items"
    __table_args__ = (CheckConstraint("status IN ('pending','confirmed','rejected')", name="ck_action_items_status"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey('meetings.id', ondelete='RESTRICT'), index=True)
    task: Mapped[str] = mapped_column(String(1000))
    assignee_name: Mapped[str | None] = mapped_column(String(100))
    assignee_user_id: Mapped[UUID | None] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    due_date_text: Mapped[str | None] = mapped_column(String(200))
    evidence: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default='pending', server_default='pending')
    revision: Mapped[int] = mapped_column(default=1, server_default='1')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (CheckConstraint("status IN ('todo','in_progress','done')", name="ck_tasks_status"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source_action_item_id: Mapped[UUID] = mapped_column(ForeignKey('action_items.id', ondelete='RESTRICT'), unique=True)
    source_meeting_id: Mapped[UUID] = mapped_column(ForeignKey('meetings.id', ondelete='RESTRICT'), index=True)
    title: Mapped[str] = mapped_column(String(1000))
    assignee_name: Mapped[str | None] = mapped_column(String(100))
    assignee_user_id: Mapped[UUID | None] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), index=True)
    due_date_text: Mapped[str | None] = mapped_column(String(200))
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default='todo', server_default='todo')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
