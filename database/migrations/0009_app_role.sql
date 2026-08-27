-- Fase 4: rol de aplicación. Sin SUPERUSER, sin BYPASSRLS — es el rol que usa el backend en
-- tiempo de ejecución para TODAS las consultas. El rol usado para migrar/seedear (superusuario
-- del contenedor) nunca se usa desde la aplicación.
--
-- La contraseña se pasa por variable psql (-v rw_app_password=...), nunca queda en texto
-- plano en este archivo ni en el repo. Idempotencia la maneja scripts/migrate.sh (no se
-- reintenta un archivo ya registrado en schema_migrations), por eso aquí no hace falta un
-- guard IF NOT EXISTS — igual que en las migraciones 0002-0008.
CREATE ROLE rw_app LOGIN PASSWORD :'rw_app_password'
    NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION;

GRANT CONNECT ON DATABASE :"db_name" TO rw_app;
GRANT USAGE ON SCHEMA public TO rw_app;

GRANT SELECT, INSERT, UPDATE ON
    rw_users, rw_channels, rw_channel_members, rw_messages,
    rw_message_history, rw_message_embeddings, rw_refresh_tokens
TO rw_app;

-- Sin DELETE en rw_users/rw_messages/rw_message_history/rw_message_embeddings: refuerza a
-- nivel de PRIVILEGIOS (no solo de ON DELETE RESTRICT, Fase 3) que la app jamás puede emitir
-- un DELETE físico sobre mensajes/usuarios (R06) — ni siquiera por un bug en el código, el rol
-- no tiene el permiso.
GRANT DELETE ON rw_channel_members, rw_refresh_tokens TO rw_app;
-- rw_channel_members: salir de un canal. rw_refresh_tokens: limpieza de tokens expirados.
