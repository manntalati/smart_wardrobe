"""
RAG pipeline for fashion knowledge retrieval.
Loads curated fashion guidance, embeds chunks with CLIP text encoder,
and retrieves relevant context for LLM outfit recommendations.
"""
import os
import numpy as np
import torch
from transformers import CLIPModel, CLIPProcessor

KNOWLEDGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "knowledge")
MODEL_NAME = "openai/clip-vit-base-patch32"

_chunks: list[str] = []
_chunk_embeddings: np.ndarray | None = None


def _get_text_embedding(text: str, model, processor) -> np.ndarray:
    """Get CLIP text embedding for a string."""
    inputs = processor(text=text, return_tensors="pt", padding=True, truncation=True, max_length=77)
    with torch.no_grad():
        outputs = model.get_text_features(**inputs)
    vec = outputs[0].cpu().numpy()
    vec = vec / np.linalg.norm(vec)
    return vec


def _load_and_embed_knowledge():
    """Load fashion knowledge base and create embeddings for each chunk."""
    global _chunks, _chunk_embeddings

    if _chunks:
        return

    knowledge_file = os.path.join(KNOWLEDGE_DIR, "fashion_guide.md")
    if not os.path.exists(knowledge_file):
        print(f"Warning: Fashion knowledge base not found at {knowledge_file}")
        return

    with open(knowledge_file, "r") as f:
        text = f.read()

    # Split on double newlines to get paragraph-level chunks
    raw_chunks = text.split("\n\n")
    _chunks = [c.strip() for c in raw_chunks if len(c.strip()) > 50]

    if not _chunks:
        return

    # Load CLIP model for text embeddings
    model = CLIPModel.from_pretrained(MODEL_NAME)
    processor = CLIPProcessor.from_pretrained(MODEL_NAME)
    model.eval()

    embeddings = []
    for chunk in _chunks:
        emb = _get_text_embedding(chunk, model, processor)
        embeddings.append(emb)

    _chunk_embeddings = np.stack(embeddings, axis=0)
    print(f"Loaded {len(_chunks)} fashion knowledge chunks")


def retrieve_fashion_context(query: str, top_k: int = 5) -> list[str]:
    """
    Retrieve the most relevant fashion knowledge chunks for a query.
    Uses CLIP text embeddings for semantic search.
    """
    _load_and_embed_knowledge()

    if not _chunks or _chunk_embeddings is None:
        return []

    model = CLIPModel.from_pretrained(MODEL_NAME)
    processor = CLIPProcessor.from_pretrained(MODEL_NAME)
    model.eval()

    query_emb = _get_text_embedding(query, model, processor)
    scores = np.dot(_chunk_embeddings, query_emb)

    top_indices = np.argsort(scores)[-top_k:][::-1]
    return [_chunks[i] for i in top_indices if scores[i] > 0.1]
