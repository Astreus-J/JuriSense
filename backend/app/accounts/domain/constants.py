"""Perfis de acesso (RF03), módulos do sistema (RF05) e planos comerciais."""

from dataclasses import dataclass
from enum import StrEnum


class Perfil(StrEnum):
    ADMINISTRADOR = "administrador"
    ADVOGADO_SENIOR = "advogado_senior"
    ADVOGADO_JUNIOR = "advogado_junior"
    ESTAGIARIO = "estagiario"
    CLIENTE = "cliente"


class StatusUsuario(StrEnum):
    ATIVO = "ativo"
    INATIVO = "inativo"
    BLOQUEADO = "bloqueado"
    PENDENTE = "pendente"


class Plano(StrEnum):
    AUTONOMO = "autonomo"
    ESCRITORIO = "escritorio"
    ESCRITORIO_PLUS = "escritorio_plus"
    ENTERPRISE = "enterprise"


@dataclass(frozen=True)
class LimitesPlano:
    """Limites de uso por plano; None significa ilimitado."""

    usuarios: int | None
    processos_ativos: int | None
    armazenamento_gb: int | None
    geracoes_ia_mes: int | None


# Espelha os planos da landing (frontend/src/lib/landing-data.ts)
LIMITES_POR_PLANO: dict[Plano, LimitesPlano] = {
    Plano.AUTONOMO: LimitesPlano(1, 250, 15, 50),
    Plano.ESCRITORIO: LimitesPlano(5, 1250, 75, 250),
    Plano.ESCRITORIO_PLUS: LimitesPlano(20, 5000, 300, 1000),
    Plano.ENTERPRISE: LimitesPlano(None, None, None, None),
}


class Modulo(StrEnum):
    PROCESSOS = "processos"
    DOCUMENTOS = "documentos"
    IA = "ia"
    JURIMETRIA = "jurimetria"
    PRAZOS = "prazos"
    FINANCEIRO = "financeiro"
    CLIENTES = "clientes"
    RELATORIOS = "relatorios"
    PORTAL_CLIENTE = "portal_cliente"
