-- Restyling pass: soporte de Mensajes Directos (DM). Reutiliza rw_channels/rw_channel_members
-- en vez de un modelo paralelo: un DM es un canal con is_direct=true, exactamente 2 miembros,
-- sin nombre propio (el frontend muestra el nombre del OTRO miembro, resuelto en la vista —
-- ver views/0004_user_conversations_direct_messages.sql). La RLS de rw_channels/rw_messages
-- (migrations/policies de Fase 4/6) ya es genérica por membresía — funciona para DMs sin
-- cambios, ni en las policies ni en los endpoints de mensajería existentes.
ALTER TABLE rw_channels ADD COLUMN is_direct BOOLEAN NOT NULL DEFAULT false;

ALTER TABLE rw_channels ALTER COLUMN name DROP NOT NULL;
ALTER TABLE rw_channels DROP CONSTRAINT rw_channels_name_not_blank;
ALTER TABLE rw_channels ADD CONSTRAINT rw_channels_name_not_blank
    CHECK (name IS NULL OR btrim(name) <> '');
ALTER TABLE rw_channels ADD CONSTRAINT rw_channels_direct_has_no_name
    CHECK (NOT is_direct OR name IS NULL);

COMMENT ON COLUMN rw_channels.is_direct IS 'true = canal 1:1 entre dos usuarios (DM), sin nombre propio.';
