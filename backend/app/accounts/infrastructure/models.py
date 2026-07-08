import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.accounts.domain.constants import Perfil, Plano, StatusConvite, StatusUsuario
from app.core.db import Base


class Organizacao(Base):
    __tablename__ = "organizacoes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(255))
    cnpj: Mapped[str | None] = mapped_column(String(18), unique=True, index=True, default=None)

    email_contato: Mapped[str | None] = mapped_column(String(320), default=None)
    telefone: Mapped[str | None] = mapped_column(String(28), default=None)
    endereco: Mapped[str | None] = mapped_column(Text, default=None)
    cidade: Mapped[str | None] = mapped_column(String(100), default=None)
    estado: Mapped[str | None] = mapped_column(String(2), default=None)
    cep: Mapped[str | None] = mapped_column(String(9), default=None)

    # Plano comercial e limites derivados dele na criação (None = ilimitado).
    # Espelha o protótipo Django (plan + user_limit etc.); vira Assinatura na Sprint 4.
    plano: Mapped[str] = mapped_column(String(20), default=Plano.AUTONOMO.value)
    limite_usuarios: Mapped[int | None] = mapped_column(default=1)
    limite_processos: Mapped[int | None] = mapped_column(default=250)
    limite_armazenamento_gb: Mapped[int | None] = mapped_column(default=15)
    limite_geracoes_ia_mes: Mapped[int | None] = mapped_column(default=50)

    ativo: Mapped[bool] = mapped_column(default=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    usuarios: Mapped[list["Usuario"]] = relationship(
        back_populates="organizacao", foreign_keys="Usuario.organizacao_id"
    )


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (
        Index("ix_usuarios_email_status", "email", "status"),
        Index("ix_usuarios_organizacao_perfil", "organizacao_id", "perfil"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organizacao_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizacoes.id"), index=True)
    nome_completo: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255))

    cpf: Mapped[str | None] = mapped_column(String(14), unique=True, default=None)
    # Número OAB + UF (obrigatório para advogados — validação na API da OAB entra na Sprint 2)
    oab: Mapped[str | None] = mapped_column(String(10), default=None)
    uf_oab: Mapped[str | None] = mapped_column(String(2), default=None)
    telefone: Mapped[str | None] = mapped_column(String(20), default=None)

    perfil: Mapped[str] = mapped_column(String(30), default=Perfil.ADMINISTRADOR.value)
    status: Mapped[str] = mapped_column(String(20), default=StatusUsuario.ATIVO.value)

    # 2FA TOTP (RF01) — habilitação/uso entram na Sprint 5
    two_factor_enabled: Mapped[bool] = mapped_column(default=False)
    two_factor_secret: Mapped[str | None] = mapped_column(String(32), default=None)

    email_verificado: Mapped[bool] = mapped_column(default=False)
    ultimo_acesso: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    organizacao: Mapped[Organizacao] = relationship(
        back_populates="usuarios", foreign_keys=[organizacao_id]
    )

    @property
    def ativo(self) -> bool:
        """Derivado de status: apenas usuários com status 'ativo' autenticam."""
        return self.status == StatusUsuario.ATIVO.value


class PermissaoModulo(Base):
    """Permissão granular por usuário, módulo e ação (RF05).

    Espelha o user_module_permissions do projeto Django; seeds por perfil e
    enforcement nas rotas entram na Sprint 3.
    """

    __tablename__ = "permissoes_modulo"
    __table_args__ = (
        UniqueConstraint(
            "usuario_id", "modulo", "organizacao_id", name="uq_permissao_usuario_modulo_org"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), index=True
    )
    organizacao_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizacoes.id"), index=True)
    modulo: Mapped[str] = mapped_column(String(50))

    pode_criar: Mapped[bool] = mapped_column(default=False)
    pode_ler: Mapped[bool] = mapped_column(default=False)
    pode_atualizar: Mapped[bool] = mapped_column(default=False)
    pode_excluir: Mapped[bool] = mapped_column(default=False)

    concedido_por_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"), default=None
    )

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    usuario: Mapped[Usuario] = relationship(foreign_keys=[usuario_id])
    concedido_por: Mapped[Usuario | None] = relationship(foreign_keys=[concedido_por_id])


class TokenRecuperacao(Base):
    """Token de recuperação de senha (RF02) — espelha TokenRecuperationModel do Django.

    Armazena apenas o hash SHA-256; o token em si só existe no link enviado.
    """

    __tablename__ = "tokens_recuperacao"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    usado: Mapped[bool] = mapped_column(default=False)
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    usuario: Mapped[Usuario] = relationship()


class Convite(Base):
    """Convite de usuário para a organização — espelha o Invite do Django."""

    __tablename__ = "convites"
    __table_args__ = (
        Index("ix_convites_email_organizacao", "email", "organizacao_id"),
        Index("ix_convites_status_expira_em", "status", "expira_em"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320))
    nome_completo: Mapped[str | None] = mapped_column(String(255), default=None)
    perfil: Mapped[str] = mapped_column(String(30))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default=StatusConvite.PENDENTE.value)

    organizacao_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizacoes.id"), index=True)
    convidado_por_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"), default=None
    )
    aceito_por_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"), default=None
    )

    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    aceito_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    organizacao: Mapped[Organizacao] = relationship()
    convidado_por: Mapped[Usuario | None] = relationship(foreign_keys=[convidado_por_id])
    aceito_por: Mapped[Usuario | None] = relationship(foreign_keys=[aceito_por_id])


class Acesso(Base):
    """Histórico de tentativas de login (RF01)."""

    __tablename__ = "acessos"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("usuarios.id"), index=True, default=None
    )
    email: Mapped[str] = mapped_column(String(320), index=True)
    ip: Mapped[str | None] = mapped_column(String(45), default=None)
    user_agent: Mapped[str | None] = mapped_column(Text, default=None)
    sucesso: Mapped[bool] = mapped_column(default=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
