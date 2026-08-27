import hashlib
import secrets


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def hash_refresh_token(raw_token: str) -> str:
    # SHA-256 alcanza acá: a diferencia de una password humana (baja entropía, hay que
    # encarecer el cómputo con bcrypt para resistir fuerza bruta), un refresh token ya es un
    # secreto aleatorio de 256 bits (secrets.token_urlsafe) — SHA-256 es la práctica estándar
    # para hashear tokens de este tipo, no contraseñas.
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
