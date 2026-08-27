from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

from backend.application.login import LoginUseCase
from backend.domain.errors import InvalidCredentialsError
from backend.infrastructure.db import get_app_connection
from backend.infrastructure.jwt_service import JwtTokenService
from backend.infrastructure.password_hasher import BcryptPasswordHasher
from backend.infrastructure.user_repository import PsycopgUserRepository

app = FastAPI(title="Sentinelly API")


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str


@app.post("/auth/login", response_model=LoginResponse)
def login(body: LoginRequest) -> LoginResponse:
    """Login mínimo (Fase 4). Sin refresh token todavía — eso llega en la Fase 15."""
    conn = get_app_connection()
    try:
        use_case = LoginUseCase(
            user_repository=PsycopgUserRepository(conn),
            password_hasher=BcryptPasswordHasher(),
            token_service=JwtTokenService(),
        )
        try:
            result = use_case.execute(body.email, body.password)
        except InvalidCredentialsError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    finally:
        conn.close()
    return LoginResponse(access_token=result.access_token, token_type=result.token_type)
