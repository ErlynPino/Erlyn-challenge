import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import UserRole


class UserCreate(BaseModel):
    """Payload for creating a new user."""

    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    first_name: str = Field(max_length=100)
    last_name: str = Field(max_length=100)
    role: UserRole = UserRole.user
    active: bool = True

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        stripped = v.replace("_", "").replace("-", "")
        if not stripped.isalnum():
            raise ValueError(
                "username must be alphanumeric (underscores and hyphens allowed)"
            )
        return v.lower()


class UserUpdate(BaseModel):
    """Payload for updating an existing user (all fields optional)."""

    username: Optional[str] = Field(default=None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    first_name: Optional[str] = Field(default=None, max_length=100)
    last_name: Optional[str] = Field(default=None, max_length=100)
    role: Optional[UserRole] = None
    active: Optional[bool] = None

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        stripped = v.replace("_", "").replace("-", "")
        if not stripped.isalnum():
            raise ValueError(
                "username must be alphanumeric (underscores and hyphens allowed)"
            )
        return v.lower()


class UserResponse(BaseModel):
    """User representation returned by the API (no sensitive fields)."""

    id: uuid.UUID
    username: str
    email: EmailStr
    first_name: str
    last_name: str
    role: UserRole
    created_at: datetime
    updated_at: datetime
    active: bool

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    """Paginated list of users."""

    total: int
    skip: int
    limit: int
    data: list[UserResponse]

    model_config = {"from_attributes": True}
