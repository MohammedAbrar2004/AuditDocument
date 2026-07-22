"""Cosine similarity via matrix multiply. Both chunk and item embeddings
were L2-normalized at Phase 3 (verified there, and re-checked in this
phase's build report) -- so the dot product is the cosine directly, no
extra normalization needed here.
"""
import numpy as np


def cosine_matrix(item_embeddings: np.ndarray, chunk_embeddings: np.ndarray) -> np.ndarray:
    """(n_items, dim) x (n_chunks, dim) -> (n_items, n_chunks)."""
    return item_embeddings @ chunk_embeddings.T
