-- Restyling pass: RLS sobre rw_channel_reads. Cada usuario solo puede ver/escribir su PROPIA
-- fila de lectura, nunca la de otro miembro del canal — eso filtraría cuándo entró alguien más
-- por última vez, una fuga de metadata igual que la que 0002_channel_members_rls.sql evita.
ALTER TABLE rw_channel_reads ENABLE ROW LEVEL SECURITY;

CREATE POLICY rw_channel_reads_own_select ON rw_channel_reads
    FOR SELECT
    USING (user_id = current_setting('app.current_user_id', true)::uuid);

CREATE POLICY rw_channel_reads_own_insert ON rw_channel_reads
    FOR INSERT
    WITH CHECK (
        user_id = current_setting('app.current_user_id', true)::uuid
        AND rw_is_channel_member(channel_id, current_setting('app.current_user_id', true)::uuid)
    );

CREATE POLICY rw_channel_reads_own_update ON rw_channel_reads
    FOR UPDATE
    USING (user_id = current_setting('app.current_user_id', true)::uuid)
    WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid);
-- UPSERT (marcar como leído) hace INSERT ... ON CONFLICT DO UPDATE, por eso hacen falta ambas
-- policies aunque el caso de uso real siempre termine en UPDATE tras la primera vez.
