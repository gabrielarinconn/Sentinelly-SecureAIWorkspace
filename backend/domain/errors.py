class InvalidCredentialsError(Exception):
    """Email/password combination does not match an active user."""


class InvalidTokenError(Exception):
    """Token is missing, malformed, expired, or fails signature verification."""


class EmptyMessageError(Exception):
    """Message content is blank."""


class MessageAccessDeniedError(Exception):
    """RLS denied the operation. Deliberately doesn't distinguish 'does not exist' from
    'exists but not yours' — that distinction itself would leak information (R09)."""


class EmptySearchQueryError(Exception):
    """Search query is blank."""


class ChannelAccessDeniedError(Exception):
    """RLS denied a channel-scoped operation (e.g. marking it as read) for a non-member."""


class InvalidDirectMessageTargetError(Exception):
    """rw_get_or_create_dm_channel rejected the target: self-DM or an inactive/unknown user."""


class InvalidRefreshTokenError(Exception):
    """Refresh token not recognized, expired, or reused after being revoked (Fase 15)."""
