from backend.domain.entities import User
from backend.domain.errors import InvalidCredentialsError
from backend.domain.ports import UserRepository


class GetCurrentUserUseCase:
    def __init__(self, user_repository: UserRepository):
        self._users = user_repository

    def execute(self, user_id: str) -> User:
        user = self._users.find_by_id(user_id)
        if user is None:
            # el JWT es válido pero el usuario ya no existe/fue desactivado desde que se emitió
            raise InvalidCredentialsError("User no longer active.")
        return user
