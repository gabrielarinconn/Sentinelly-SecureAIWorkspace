-- Fase 8/11: historial de un canal, keyset pagination (D005 — nunca OFFSET). SECURITY
-- INVOKER (default): corre con los privilegios de rw_app, por lo tanto sujeta a la policy
-- rw_messages_member_select (Fase 4) — un non-member que llame esto con cualquier
-- channel_id ajeno recibe 0 filas, nunca un error que revele si el canal existe.
CREATE OR REPLACE FUNCTION get_channel_messages(
    p_channel_id uuid,
    p_cursor_created_at timestamptz DEFAULT NULL,
    p_cursor_id uuid DEFAULT NULL,
    p_limit int DEFAULT 50
)
RETURNS TABLE (
    id uuid,
    channel_id uuid,
    sender_id uuid,
    content text,
    message_status varchar,
    created_at timestamptz,
    updated_at timestamptz
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        m.id,
        m.channel_id,
        m.sender_id,
        -- un mensaje eliminado no expone su contenido a los lectores del canal, aunque siga
        -- vivo en rw_message_history para auditoría (R06/R07).
        CASE WHEN m.message_status = 'deleted' THEN NULL ELSE m.content END AS content,
        m.message_status,
        m.created_at,
        m.updated_at
    FROM rw_messages m
    WHERE m.channel_id = p_channel_id
      AND (
            p_cursor_created_at IS NULL
            OR (m.created_at, m.id) < (p_cursor_created_at, p_cursor_id)
          )
    ORDER BY m.created_at DESC, m.id DESC
    LIMIT p_limit;
$$;
