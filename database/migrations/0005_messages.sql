CREATE TABLE rw_messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_id      UUID NOT NULL REFERENCES rw_channels (id) ON DELETE RESTRICT,
    sender_id       UUID NOT NULL REFERENCES rw_users (id) ON DELETE RESTRICT,
    content         TEXT NOT NULL,
    message_status  VARCHAR(20) NOT NULL DEFAULT 'active',
    search_vector   TSVECTOR,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT rw_messages_content_not_blank CHECK (btrim(content) <> ''),
    CONSTRAINT rw_messages_status_check CHECK (message_status IN ('active', 'edited', 'deleted'))
);
-- ON DELETE RESTRICT en ambas FK: nunca se pierde historial de conversación por accidente
-- (R06, R07). Borrar un canal o un usuario que ya tiene mensajes queda bloqueado a nivel de
-- base de datos; la app jamás emite DELETE físico sobre mensajes ni usuarios (soft delete,
-- D004) — RESTRICT es la red de seguridad si alguien lo intentara igual.

CREATE INDEX rw_messages_channel_created_idx
    ON rw_messages (channel_id, created_at DESC, id DESC);
-- soporta keyset pagination (cursor = (created_at, id), D005) y get_channel_messages() (Fase 11).

CREATE INDEX rw_messages_search_vector_idx ON rw_messages USING GIN (search_vector);
-- soporta search_messages() + ts_headline() (Fase 8). El trigger que mantiene search_vector
-- sincronizado se agrega en la migración de Fase 8, no aquí — la columna ya existe para no
-- requerir un ALTER TABLE posterior.

COMMENT ON TABLE rw_messages IS 'Mensajes de canal; soft delete únicamente (R06).';
