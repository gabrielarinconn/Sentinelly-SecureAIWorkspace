-- Seed de demo: reproduce el escenario de seguridad necesario para probar RLS y RAG
-- (Fase 3 DoD, Fase 24 golden path). Contraseña de demo para ambos usuarios: DemoPass123!
-- (hasheada con bcrypt vía pgcrypto, nunca en texto plano).

INSERT INTO rw_users (id, email, password_hash, full_name, role_title) VALUES
    ('00000000-0000-0000-0000-000000000001', 'alice@sentinel.dev',
     crypt('DemoPass123!', gen_salt('bf')), 'Alice Morgan', 'Product Manager'),
    ('00000000-0000-0000-0000-000000000002', 'bob@sentinel.dev',
     crypt('DemoPass123!', gen_salt('bf')), 'Bob Chen', 'Engineering Lead');

-- Canal compartido: ambos son miembros.
INSERT INTO rw_channels (id, name, is_private, created_by) VALUES
    ('10000000-0000-0000-0000-000000000001', 'general', false,
     '00000000-0000-0000-0000-000000000001');

-- Canal privado: solo Bob es miembro. Ajeno a Alice — debe ser invisible para ella tanto en
-- la vista de conversaciones como en el retrieval del copiloto (R03, R05, R19).
INSERT INTO rw_channels (id, name, is_private, created_by) VALUES
    ('10000000-0000-0000-0000-000000000002', 'leadership-private', true,
     '00000000-0000-0000-0000-000000000002');

INSERT INTO rw_channel_members (channel_id, user_id, role) VALUES
    ('10000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', 'owner'),
    ('10000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000002', 'member'),
    ('10000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000002', 'owner');

-- Mensajes en el canal compartido — soportan el escenario de búsqueda ("budget") del golden path.
INSERT INTO rw_messages (channel_id, sender_id, content) VALUES
    ('10000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001',
     'Necesitamos revisar el budget del proximo trimestre antes del viernes.'),
    ('10000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000002',
     'De acuerdo, preparo el desglose de budget por equipo.');

-- Mensaje en el canal privado — nunca debe aparecer en resultados de Alice (RLS, R19).
INSERT INTO rw_messages (channel_id, sender_id, content) VALUES
    ('10000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000002',
     'Discusion confidencial de liderazgo, fuera del alcance de Alice.');
