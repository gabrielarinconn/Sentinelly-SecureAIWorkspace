-- Restyling pass: agrega unread_count a la vista de conversaciones — mensajes de OTROS
-- usuarios, no eliminados, posteriores al último rw_channel_reads.last_read_at del actor (o
-- todos si nunca marcó el canal como leído). security_invoker se mantiene (ver
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
    (SELECT count(*) FROM rw_channel_members cm2 WHERE cm2.channel_id = c.id) AS member_count,
    (
        SELECT count(*)
        FROM rw_messages m
        WHERE m.channel_id = c.id
          AND m.message_status <> 'deleted'
          AND m.sender_id <> cm.user_id
          AND m.created_at > COALESCE(
              (SELECT cr.last_read_at FROM rw_channel_reads cr
               WHERE cr.channel_id = c.id AND cr.user_id = cm.user_id),
              '-infinity'::timestamptz
          )
    ) AS unread_count
FROM rw_channels c
JOIN rw_channel_members cm ON cm.channel_id = c.id
WHERE cm.user_id = current_setting('app.current_user_id', true)::uuid;

GRANT SELECT ON view_user_conversations TO rw_app;
