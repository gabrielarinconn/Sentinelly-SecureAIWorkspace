import bcrypt

from backend.domain.ports import PasswordHasher


class BcryptPasswordHasher(PasswordHasher):
    """Compatible con los hashes generados en el seed vía pgcrypto crypt(gen_salt('bf')) —
    mismo formato bcrypt estándar ($2a$/$2b$)."""

    def verify(self, plain_password: str, password_hash: str) -> bool:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
