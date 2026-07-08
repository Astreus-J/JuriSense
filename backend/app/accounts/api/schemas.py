import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.accounts.domain.constants import Perfil, Plano, StatusConvite, StatusUsuario


class RegisterRequest(BaseModel):
    organizacao_nome: str = Field(min_length=2, max_length=255)
    nome_completo: str = Field(min_length=2, max_length=255)
    email: EmailStr
    senha: str = Field(min_length=1, max_length=128)
    oab: str | None = Field(default=None, max_length=10)
    uf_oab: str | None = Field(default=None, min_length=2, max_length=2)
    cpf: str | None = Field(default=None, max_length=14)
    telefone: str | None = Field(default=None, max_length=20)
    plano: Plano = Plano.AUTONOMO


class CreateUserRequest(BaseModel):
    nome_completo: str = Field(min_length=2, max_length=255)
    email: EmailStr
    senha: str = Field(min_length=1, max_length=128)
    perfil: Perfil
    oab: str | None = Field(default=None, max_length=10)
    uf_oab: str | None = Field(default=None, min_length=2, max_length=2)
    cpf: str | None = Field(default=None, max_length=14)
    telefone: str | None = Field(default=None, max_length=20)


class UpdateUserRequest(BaseModel):
    """PATCH parcial: apenas os campos enviados são alterados."""

    model_config = ConfigDict(extra="forbid")

    nome_completo: str | None = Field(default=None, min_length=2, max_length=255)
    telefone: str | None = Field(default=None, max_length=20)
    perfil: Perfil | None = None
    status: StatusUsuario | None = None
    oab: str | None = Field(default=None, max_length=10)
    uf_oab: str | None = Field(default=None, min_length=2, max_length=2)
    cpf: str | None = Field(default=None, max_length=14)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1, max_length=128)
    nova_senha: str = Field(min_length=1, max_length=128)


class InviteRequest(BaseModel):
    email: EmailStr
    perfil: Perfil
    nome_completo: str | None = Field(default=None, min_length=2, max_length=255)


class AcceptInviteRequest(BaseModel):
    token: str = Field(min_length=1, max_length=128)
    senha: str = Field(min_length=1, max_length=128)
    nome_completo: str | None = Field(default=None, min_length=2, max_length=255)


class ConviteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    nome_completo: str | None
    perfil: str
    status: StatusConvite
    expira_em: datetime
    criado_em: datetime


class MessageResponse(BaseModel):
    detail: str


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105 — tipo do esquema HTTP, não segredo


class UsuarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organizacao_id: uuid.UUID
    nome_completo: str
    email: EmailStr
    cpf: str | None
    oab: str | None
    uf_oab: str | None
    telefone: str | None
    perfil: str
    status: str
    ativo: bool
    ultimo_acesso: datetime | None
    criado_em: datetime
