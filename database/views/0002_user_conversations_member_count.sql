-- Restyling pass: agrega member_count a la vista de conversaciones para mostrar el número de
-- miembros por canal en la UI sin una query adicional por canal. CREATE OR REPLACE VIEW admite
-- agregar columnas al final sin romper la vista existente. security_invoker se mantiene (ver
-- views/0001_user_conversations.sql): sigue evaluando bajo rw_app, nunca bypassa RLS.
CREATE OR REPLACE VIEW view_user_conversations
WITH (security_invoker = true)
AS
SELECT
    c.id AS channel_id,
    c.name AS channel_name,
    c.is_private,
    cm.role AS my_role,
    cm.joined_at,
    (SELECT max(m.created_at) FROM rw_messages m WHERE m.channel_id = c.id) AS last_message_at,
    (SELECT count(*) FROM rw_channel_members cm2 WHERE cm2.channel_id = c.id) AS member_count
FROM rw_channels c
JOIN rw_channel_members cm ON cm.channel_id = c.id
WHERE cm.user_id = current_setting('app.current_user_id', true)::uuid;

GRANT SELECT ON view_user_conversations TO rw_app;
