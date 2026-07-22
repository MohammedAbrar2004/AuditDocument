"""Orchestrates Phase 4: for every checklist item, scores and ranks the
full corpus three ways (keyword, semantic, both) and assembles the
per-checklist artifact. Reads Phase 3's artifacts only -- never re-embeds,
re-tokenizes, or re-parses a PDF.
"""
import json

import numpy as np
from rank_bm25 import BM25Okapi

from app.pipeline.phase3.bm25_index import tokenize

from .constants import HIGH_IDF_THRESHOLD, MIN_HIGH_IDF_TERMS, MIN_SCORE, RRF_K
from .fuse_rrf import fuse, view_entries
from .keyword_rank import chunk_token_sets, high_idf_vocab, score_item
from .semantic_rank import cosine_matrix

CHECKLISTS = ("AQB", "AEC")


def load_corpus(phase3_dir) -> tuple[list[str], list[list[str]], np.ndarray]:
    manifest = json.loads((phase3_dir / "chunk_manifest.json").read_text(encoding="utf-8"))
    bm25_corpus = json.loads((phase3_dir / "bm25_corpus.json").read_text(encoding="utf-8"))

    if list(bm25_corpus.keys()) != manifest:
        raise ValueError(
            "bm25_corpus.json key order does not match chunk_manifest.json -- "
            "refusing to rank against a misaligned corpus."
        )

    tokens_list = [bm25_corpus[cid] for cid in manifest]
    chunk_embeddings = np.load(phase3_dir / "chunk_embeddings.npy")
    if chunk_embeddings.shape[0] != len(manifest):
        raise ValueError(
            f"chunk_embeddings.npy has {chunk_embeddings.shape[0]} rows, "
            f"chunk_manifest.json has {len(manifest)} entries -- misaligned."
        )

    return manifest, tokens_list, chunk_embeddings


def load_checklist(phase3_dir, prefix: str) -> tuple[list[dict], np.ndarray]:
    data = json.loads(
        (phase3_dir / f"checklist_{prefix.lower()}.json").read_text(encoding="utf-8")
    )
    items = data["items"]
    item_embeddings = np.load(phase3_dir / f"item_embeddings_{prefix.lower()}.npy")
    if item_embeddings.shape[0] != len(items):
        raise ValueError(
            f"item_embeddings_{prefix.lower()}.npy has {item_embeddings.shape[0]} rows, "
            f"checklist_{prefix.lower()}.json has {len(items)} items -- misaligned."
        )
    return items, item_embeddings


def build_artifacts(phase3_dir) -> dict[str, dict]:
    manifest, tokens_list, chunk_embeddings = load_corpus(phase3_dir)
    chunk_sets = chunk_token_sets(tokens_list)
    bm25 = BM25Okapi(tokens_list)
    rare_vocab = high_idf_vocab(bm25)

    out = {}
    for prefix in CHECKLISTS:
        items, item_embeddings = load_checklist(phase3_dir, prefix)
        sim_matrix = cosine_matrix(item_embeddings, chunk_embeddings)

        items_out = {}
        for idx, item in enumerate(items):
            kw_scores, above_floor = score_item(
                bm25, item["text"], tokenize, rare_vocab, chunk_sets
            )
            sem_scores = sim_matrix[idx]

            keyword, kw_ranks = view_entries(kw_scores, manifest, above_floor)
            semantic, sem_ranks = view_entries(sem_scores, manifest, None)

            rrf_scores = fuse(kw_ranks, sem_ranks)
            both, _ = view_entries(rrf_scores, manifest, None)

            items_out[item["item_id"]] = {
                "keyword": keyword,
                "semantic": semantic,
                "both": both,
            }

        out[prefix] = {
            "source_checklist": prefix,
            "n_items": len(items),
            "n_chunks": len(manifest),
            "rrf_k": RRF_K,
            "gate": {
                "high_idf_threshold": HIGH_IDF_THRESHOLD,
                "min_high_idf_terms": MIN_HIGH_IDF_TERMS,
                "min_score": MIN_SCORE,
            },
            "items": items_out,
        }

    return out
