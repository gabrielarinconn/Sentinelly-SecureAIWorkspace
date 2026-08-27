-- Helper de RLS: evalúa membresía sin volver a pasar por las policies de rw_channel_members.
--
-- Por qué SECURITY DEFINER (justificación explícita, R17/auditoría): una policy de
-- rw_channel_members que hace SELECT sobre la propia rw_channel_members dispara "infinite
-- recursion detected in policy" en PostgreSQL — la subconsulta vuelve a evaluar la misma
-- policy que la está llamando. La función corre con los privilegios de quien la creó (el rol
-- admin), lo que le permite leer rw_channel_members sin RLS, rompiendo la recursión. No elude
-- ninguna policy de negocio: lo único que expone es un booleano ("¿este user_id es miembro de
-- este channel_id?"), nunca filas completas, y solo se usa DESDE otras policies — nunca se le
-- da EXECUTE a nadie fuera de rw_app.
CREATE OR REPLACE FUNCTION rw_is_channel_member(p_channel_id uuid, p_user_id uuid)
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
    SELECT EXISTS (
        SELECT 1 FROM rw_channel_members
        WHERE channel_id = p_channel_id AND user_id = p_user_id
    );
$$;

REVOKE ALL ON FUNCTION rw_is_channel_member(uuid, uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION rw_is_channel_member(uuid, uuid) TO rw_app;
