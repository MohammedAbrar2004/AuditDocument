"""Embedding step: chunks (Phase 2's artifact) and checklist items (this
phase's own parser), both through BGE-M3, dense vectors only.

Two hard gates, both grounded in phases/v2_phase3.md, both fail loudly rather
than silently degrading:
- CUDA must be available (Phase 0's FLAG-1 -- a plain pip install resolves a
  CPU torch build with no error, and Phase 3 would then quietly take hours).
- Every chunk_id must be unique (a real collision was found and hotfixed
  once already -- see the plan's Flag (f) -- and would silently overwrite a
  row in the embedding matrix if it ever recurred).
"""
from collections import Counter

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

BATCH_SIZE = 8


def assert_chunk_id_uniqueness(chunks: list[dict]) -> None:
    ids = [c["chunk_id"] for c in chunks]
    counts = Counter(ids)
    dupes = {cid: n for cid, n in counts.items() if n > 1}
    if dupes:
        raise ValueError(
            f"chunk_id collision(s) found, refusing to embed: {dupes}. "
            "This would silently overwrite a row in the embedding matrix. "
            "See phases/v2_phase3.md Flag (f) for the known root cause."
        )


def assert_cuda() -> None:
    if not torch.cuda.is_available():
        raise RuntimeError(
            "torch.cuda.is_available() is False -- refusing to embed on CPU. "
            "Phase 0 FLAG-1: a plain pip install resolves a CPU torch build "
            "with no error; this assertion is what catches it instead of "
            "silently taking hours. If CPU is genuinely intended, that must "
            "be an explicit, deliberate override, not this default path."
        )


def load_model(model_dir) -> SentenceTransformer:
    """`model_dir` must be a filesystem path, never a hub repo id -- a
    repo-id load reaches for the network even when fully cached (proven,
    phases/v2_phase3.md SS8), a local-dir load structurally cannot.

    fp16 (`torch_dtype=float16`): the RTX 4050 Laptop's 6GB VRAM cannot hold
    BGE-M3's fp32 activations for its longest real chunks (up to 6091 tokens
    under M3's own tokenizer, phases/v2_phase3.md SS6) at any usable batch
    size -- confirmed by a real `CUDA out of memory` crash at fp32,
    batch_size=32, not a precaution taken in advance. fp16 roughly halves
    activation memory and unlocks PyTorch's memory-efficient SDPA attention
    kernel, which the fp32 path did not use.
    """
    return SentenceTransformer(
        str(model_dir), device="cuda",
        model_kwargs={"torch_dtype": torch.float16},
    )


def embed_texts(model: SentenceTransformer, texts: list[str]) -> np.ndarray:
    """No instruction prefix on either side -- BGE-M3's own card: 'no longer
    requires adding instructions to the queries' (phases/v2_phase3.md SS5).
    Same function serves chunks and checklist items; there is no asymmetry
    to encode.
    """
    if not texts:
        return np.zeros((0, model.get_sentence_embedding_dimension()), dtype=np.float32)
    vecs = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    return vecs.astype(np.float32)
