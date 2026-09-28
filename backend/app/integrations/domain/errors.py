class IntegrationError(Exception):
    """Domain error for the Integrations bounded context."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class IntegrationNotFoundError(IntegrationError):
    def __init__(self) -> None:
        super().__init__("Integration not found")
