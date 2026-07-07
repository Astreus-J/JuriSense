class AccountsError(Exception):
    """Erro de domínio do contexto Accounts."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class EmailJaCadastradoError(AccountsError):
    def __init__(self) -> None:
        super().__init__("E-mail já cadastrado")


class SenhaFracaError(AccountsError):
    def __init__(self, motivos: list[str]) -> None:
        super().__init__("Senha não atende à política de segurança")
        self.motivos = motivos


class CredenciaisInvalidasError(AccountsError):
    def __init__(self) -> None:
        super().__init__("Credenciais inválidas")


class ContaBloqueadaError(AccountsError):
    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("Conta temporariamente bloqueada por excesso de tentativas")
        self.retry_after_seconds = retry_after_seconds


class UsuarioInativoError(AccountsError):
    def __init__(self) -> None:
        super().__init__("Usuário inativo")


class RefreshTokenInvalidoError(AccountsError):
    def __init__(self) -> None:
        super().__init__("Sessão inválida ou expirada")
