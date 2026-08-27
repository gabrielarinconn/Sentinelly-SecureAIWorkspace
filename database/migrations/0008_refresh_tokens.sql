CREATE TABLE rw_refresh_tokens (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id               UUID NOT NULL REFERENCES rw_users (id) ON DELETE CASCADE,
    token_hash            VARCHAR(255) NOT NULL,
    expires_at            TIMESTAMPTZ NOT NULL,
    revoked_at            TIMESTAMPTZ,
    replaced_by_token_id  UUID REFERENCES rw_refresh_tokens (id) ON DELETE SET NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT rw_refresh_tokens_token_hash_key UNIQUE (token_hash),
    CONSTRAINT rw_refresh_tokens_expiry_check CHECK (expires_at > created_at)
);
-- ON DELETE CASCADE en user_id: un refresh token sin usuario dueño no tiene ningún valor de
-- seguridad ni de auditoría — a diferencia de rw_messages, aquí no hay razón para bloquear.
-- ON DELETE SET NULL en replaced_by_token_id (self-reference): si el token de reemplazo se
-- eliminara, no se debe cascadear hacia atrás y borrar toda la cadena de rotación.

CREATE INDEX rw_refresh_tokens_user_id_idx ON rw_refresh_tokens (user_id);
CREATE INDEX rw_refresh_tokens_active_idx ON rw_refresh_tokens (user_id) WHERE revoked_at IS NULL;
-- índice parcial: acelera la búsqueda de tokens activos para reuse detection (Fase 15).

COMMENT ON TABLE rw_refresh_tokens IS 'Refresh tokens hasheados, con rotación y revocación (Fase 15).';
