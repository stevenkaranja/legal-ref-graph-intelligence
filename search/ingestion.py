"""Batch document ingestion pipeline: parse → embed → upsert."""
import hashlib
import logging
from pathlib import Path
from typing import Iterator
import pinecone
from search.embeddings import DocumentEmbedder

logger = logging.getLogger(__name__)
BATCH = 100


class DocumentIngester:
    def __init__(self, index_name: str = "legal-ref-docs"):
        self.embedder = DocumentEmbedder()
        self.index = pinecone.Index(index_name)

    def ingest_directory(self, path: str, jurisdiction: str):
        docs = list(Path(path).glob("**/*.txt")) + list(Path(path).glob("**/*.pdf"))
        logger.info(f"Ingesting {len(docs)} documents ({jurisdiction})")
        for batch in self._batched(self._parse_docs(docs, jurisdiction), BATCH):
            texts = [d["text"] for d in batch]
            embeddings = self.embedder.embed(texts)
            vectors = [
                (d["id"], emb.tolist(), {k: v for k, v in d.items() if k != "text"})
                for d, emb in zip(batch, embeddings)
            ]
            self.index.upsert(vectors=vectors)
            logger.info(f"Upserted {len(vectors)} vectors")

    def _parse_docs(self, paths, jurisdiction) -> Iterator[dict]:
        for p in paths:
            text = p.read_text(errors="ignore")
            for i, chunk in enumerate(self.embedder.chunk_document(text)):
                yield {
                    "id": f"{hashlib.md5(str(p).encode()).hexdigest()}_{i}",
                    "text": chunk,
                    "jurisdiction": jurisdiction,
                    "source": p.name,
                }

    @staticmethod
    def _batched(it, n):
        batch = []
        for item in it:
            batch.append(item)
            if len(batch) == n:
                yield batch; batch = []
        if batch:
            yield batch
