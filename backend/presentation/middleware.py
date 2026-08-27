import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Fase 16: X-Correlation-ID entra por header (o se genera si falta), queda disponible en
    request.state para logs/metadata de auditoría, y siempre vuelve en la respuesta —
    incluida la de error. Es trazabilidad de REQUEST, nunca identidad: no reemplaza ni se
    mezcla con app.current_user_id (D003)."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
