from pathlib import PurePosixPath
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import CurrentUser
from app.services.access import meeting_query, require_meeting
from app.db.session import get_session
from app.models.meeting import Meeting
from app.schemas.meeting import MAX_FILE_BYTES, MeetingCreate, MeetingPatch, MeetingRead

router = APIRouter(prefix="/meetings", tags=["meetings"])
DB = Annotated[Session, Depends(get_session)]


def save_meeting(payload: MeetingCreate, source_type: str, session: Session, creator_user_id: UUID) -> Meeting:
    meeting = Meeting(**payload.model_dump(), source_type=source_type, creator_user_id=creator_user_id)
    session.add(meeting)
    session.commit()
    session.refresh(meeting)
    return meeting


@router.post("", response_model=MeetingRead, status_code=201)
def create_meeting(payload: MeetingCreate, session: DB, user: CurrentUser) -> Meeting:
    return save_meeting(payload, "pasted_text", session, user.id)


@router.get("", response_model=list[MeetingRead])
def list_meetings(session: DB, user: CurrentUser, limit: Annotated[int, Query(ge=1, le=100)] = 20,
                  offset: Annotated[int, Query(ge=0)] = 0) -> list[Meeting]:
    return list(session.scalars(meeting_query(user).order_by(Meeting.created_at.desc(), Meeting.id)
                                .offset(offset).limit(limit)))


# 静态 upload 路由放在 UUID 动态路由之前。
@router.post("/upload", response_model=MeetingRead, status_code=201)
def upload_meeting(session: DB, user: CurrentUser, file: Annotated[UploadFile, File()],
                   title: Annotated[str | None, Form()] = None) -> Meeting:
    try:
        name = PurePosixPath((file.filename or "").replace("\\", "/")).name
        suffix = PurePosixPath(name).suffix.lower()
        allowed = {".txt": {"text/plain", "application/octet-stream"},
                   ".md": {"text/markdown", "text/x-markdown", "text/plain", "application/octet-stream"}}
        content_type = (file.content_type or "").split(";", 1)[0].lower()
        if suffix not in allowed or content_type not in allowed[suffix]:
            raise HTTPException(415, "Only TXT/Markdown text uploads are supported")
        # 只读取上限 + 1 字节；不把用户文件名当作本地保存路径。
        raw = file.file.read(MAX_FILE_BYTES + 1)
        if len(raw) > MAX_FILE_BYTES:
            raise HTTPException(413, "File exceeds 1 MiB")
        try:
            content = raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise HTTPException(422, "File must be valid UTF-8") from exc
        try:
            payload = MeetingCreate(title=title if title is not None else PurePosixPath(name).stem,
                                    content=content)
        except ValidationError as exc:
            raise HTTPException(422, "Meeting title or content is empty, too long, or invalid") from exc
        return save_meeting(payload, "txt" if suffix == ".txt" else "markdown", session, user.id)
    finally:
        file.file.close()


@router.get("/{meeting_id}", response_model=MeetingRead)
def get_meeting(meeting_id: UUID, session: DB, user: CurrentUser) -> Meeting:
    return require_meeting(session, meeting_id, user)


@router.patch("/{meeting_id}", response_model=MeetingRead)
def patch_meeting(meeting_id: UUID, payload: MeetingPatch, session: DB, user: CurrentUser) -> Meeting:
    meeting = require_meeting(session, meeting_id, user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(meeting, field, value)
    session.commit()
    session.refresh(meeting)
    return meeting


@router.delete("/{meeting_id}", status_code=204)
def delete_meeting(meeting_id: UUID, session: DB, user: CurrentUser) -> Response:
    session.delete(require_meeting(session, meeting_id, user))
    session.commit()
    return Response(status_code=204)
