-- Fase 10: trigger híbrido. NUNCA llama a una API de embeddings desde SQL (bloquearía la
-- transacción) — solo marca 'pending' y notifica; un worker asíncrono en el backend, fuera
-- de esta transacción, hace el trabajo real (backend/infrastructure/embedding_worker.py).
CREATE OR REPLACE FUNCTION rw_messages_embedding_trigger() RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO rw_message_embeddings (message_id, status, updated_at)
    VALUES (NEW.id, 'pending', now())
    ON CONFLICT (message_id) DO UPDATE SET status = 'pending', updated_at = now();
    -- NOTIFY es opcional (el plan lo permite explícitamente) — el worker de esta fase hace
    -- polling; NOTIFY queda disponible para quien prefiera un consumidor basado en LISTEN.
    PERFORM pg_notify('rw_message_embeddings_pending', NEW.id::text);
    RETURN NEW;
END;
$$;

CREATE TRIGGER rw_messages_embedding_insert_trigger
    AFTER INSERT ON rw_messages
    FOR EACH ROW
    EXECUTE FUNCTION rw_messages_embedding_trigger();

-- "UPDATE OF content" -> re-encolar cuando se edita un mensaje (el embedding queda
-- desactualizado); un soft delete (que no toca content) no dispara esto.
CREATE TRIGGER rw_messages_embedding_update_trigger
    AFTER UPDATE OF content ON rw_messages
    FOR EACH ROW
    EXECUTE FUNCTION rw_messages_embedding_trigger();
