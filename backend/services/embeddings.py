"""
CLIP embedding management and FAISS vector index for wardrobe similarity search.
"""
import os
import json
import numpy as np
import faiss
from models.database import SessionLocal, ClothingItem

EMBEDDING_DIM = 512
INDEX_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "faiss_index.bin")


class EmbeddingIndex:
    """Manages FAISS index for clothing item embeddings."""

    def __init__(self):
        self.index = None
        self.item_ids: list[int] = []
        self._load_or_create()

    def _load_or_create(self):
        """Load existing index or create a new one."""
        if os.path.exists(INDEX_PATH):
            self.index = faiss.read_index(INDEX_PATH)
            self._load_item_ids()
        else:
            self.index = faiss.IndexFlatIP(EMBEDDING_DIM)  # Inner product (cosine sim after normalization)
            self.item_ids = []

    def _load_item_ids(self):
        """Load item IDs from database to maintain index-to-ID mapping."""
        db = SessionLocal()
        try:
            items = db.query(ClothingItem).filter(
                ClothingItem.embedding_json.isnot(None)
            ).order_by(ClothingItem.id).all()
            self.item_ids = [item.id for item in items]
        finally:
            db.close()

    def add_item(self, item_id: int, embedding: list[float]):
        """Add a single item embedding to the index."""
        vec = np.array([embedding], dtype=np.float32)
        # Normalize for cosine similarity
        faiss.normalize_L2(vec)
        self.index.add(vec)
        self.item_ids.append(item_id)
        self._save()

    def remove_item(self, item_id: int):
        """Remove an item and rebuild the index."""
        if item_id in self.item_ids:
            self._rebuild_without(item_id)

    def _rebuild_without(self, exclude_id: int):
        """Rebuild the entire index excluding a specific item."""
        db = SessionLocal()
        try:
            items = db.query(ClothingItem).filter(
                ClothingItem.embedding_json.isnot(None),
                ClothingItem.id != exclude_id
            ).order_by(ClothingItem.id).all()

            self.index = faiss.IndexFlatIP(EMBEDDING_DIM)
            self.item_ids = []

            for item in items:
                embedding = json.loads(item.embedding_json)
                vec = np.array([embedding], dtype=np.float32)
                faiss.normalize_L2(vec)
                self.index.add(vec)
                self.item_ids.append(item.id)

            self._save()
        finally:
            db.close()

    def search_similar(self, embedding: list[float], k: int = 10, exclude_id: int = None) -> list[tuple[int, float]]:
        """
        Search for similar items by embedding.
        Returns list of (item_id, similarity_score) tuples.
        """
        if self.index.ntotal == 0:
            return []

        vec = np.array([embedding], dtype=np.float32)
        faiss.normalize_L2(vec)

        actual_k = min(k + (1 if exclude_id else 0), self.index.ntotal)
        scores, indices = self.index.search(vec, actual_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.item_ids):
                continue
            item_id = self.item_ids[idx]
            if exclude_id and item_id == exclude_id:
                continue
            results.append((item_id, float(score)))
            if len(results) >= k:
                break

        return results

    def get_all_embeddings(self) -> dict[int, np.ndarray]:
        """Get all embeddings mapped to their item IDs."""
        db = SessionLocal()
        try:
            items = db.query(ClothingItem).filter(
                ClothingItem.embedding_json.isnot(None)
            ).all()
            return {
                item.id: np.array(json.loads(item.embedding_json), dtype=np.float32)
                for item in items
            }
        finally:
            db.close()

    def _save(self):
        """Persist the FAISS index to disk."""
        faiss.write_index(self.index, INDEX_PATH)


# Singleton instance
_embedding_index = None


def get_embedding_index() -> EmbeddingIndex:
    global _embedding_index
    if _embedding_index is None:
        _embedding_index = EmbeddingIndex()
    return _embedding_index
