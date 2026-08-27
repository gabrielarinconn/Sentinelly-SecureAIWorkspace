-- Fase 3: extensiones requeridas por el esquema.
CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- gen_random_uuid(), crypt()/gen_salt() para hash de passwords
CREATE EXTENSION IF NOT EXISTS vector;    -- pgvector, usado por rw_message_embeddings (Fase 10)
