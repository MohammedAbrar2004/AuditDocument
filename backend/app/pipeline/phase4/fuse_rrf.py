"""Turns per-view scores into ranks, then fuses ranks only -- never raw
scores. master_contextC.md, locked: "Ranks only. No score normalization.
No alpha weighting."

`fuse` takes 1-based rank arrays exclusively, not score arrays -- the
signature itself makes it structurally impossible to smuggle a raw score
into the fusion.
"""
import numpy as np

from .constants import RRF_K


def stable_order(scores: np.ndarray) -> np.ndarray:
    """Descending sort. Ties broken by keeping chunk_manifest order --
    deterministic and reproducible rebuild-to-rebuild, no arbitrary
    re-sort needed.
    """
    return np.argsort(-scores, kind="stable")


def ranks_from_order(order: np.ndarray) -> np.ndarray:
    """`order[i]` = corpus index placed at rank i+1. Returns the inverse:
    a 1-based rank per corpus index.
    """
    ranks = np.empty(len(order), dtype=int)
    ranks[order] = np.arange(1, len(order) + 1)
    return ranks


def fuse(kw_rank: np.ndarray, sem_rank: np.ndarray) -> np.ndarray:
    """RRF: score(chunk) = 1/(k + rank_keyword) + 1/(k + rank_semantic)."""
    return 1.0 / (RRF_K + kw_rank) + 1.0 / (RRF_K + sem_rank)


def view_entries(
    scores: np.ndarray, manifest: list[str], above_floor: np.ndarray | None
) -> tuple[list[dict], np.ndarray]:
    """Full-length ranked list, never truncated. Returns the entries (in
    rank order) and the 1-based rank-per-chunk-index array, for reuse by
    RRF. Public (relocated from phase4/build.py's private `_view_entries`,
    v2_phase5.md SS1) -- Phase 5's per-upload build needs the identical
    assembly. Pure relocation, no behavior change.
    """
    order = stable_order(scores)
    ranks = ranks_from_order(order)
    entries = []
    for i in order:
        entry = {
            "chunk_id": manifest[i],
            "rank": int(ranks[i]),
            "score": round(float(scores[i]), 6),
        }
        if above_floor is not None:
            entry["above_floor"] = bool(above_floor[i])
        entries.append(entry)
    return entries, ranks
