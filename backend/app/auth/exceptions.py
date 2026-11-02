class AuthenticationError(Exception):
    """Raised when authentication credentials are missing, invalid, expired, or malformed."""
    pass


class AuthorizationError(Exception):
    """Raised when an authenticated principal lacks permission for a requested resource."""

    def __init__(self, message: str, status_code: int = 403):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

