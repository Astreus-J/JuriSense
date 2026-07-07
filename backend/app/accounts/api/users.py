from fastapi import APIRouter, HTTPException, status

from app.accounts.api.deps import CurrentAdmin
from app.accounts.api.schemas import CreateUserRequest, UsuarioResponse
from app.accounts.application import user_service
from app.accounts.domain.errors import (
    CpfJaCadastradoError,
    EmailJaCadastradoError,
    LimiteUsuariosAtingidoError,
    OabJaCadastradaError,
    SenhaFracaError,
)
from app.core.db import SessionDep

router = APIRouter(prefix="/users", tags=["users"])


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
    except SenhaFracaError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{exc.message}: {', '.join(exc.motivos)}",
        ) from exc
    except LimiteUsuariosAtingidoError as exc:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=exc.message
        ) from exc
    except (EmailJaCadastradoError, CpfJaCadastradoError, OabJaCadastradaError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    return UsuarioResponse.model_validate(usuario)
