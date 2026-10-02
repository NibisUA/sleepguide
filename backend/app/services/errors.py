class DomainError(Exception):
    """Business-rule violation; the API layer maps `code` to an HTTP status."""

    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(message or code)
        self.code = code
        self.message = message or code
