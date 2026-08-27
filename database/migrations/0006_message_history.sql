CREATE TABLE rw_message_history (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id        UUID NOT NULL REFERENCES rw_messages (id) ON DELETE RESTRICT,
    previous_content  TEXT NOT NULL,
    previous_status   VARCHAR(20) NOT NULL,
    action            VARCHAR(20) NOT NULL,
    changed_by        UUID NOT NULL REFERENCES rw_users (id) ON DELETE RESTRICT,
    changed_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT rw_message_history_status_check CHECK (previous_status IN ('active', 'edited', 'deleted')),
    CONSTRAINT rw_message_history_action_check CHECK (action IN ('edit', 'delete'))
);
-- ON DELETE RESTRICT en message_id: si un mensaje ya tiene historial (fue editado o
-- eliminado al menos una vez), la base de datos bloquea físicamente cualquier intento de
-- DELETE sobre ese mensaje — refuerzo a nivel de esquema de "nunca DELETE FROM rw_messages"
-- (R06), además de que el rol de aplicación no tendrá privilegio DELETE (Fase 4).
-- ON DELETE RESTRICT en changed_by: preserva accountability — no se puede hacer desaparecer
-- al usuario responsable de un cambio auditado.

CREATE INDEX rw_message_history_message_id_idx ON rw_message_history (message_id);

COMMENT ON TABLE rw_message_history IS 'Auditoría de estados previos de un mensaje (R07), poblada por trigger.';
