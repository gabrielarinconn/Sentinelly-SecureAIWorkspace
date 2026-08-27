-- Restyling pass: registra la última vez que cada usuario leyó cada canal, para calcular
-- mensajes no leídos sin guardar un flag por mensaje. PK compuesta (channel_id, user_id): un
-- registro por combinación, se actualiza con UPSERT cada vez que el usuario abre el canal.
CREATE TABLE rw_channel_reads (
    channel_id     UUID NOT NULL REFERENCES rw_channels (id) ON DELETE CASCADE,
    user_id        UUID NOT NULL REFERENCES rw_users (id) ON DELETE CASCADE,
    last_read_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (channel_id, user_id)
);
-- ON DELETE CASCADE en ambas FK: el marcador de lectura no tiene sentido sin el canal o el
-- usuario, igual que rw_channel_members (0004_channel_members.sql).

COMMENT ON TABLE rw_channel_reads IS 'Última lectura por usuario/canal; base para el contador de mensajes no leídos.';

GRANT SELECT, INSERT, UPDATE ON rw_channel_reads TO rw_app;
-- Sin DELETE: la fila no se borra explícitamente, el CASCADE de las FK ya cubre la limpieza
-- si el canal o el usuario desaparecen (mismo criterio que rw_channel_members en 0009_app_role.sql).
