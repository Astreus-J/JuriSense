from fastapi import APIRouter, HTTPException, Request, status

from app.accounts.api.deps import AccessPayload, CurrentUser, EmailDep
from app.accounts.api.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UsuarioResponse,
)
from app.accounts.application import auth_service, password_service
from app.accounts.domain.errors import (
    ContaBloqueadaError,
    CredenciaisInvalidasError,
    EmailJaCadastradoError,
    RefreshTokenInvalidoError,
    SenhaFracaError,
    TokenRecuperacaoInvalidoError,
    UsuarioInativoError,
)
from app.core.db import SessionDep
from app.core.redis import RedisDep

router = APIRouter(prefix="/auth", tags=["auth"])


_REGISTRO_RECEBIDO = "Cadastro recebido; verifique seu e-mail para os próximos passos."


@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_202_ACCEPTED)
async def register(
    body: RegisterRequest, session: SessionDep, email_sender: EmailDep
) -> MessageResponse:
    """Resposta idêntica exista o e-mail ou não (MED-002: evita enumeração)."""
    try:
        await auth_service.registrar_organizacao(
            session,
            organizacao_nome=body.organizacao_nome,
            nome_completo=body.nome_completo,
            email=body.email,
            senha=body.senha,
            oab=body.oab,
            uf_oab=body.uf_oab,
            cpf=body.cpf,
            telefone=body.telefone,
            plano=body.plano,
        )
    except SenhaFracaError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{exc.message}: {', '.join(exc.motivos)}",
        ) from exc
    except EmailJaCadastradoError:
        await email_sender.send(
            to=body.email.strip().lower(),
            subject="JuriSense — Tentativa de cadastro",
            body=(
                "Alguém tentou criar uma conta no JuriSense com este e-mail, "
                "que já está cadastrado. Se foi você, faça login ou recupere sua senha."
            ),
        )
        return MessageResponse(detail=_REGISTRO_RECEBIDO)
    return MessageResponse(detail=_REGISTRO_RECEBIDO)


@router.post(
    "/password/forgot", response_model=MessageResponse, status_code=status.HTTP_202_ACCEPTED
)
async def forgot_password(
    body: ForgotPasswordRequest, session: SessionDep, email_sender: EmailDep
) -> MessageResponse:
    await password_service.solicitar_recuperacao(session, email_sender, email=body.email)
    return MessageResponse(
        detail="Se o e-mail estiver cadastrado, enviaremos um link de recuperação."
    )


@router.post("/password/reset", response_model=MessageResponse)
async def reset_password(
    body: ResetPasswordRequest, session: SessionDep, redis: RedisDep, email_sender: EmailDep
) -> MessageResponse:
    try:
        await password_service.redefinir_senha(
            session, redis, email_sender, token=body.token, nova_senha=body.nova_senha
        )
    except SenhaFracaError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{exc.message}: {', '.join(exc.motivos)}",
        ) from exc
    except TokenRecuperacaoInvalidoError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message
        ) from exc
    return MessageResponse(detail="Senha redefinida com sucesso.")


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest, request: Request, session: SessionDep, redis: RedisDep
) -> TokenResponse:
    try:
        tokens = await auth_service.login(
            session,
            redis,
            email=body.email,
            senha=body.senha,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except ContaBloqueadaError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=exc.message,
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc
    except (CredenciaisInvalidasError, UsuarioInativoError) as exc:
        # Mesma resposta para usuário inexistente, senha errada e conta inativa
        # (evita enumeração de usuários)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas"
        ) from exc
    return TokenResponse(access_token=tokens.access_token, refresh_token=tokens.refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, session: SessionDep, redis: RedisDep) -> TokenResponse:
    try:
        tokens = await auth_service.renovar_tokens(session, redis, refresh_token=body.refresh_token)
    except RefreshTokenInvalidoError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message
        ) from exc
    return TokenResponse(access_token=tokens.access_token, refresh_token=tokens.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: LogoutRequest, payload: AccessPayload, redis: RedisDep) -> None:
    await auth_service.logout(redis, access_payload=payload, refresh_token=body.refresh_token)


@router.get("/me", response_model=UsuarioResponse)
async def me(usuario: CurrentUser) -> UsuarioResponse:
    return UsuarioResponse.model_validate(usuario)
