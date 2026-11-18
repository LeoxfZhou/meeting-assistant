from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Review(BaseModel):
    model_config = ConfigDict(extra='forbid')
    revision: int = Field(ge=1)


class CandidateEdit(Review):
    task: str | None = Field(default=None, min_length=1, max_length=1000)
    assignee_name: str | None = Field(default=None, max_length=100)
    assignee_user_id: UUID | None = None
    due_date_text: str | None = Field(default=None, max_length=200)

    @model_validator(mode='after')
    def valid_edit(self):
        if self.model_fields_set == {'revision'} or ('task' in self.model_fields_set and not self.task):
            raise ValueError('Provide edited fields; task cannot be null')
        for key in ['task', 'assignee_name', 'due_date_text']:
            value = getattr(self, key)
            if value is not None and (not value.strip() or '\x00' in value):
                raise ValueError('Invalid text')
        return self


class CandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    meeting_id: UUID
    task: str
    assignee_name: str | None
    assignee_user_id: UUID | None
    due_date_text: str | None
    evidence: str
    status: Literal['pending','confirmed','rejected']
    revision: int
    created_at: datetime


class TaskEdit(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str | None = Field(default=None, min_length=1, max_length=1000)
    status: Literal['todo','in_progress','done'] | None = None
    assignee_name: str | None = Field(default=None, max_length=100)
    assignee_user_id: UUID | None = None
    due_date_text: str | None = Field(default=None, max_length=200)
    due_date: datetime | None = None

    @model_validator(mode='after')
    def validate_edit(self):
        if not self.model_fields_set:
            raise ValueError('Empty patch')
        for key in ['title', 'status']:
            if key in self.model_fields_set and getattr(self, key) is None:
                raise ValueError('Null is not allowed for '+key)
        for key in ['title','assignee_name','due_date_text']:
            value = getattr(self,key)
            if value is not None and (not value.strip() or '\x00' in value):
                raise ValueError('Invalid text')
        if self.due_date is not None and self.due_date.tzinfo is None:
            raise ValueError('due_date requires timezone')
        return self


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    source_action_item_id: UUID
    source_meeting_id: UUID
    title: str
    assignee_name: str | None
    assignee_user_id: UUID | None
    due_date_text: str | None
    due_date: datetime | None
    status: Literal['todo','in_progress','done']
    created_at: datetime
    updated_at: datetime
