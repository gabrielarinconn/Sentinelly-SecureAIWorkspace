from typing import Optional

from backend.domain.entities import User
from backend.domain.ports import UserRepository


class ListUsersUseCase:
    """Directorio de usuarios (rw_query_users) para el selector de 'nuevo mensaje directo' —
    excluye al propio actor, no tiene sentido iniciar un DM consigo mismo."""

    def __init__(self, user_repository: UserRepository):
        self._users = user_repository

    def execute(self, search: Optional[str], actor_id: str) -> list[User]:
        return [u for u in self._users.search(search) if u.id != actor_id]
