from fastembed import TextEmbedding

from backend.domain.ports import EmbeddingProvider

EMBEDDING_DIMENSIONS = 384  # debe coincidir con rw_message_embeddings.embedding (vector(384))
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"  # multilingüe (ES)


class FastEmbedProvider(EmbeddingProvider):
    """Proveedor real de embeddings (Fase 18, D007) — corre localmente vía ONNX Runtime, sin
    API key ni llamada de red. El modelo (~220MB) se descarga una sola vez la primera vez que
    se instancia esta clase y queda cacheado en disco."""

    def __init__(self) -> None:
        self._model = TextEmbedding(model_name=MODEL_NAME)

    def embed(self, text: str) -> list[float]:
        (vector,) = self._model.embed([text])
        return vector.tolist()
