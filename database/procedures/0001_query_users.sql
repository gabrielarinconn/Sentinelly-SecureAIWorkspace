-- Fase 9: procedimiento #1 (consulta de usuarios). Directorio abierto a cualquier usuario
-- autenticado — necesario para que el chat pueda resolver nombre/cargo de remitentes y
-- miembros de canal; rw_users no tiene RLS (Fase 4/5 solo cubren rw_channels/rw_messages/
-- rw_channel_members). No hay campos sensibles expuestos (no password_hash).
--
-- Usa el patrón REFCURSOR porque un PROCEDURE de PostgreSQL no puede devolver un result set
-- directamente como una función (esa es la diferencia real entre FUNCTION y PROCEDURE que
-- esta fase pide demostrar) — el caller abre el cursor con CALL y lo consume con FETCH,
-- dentro de la misma transacción.
CREATE OR REPLACE PROCEDURE rw_query_users(
    IN p_search text DEFAULT NULL,
    INOUT p_cursor refcursor DEFAULT 'rw_query_users_cursor'
)
LANGUAGE plpgsql
AS $$
BEGIN
    OPEN p_cursor FOR
        SELECT id, email, full_name, role_title, is_active, created_at
        FROM rw_users
        WHERE p_search IS NULL
           OR full_name ILIKE '%' || p_search || '%'
           OR email ILIKE '%' || p_search || '%'
        ORDER BY full_name;
END;
$$;
