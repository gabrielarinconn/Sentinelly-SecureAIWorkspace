import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse


def app_error(status_code: int, code: str, message: str) -> HTTPException:
    """Construye un HTTPException cuyo detail ya trae la forma que espera el envelope
    uniforme de error (Fase 16) — nunca se lanza HTTPException con un string suelto."""
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def _correlation_id(request: Request) -> str:
    return getattr(request.state, "correlation_id", None) or str(uuid.uuid4())


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
        correlation_id = _correlation_id(request)
        detail = exc.detail
        if isinstance(detail, dict) and "code" in detail:
            code, message = detail["code"], detail.get("message", "")
        else:
            code, message = "HTTP_ERROR", str(detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": code, "message": message, "correlation_id": correlation_id}},
            headers={"X-Correlation-ID": correlation_id},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
        # nunca se filtra el detalle interno (stack trace, mensaje de driver) al cliente —
        # eso sí queda en los logs del servidor, correlacionado por el mismo correlation_id.
        correlation_id = _correlation_id(request)
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INTERNAL_ERROR", "message": "Unexpected server error.", "correlation_id": correlation_id}},
            headers={"X-Correlation-ID": correlation_id},
        )
