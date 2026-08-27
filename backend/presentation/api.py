import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, Query, WebSocket, WebSocketDisconnect, status
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.application.ask_copilot import AskCopilotUseCase
from backend.application.cursor import encode_cursor
from backend.application.delete_message import DeleteMessageUseCase
from backend.application.edit_message import EditMessageUseCase
from backend.application.get_channel_messages import GetChannelMessagesUseCase
from backend.application.get_copilot_usage import GetCopilotUsageUseCase
from backend.application.get_current_user import GetCurrentUserUseCase
from backend.application.issue_refresh_token import IssueRefreshTokenUseCase
from backend.application.list_channels import ListChannelsUseCase
from backend.application.list_users import ListUsersUseCase
from backend.application.mark_channel_read import MarkChannelReadUseCase
from backend.application.start_direct_message import StartDirectMessageUseCase
from backend.domain.entities import Conversation, Message
from backend.application.login import LoginUseCase
from backend.application.logout import LogoutUseCase
from backend.application.refresh_token import RefreshTokenUseCase
from backend.application.search_messages import SearchMessagesUseCase
from backend.application.send_message import SendMessageUseCase
from backend.domain.errors import (
    ChannelAccessDeniedError,
    EmptyMessageError,
    EmptySearchQueryError,
    InvalidCredentialsError,
    InvalidDirectMessageTargetError,
    InvalidRefreshTokenError,
    InvalidTokenError,
    MessageAccessDeniedError,
)
from backend.infrastructure.conversation_repository import PsycopgConversationRepository
from backend.infrastructure.copilot_usage_repository import PsycopgCopilotUsageRepository
from backend.infrastructure.db import authorized_transaction, get_app_connection
from backend.infrastructure.deepseek_llm_provider import DeepSeekLLMProvider
from backend.infrastructure.embedding_worker import process_pending_embeddings
from backend.infrastructure.fastembed_provider import FastEmbedProvider
from backend.infrastructure.jwt_service import JwtTokenService
from backend.infrastructure.message_repository import PsycopgMessageRepository
from backend.infrastructure.password_hasher import BcryptPasswordHasher
from backend.infrastructure.realtime import broadcaster, presence
from backend.infrastructure.refresh_token_repository import PsycopgRefreshTokenRepository
from backend.infrastructure.user_repository import PsycopgUserRepository
from backend.presentation.auth import get_current_user_id, user_id_from_ws_token
from backend.presentation.errors import app_error, register_error_handlers
from backend.presentation.middleware import CorrelationIdMiddleware

# Singletons perezosos (Fase 18): FastEmbedProvider carga un modelo ONNX (~220MB) al
# instanciarse — hacerlo una vez por proceso, no una vez por request. DeepSeekLLMProvider
# también, para no leer os.environ["DEEPSEEK_API_KEY"] en cada llamada. Perezosos (no a nivel
# de módulo) para que importar este archivo no falle en entornos donde DEEPSEEK_API_KEY
# todavía no está seteada (ej. tests de fases anteriores que no tocan el copiloto).
_embedding_provider: Optional[FastEmbedProvider] = None
_llm_provider: Optional[DeepSeekLLMProvider] = None


def _get_embedding_provider() -> FastEmbedProvider:
    global _embedding_provider
    if _embedding_provider is None:
        _embedding_provider = FastEmbedProvider()
    return _embedding_provider


