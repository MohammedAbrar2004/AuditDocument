"""Tokenizes chunk text for BM25. Stores tokens, not a pickled BM25Okapi
object -- rebuilding BM25Okapi(tokens) at Phase 4's scoring time is cheap
(milliseconds at this corpus size) and avoids pinning a rank-bm25 pickle
format across versions (phases/v2_phase3.md, artifact schema section).
"""
import re

_WORD_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Lowercase, strip punctuation, whitespace split -- plain, no stemming,
    matching master_contextC.md's "word overlap" framing for the keyword
    view. The floor gate (min high-IDF terms, min score) is Phase 4's job,
    not this one's.
    """
    return _WORD_RE.findall(text.lower())


def build_bm25_corpus(chunks: list[dict]) -> dict[str, list[str]]:
    return {c["chunk_id"]: tokenize(c["text"]) for c in chunks}
