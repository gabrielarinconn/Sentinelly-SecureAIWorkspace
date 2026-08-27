class InvalidCredentialsError(Exception):
    """Email/password combination does not match an active user."""


class InvalidTokenError(Exception):
    """Token is missing, malformed, expired, or fails signature verification."""
