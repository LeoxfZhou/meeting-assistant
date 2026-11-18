from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select, or_
from sqlalchemy.orm import Session
from app.models.action_item import ActionItem, Task
from app.models.meeting import Meeting
from app.models.user import User
from app.services.access import require_meeting


def validate_assignee(session: Session, user_id: UUID | None) -> None:
    if user_id is not None:
        user = session.get(User, user_id)
        if user is None or not user.is_active:
            raise HTTPException(422, 'Assignee must be an active registered user')


def require_candidate(session: Session, candidate_id: UUID, user: User) -> ActionItem:
    item = session.get(ActionItem, candidate_id)
    if item is None:
        raise HTTPException(404, 'Candidate not found')
    require_meeting(session, item.meeting_id, user, lock=True)
    return session.scalar(select(ActionItem).where(ActionItem.id == candidate_id).with_for_update()
                          .execution_options(populate_existing=True))


def check_pending(item: ActionItem, revision: int) -> None:
    if item.status != 'pending' or item.revision != revision:
        raise HTTPException(409, 'Candidate is no longer pending or revision changed')


def confirm_candidate(session: Session, candidate_id: UUID, revision: int, user: User) -> Task:
    item = require_candidate(session, candidate_id, user)
    if item.status == 'confirmed':
        task = session.scalar(select(Task).where(Task.source_action_item_id == item.id))
        if task is None:
            raise HTTPException(409, 'Inconsistent confirmation state')
        return task
    check_pending(item, revision)
    validate_assignee(session, item.assignee_user_id)
    task = Task(source_action_item_id=item.id, source_meeting_id=item.meeting_id, title=item.task,
                assignee_name=item.assignee_name, assignee_user_id=item.assignee_user_id,
                due_date_text=item.due_date_text)
    session.add(task)
    item.status = 'confirmed'
    item.revision += 1
    # 唯一约束 + 行锁 + 同一事务：并发点击/失败重试都不能创建第二个 Task。
    session.commit()
    session.refresh(task)
    return task


def task_query(user: User):
    query = select(Task).join(Meeting, Task.source_meeting_id == Meeting.id)
    return query if user.is_owner else query.where(or_(Meeting.creator_user_id == user.id, Task.assignee_user_id == user.id))


def update_task(session: Session, task_id: UUID, changes: dict, user: User) -> Task:
    task = session.scalar(task_query(user).where(Task.id == task_id).with_for_update())
    if task is None:
        raise HTTPException(404, 'Task not found')
    meeting = session.get(Meeting, task.source_meeting_id)
    if not user.is_owner and meeting.creator_user_id != user.id and set(changes) != {'status'}:
        raise HTTPException(403, 'Assignees may only update task status')
    if 'assignee_user_id' in changes:
        validate_assignee(session, changes['assignee_user_id'])
    for field, value in changes.items():
        setattr(task, field, value)
    session.commit()
    session.refresh(task)
    return task
