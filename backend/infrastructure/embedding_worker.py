from backend.domain.ports import EmbeddingProvider
from backend.infrastructure.db import get_admin_connection


def process_pending_embeddings(embedding_provider: EmbeddingProvider, limit: int = 10) -> int:
    """Worker asíncrono (Fase 10): corre FUERA de la transacción SQL que insertó/editó el
    mensaje — el trigger (database/triggers/0003_message_embeddings_pending.sql) solo dejó la
    fila en 'pending'; acá es donde se llama al proveedor de embeddings de verdad.

    Usa la conexión admin (bypassa RLS), no rw_app: este worker es un proceso de sistema sin
    actor humano detrás, necesita ver mensajes pendientes de TODOS los canales para poder
    vectorizarlos — si usara rw_app sin un app.current_user_id fijado, RLS le devolvería 0
    filas de rw_messages (fail-closed) y el worker nunca procesaría nada. El vector resultante
    solo se vuelve visible a un usuario real más adelante, a través de retrieve_ai_context()
    (Fase 12), que sí corre bajo RLS con el actor real.

    `FOR UPDATE SKIP LOCKED` evita que dos instancias del worker procesen la misma fila dos
    veces. Retorna cuántos mensajes procesó (útil para tests y logging).
    """
    conn = get_admin_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT me.message_id, m.content
                FROM rw_message_embeddings me
                JOIN rw_messages m ON m.id = me.message_id
                WHERE me.status = 'pending' AND m.message_status <> 'deleted'
                ORDER BY me.updated_at
                LIMIT %s
                FOR UPDATE SKIP LOCKED
                """,
                (limit,),
            )
            rows = cur.fetchall()

            for message_id, content in rows:
                try:
                    vector = embedding_provider.embed(content)
                except Exception:
                    cur.execute(
                        "UPDATE rw_message_embeddings SET status = 'failed', updated_at = now() WHERE message_id = %s",
                        (message_id,),
                    )
                    continue
                # register_vector() (backend/infrastructure/db.py) adapta list[float] <-> vector.
                cur.execute(
                    "UPDATE rw_message_embeddings SET embedding = %s, status = 'completed', updated_at = now() WHERE message_id = %s",
                    (vector, message_id),
                )
        conn.commit()
    finally:
        conn.close()
    return len(rows)
