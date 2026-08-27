-- Fase 9: procedimiento #2 (edición y eliminación de usuarios). "Eliminación" = desactivación
-- (D004, soft delete también para usuarios) — nunca DELETE físico.
--
-- No recibe un p_user_id como parámetro: opera EXCLUSIVAMENTE sobre
-- current_setting('app.current_user_id') — el actor viene siempre del JWT verificado, nunca
-- de un argumento que el caller pudiera manipular para editar la cuenta de otra persona
-- (regla dura del proyecto, aplicada aquí porque rw_users no tiene RLS que lo haga por sí
-- sola). Sin rol admin (Fase 1: no se crea sin función real), no existe "editar a otro".
CREATE OR REPLACE PROCEDURE rw_edit_or_delete_user(
    IN p_full_name text DEFAULT NULL,
    IN p_role_title text DEFAULT NULL,
    IN p_deactivate boolean DEFAULT false
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_actor uuid := current_setting('app.current_user_id', true)::uuid;
BEGIN
    IF v_actor IS NULL THEN
        RAISE EXCEPTION 'No authenticated actor set (app.current_user_id).';
    END IF;

    IF p_deactivate THEN
        UPDATE rw_users SET is_active = false, updated_at = now() WHERE id = v_actor;
    ELSE
        UPDATE rw_users
        SET full_name = COALESCE(p_full_name, full_name),
            role_title = COALESCE(p_role_title, role_title),
            updated_at = now()
        WHERE id = v_actor;
    END IF;
END;
$$;
