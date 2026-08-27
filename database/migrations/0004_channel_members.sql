CREATE TABLE rw_channel_members (
    channel_id  UUID NOT NULL REFERENCES rw_channels (id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES rw_users (id) ON DELETE CASCADE,
    role        VARCHAR(20) NOT NULL,
    joined_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (channel_id, user_id),
    CONSTRAINT rw_channel_members_role_check CHECK (role IN ('owner', 'member'))
);
-- ON DELETE CASCADE en ambas FK: la membresía no tiene sentido sin el canal o el usuario, y
-- no se conserva historial de membresía en esta fase (R01, R02, R03).

CREATE INDEX rw_channel_members_user_id_idx ON rw_channel_members (user_id);
-- la PK (channel_id, user_id) ya sirve para "miembros de un canal"; este índice acelera
-- el patrón inverso, "canales de un usuario" (vista de conversaciones, Fase 9).

COMMENT ON TABLE rw_channel_members IS 'Membresía N:N; tabla que RLS usa para decidir acceso (R03).';
