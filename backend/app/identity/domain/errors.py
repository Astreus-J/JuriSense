class IdentityError(Exception):
    """Domain error for the Identity & Organizations bounded context."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class EmailAlreadyRegisteredError(IdentityError):
    def __init__(self) -> None:
        super().__init__("Email already registered")


class WeakPasswordError(IdentityError):
    def __init__(self, reasons: list[str]) -> None:
        super().__init__("Password does not meet the security policy")
        self.reasons = reasons


class InvalidCredentialsError(IdentityError):
    def __init__(self) -> None:
        super().__init__("Invalid credentials")


class AccountLockedError(IdentityError):
    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("Account temporarily locked due to too many failed attempts")
        self.retry_after_seconds = retry_after_seconds


class UserInactiveError(IdentityError):
    def __init__(self) -> None:
        super().__init__("Inactive user")


class InvalidRefreshTokenError(IdentityError):
    def __init__(self) -> None:
        super().__init__("Invalid or expired session")


class InvalidPasswordResetTokenError(IdentityError):
    def __init__(self) -> None:
        super().__init__("Invalid or expired password reset token")


class InvalidInvitationError(IdentityError):
    def __init__(self) -> None:
        super().__init__("Invalid, expired, or already used invitation")


class UserNotFoundError(IdentityError):
    def __init__(self) -> None:
        super().__init__("User not found")


class OperationNotAllowedError(IdentityError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)


class UserLimitReachedError(IdentityError):
    def __init__(self, plan: str, limit: int) -> None:
        super().__init__(
            f"Limit of {limit} active user(s) on the '{plan}' plan reached; "
            "upgrade your plan to add more users"
        )
        self.plan = plan
        self.limit = limit
