import hashlib
import struct

from backend.domain.ports import EmbeddingProvider

EMBEDDING_DIMENSIONS = 384  # debe coincidir con rw_message_embeddings.embedding (vector(384))


class LocalHashEmbeddingProvider(EmbeddingProvider):
    """Placeholder determinístico usado SOLO por los tests de Fase 10 que verifican la
    mecánica del pipeline (pending -> completed, sin bloquear el INSERT) — no la calidad
    semántica del retrieval, eso lo cubren los tests de Fase 18 con el proveedor real
    (FastEmbedProvider). Evita pagar el costo de cargar el modelo ONNX en tests que no lo
    necesitan.

    NO es un embedding semántico real — dos textos parecidos no producen vectores parecidos.
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
