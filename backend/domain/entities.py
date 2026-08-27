from dataclasses import dataclass
from datetime import datetime


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
    content: str
    status: str
    created_at: datetime
    updated_at: datetime
