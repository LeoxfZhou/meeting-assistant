from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.meeting import Meeting
from app.models.user import User


def meeting_query(user: User):
    query = select(Meeting)
    return query if user.is_owner else query.where(Meeting.creator_user_id == user.id)


def require_meeting(session: Session, meeting_id: UUID, user: User, *, lock: bool = False) -> Meeting:
    query = meeting_query(user).where(Meeting.id == meeting_id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    meeting = session.scalar(query)
    if meeting is None:
        # 不泄露另一用户的 Meeting 是否存在。
        raise HTTPException(404, "Meeting not found")
    return meeting
