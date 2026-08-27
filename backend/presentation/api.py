from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from backend.application.cursor import encode_cursor
from backend.application.get_channel_messages import GetChannelMessagesUseCase
from backend.application.get_current_user import GetCurrentUserUseCase
from backend.application.issue_refresh_token import IssueRefreshTokenUseCase
from backend.application.list_channels import ListChannelsUseCase
from backend.application.login import LoginUseCase
from backend.application.logout import LogoutUseCase
from backend.application.refresh_token import RefreshTokenUseCase
from backend.application.search_messages import SearchMessagesUseCase
from backend.application.send_message import SendMessageUseCase
from backend.domain.errors import (
    EmptyMessageError,
    EmptySearchQueryError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    InvalidTokenError,
    MessageAccessDeniedError,
)
from backend.infrastructure.conversation_repository import PsycopgConversationRepository
from backend.infrastructure.db import authorized_transaction, get_app_connection
from backend.infrastructure.jwt_service import JwtTokenService
from backend.infrastructure.message_repository import PsycopgMessageRepository
from backend.infrastructure.password_hasher import BcryptPasswordHasher
from backend.infrastructure.realtime import broadcaster
from backend.infrastructure.refresh_token_repository import PsycopgRefreshTokenRepository
from backend.infrastructure.user_repository import PsycopgUserRepository
from backend.presentation.auth import get_current_user_id, user_id_from_ws_token

app = FastAPI(title="Sentinelly API")


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


@app.post("/auth/login", response_model=TokenPairResponse)
def login(body: LoginRequest) -> TokenPairResponse:
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
        refresh_token = IssueRefreshTokenUseCase(PsycopgRefreshTokenRepository(conn)).execute(result.user_id)
        conn.commit()
    finally:
        conn.close()
    return TokenPairResponse(access_token=result.access_token, refresh_token=refresh_token, token_type=result.token_type)


class RefreshRequest(BaseModel):
    refresh_token: str


@app.post("/auth/refresh", response_model=TokenPairResponse)
def refresh(body: RefreshRequest) -> TokenPairResponse:
    conn = get_app_connection()
    try:
        try:
            result = RefreshTokenUseCase(PsycopgRefreshTokenRepository(conn), JwtTokenService()).execute(body.refresh_token)
            conn.commit()
        except InvalidRefreshTokenError as exc:
            conn.commit()  # persiste la revocación en cascada de reuse detection, si aplicó
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    finally:
        conn.close()
    return TokenPairResponse(access_token=result.access_token, refresh_token=result.refresh_token, token_type=result.token_type)


class LogoutRequest(BaseModel):
    refresh_token: str


@app.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(body: LogoutRequest) -> None:
    conn = get_app_connection()
    try:
        LogoutUseCase(PsycopgRefreshTokenRepository(conn)).execute(body.refresh_token)
        conn.commit()
    finally:
        conn.close()


class SendMessageRequest(BaseModel):
    content: str


class MessageResponse(BaseModel):
    id: str
    channel_id: str
    sender_id: str
    content: Optional[str]
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


class PageResponse(BaseModel):
    items: list[MessageResponse]
    next_cursor: Optional[str]


@app.get("/channels/{channel_id}/messages", response_model=PageResponse)
def get_channel_messages(
    channel_id: str,
    cursor: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    user_id: str = Depends(get_current_user_id),
) -> PageResponse:
    conn = get_app_connection()
    try:
        with authorized_transaction(conn, user_id):
            repo = PsycopgMessageRepository(conn)
            messages = GetChannelMessagesUseCase(repo).execute(channel_id, cursor, limit)
    finally:
        conn.close()
    next_cursor = encode_cursor(messages[-1].created_at, messages[-1].id) if len(messages) == limit else None
    return PageResponse(
        items=[
            MessageResponse(id=m.id, channel_id=m.channel_id, sender_id=m.sender_id, content=m.content, status=m.status)
            for m in messages
        ],
        next_cursor=next_cursor,
    )


class SearchResultResponse(BaseModel):
    id: str
    channel_id: str
    sender_id: str
    headline: str
    rank: float


class SearchPageResponse(BaseModel):
    items: list[SearchResultResponse]
    next_cursor: Optional[str]


@app.get("/messages/search", response_model=SearchPageResponse)
def search_messages(
    q: str,
    cursor: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
) -> SearchPageResponse:
    conn = get_app_connection()
    try:
        with authorized_transaction(conn, user_id):
            repo = PsycopgMessageRepository(conn)
            try:
                results = SearchMessagesUseCase(repo).execute(q, cursor, limit)
            except EmptySearchQueryError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        conn.close()
    next_cursor = encode_cursor(results[-1].created_at, results[-1].id) if len(results) == limit else None
    return SearchPageResponse(
        items=[
            SearchResultResponse(id=r.id, channel_id=r.channel_id, sender_id=r.sender_id, headline=r.headline, rank=r.rank)
            for r in results
        ],
        next_cursor=next_cursor,
    )


class ConversationResponse(BaseModel):
    channel_id: str
    channel_name: str
    is_private: bool
    my_role: str


@app.get("/channels", response_model=list[ConversationResponse])
def list_channels(user_id: str = Depends(get_current_user_id)) -> list[ConversationResponse]:
    conn = get_app_connection()
    try:
        with authorized_transaction(conn, user_id):
            conversations = ListChannelsUseCase(PsycopgConversationRepository(conn)).execute()
    finally:
        conn.close()
    return [
        ConversationResponse(channel_id=c.channel_id, channel_name=c.channel_name, is_private=c.is_private, my_role=c.my_role)
        for c in conversations
    ]


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role_title: str


@app.get("/users/me", response_model=UserResponse)
def get_current_user(user_id: str = Depends(get_current_user_id)) -> UserResponse:
    conn = get_app_connection()
    try:
        try:
            user = GetCurrentUserUseCase(PsycopgUserRepository(conn)).execute(user_id)
        except InvalidCredentialsError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    finally:
        conn.close()
    return UserResponse(id=user.id, email=user.email, full_name=user.full_name, role_title=user.role_title)


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
