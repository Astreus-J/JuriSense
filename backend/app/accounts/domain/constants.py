"""Perfis de acesso (RF03) e módulos do sistema (RF05)."""

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
