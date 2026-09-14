import uuid

from pydantic import BaseModel, EmailStr

from app.schemas.common import ORMModel


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class RoleOut(ORMModel):
    id: uuid.UUID
    name: str
    description: str


class CurrentUserOut(ORMModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: RoleOut
    badge_number: str | None
    is_active: bool
    permissions: list[str] = []
