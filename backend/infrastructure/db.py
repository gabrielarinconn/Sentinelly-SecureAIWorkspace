import os
from contextlib import contextmanager
from typing import Iterator

import psycopg
from pgvector.psycopg import register_vector


def get_app_connection() -> psycopg.Connection:
    """Conexión con el rol de aplicación (rw_app: sin SUPERUSER, sin BYPASSRLS, Fase 4).
    Usar SIEMPRE para código que atiende una request de un usuario autenticado.

    Nota (Fase 12): al pasar un list[float] como parámetro de una función SQL que espera
    `vector` (ej. retrieve_ai_context), hace falta castear explícitamente en la query
    (`%s::vector`) — Postgres solo infiere `vector` desde un array sin tipo en contexto de
    asignación (INSERT/UPDATE ... SET columna = %s), no en la posición de un argumento de
    función."""
    conn = psycopg.connect(os.environ["RW_APP_DATABASE_URL"])
    register_vector(conn)  # adapta vector <-> list[float] automáticamente (Fase 10/12)
    return conn


def get_admin_connection() -> psycopg.Connection:
    """Conexión con el rol admin (superusuario del contenedor, bypassa RLS).

    Reservada para procesos de sistema sin actor humano detrás — hoy, únicamente el worker
    de embeddings (Fase 10), que necesita ver TODOS los mensajes pendientes de vectorizar sin
    estar limitado a lo que un usuario particular podría autorizar. No usarla nunca para
    código que responde a una request HTTP de un usuario: eso es exactamente lo que
    get_app_connection() + RLS existen para evitar."""
    conn = psycopg.connect(os.environ["DATABASE_URL"])
    register_vector(conn)
    return conn


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
