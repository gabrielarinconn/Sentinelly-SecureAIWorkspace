import os
from contextlib import contextmanager
from typing import Iterator

import psycopg


def get_app_connection() -> psycopg.Connection:
    """Conexión con el rol de aplicación (rw_app: sin SUPERUSER, sin BYPASSRLS, Fase 4).
    Nunca usa el rol admin (DATABASE_URL) — ese es solo para migrar/seedear."""
    return psycopg.connect(os.environ["RW_APP_DATABASE_URL"])


@contextmanager
def authorized_transaction(conn: psycopg.Connection, user_id: str) -> Iterator[psycopg.Connection]:
    """Abre una transacción con el actor fijado vía SET LOCAL app.current_user_id.

    El user_id SIEMPRE viene del JWT ya verificado por el caller — nunca del body del
    request (regla dura del proyecto). RLS decide qué filas son visibles a partir de aquí.
    """
    with conn.transaction():
        with conn.cursor() as cur:
            # SET LOCAL no admite parámetros bindeados (limitación del protocolo de
            # PostgreSQL) — set_config(..., true) es el equivalente parametrizable.
            cur.execute("SELECT set_config('app.current_user_id', %s, true)", (str(user_id),))
        yield conn
