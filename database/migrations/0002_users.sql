CREATE TABLE rw_users (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email          VARCHAR(320) NOT NULL,
    password_hash  VARCHAR(255) NOT NULL,
    full_name      VARCHAR(200) NOT NULL,
    role_title     VARCHAR(200) NOT NULL,
    is_active      BOOLEAN NOT NULL DEFAULT true,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT rw_users_email_not_blank CHECK (btrim(email) <> ''),
    CONSTRAINT rw_users_full_name_not_blank CHECK (btrim(full_name) <> ''),
    CONSTRAINT rw_users_role_title_not_blank CHECK (btrim(role_title) <> '')
);

-- Índice único PARCIAL (requisito de Fase 3): el email solo debe ser único entre usuarios
-- activos. Al desactivar (soft delete, D004) un usuario, su email queda libre para un nuevo
-- registro sin sufijos ni borrado físico de la fila original — se conserva el historial.
CREATE UNIQUE INDEX rw_users_email_active_uk
    ON rw_users (lower(email))
    WHERE is_active = true;

COMMENT ON TABLE rw_users IS 'Identidad y credenciales del usuario autenticado (R08, R09).';