def _get_llm_provider() -> DeepSeekLLMProvider:
    global _llm_provider
    if _llm_provider is None:
        _llm_provider = DeepSeekLLMProvider()
    return _llm_provider


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Corre el worker de embeddings (Fase 10) en segundo plano mientras el proceso vive —
    sin esto, un mensaje recién enviado nunca pasaría de 'pending' a 'completed' salvo que
    algo externo llamara process_pending_embeddings() a mano (como hacían los tests antes de
    esta fase).

    DISABLE_COPILOT_BACKGROUND_WORKER=1 lo apaga — usado por tests/conftest.py: cada test que
    abre `with TestClient(app)` dispara este lifespan, y el loop de fondo competía por
    FOR UPDATE SKIP LOCKED con las llamadas explícitas a process_pending_embeddings() de los
    tests (causaba fallos intermitentes). La app en vivo (uvicorn, sin esta variable) sigue
    corriendo el worker normalmente."""
    if os.environ.get("DISABLE_COPILOT_BACKGROUND_WORKER") == "1":
        yield
        return

    async def embedding_worker_loop() -> None:
        while True:
            try:
                await run_in_threadpool(process_pending_embeddings, _get_embedding_provider())
            except Exception:
                pass  # un fallo puntual (ej. red) no debe tumbar el worker completo
            await asyncio.sleep(3)

    task = asyncio.create_task(embedding_worker_loop())
    yield
    task.cancel()


app = FastAPI(title="Sentinelly API", lifespan=lifespan)
app.add_middleware(CorrelationIdMiddleware)
# El origen del frontend en dev (Fase 17) — configurable porque en Docker (Fase 21) cambia.
# allow_credentials=False: la app usa Bearer tokens, no cookies, así que no hace falta y
# evita la combinación (con allow_origins abierto) que los navegadores rechazan.
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(","),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Correlation-ID"],
)
register_error_handlers(app)


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
            raise app_error(status.HTTP_401_UNAUTHORIZED, "INVALID_CREDENTIALS", str(exc)) from exc
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
            raise app_error(status.HTTP_401_UNAUTHORIZED, "INVALID_REFRESH_TOKEN", str(exc)) from exc
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
    created_at: datetime


def _message_to_response(m: Message) -> MessageResponse:
    return MessageResponse(
        id=m.id, channel_id=m.channel_id, sender_id=m.sender_id, content=m.content, status=m.status, created_at=m.created_at
    )


def _send_message_sync(channel_id: str, user_id: str, content: str) -> MessageResponse:
    conn = get_app_connection()
    try:
        with authorized_transaction(conn, user_id):
            repo = PsycopgMessageRepository(conn)
            message = SendMessageUseCase(repo).execute(channel_id, user_id, content)
    finally:
        conn.close()
    return _message_to_response(message)


@app.post("/channels/{channel_id}/messages", response_model=MessageResponse)
async def send_message(channel_id: str, body: SendMessageRequest, user_id: str = Depends(get_current_user_id)) -> MessageResponse:
    try:
        message = await run_in_threadpool(_send_message_sync, channel_id, user_id, body.content)
    except EmptyMessageError as exc:
        raise app_error(422, "EMPTY_MESSAGE", str(exc)) from exc
    except MessageAccessDeniedError as exc:
        raise app_error(status.HTTP_403_FORBIDDEN, "MESSAGE_ACCESS_DENIED", "You do not have access to this channel.") from exc
    # Realtime se emite SOLO después de que run_in_threadpool ya retornó — es decir, después
    # de que authorized_transaction hizo COMMIT. Nunca antes (Fase 7, orden estricto).
    await broadcaster.publish(channel_id, {**message.model_dump(mode="json"), "event": "message_created"})
    return message


class EditMessageRequest(BaseModel):
    content: str


def _edit_message_sync(message_id: str, user_id: str, content: str) -> MessageResponse:
    conn = get_app_connection()
    try:
        with authorized_transaction(conn, user_id):
            repo = PsycopgMessageRepository(conn)
            message = EditMessageUseCase(repo).execute(message_id, content)
    finally:
        conn.close()
    return _message_to_response(message)


@app.patch("/messages/{message_id}", response_model=MessageResponse)
async def edit_message(message_id: str, body: EditMessageRequest, user_id: str = Depends(get_current_user_id)) -> MessageResponse:
    try:
        message = await run_in_threadpool(_edit_message_sync, message_id, user_id, body.content)
    except EmptyMessageError as exc:
        raise app_error(422, "EMPTY_MESSAGE", str(exc)) from exc
    except MessageAccessDeniedError as exc:
        raise app_error(status.HTTP_403_FORBIDDEN, "MESSAGE_ACCESS_DENIED", "You do not have access to this message.") from exc
    await broadcaster.publish(message.channel_id, {**message.model_dump(mode="json"), "event": "message_edited"})
    return message


def _delete_message_sync(message_id: str, user_id: str) -> MessageResponse:
    conn = get_app_connection()
    try:
        with authorized_transaction(conn, user_id):
            repo = PsycopgMessageRepository(conn)
            message = DeleteMessageUseCase(repo).execute(message_id)
    finally:
        conn.close()
    return _message_to_response(message)


@app.delete("/messages/{message_id}", response_model=MessageResponse)
async def delete_message(message_id: str, user_id: str = Depends(get_current_user_id)) -> MessageResponse:
    try:
        message = await run_in_threadpool(_delete_message_sync, message_id, user_id)
    except MessageAccessDeniedError as exc:
        raise app_error(status.HTTP_403_FORBIDDEN, "MESSAGE_ACCESS_DENIED", "You do not have access to this message.") from exc
    await broadcaster.publish(message.channel_id, {**message.model_dump(mode="json"), "event": "message_deleted"})
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
        items=[_message_to_response(m) for m in messages],
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
                raise app_error(422, "EMPTY_SEARCH_QUERY", str(exc)) from exc
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
    channel_name: Optional[str]
    is_private: bool
    my_role: str
    member_count: int
    unread_count: int
    is_direct: bool
    dm_peer_id: Optional[str]
    dm_peer_name: Optional[str]


def _conversation_to_response(c: Conversation) -> ConversationResponse:
    return ConversationResponse(
        channel_id=c.channel_id,
        channel_name=c.channel_name,
        is_private=c.is_private,
        my_role=c.my_role,
        member_count=c.member_count,
        unread_count=c.unread_count,
        is_direct=c.is_direct,
        dm_peer_id=c.dm_peer_id,
        dm_peer_name=c.dm_peer_name,
    )


@app.get("/channels", response_model=list[ConversationResponse])
def list_channels(user_id: str = Depends(get_current_user_id)) -> list[ConversationResponse]:
    conn = get_app_connection()
    try:
        with authorized_transaction(conn, user_id):
            conversations = ListChannelsUseCase(PsycopgConversationRepository(conn)).execute()
    finally:
        conn.close()
    return [_conversation_to_response(c) for c in conversations]


def _mark_channel_read_sync(channel_id: str, user_id: str) -> None:
    conn = get_app_connection()
    try:
        with authorized_transaction(conn, user_id):
            MarkChannelReadUseCase(PsycopgConversationRepository(conn)).execute(channel_id, user_id)
    finally:
        conn.close()


@app.post("/channels/{channel_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_channel_read(channel_id: str, user_id: str = Depends(get_current_user_id)) -> None:
    try:
        await run_in_threadpool(_mark_channel_read_sync, channel_id, user_id)
    except ChannelAccessDeniedError as exc:
        raise app_error(status.HTTP_403_FORBIDDEN, "CHANNEL_ACCESS_DENIED", "You do not have access to this channel.") from exc


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
            raise app_error(status.HTTP_401_UNAUTHORIZED, "INVALID_CREDENTIALS", str(exc)) from exc
    finally:
        conn.close()
    return UserResponse(id=user.id, email=user.email, full_name=user.full_name, role_title=user.role_title)


@app.get("/users", response_model=list[UserResponse])
def list_users(search: Optional[str] = Query(default=None), user_id: str = Depends(get_current_user_id)) -> list[UserResponse]:
    conn = get_app_connection()
    try:
        with authorized_transaction(conn, user_id):
            users = ListUsersUseCase(PsycopgUserRepository(conn)).execute(search, user_id)
    finally:
        conn.close()
    return [UserResponse(id=u.id, email=u.email, full_name=u.full_name, role_title=u.role_title) for u in users]


class StartDirectMessageRequest(BaseModel):
    other_user_id: str


def _start_direct_message_sync(other_user_id: str, user_id: str) -> Conversation:
    conn = get_app_connection()
    try:
        with authorized_transaction(conn, user_id):
            return StartDirectMessageUseCase(PsycopgConversationRepository(conn)).execute(other_user_id)
    finally:
        conn.close()


@app.post("/dms", response_model=ConversationResponse)
async def start_direct_message(body: StartDirectMessageRequest, user_id: str = Depends(get_current_user_id)) -> ConversationResponse:
    try:
        conversation = await run_in_threadpool(_start_direct_message_sync, body.other_user_id, user_id)
    except InvalidDirectMessageTargetError as exc:
        raise app_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "INVALID_DM_TARGET", "Cannot start a direct message with this user.") from exc
    return _conversation_to_response(conversation)


class AskCopilotRequest(BaseModel):
    question: str


class CitationResponse(BaseModel):
    message_id: str
    channel_id: str


class AskCopilotResponse(BaseModel):
    answer: str
    citations: list[CitationResponse]


def _ask_copilot_sync(user_id: str, question: str) -> AskCopilotResponse:
    conn = get_app_connection()
    try:
        with authorized_transaction(conn, user_id):
            use_case = AskCopilotUseCase(
                message_repository=PsycopgMessageRepository(conn),
                user_repository=PsycopgUserRepository(conn),
                embedding_provider=_get_embedding_provider(),
                llm_provider=_get_llm_provider(),
                copilot_usage_repository=PsycopgCopilotUsageRepository(conn),
            )
            answer = use_case.execute(user_id, question)
    finally:
        conn.close()
    return AskCopilotResponse(
        answer=answer.answer,
        citations=[CitationResponse(message_id=c.message_id, channel_id=c.channel_id) for c in answer.citations],
    )


@app.post("/copilot/ask", response_model=AskCopilotResponse)
async def ask_copilot(body: AskCopilotRequest, user_id: str = Depends(get_current_user_id)) -> AskCopilotResponse:
    try:
        return await run_in_threadpool(_ask_copilot_sync, user_id, body.question)
    except EmptySearchQueryError as exc:
        raise app_error(422, "EMPTY_QUESTION", str(exc)) from exc


class CopilotUsageResponse(BaseModel):
    total_questions: int
    total_prompt_tokens: int
    total_completion_tokens: int


@app.get("/copilot/usage", response_model=CopilotUsageResponse)
def get_copilot_usage(user_id: str = Depends(get_current_user_id)) -> CopilotUsageResponse:
    conn = get_app_connection()
    try:
        with authorized_transaction(conn, user_id):
            usage = GetCopilotUsageUseCase(PsycopgCopilotUsageRepository(conn)).execute()
    finally:
        conn.close()
    return CopilotUsageResponse(
        total_questions=usage.total_questions,
        total_prompt_tokens=usage.total_prompt_tokens,
        total_completion_tokens=usage.total_completion_tokens,
    )


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


@app.websocket("/ws/presence")
async def presence_websocket(websocket: WebSocket, token: str) -> None:
    """Un único socket global por sesión de cliente (no uno por canal, D008-style
    single-process) — informa quién está online entre las personas con las que el actor
    comparte algún canal. No filtra por RLS porque no expone contenido, solo un booleano
    online/offline por user_id, igual criterio que rw_is_channel_member (functions/0001).

    A diferencia de channel_websocket (que solo envía), este socket corre un receiver en
    paralelo puramente para detectar el cierre de la conexión cuanto antes: el cliente nunca
    manda nada por aquí, pero sin leer activamente, un `await websocket.receive()` nunca
    dispara y un usuario que cierra la pestaña sin que nadie más se conecte/desconecte después
    quedaría marcado online para siempre (nada volvería a intentar escribirle para revelar que
    el socket ya está cerrado)."""
    try:
        user_id = user_id_from_ws_token(token)
    except InvalidTokenError:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    await presence.connect(user_id)
    queue = presence.subscribe()

    async def sender() -> None:
        await websocket.send_json({"event": "presence_snapshot", "user_ids": presence.online_user_ids()})
        while True:
            event = await queue.get()
            await websocket.send_json(event)

    async def receiver() -> None:
        while True:
            await websocket.receive()

    sender_task = asyncio.create_task(sender())
    receiver_task = asyncio.create_task(receiver())
    try:
        await asyncio.wait({sender_task, receiver_task}, return_when=asyncio.FIRST_COMPLETED)
    finally:
        sender_task.cancel()
        receiver_task.cancel()
        presence.unsubscribe(queue)
        await presence.disconnect(user_id)
