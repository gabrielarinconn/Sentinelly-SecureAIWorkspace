-- Fase 6: INSERT/UPDATE sobre rw_messages (enviar / editar / eliminar mensaje). Diferido
-- desde 0001_channels_messages_rls.sql (Fase 4), que solo cubría SELECT.

CREATE POLICY rw_messages_member_insert ON rw_messages
    FOR INSERT
    WITH CHECK (
        sender_id = current_setting('app.current_user_id', true)::uuid
        AND rw_is_channel_member(channel_id, current_setting('app.current_user_id', true)::uuid)
    );
-- solo se puede enviar como uno mismo (no se puede falsificar sender_id) y solo a un canal
-- del que se es miembro.

CREATE POLICY rw_messages_owner_update ON rw_messages
    FOR UPDATE
    USING (
        sender_id = current_setting('app.current_user_id', true)::uuid
        AND rw_is_channel_member(channel_id, current_setting('app.current_user_id', true)::uuid)
    )
    WITH CHECK (
        sender_id = current_setting('app.current_user_id', true)::uuid
    );
-- editar/eliminar (ambas son UPDATE: content o message_status) solo lo propio, y solo en un
-- canal del que se sigue siendo miembro. La inmutabilidad de channel_id/sender_id y las
-- transiciones válidas de message_status las garantiza el trigger de auditoría
-- (database/triggers/0001_messages_audit.sql), no esta policy — RLS decide QUIÉN, el
-- trigger decide QUÉ transiciones son válidas.
