from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator, model_validator

MAX_TEXT_CHARS = 1_000_000
MAX_FILE_BYTES = 1_048_576
Title = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=200)]
Content = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=MAX_TEXT_CHARS)]


class MeetingInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("title", "content", check_fields=False)
    @classmethod
    def no_null_byte(cls, value: str | None) -> str | None:
        if value is not None and "\x00" in value:
            raise ValueError("NUL characters are not supported")
        return value


class MeetingCreate(MeetingInput):
    title: Title
    content: Content


class MeetingPatch(MeetingInput):
    title: Title | None = None
    content: Content | None = None

    @model_validator(mode="after")
    def nonempty_patch(self) -> "MeetingPatch":
        if not self.model_fields_set or any(getattr(self, k) is None for k in self.model_fields_set):
            raise ValueError("Provide at least one non-null title or content")
        return self


class MeetingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    creator_user_id: UUID | None
    title: str
    content: str
    source_type: Literal["pasted_text", "txt", "markdown"]
    status: Literal["ready"]
    created_at: datetime
    updated_at: datetime
