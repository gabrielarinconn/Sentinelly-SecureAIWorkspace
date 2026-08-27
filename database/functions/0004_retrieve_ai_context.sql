-- Fase 12 — la función técnicamente más importante del proyecto. SECURITY INVOKER (default):
-- corre con los privilegios de rw_app bajo el actor real (SET LOCAL app.current_user_id ya
-- fijado por el caller, igual que el resto de funciones de lectura). El JOIN contra
-- rw_messages hereda su policy de RLS (rw_messages_member_select, Fase 4) automáticamente —
-- la similitud vectorial NUNCA se calcula sobre una fila que el actor no podría ver de todos
-- modos. Este es el flujo exigido por el plan:
--
--   JWT → app.current_user_id → RLS → mensajes autorizados → similitud pgvector → top K
--
-- Nunca al revés (todos los mensajes → vector search → filtrar permisos en Python). No
-- existe combinación de p_query_embedding que le devuelva a un usuario una fila de un canal
-- del que no es miembro — la garantía se sostiene "aunque el LLM sea completamente
-- malicioso" (12.3): esta función ni siquiera sabe qué es un LLM, solo filtra por RLS.
--
-- Sin índice ANN (ivfflat/hnsw) todavía: con el tamaño del dataset de esta prueba, un índice
-- de aproximación no aporta nada real y hasta podría degradar la calidad del ranking —
-- reevaluar si el volumen de datos crece (nota de escala, no requisito de esta fase).
CREATE OR REPLACE FUNCTION retrieve_ai_context(
    p_query_embedding vector(1536),
    p_limit int DEFAULT 5
)
RETURNS TABLE (
    message_id uuid,
    channel_id uuid,
    sender_id uuid,
    content text,
    created_at timestamptz,
    similarity real
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        m.id,
        m.channel_id,
        m.sender_id,
        m.content,
        m.created_at,
        (1 - (e.embedding <=> p_query_embedding))::real AS similarity
    FROM rw_messages m
    JOIN rw_message_embeddings e ON e.message_id = m.id
    WHERE e.status = 'completed'
      AND m.message_status <> 'deleted'
    ORDER BY e.embedding <=> p_query_embedding
    LIMIT p_limit;
$$;
