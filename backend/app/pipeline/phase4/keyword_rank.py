"""Scores every chunk against one checklist item's BM25 query, and applies
the floor gate. The gate tags `above_floor`; it never removes anything from
the returned array -- filtering is the UI slider's job, at view time
(master_contextC.md).
"""
import numpy as np

from .constants import HIGH_IDF_THRESHOLD, MIN_HIGH_IDF_TERMS, MIN_SCORE


def high_idf_vocab(bm25, threshold: float = HIGH_IDF_THRESHOLD) -> set[str]:
    """Terms whose corpus-wide idf clears the "rare" threshold -- see
    constants.py for the grounding (idf >= 5.0 <=> appears in at most 2 of
    501 chunks, confirmed against the real corpus, not assumed).

    `threshold` defaults to the reference corpus's grounded constant, so
    every existing call site is unaffected. Phase 5's per-upload path passes
    its own document's formula-derived threshold instead (v2_phase5.md SS5,
    pipeline/upload/gate_grounding.py) -- pure additive parameterization, no
    behavior change for Phase 4's own batch build (confirmed: rebuild after
    this change is byte-identical to before it).
    """
    return {w for w, v in bm25.idf.items() if v >= threshold}


def chunk_token_sets(tokens_list: list[list[str]]) -> list[set[str]]:
    return [set(toks) for toks in tokens_list]


def score_item(
    bm25,
    item_text: str,
    tokenize,
    rare_vocab: set[str],
    chunk_sets: list[set[str]],
    min_high_idf_terms: int = MIN_HIGH_IDF_TERMS,
    min_score: float = MIN_SCORE,
) -> tuple[np.ndarray, np.ndarray]:
    """Returns (scores, above_floor), both length n_chunks, in
    chunk_manifest order.

    `min_high_idf_terms` / `min_score` default to the reference corpus's
    grounded constants (unchanged behavior for Phase 4's own batch build).
    Phase 5's per-upload path passes its own document's re-derived gate
    values instead (v2_phase5.md SS5).
    """
    query = tokenize(item_text)
    scores = bm25.get_scores(query)

    query_rare = {w for w in set(query) if w in rare_vocab}
    if query_rare:
        rare_overlap = np.array(
            [sum(1 for w in query_rare if w in cs) for cs in chunk_sets]
        )
    else:
        rare_overlap = np.zeros(len(chunk_sets), dtype=int)

    above_floor = (rare_overlap >= min_high_idf_terms) & (scores >= min_score)
    return scores, above_floor
