import hashlib
import struct

from backend.domain.ports import EmbeddingProvider

EMBEDDING_DIMENSIONS = 1536  # debe coincidir con rw_message_embeddings.embedding (vector(1536))


class LocalHashEmbeddingProvider(EmbeddingProvider):
    """Placeholder determinístico para probar el PIPELINE (Fase 10: pending -> completed,
    sin bloquear el INSERT) sin depender de una API key externa todavía.

    NO es un embedding semántico real — dos textos parecidos no producen vectores parecidos.
    Se reemplaza por el proveedor real (Fase 18, D007) una vez que exista una API key; el
    resto del sistema no cambia porque depende de EmbeddingProvider, no de esta clase.
    """

    def embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        # 32 bytes de digest no alcanzan para 1536 floats -> se repite/mezcla con un contador.
        values: list[float] = []
        counter = 0
        while len(values) < EMBEDDING_DIMENSIONS:
            chunk = hashlib.sha256(digest + counter.to_bytes(4, "big")).digest()
            for i in range(0, len(chunk), 4):
                if len(values) >= EMBEDDING_DIMENSIONS:
                    break
                (raw,) = struct.unpack(">I", chunk[i : i + 4])
                values.append((raw / 0xFFFFFFFF) * 2 - 1)  # normalizado a [-1, 1]
            counter += 1
        return values
