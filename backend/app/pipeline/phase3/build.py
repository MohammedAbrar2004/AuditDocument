"""Orchestrates Phase 3: parse both checklists, embed chunks + items,
tokenize chunks for BM25. Reads Phase 2's chunk artifact and the checklist
PDFs directly -- checklists never went through Phase 1/2, per
phases/v2_phase3.md.
"""
import json

from .bm25_index import build_bm25_corpus
from .checklist_parse import parse_checklist
from .checklist_rows import extract_rows
from .embed import assert_chunk_id_uniqueness, assert_cuda, embed_texts, load_model

CHECKLISTS = [
    ("AUDIT_CHECKLIST_AQB.pdf", "AQB"),
    ("AUDIT_CHECKLIST_AEC.pdf", "AEC"),
]


def parse_checklists(docs_dir) -> dict[str, dict]:
    """Returns {"AQB": {"items": [...], "debug": {...}}, "AEC": {...}}."""
    out = {}
    for filename, prefix in CHECKLISTS:
        rows = extract_rows(str(docs_dir / filename))
        items, debug = parse_checklist(rows, prefix)
        out[prefix] = {"source_pdf": filename, "items": items, "debug": debug}
    return out


def load_chunks(phase2_dir) -> list[dict]:
    path = phase2_dir / "combined_complete_qms.json"
    with open(path, "r", encoding="utf-8") as f:
        artifact = json.load(f)
    return artifact["chunks"]


def build_artifacts(docs_dir, phase2_dir) -> dict:
    checklists = parse_checklists(docs_dir)
    chunks = load_chunks(phase2_dir)

    assert_chunk_id_uniqueness(chunks)
    assert_cuda()

    from app.config import settings
    model = load_model(settings.MODEL_DIR)

    chunk_manifest = [c["chunk_id"] for c in chunks]
    chunk_texts = [c["text"] for c in chunks]
    chunk_embeddings = embed_texts(model, chunk_texts)

    item_embeddings = {}
    for prefix, data in checklists.items():
        texts = [it["text"] for it in data["items"]]
        item_embeddings[prefix] = embed_texts(model, texts)

    bm25_corpus = build_bm25_corpus(chunks)

    return {
        "checklists": checklists,
        "chunk_manifest": chunk_manifest,
        "chunk_embeddings": chunk_embeddings,
        "item_embeddings": item_embeddings,
        "bm25_corpus": bm25_corpus,
        "model_dim": model.get_embedding_dimension(),
        "model_max_seq_length": model.max_seq_length,
        "n_chunks": len(chunks),
    }
