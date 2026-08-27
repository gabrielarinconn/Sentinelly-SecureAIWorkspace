-- Fase 4: RLS sobre rw_channels y rw_messages. El actor autenticado se fija por transacción
-- con SET LOCAL app.current_user_id = '<uuid>' (nunca del body del request — siempre del JWT
-- verificado). Si nunca se fija, current_setting(..., true) devuelve NULL y las políticas
-- deniegan por defecto (fail-closed), no fallan con error.

ALTER TABLE rw_channels ENABLE ROW LEVEL SECURITY;
ALTER TABLE rw_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY rw_channels_member_select ON rw_channels
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM rw_channel_members cm
            WHERE cm.channel_id = rw_channels.id
              AND cm.user_id = current_setting('app.current_user_id', true)::uuid
        )
    );

CREATE POLICY rw_messages_member_select ON rw_messages
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM rw_channel_members cm
            WHERE cm.channel_id = rw_messages.channel_id
              AND cm.user_id = current_setting('app.current_user_id', true)::uuid
        )
    );

-- INSERT/UPDATE de rw_messages (enviar/editar mensaje) y de rw_channels (crear canal) se
-- agregan en la Fase 6 junto con las funciones transaccionales create_message/edit_message.
-- Hasta entonces, con solo estas policies de SELECT, rw_app no puede escribir en ninguna de
-- las dos tablas (RLS deniega por defecto cualquier comando sin policy aplicable) — correcto
-- para esta fase, donde solo se valida lectura autorizada.
