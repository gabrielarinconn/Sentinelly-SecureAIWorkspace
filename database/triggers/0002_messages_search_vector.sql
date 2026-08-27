-- Fase 8: mantiene rw_messages.search_vector sincronizado. Config 'spanish' porque el
-- contenido de la demo está en español (D001 nota: revisar si el proyecto necesita
-- soportar multi-idioma más allá del alcance de esta prueba).
--
-- "BEFORE INSERT OR UPDATE OF content" solo dispara en INSERT o cuando `content` está en el
-- SET de un UPDATE — el UPDATE de delete_message() no toca `content` (solo message_status),
-- así que no vuelve a calcular el vector para un mensaje eliminado: correcto, el contenido no
-- cambió, el vector viejo sigue siendo válido para cuando se necesite auditoría, aunque
-- get_channel_messages() ya lo enmascare de cara al usuario.
CREATE OR REPLACE FUNCTION rw_messages_search_vector_update() RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.search_vector := to_tsvector('spanish', COALESCE(NEW.content, ''));
    RETURN NEW;
END;
$$;

CREATE TRIGGER rw_messages_search_vector_trigger
    BEFORE INSERT OR UPDATE OF content ON rw_messages
    FOR EACH ROW
    EXECUTE FUNCTION rw_messages_search_vector_update();
