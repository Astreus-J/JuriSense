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


class CpfJaCadastradoError(AccountsError):
    def __init__(self) -> None:
        super().__init__("CPF já cadastrado")


class OabJaCadastradaError(AccountsError):
    def __init__(self) -> None:
        super().__init__("OAB já cadastrada")


class OabInvalidaError(AccountsError):
    def __init__(self, motivo: str) -> None:
        super().__init__(f"OAB inválida: {motivo}")


class TokenRecuperacaoInvalidoError(AccountsError):
    def __init__(self) -> None:
        super().__init__("Token de recuperação inválido ou expirado")


class ConviteInvalidoError(AccountsError):
    def __init__(self) -> None:
        super().__init__("Convite inválido, expirado ou já utilizado")


class UsuarioNaoEncontradoError(AccountsError):
    def __init__(self) -> None:
        super().__init__("Usuário não encontrado")


class OperacaoNaoPermitidaError(AccountsError):
    def __init__(self, motivo: str) -> None:
        super().__init__(motivo)


class LimiteUsuariosAtingidoError(AccountsError):
    def __init__(self, plano: str, limite: int) -> None:
        super().__init__(
            f"Limite de {limite} usuário(s) ativo(s) do plano '{plano}' atingido; "
            "faça upgrade de plano para adicionar mais usuários"
        )
        self.plano = plano
        self.limite = limite
