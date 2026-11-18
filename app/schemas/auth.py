from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator


class Register(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=100)
    password: SecretStr = Field(min_length=10, max_length=128)

    @field_validator("display_name")
    @classmethod
    def valid_name(cls, value: str) -> str:
        value = value.strip()
        if not value or "\x00" in value:
            raise ValueError("Invalid display name")
        return value


class Login(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    password: SecretStr = Field(min_length=1, max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: str
    display_name: str
    is_active: bool
    is_owner: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
