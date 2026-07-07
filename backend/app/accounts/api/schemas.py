import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.accounts.domain.constants import Perfil, Plano


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
