-- Fase 18/11: registro de consumo del copiloto por usuario (get_user_copilot_usage()).
CREATE TABLE rw_copilot_usage (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID NOT NULL REFERENCES rw_users (id) ON DELETE CASCADE,
    prompt_tokens     INT NOT NULL,
    completion_tokens INT NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT rw_copilot_usage_tokens_check CHECK (prompt_tokens >= 0 AND completion_tokens >= 0)
);
-- ON DELETE CASCADE: es un log de consumo, no un registro de auditoría de negocio (a
-- diferencia de rw_message_history) — no hay razón para bloquear la desactivación de un
-- usuario por esto.

CREATE INDEX rw_copilot_usage_user_id_idx ON rw_copilot_usage (user_id);

GRANT SELECT, INSERT ON rw_copilot_usage TO rw_app;
