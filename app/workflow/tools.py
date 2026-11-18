"""Schema-validated tools called by server-controlled workflows, not arbitrary model writes."""
from dataclasses import dataclass
from uuid import UUID
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.actions import TaskEdit, TaskRead
from app.services.access import require_meeting
from app.services.actions import confirm_candidate, update_task
from app.rag.service import retrieve
from app.rag.embedding import get_embedder
from app.core.logging import log_event


class GetMeeting(BaseModel):
    model_config=ConfigDict(extra='forbid')
    meeting_id: UUID


class SearchKnowledge(BaseModel):
    model_config=ConfigDict(extra='forbid')
    query: str=Field(min_length=1,max_length=380)
    k: int=Field(default=3,ge=1,le=10)


class CreateTask(BaseModel):
    model_config=ConfigDict(extra='forbid')
    candidate_id: UUID
    revision: int=Field(ge=1)


class UpdateTask(BaseModel):
    model_config=ConfigDict(extra='forbid')
    task_id: UUID
    changes: TaskEdit


SCHEMAS={'get_meeting':GetMeeting,'search_knowledge':SearchKnowledge,'create_task':CreateTask,'update_task':UpdateTask}


@dataclass
class ToolContext:
    session: Session
    user: User
    human_approved: bool=False


def tool_schemas() -> list[dict]:
    return [{'type':'function','function':{'name':name,'parameters':schema.model_json_schema()}} for name,schema in SCHEMAS.items()]


def execute_tool(name: str, arguments: dict, context: ToolContext):
    if name not in SCHEMAS:
        raise HTTPException(422,'Unknown tool')
    payload=SCHEMAS[name].model_validate(arguments)
    if name in {'create_task','update_task'} and not context.human_approved:
        raise HTTPException(403,'Human confirmation required for write tool')
    session,user=context.session,context.user
    if name=='get_meeting':
        meeting=require_meeting(session,payload.meeting_id,user)
        result={'id':str(meeting.id),'title':meeting.title,'content':meeting.content}
    elif name=='search_knowledge':
        result=retrieve(session,payload.query,user,get_embedder(),payload.k)
    elif name=='create_task':
        result=confirm_candidate(session,payload.candidate_id,payload.revision,user)
    else:
        result=update_task(session,payload.task_id,payload.changes.model_dump(exclude_unset=True),user)
    log_event('tool',tool=name,user_id=user.id,status='success')
    return result
