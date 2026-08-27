from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class User:
    id: str
    email: str
    full_name: str
    role_title: str
    is_active: bool


@dataclass(frozen=True)
class Message:
    id: str
    channel_id: str
    sender_id: str
    content: Optional[str]  # None cuando status == 'deleted' (enmascarado, R06)
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class SearchResult:
    id: str
    channel_id: str
    sender_id: str
    headline: str
    created_at: datetime
    rank: float


@dataclass(frozen=True)
class Conversation:
    channel_id: str
    channel_name: str
    is_private: bool
    my_role: str
    last_message_at: Optional[datetime]
    member_count: int
    unread_count: int
    is_direct: bool
    dm_peer_id: Optional[str]
    dm_peer_name: Optional[str]


@dataclass(frozen=True)
class RefreshTokenRecord:
    id: str
    user_id: str
    revoked_at: Optional[datetime]
    replaced_by_token_id: Optional[str]
    expires_at: datetime


@dataclass(frozen=True)
class RetrievedContext:
    message_id: str
    channel_id: str
    sender_id: str
    content: str
    created_at: datetime
    similarity: float


@dataclass(frozen=True)
class LLMCompletion:
    text: str
    prompt_tokens: int
    completion_tokens: int


@dataclass(frozen=True)
class Citation:
    message_id: str
    channel_id: str
    sender_id: str
    content: str
    citation_number: int


@dataclass(frozen=True)
class CopilotAnswer:
    answer: str
    citations: list[Citation]


@dataclass(frozen=True)
class CopilotUsage:
    total_questions: int
    total_prompt_tokens: int
    total_completion_tokens: int
