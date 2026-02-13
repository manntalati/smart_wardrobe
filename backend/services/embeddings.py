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
    """Manages FAISS index for clothing item embeddings with user isolation."""

    def __init__(self):
        self.index = None
        self.item_ids: list[int] = [] # Maps FAISS index to item_id
        self.user_map: dict[int, int] = {} # Maps item_id to user_id
        self._load_or_create()

    def _load_or_create(self):
        """Load existing index or create a new one."""
        if os.path.exists(INDEX_PATH):
            self.index = faiss.read_index(INDEX_PATH)
            self._load_metadata()
        else:
            self.index = faiss.IndexFlatIP(EMBEDDING_DIM)
            self.item_ids = []
            self.user_map = {}

    def _load_metadata(self):
        """Load item IDs and user mapping from database."""
        db = SessionLocal()
        try:
            items = db.query(ClothingItem).filter(
                ClothingItem.embedding_json.isnot(None)
            ).order_by(ClothingItem.id).all()
            
            self.item_ids = [item.id for item in items]
            
            # Rebuild user map
            self.user_map = {}
            for item in items:
                if item.user_id:
                    self.user_map[item.id] = item.user_id
                    
            # If item count mismatch (e.g. DB items deleted directly), 
            # we should ideally rebuild index. For now trust consistent state.
            if len(self.item_ids) != self.index.ntotal:
                 print(f"⚠️ Index mismatch: DB has {len(self.item_ids)} items, Index has {self.index.ntotal}. Rebuilding...")
                 self._rebuild_all(items)
                 
        finally:
            db.close()

    def _rebuild_all(self, items):
        """Rebuild index from scratch using provided items."""
        self.index = faiss.IndexFlatIP(EMBEDDING_DIM)
        self.item_ids = []
        self.user_map = {}
        
        for item in items:
            if not item.embedding_json:
                continue
            embedding = json.loads(item.embedding_json)
            vec = np.array([embedding], dtype=np.float32)
            faiss.normalize_L2(vec)
            self.index.add(vec)
            self.item_ids.append(item.id)
            if item.user_id:
                self.user_map[item.id] = item.user_id
                
        self._save()

    def add_item(self, item_id: int, embedding: list[float], user_id: int = None):
        """Add a single item embedding to the index."""
        vec = np.array([embedding], dtype=np.float32)
        faiss.normalize_L2(vec)
        self.index.add(vec)
        self.item_ids.append(item_id)
        if user_id:
            self.user_map[item_id] = user_id
        self._save()

    def remove_item(self, item_id: int):
        """Remove an item and rebuild the index."""
        if item_id in self.item_ids:
            self._rebuild_without(item_id)
        if item_id in self.user_map:
            del self.user_map[item_id]

    def _rebuild_without(self, exclude_id: int):
        """Rebuild the entire index excluding a specific item."""
        db = SessionLocal()
        try:
            items = db.query(ClothingItem).filter(
                ClothingItem.embedding_json.isnot(None),
                ClothingItem.id != exclude_id
            ).order_by(ClothingItem.id).all()
            
            self._rebuild_all(items)
        finally:
            db.close()

    def search_similar(self, embedding: list[float], k: int = 10, exclude_id: int = None, user_id: int = None) -> list[tuple[int, float]]:
        """
        Search for similar items by embedding, optionally filtered by user_id.
        """
        if self.index.ntotal == 0:
            return []

        vec = np.array([embedding], dtype=np.float32)
        faiss.normalize_L2(vec)

        # Search more candidates to allow for filtering
        search_k = min(k * 10, self.index.ntotal)
        scores, indices = self.index.search(vec, search_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.item_ids):
                continue
                
            item_id = self.item_ids[idx]
            
            # User isolation filter
            if user_id is not None:
                item_owner = self.user_map.get(item_id)
                # If item has owner and it's different, skip
                if item_owner is not None and item_owner != user_id:
                    continue
                # If item has no owner (legacy public items), maybe include? 
                # For now, let's say strict mode: only user's items.
                if item_owner is None:
                     # Decide policy: public items visible? Let's say yes for now to not break legacy
                     pass

            if exclude_id and item_id == exclude_id:
                continue
                
            results.append((item_id, float(score)))
            if len(results) >= k:
                break

        return results

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
