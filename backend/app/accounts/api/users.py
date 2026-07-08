import uuid

from fastapi import APIRouter, HTTPException, status

from app.accounts.api.deps import CurrentAdmin, EmailDep
from app.accounts.api.schemas import (
    AcceptInviteRequest,
    ConviteResponse,
    CreateUserRequest,
    InviteRequest,
    UpdateUserRequest,
    UsuarioResponse,
)
from app.accounts.application import invite_service, user_service
from app.accounts.domain.errors import (
    ConviteInvalidoError,
    CpfJaCadastradoError,
    EmailJaCadastradoError,
    LimiteUsuariosAtingidoError,
    OabInvalidaError,
    OabJaCadastradaError,
    OperacaoNaoPermitidaError,
    SenhaFracaError,
    UsuarioNaoEncontradoError,
)
from app.core.db import SessionDep
from app.core.redis import RedisDep

router = APIRouter(prefix="/users", tags=["users"])


def _map_error(exc: Exception) -> HTTPException:
    """Traduz erros de domínio em respostas HTTP."""
    match exc:
        case SenhaFracaError():
            return HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"{exc.message}: {', '.join(exc.motivos)}",
            )
        case OabInvalidaError():
            return HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=exc.message
            )
        case LimiteUsuariosAtingidoError():
            return HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=exc.message
            )
        case EmailJaCadastradoError() | CpfJaCadastradoError() | OabJaCadastradaError():
            return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message)
        case UsuarioNaoEncontradoError():
            return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
        case OperacaoNaoPermitidaError():
            return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)
        case ConviteInvalidoError():
            return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)
        case _:  # pragma: no cover — erro de programação, não de entrada
            raise exc


# ---- Convites (antes das rotas com {usuario_id} para não colidir) ----


@router.post("/invites", response_model=ConviteResponse, status_code=status.HTTP_201_CREATED)
async def create_invite(
    body: InviteRequest, admin: CurrentAdmin, session: SessionDep, email_sender: EmailDep
) -> ConviteResponse:
    """Convida um usuário para a organização do admin; reenvio cancela o anterior."""
    try:
        convite = await invite_service.convidar_usuario(
            session,
            email_sender,
            admin=admin,
            email=body.email,
            perfil=body.perfil,
            nome_completo=body.nome_completo,
        )
    except Exception as exc:  # noqa: BLE001 — traduzido em _map_error
        raise _map_error(exc) from exc
    return ConviteResponse.model_validate(convite)


@router.get("/invites", response_model=list[ConviteResponse])
async def list_invites(admin: CurrentAdmin, session: SessionDep) -> list[ConviteResponse]:
    convites = await invite_service.listar_convites(session, admin=admin)
    return [ConviteResponse.model_validate(c) for c in convites]


@router.post(
    "/accept-invite", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED
)
async def accept_invite(body: AcceptInviteRequest, session: SessionDep) -> UsuarioResponse:
    """Endpoint público: o convidado define a senha e entra na organização do convite."""
    try:
        usuario = await invite_service.aceitar_convite(
            session, token=body.token, senha=body.senha, nome_completo=body.nome_completo
        )
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc
    return UsuarioResponse.model_validate(usuario)


# ---- CRUD de usuários (RF04) ----


@router.post("", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: CreateUserRequest, admin: CurrentAdmin, session: SessionDep
) -> UsuarioResponse:
    """Cria um usuário na organização do administrador autenticado."""
    try:
        usuario = await user_service.criar_usuario(
            session,
            admin=admin,
            nome_completo=body.nome_completo,
            email=body.email,
            senha=body.senha,
            perfil=body.perfil,
            oab=body.oab,
            uf_oab=body.uf_oab,
            cpf=body.cpf,
            telefone=body.telefone,
        )
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc
    return UsuarioResponse.model_validate(usuario)


@router.get("", response_model=list[UsuarioResponse])
async def list_users(admin: CurrentAdmin, session: SessionDep) -> list[UsuarioResponse]:
    usuarios = await user_service.listar_usuarios(session, admin=admin)
    return [UsuarioResponse.model_validate(u) for u in usuarios]


@router.get("/{usuario_id}", response_model=UsuarioResponse)
async def get_user(
    usuario_id: uuid.UUID, admin: CurrentAdmin, session: SessionDep
) -> UsuarioResponse:
    try:
        usuario = await user_service.obter_usuario(session, admin=admin, usuario_id=usuario_id)
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc
    return UsuarioResponse.model_validate(usuario)


@router.patch("/{usuario_id}", response_model=UsuarioResponse)
async def update_user(
    usuario_id: uuid.UUID, body: UpdateUserRequest, admin: CurrentAdmin, session: SessionDep
) -> UsuarioResponse:
    try:
        usuario = await user_service.atualizar_usuario(
            session,
            admin=admin,
            usuario_id=usuario_id,
            campos=body.model_dump(exclude_unset=True),
        )
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc
    return UsuarioResponse.model_validate(usuario)


@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    usuario_id: uuid.UUID, admin: CurrentAdmin, session: SessionDep, redis: RedisDep
) -> None:
    """Desativação lógica (RF04 não permite exclusão física)."""
    try:
        await user_service.desativar_usuario(
            session, redis, admin=admin, usuario_id=usuario_id
        )
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc
