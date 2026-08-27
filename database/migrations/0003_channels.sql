CREATE TABLE rw_channels (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(200) NOT NULL,
    is_private  BOOLEAN NOT NULL DEFAULT false,
    created_by  UUID REFERENCES rw_users (id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT rw_channels_name_not_blank CHECK (btrim(name) <> '')
);
-- ON DELETE SET NULL: si el usuario creador se desactiva/elimina, el canal y sus mensajes
-- deben sobrevivir (R07); solo se pierde la referencia a quién lo creó.

COMMENT ON TABLE rw_channels IS 'Canales de conversación, públicos o privados.';
