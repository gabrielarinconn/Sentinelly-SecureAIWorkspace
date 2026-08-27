-- Fase 9: vista de conversaciones del usuario autenticado. security_invoker = true es
-- OBLIGATORIO aquí: sin él, PostgreSQL evalúa el acceso a rw_channels/rw_messages con los
-- privilegios del DUEÑO de la vista (el rol admin que la crea, que bypassa RLS por ser
-- superusuario) en vez de los del rol que realmente hace la consulta — la vista se
-- convertiría en un bypass silencioso de RLS, justo lo opuesto al principio central del
-- proyecto. Con security_invoker = true, corre como rw_app y respeta RLS de verdad.
CREATE VIEW view_user_conversations
WITH (security_invoker = true)
AS
SELECT
    c.id AS channel_id,
    c.name AS channel_name,
    c.is_private,
    cm.role AS my_role,
    cm.joined_at,
    (SELECT max(m.created_at) FROM rw_messages m WHERE m.channel_id = c.id) AS last_message_at
FROM rw_channels c
JOIN rw_channel_members cm ON cm.channel_id = c.id
WHERE cm.user_id = current_setting('app.current_user_id', true)::uuid;

-- a diferencia de FUNCTION/PROCEDURE (EXECUTE se otorga a PUBLIC por defecto), las vistas se
-- tratan como tablas: sin este GRANT explícito, rw_app recibe "permission denied".
GRANT SELECT ON view_user_conversations TO rw_app;
