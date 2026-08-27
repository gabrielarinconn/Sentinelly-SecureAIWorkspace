from fastapi import Header, HTTPException, status

from backend.domain.errors import InvalidTokenError
from backend.infrastructure.jwt_service import JwtTokenService


def get_current_user_id(authorization: str = Header(...)) -> str:
    """El user_id SIEMPRE sale del JWT verificado (regla dura) — nunca del body/query."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token.")
    token = authorization.removeprefix("Bearer ")
    try:
        return JwtTokenService().decode_access_token(token)
    except InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


def user_id_from_ws_token(token: str) -> str:
    """Igual que get_current_user_id, pero para WebSocket: los navegadores no permiten fijar
    el header Authorization en el handshake de WS, así que el token viaja como query param
    (?token=...). Sigue siendo el JWT verificado — nunca un user_id crudo del cliente."""
    return JwtTokenService().decode_access_token(token)
