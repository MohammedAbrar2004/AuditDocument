"""Automated per-document gate grounding -- the ingest-time equivalent of Phase 4's
manual grounding pass (v2_phase4.md SS3), turned into code because there is no human
review step at upload time (v2_phase5.md SS5).

`phase4/constants.py`'s HIGH_IDF_THRESHOLD=5.0 was never really "idf >= 5.0" -- it was
"a term appearing in at most 2 of the corpus's chunks." 5.0 is only the idf value that
condition produces at N=501 under rank_bm25's own formula. This module re-derives that
same idf value for whatever N a newly uploaded document actually has, instead of
inheriting 501's number. MIN_SCORE is recomputed the same way v2_phase4.md's grounding
pass computed it by hand -- the ~1st percentile of real single-rare-term BM25
contributions -- because that is a genuine distributional statistic, not a formula
lookup, and the distribution differs per document (depends on avgdl and the corpus's
real df values). MIN_HIGH_IDF_TERMS stays fixed at 1: v2_phase4.md's own dry run showed
that knob is driven by how many rare terms a short checklist item's text contains, not
by the size of the corpus being ranked against -- the same 212 items get ranked
against every uploaded document.
"""
import math

import numpy as np

# Not re-derived per document -- see module docstring.
MIN_HIGH_IDF_TERMS = 1

# "Rare" = a term appearing in at most this many chunks. Phase 4 grounded this concept
# by hand at N=501 (idf>=5.0 <=> df<=2, confirmed against the real corpus). The
# concept (df<=2) is what generalizes; the idf number it produces does not, since
# rank_bm25's idf formula is a function of N as well as df.
RARE_DF = 2

# The ~1st percentile of real single-rare-term BM25 contributions, same statistic
# v2_phase4.md computed for the reference corpus (minimum 0.6234, ~1st percentile
# ~0.63, both close to the 0.5 that shipped). Recomputed per document instead of
# inherited, since the distribution depends on this document's own avgdl and df values.
MIN_SCORE_PERCENTILE = 1


def idf_for_df(df: int, n_docs: int) -> float:
    """rank_bm25's own BM25Okapi._calc_idf formula (confirmed by reading
    rank_bm25.py directly: idf = ln(N - df + 0.5) - ln(df + 0.5)), evaluated
    for a hypothetical term at this document frequency -- a direct formula
    evaluation, not a fit or an estimate.
    """
    return math.log(n_docs - df + 0.5) - math.log(df + 0.5)


def derive_gate(bm25) -> dict:
    """`bm25` is a BM25Okapi already built over this document's own chunk tokens.

    Returns the gate dict persisted to gate.json: {high_idf_threshold,
    min_high_idf_terms, min_score, n_chunks, rare_vocab_size, vocab_size,
    single_term_contribution_min, single_term_contribution_n} -- the last four
    are diagnostic, kept for post-hoc inspection since there is no pre-hoc
    sign-off step possible at ingest time (v2_phase5.md SS5).
    """
    n_chunks = bm25.corpus_size
    high_idf_threshold = idf_for_df(RARE_DF, n_chunks)

    rare_vocab = {w for w, v in bm25.idf.items() if v >= high_idf_threshold}

    k1, b, avgdl = bm25.k1, bm25.b, bm25.avgdl
    doc_len = np.array(bm25.doc_len)
    contributions = []
    for i in range(n_chunks):
        freqs = bm25.doc_freqs[i]
        dl = doc_len[i]
        for term, tf in freqs.items():
            if term in rare_vocab:
                idf = bm25.idf[term]
                contrib = idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avgdl))
                contributions.append(contrib)

    if contributions:
        min_score = float(np.percentile(contributions, MIN_SCORE_PERCENTILE))
    else:
        # No term in this document's corpus clears the rare-term threshold at all
        # (possible on a very small or very repetitive document) -- the rare-term
        # gate already can't pass anything, MIN_SCORE has no distribution to trim.
        # Fall back to 0.0 rather than raise: the gate still tags correctly (every
        # chunk fails MIN_HIGH_IDF_TERMS, above_floor is false everywhere), it just
        # isn't the interesting case MIN_SCORE was designed for.
        min_score = 0.0

    return {
        "high_idf_threshold": round(high_idf_threshold, 6),
        "min_high_idf_terms": MIN_HIGH_IDF_TERMS,
        "min_score": round(min_score, 6),
        "n_chunks": n_chunks,
        "rare_vocab_size": len(rare_vocab),
        "vocab_size": len(bm25.idf),
        "single_term_contribution_min": float(min(contributions)) if contributions else None,
        "single_term_contribution_n": len(contributions),
    }
