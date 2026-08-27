-- Restyling pass: obtiene (o crea) el canal DM entre el actor autenticado y otro usuario.
--
-- Por qué SECURITY DEFINER (mismo criterio que rw_is_channel_member, functions/0001): ninguna
-- policy de INSERT existe sobre rw_channels/rw_channel_members (Fase 5 lo dejó fuera de
-- alcance a propósito — ver policies/0002_channel_members_rls.sql, "no crear abstracciones sin
-- necesidad concreta"). Esta función es la ÚNICA vía para crear un canal, y lo hace de forma
-- estrictamente acotada: solo canales DM de exactamente 2 miembros (el actor + p_other_user_id),
-- nunca canales públicos/privados arbitrarios ni membresías de terceros — no es un bypass
-- general de RLS, es una operación transaccional puntual con su propia validación interna.
CREATE OR REPLACE FUNCTION rw_get_or_create_dm_channel(p_other_user_id uuid)
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_actor uuid := current_setting('app.current_user_id', true)::uuid;
    v_channel_id uuid;
BEGIN
    IF v_actor IS NULL THEN
        RAISE EXCEPTION 'No authenticated actor set (app.current_user_id).';
    END IF;
    IF p_other_user_id = v_actor THEN
        RAISE EXCEPTION 'Cannot start a direct message with yourself.';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM rw_users WHERE id = p_other_user_id AND is_active) THEN
        RAISE EXCEPTION 'Target user does not exist or is not active.';
    END IF;

    SELECT cm1.channel_id INTO v_channel_id
    FROM rw_channel_members cm1
    JOIN rw_channel_members cm2 ON cm2.channel_id = cm1.channel_id
    JOIN rw_channels c ON c.id = cm1.channel_id
    WHERE c.is_direct
      AND cm1.user_id = v_actor
      AND cm2.user_id = p_other_user_id
    LIMIT 1;

    IF v_channel_id IS NOT NULL THEN
        RETURN v_channel_id;
    END IF;

    INSERT INTO rw_channels (name, is_private, is_direct, created_by)
    VALUES (NULL, true, true, v_actor)
    RETURNING id INTO v_channel_id;

    INSERT INTO rw_channel_members (channel_id, user_id, role)
    VALUES (v_channel_id, v_actor, 'member'), (v_channel_id, p_other_user_id, 'member');

    RETURN v_channel_id;
END;
$$;

REVOKE ALL ON FUNCTION rw_get_or_create_dm_channel(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION rw_get_or_create_dm_channel(uuid) TO rw_app;
