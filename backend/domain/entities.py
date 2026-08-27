from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    id: str
    email: str
    full_name: str
    role_title: str
    is_active: bool
