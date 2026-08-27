-- Fase 5: RLS sobre rw_channel_members. Sin esto, un usuario podría hacer SELECT directo a
-- esta tabla y ver la membresía de canales privados ajenos (quién pertenece a qué canal) —
-- una fuga de metadata que rw_channels/rw_messages (Fase 4) no cubren por sí solas.
--
-- Usa rw_is_channel_member() (database/functions/0001_is_channel_member.sql) en vez de un
-- EXISTS inline sobre esta misma tabla: una policy de rw_channel_members que hace SELECT
-- sobre rw_channel_members dispara "infinite recursion detected in policy" en PostgreSQL —
-- la función, al ser SECURITY DEFINER, lee la tabla sin volver a pasar por esta policy.

ALTER TABLE rw_channel_members ENABLE ROW LEVEL SECURITY;

CREATE POLICY rw_channel_members_member_select ON rw_channel_members
    FOR SELECT
    USING (rw_is_channel_member(rw_channel_members.channel_id, current_setting('app.current_user_id', true)::uuid));

-- INSERT/UPDATE/DELETE (agregar/quitar miembros) no tienen policy en esta fase: el plan no
-- expone ningún endpoint de gestión de canales (Fase 16 — API REST no incluye
-- POST/PATCH /channels), así que no hay caso de uso real que las necesite todavía (D011,
-- "no crear abstracciones sin necesidad concreta"). Sin policy, RLS deniega por defecto —
-- ni siquiera un owner puede escribir aquí hasta que exista un caso de uso real respaldado
-- por una policy explícita.
