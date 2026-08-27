-- Fase 6: trigger de auditoría + guarda de integridad para rw_messages. Corre con los
-- privilegios de quien ejecuta el UPDATE (rw_app ya tiene INSERT en rw_message_history y
-- UPDATE en rw_messages desde la migración 0009) — sin SECURITY DEFINER, no hace falta.
--
-- Responsabilidades (todas dentro de la misma transacción que el UPDATE, R06/R07):
--   1. channel_id y sender_id son inmutables (RLS no puede expresar esto por sí sola).
--   2. Un mensaje 'deleted' no se puede volver a tocar.
--   3. Si cambia el contenido, o si el nuevo estado es 'deleted', copia el estado OLD a
--      rw_message_history ANTES de aplicar el cambio — esto es lo que garantiza que nunca
--      hay un DELETE físico ni una edición sin rastro.
CREATE OR REPLACE FUNCTION rw_messages_audit_and_guard() RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    v_actor uuid := current_setting('app.current_user_id', true)::uuid;
BEGIN
    IF NEW.channel_id IS DISTINCT FROM OLD.channel_id THEN
        RAISE EXCEPTION 'rw_messages.channel_id is immutable';
    END IF;
    IF NEW.sender_id IS DISTINCT FROM OLD.sender_id THEN
        RAISE EXCEPTION 'rw_messages.sender_id is immutable';
    END IF;
    IF OLD.message_status = 'deleted' THEN
        RAISE EXCEPTION 'cannot modify a message that is already deleted';
    END IF;

    IF NEW.message_status = 'deleted' THEN
        INSERT INTO rw_message_history (message_id, previous_content, previous_status, action, changed_by)
        VALUES (OLD.id, OLD.content, OLD.message_status, 'delete', v_actor);
        -- soft delete: el contenido se conserva en rw_message_history; la fila viva no se
        -- reescribe con el nuevo content que venga en el UPDATE (si alguno), solo cambia
        -- message_status. Enmascarar el content ante lectores no autorizados a verlo es
        -- responsabilidad de get_channel_messages() (Fase 11), no de este trigger.
        NEW.content := OLD.content;
    ELSIF NEW.content IS DISTINCT FROM OLD.content THEN
        INSERT INTO rw_message_history (message_id, previous_content, previous_status, action, changed_by)
        VALUES (OLD.id, OLD.content, OLD.message_status, 'edit', v_actor);
        NEW.message_status := 'edited';
    END IF;

    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER rw_messages_audit_trigger
    BEFORE UPDATE ON rw_messages
    FOR EACH ROW
    EXECUTE FUNCTION rw_messages_audit_and_guard();
