-- Fase 11/18: consumo acumulado del copiloto del actor autenticado. No recibe user_id como
-- parámetro — igual que rw_edit_or_delete_user (Fase 9), opera exclusivamente sobre
-- current_setting('app.current_user_id'), nunca sobre un id que el caller pudiera manipular
-- para ver el consumo de otro usuario (rw_copilot_usage no tiene RLS propia).
CREATE OR REPLACE FUNCTION get_user_copilot_usage()
RETURNS TABLE (
    total_questions int,
    total_prompt_tokens bigint,
    total_completion_tokens bigint
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        count(*)::int,
        COALESCE(sum(prompt_tokens), 0),
        COALESCE(sum(completion_tokens), 0)
    FROM rw_copilot_usage
    WHERE user_id = current_setting('app.current_user_id', true)::uuid;
$$;
