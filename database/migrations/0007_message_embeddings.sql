CREATE TABLE rw_message_embeddings (
    message_id  UUID PRIMARY KEY REFERENCES rw_messages (id) ON DELETE CASCADE,
    embedding   VECTOR(1536),  -- dimensión provisional (OpenAI text-embedding-3-small); ajustar en Fase 18 si cambia el proveedor
    status      VARCHAR(20) NOT NULL DEFAULT 'pending',
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT rw_message_embeddings_status_check CHECK (status IN ('pending', 'completed', 'failed'))
);
-- ON DELETE CASCADE: el embedding es un artefacto derivado del mensaje, sin valor propio si
-- el mensaje desaparece — a diferencia de rw_message_history, que es evidencia de auditoría
-- y por eso usa RESTRICT en vez de CASCADE.

COMMENT ON TABLE rw_message_embeddings IS 'Vector pgvector por mensaje para RAG (R05, Fase 10).';
