from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.security import CurrentUser
from app.core.logging import log_event
from app.db.session import get_session
from app.llm.client import LLMClient
from app.llm.extraction import extract
from app.models.action_item import ActionItem, Task
from app.models.user import User
from app.schemas.actions import CandidateRead, CandidateEdit, Review, TaskRead, TaskEdit
from app.services.access import require_meeting
from app.services.actions import require_candidate, check_pending, validate_assignee, confirm_candidate, task_query, update_task

router = APIRouter(tags=['actions'])
DB = Annotated[Session, Depends(get_session)]


def get_llm(request: Request) -> LLMClient:
    return LLMClient(request.app.state.settings)


@router.post('/meetings/{meeting_id}/extract', response_model=list[CandidateRead], status_code=201)
def extract_meeting(meeting_id: UUID, session: DB, user: CurrentUser, llm: Annotated[LLMClient, Depends(get_llm)]):
    meeting = require_meeting(session, meeting_id, user)
    if session.scalar(select(ActionItem.id).where(ActionItem.meeting_id == meeting_id).limit(1)):
        raise HTTPException(409, 'Candidates already exist; review existing candidates')
    original = meeting.content
    session.commit()  # 不跨网络调用持有事务锁。
    result = extract(original, llm)
    meeting = require_meeting(session, meeting_id, user, lock=True)
    if meeting.content != original:
        raise HTTPException(409, 'Meeting changed during extraction')
    if session.scalar(select(ActionItem.id).where(ActionItem.meeting_id == meeting_id).limit(1)):
        raise HTTPException(409, 'Concurrent extraction already saved candidates')
    items = [ActionItem(meeting_id=meeting_id, task=i.task, assignee_name=i.assignee_name,
                        due_date_text=i.deadline, evidence=i.evidence) for i in result.action_items]
    session.add_all(items)
    session.commit()
    log_event('extraction', meeting_id=meeting_id, user_id=user.id, status='success', candidate_count=len(items))
    return items


@router.get('/meetings/{meeting_id}/candidates', response_model=list[CandidateRead])
def list_candidates(meeting_id: UUID, session: DB, user: CurrentUser):
    require_meeting(session, meeting_id, user)
    return list(session.scalars(select(ActionItem).where(ActionItem.meeting_id == meeting_id).order_by(ActionItem.created_at, ActionItem.id)))


@router.patch('/candidates/{candidate_id}', response_model=CandidateRead)
def edit_candidate(candidate_id: UUID, payload: CandidateEdit, session: DB, user: CurrentUser):
    item = require_candidate(session, candidate_id, user)
    check_pending(item, payload.revision)
    changes = payload.model_dump(exclude_unset=True, exclude={'revision'})
    if 'assignee_user_id' in changes:
        validate_assignee(session, changes['assignee_user_id'])
    for key, value in changes.items():
        setattr(item, key, value)
    item.revision += 1
    session.commit()
    session.refresh(item)
    return item


@router.post('/candidates/{candidate_id}/confirm', response_model=TaskRead)
def confirm(candidate_id: UUID, payload: Review, session: DB, user: CurrentUser):
    return confirm_candidate(session, candidate_id, payload.revision, user)


@router.post('/candidates/{candidate_id}/reject', response_model=CandidateRead)
def reject(candidate_id: UUID, payload: Review, session: DB, user: CurrentUser):
    item = require_candidate(session, candidate_id, user)
    if item.status == 'rejected':
        return item
    check_pending(item, payload.revision)
    item.status = 'rejected'
    item.revision += 1
    session.commit()
    return item


@router.get('/users', response_model=list[dict])
def list_users(session: DB, user: CurrentUser):
    # 单公司目录，仅提供绑定负责人所需的 id/name，不暴露密码或邮件。
    return [{'id': str(u.id), 'display_name': u.display_name} for u in
            session.scalars(select(User).where(User.is_active.is_(True)).order_by(User.created_at).limit(200))]


@router.get('/tasks', response_model=list[TaskRead])
def list_tasks(session: DB, user: CurrentUser, limit: Annotated[int, Query(ge=1, le=100)] = 20,
               offset: Annotated[int, Query(ge=0)] = 0):
    return list(session.scalars(task_query(user).order_by(Task.created_at.desc(), Task.id).limit(limit).offset(offset)))


@router.get('/tasks/my', response_model=list[TaskRead])
def my_tasks(session: DB, user: CurrentUser):
    return list(session.scalars(select(Task).where(Task.assignee_user_id == user.id).order_by(Task.created_at.desc())))


@router.get('/tasks/{task_id}', response_model=TaskRead)
def get_task(task_id: UUID, session: DB, user: CurrentUser):
    task = session.scalar(task_query(user).where(Task.id == task_id))
    if task is None:
        raise HTTPException(404, 'Task not found')
    return task


@router.patch('/tasks/{task_id}', response_model=TaskRead)
def patch_task(task_id: UUID, payload: TaskEdit, session: DB, user: CurrentUser):
    return update_task(session, task_id, payload.model_dump(exclude_unset=True), user)
