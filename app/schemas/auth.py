from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserResponse"


class TokenPayload(BaseModel):
    sub: str
    exp: int
    type: str = "access"


class LoginRequest(BaseModel):
    username_or_email: str
    password: str


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str] = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str  # Use plain str instead of EmailStr to avoid .local TLD rejection
    username: str
    full_name: Optional[str] = None
    is_active: bool
    is_superuser: bool
    roles: List[RoleResponse] = []
    created_at: datetime


class UserCreate(BaseModel):
    email: str
    username: str
    password: str = Field(min_length=8)
    full_name: Optional[str] = None
    role: str = "viewer"


class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None
