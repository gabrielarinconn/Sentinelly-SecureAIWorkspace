-- Fase 8/11: búsqueda léxica con highlighting (ts_headline), keyset pagination (D005). Igual
-- que get_channel_messages(): SECURITY INVOKER, sujeta a RLS — un usuario nunca ve resultados
-- de un canal privado ajeno, sin importar qué busque.
--
-- Ordena por (created_at, id) DESC, no por relevancia (ts_rank) — el plan exige keyset
-- pagination también para la búsqueda, y eso requiere un orden total estable en las mismas
-- columnas del cursor. `rank` se devuelve igual como dato informativo para el frontend.
--
-- websearch_to_tsquery() (no to_tsquery()) porque acepta lenguaje natural del usuario sin
-- que un término mal formado rompa la consulta con un error de sintaxis de tsquery.
CREATE OR REPLACE FUNCTION search_messages(
    p_query text,
    p_cursor_created_at timestamptz DEFAULT NULL,
    p_cursor_id uuid DEFAULT NULL,
    p_limit int DEFAULT 20
)
RETURNS TABLE (
    id uuid,
    channel_id uuid,
    sender_id uuid,
    headline text,
    created_at timestamptz,
    rank real
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        m.id,
        m.channel_id,
        m.sender_id,
        ts_headline(
            'spanish', m.content, websearch_to_tsquery('spanish', p_query),
            'StartSel=<mark>, StopSel=</mark>, MaxFragments=2, MaxWords=15, MinWords=5'
        ) AS headline,
        m.created_at,
        ts_rank(m.search_vector, websearch_to_tsquery('spanish', p_query)) AS rank
    FROM rw_messages m
    WHERE m.message_status <> 'deleted'
      AND m.search_vector @@ websearch_to_tsquery('spanish', p_query)
      AND (
            p_cursor_created_at IS NULL
            OR (m.created_at, m.id) < (p_cursor_created_at, p_cursor_id)
          )
    ORDER BY m.created_at DESC, m.id DESC
    LIMIT p_limit;
$$;
