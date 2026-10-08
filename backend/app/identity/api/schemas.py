import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.identity.domain.constants import InvitationStatus, Plan, Role, UserStatus


class RegisterRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=255)
    full_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    phone: str | None = Field(default=None, max_length=20)
    plan: Plan = Plan.STARTER


class CreateUserRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    role: Role
    phone: str | None = Field(default=None, max_length=20)


class UpdateUserRequest(BaseModel):
    """Partial PATCH: only the sent fields are changed."""

    model_config = ConfigDict(extra="forbid")

    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    phone: str | None = Field(default=None, max_length=20)
    role: Role | None = None
    status: UserStatus | None = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=1, max_length=128)


class InviteRequest(BaseModel):
    email: EmailStr
    role: Role
    full_name: str | None = Field(default=None, min_length=2, max_length=255)


class AcceptInviteRequest(BaseModel):
    token: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=128)
    full_name: str | None = Field(default=None, min_length=2, max_length=255)


class InvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    role: str
    status: InvitationStatus
    expires_at: datetime
    created_at: datetime


class MessageResponse(BaseModel):
    detail: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105 — HTTP scheme name, not a secret


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    full_name: str
    email: EmailStr
    phone: str | None
    role: str
    status: str
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime


class OrganizationResponse(BaseModel):
    """The `/settings/organization` screen's "plan and usage" panel. Limits are `None`
    on the Enterprise tier (negotiated capacity, not a numeric cap -- see
    `PLAN_LIMITS`/`register_organization`); the frontend renders that as "unlimited" or
    "custom", not a blank field."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    plan: str
    user_limit: int | None
    supplier_limit: int | None
    storage_limit_gb: int | None
    ai_execution_limit: int | None
    active_user_count: int
    created_at: datetime
