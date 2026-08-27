from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from backend.application.login import LoginUseCase
from backend.application.send_message import SendMessageUseCase
from backend.domain.errors import EmptyMessageError, InvalidCredentialsError, InvalidTokenError, MessageAccessDeniedError
from backend.infrastructure.db import authorized_transaction, get_app_connection
from backend.infrastructure.jwt_service import JwtTokenService
from backend.infrastructure.message_repository import PsycopgMessageRepository
from backend.infrastructure.password_hasher import BcryptPasswordHasher
from backend.infrastructure.realtime import broadcaster
from backend.infrastructure.user_repository import PsycopgUserRepository
from backend.presentation.auth import get_current_user_id, user_id_from_ws_token

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


class SendMessageRequest(BaseModel):
    content: str


class MessageResponse(BaseModel):
    id: str
    channel_id: str
    sender_id: str
    content: str
    status: str


def _send_message_sync(channel_id: str, user_id: str, content: str) -> MessageResponse:
    conn = get_app_connection()
    try:
        with authorized_transaction(conn, user_id):
            repo = PsycopgMessageRepository(conn)
            message = SendMessageUseCase(repo).execute(channel_id, user_id, content)
    finally:
        conn.close()
    return MessageResponse(
        id=message.id, channel_id=message.channel_id, sender_id=message.sender_id, content=message.content, status=message.status
    )


@app.post("/channels/{channel_id}/messages", response_model=MessageResponse)
async def send_message(channel_id: str, body: SendMessageRequest, user_id: str = Depends(get_current_user_id)) -> MessageResponse:
    try:
        message = await run_in_threadpool(_send_message_sync, channel_id, user_id, body.content)
    except EmptyMessageError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except MessageAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="MESSAGE_ACCESS_DENIED") from exc
    # Realtime se emite SOLO después de que run_in_threadpool ya retornó — es decir, después
    # de que authorized_transaction hizo COMMIT. Nunca antes (Fase 7, orden estricto).
    await broadcaster.publish(channel_id, message.model_dump())
    return message


def _is_member_sync(channel_id: str, user_id: str) -> bool:
    conn = get_app_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT rw_is_channel_member(%s, %s)", (channel_id, user_id))
            row = cur.fetchone()
    finally:
        conn.close()
    return bool(row and row[0])


@app.websocket("/ws/channels/{channel_id}")
async def channel_websocket(websocket: WebSocket, channel_id: str, token: str) -> None:
    """Un cliente solo puede suscribirse a un canal del que es miembro — el token viaja como
    query param porque los navegadores no permiten fijar el header Authorization en el
    handshake de WebSocket. Sigue siendo el JWT verificado, nunca un user_id crudo."""
    try:
        user_id = user_id_from_ws_token(token)
    except InvalidTokenError:
        await websocket.close(code=4401)
        return

    if not await run_in_threadpool(_is_member_sync, channel_id, user_id):
        await websocket.close(code=4403)
        return

    await websocket.accept()
    queue = broadcaster.subscribe(channel_id)
    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        pass
    finally:
        broadcaster.unsubscribe(channel_id, queue)
