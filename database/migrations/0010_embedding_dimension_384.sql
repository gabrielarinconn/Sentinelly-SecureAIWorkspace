-- Fase 18: rw_message_embeddings.embedding pasa de vector(1536) (placeholder de la Fase 10,
-- dimensión de OpenAI text-embedding-3-small) a vector(384) — dimensión real del proveedor
-- de embeddings elegido (fastembed local, modelo multilingüe
-- sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2, D006/D007).
--
-- ALTER COLUMN ... TYPE solo funciona en limpio porque no hay datos reales de producción
-- todavía (el proyecto no se ha entregado); si la tabla tuviera filas con vectores de 1536
-- dimensiones, este ALTER fallaría — habría que primero poner esas filas de vuelta en
-- 'pending' para que el worker las regenere con el nuevo proveedor.
ALTER TABLE rw_message_embeddings ALTER COLUMN embedding TYPE vector(384);

-- retrieve_ai_context() tiene la dimensión del vector en su firma — CREATE OR REPLACE no
-- permite cambiar el tipo de un parámetro, hay que DROP + CREATE.
DROP FUNCTION IF EXISTS retrieve_ai_context(vector, int);

CREATE OR REPLACE FUNCTION retrieve_ai_context(
    p_query_embedding vector(384),
    p_limit int DEFAULT 5
)
RETURNS TABLE (
    message_id uuid,
    channel_id uuid,
    sender_id uuid,
    content text,
    created_at timestamptz,
    similarity real
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        m.id,
        m.channel_id,
        m.sender_id,
        m.content,
        m.created_at,
        (1 - (e.embedding <=> p_query_embedding))::real AS similarity
    FROM rw_messages m
    JOIN rw_message_embeddings e ON e.message_id = m.id
    WHERE e.status = 'completed'
      AND m.message_status <> 'deleted'
    ORDER BY e.embedding <=> p_query_embedding
    LIMIT p_limit;
$$;
