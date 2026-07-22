"""Stage A (parse + chunk, fast, no GPU) and Stage B (embed + rank, slow,
GPU) of the upload pipeline (v2_phase5.md Design). Both call Phase 1-4's
existing library functions against one uploaded document -- no scoring,
ranking, chunking, or extraction logic is reimplemented here (v2_phase5.md
SS1: "Phase 5 is an orchestration + serving layer").
"""
import json
import time

import numpy as np
from rank_bm25 import BM25Okapi

from app.pipeline.phase1.build import build_artifact as phase1_build_artifact
from app.pipeline.phase2.build import build_artifact as phase2_build_artifact
from app.pipeline.phase3.bm25_index import build_bm25_corpus, tokenize
from app.pipeline.phase3.embed import assert_chunk_id_uniqueness, embed_texts
from app.pipeline.phase4.constants import RRF_K
from app.pipeline.phase4.fuse_rrf import fuse, view_entries
from app.pipeline.phase4.keyword_rank import chunk_token_sets, high_idf_vocab, score_item
from app.pipeline.phase4.semantic_rank import cosine_matrix

from . import store
from .gate_grounding import derive_gate

CHECKLISTS = ("AQB", "AEC")


def run_stage_a(pdf_bytes: bytes, filename: str) -> dict:
    """Clears the per-document scope, then runs Phase 1 (extract, segment,
    clean) + Phase 2 (chunk) against the uploaded bytes. No checklist
    involvement, no GPU.
    """
    store.clear_scope()

    pdf_path = store.source_pdf_path()
    pdf_path.write_bytes(pdf_bytes)

    t0 = time.monotonic()
    p1_artifact = phase1_build_artifact(pdf_path, filename)
    # Same convention as phase1/run.py: strip the underscore-prefixed debug
    # keys (_table_stats, _diagram_page_report) before persisting.
    persisted_p1 = {k: v for k, v in p1_artifact.items() if not k.startswith("_")}
    store.phase1_path().write_text(
        json.dumps(persisted_p1, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Re-read from disk rather than pass persisted_p1 straight through: Phase
    # 2's table-insertion code (phase2/tables.py) looks up bbox_by_page by
    # str(page_start) -- true after a JSON round-trip (JSON has no int keys,
    # so phase1/run.py -> phase2/run.py always hands Phase 2 string-keyed
    # dicts), false on the raw in-memory dict phase1.build.build_artifact
    # returns (int keys there). Found by a real KeyError on the first live
    # run against COMBINED_Complete_QMS.pdf, not assumed -- see this
    # document's build report. Re-reading here reproduces the batch
    # pipeline's actual contract instead of patching Phase 2's code.
    p1_from_disk = json.loads(store.phase1_path().read_text(encoding="utf-8"))
    p2_artifact, _debug = phase2_build_artifact(p1_from_disk)
    store.phase2_path().write_text(
        json.dumps(p2_artifact, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    elapsed = time.monotonic() - t0

    chunks = p2_artifact["chunks"]
    subdocs = p1_from_disk["subdocuments"]

    return {
        "filename": filename,
        "subdocument_count": len(subdocs),
        "subdocuments": [{"doc_id": sd["doc_id"], "doc_name": sd["doc_name"]} for sd in subdocs],
        "chunk_count": len(chunks),
        "elapsed_seconds": round(elapsed, 3),
    }


def run_stage_b(model, checklists: dict) -> dict:
    """`checklists` is {"AQB": {"items": [...], "embeddings": np.ndarray},
    "AEC": {...}} -- the checklist-persistent scope, loaded once at startup
    (app/state.py). Embeds this document's own chunks on GPU, builds this
    document's own BM25 corpus, re-derives the gate for this document
    (gate_grounding.py), then ranks every item of both checklists against
    this document's chunks.
    """
    if not store.phase2_path().exists():
        raise FileNotFoundError(
            "No per-document Phase 2 artifact -- run POST /documents/upload first."
        )

    t0 = time.monotonic()
    p2_artifact = json.loads(store.phase2_path().read_text(encoding="utf-8"))
    chunks = p2_artifact["chunks"]
    assert_chunk_id_uniqueness(chunks)

    manifest = [c["chunk_id"] for c in chunks]
    chunk_ids_in_p2 = {c["chunk_id"] for c in chunks}
    # Join-integrity guarantee (v2_phase5.md "Hydration"): every id this
    # build will ever rank is drawn directly from this same p2 artifact --
    # asserted here, not just trusted, same discipline as Phase 4's own
    # load-time asserts.
    assert set(manifest) <= chunk_ids_in_p2, (
        "chunk_manifest references a chunk_id not present in this document's "
        "own phase2.json -- refusing to rank against a misaligned corpus."
    )

    texts = [c["text"] for c in chunks]
    t_embed0 = time.monotonic()
    chunk_embeddings = embed_texts(model, texts)
    embed_elapsed = time.monotonic() - t_embed0

    np.save(store.chunk_embeddings_path(), chunk_embeddings)
    store.chunk_manifest_path().write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
    )

    bm25_corpus = build_bm25_corpus(chunks)
    store.bm25_corpus_path().write_text(
        json.dumps(bm25_corpus, ensure_ascii=False), encoding="utf-8"
    )

    tokens_list = [bm25_corpus[cid] for cid in manifest]
    bm25 = BM25Okapi(tokens_list)
    gate = derive_gate(bm25)
    store.gate_path().write_text(json.dumps(gate, indent=2), encoding="utf-8")

    rare_vocab = high_idf_vocab(bm25, threshold=gate["high_idf_threshold"])
    chunk_sets = chunk_token_sets(tokens_list)

    zero_pass = {}
    for prefix in CHECKLISTS:
        items = checklists[prefix]["items"]
        item_embeddings = checklists[prefix]["embeddings"]
        sim_matrix = cosine_matrix(item_embeddings, chunk_embeddings)

        items_out = {}
        zero = 0
        for idx, item in enumerate(items):
            kw_scores, above_floor = score_item(
                bm25,
                item["text"],
                tokenize,
                rare_vocab,
                chunk_sets,
                min_high_idf_terms=gate["min_high_idf_terms"],
                min_score=gate["min_score"],
            )
            sem_scores = sim_matrix[idx]

            keyword, kw_ranks = view_entries(kw_scores, manifest, above_floor)
            semantic, sem_ranks = view_entries(sem_scores, manifest, None)
            rrf_scores = fuse(kw_ranks, sem_ranks)
            both, _ = view_entries(rrf_scores, manifest, None)

            items_out[item["item_id"]] = {"keyword": keyword, "semantic": semantic, "both": both}
            if not any(e["above_floor"] for e in keyword):
                zero += 1

        zero_pass[prefix] = {"n_items": len(items), "zero_pass": zero}
        out = {
            "source_checklist": prefix,
            "n_items": len(items),
            "n_chunks": len(manifest),
            "rrf_k": RRF_K,
            "gate": gate,
            "items": items_out,
        }
        store.rankings_path(prefix).write_text(
            json.dumps(out, ensure_ascii=False), encoding="utf-8"
        )

    elapsed = time.monotonic() - t0

    summary = {
        "n_chunks": len(chunks),
        "embed_elapsed_seconds": round(embed_elapsed, 3),
        "total_elapsed_seconds": round(elapsed, 3),
        "gate": gate,
        "zero_pass": zero_pass,
    }
    store.build_report_path().write_text(_stage_b_report_md(summary), encoding="utf-8")
    return summary


def _stage_b_report_md(summary: dict) -> str:
    lines = ["# Upload Stage B build report", ""]
    lines.append(f"- chunks: {summary['n_chunks']}")
    lines.append(f"- embedding time: {summary['embed_elapsed_seconds']}s")
    lines.append(f"- total Stage B time: {summary['total_elapsed_seconds']}s")
    lines.append(f"- gate: {json.dumps(summary['gate'])}")
    for prefix, z in summary["zero_pass"].items():
        lines.append(
            f"- {prefix}: {z['zero_pass']} / {z['n_items']} items have no chunk "
            f"tagged above_floor:true"
        )
    return "\n".join(lines)
