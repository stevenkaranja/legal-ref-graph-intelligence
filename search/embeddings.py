"""Document embedding generation for vector search."""
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List


MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"
BATCH_SIZE = 64


class DocumentEmbedder:
    def __init__(self, model_name: str = MODEL_NAME):
        self.model = SentenceTransformer(model_name)
        self.dim = self.model.get_sentence_embedding_dimension()

    def embed(self, texts: List[str], batch_size: int = BATCH_SIZE) -> np.ndarray:
        return self.model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > 100,
        )

    def embed_query(self, query: str) -> np.ndarray:
        return self.model.encode([query], normalize_embeddings=True)[0]

    def chunk_document(self, text: str, max_tokens: int = 512) -> List[str]:
        """Naive sentence-boundary chunker."""
        sentences = text.replace("\n", " ").split(". ")
        chunks, current, length = [], [], 0
        for s in sentences:
            tokens = len(s.split())
            if length + tokens > max_tokens and current:
                chunks.append(". ".join(current) + ".")
                current, length = [], 0
            current.append(s)
            length += tokens
        if current:
            chunks.append(". ".join(current))
        return chunks
