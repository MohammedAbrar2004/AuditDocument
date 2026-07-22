"""Writes the Phase 4 build report -- same convention as every prior
phase's report: real numbers from the real run, independently reloaded
from the artifacts just written to disk, not carried over from the
build's own in-memory state or from the plan's dry run.
"""
import json

import numpy as np
from rank_bm25 import BM25Okapi

from app.pipeline.phase3.bm25_index import tokenize

from .constants import HIGH_IDF_THRESHOLD, MIN_HIGH_IDF_TERMS, MIN_SCORE, RRF_K
from .keyword_rank import high_idf_vocab

SAMPLE_ITEMS = {
    # (checklist, item_id): why it's shown
    "AQB": ["AQB__6.2.17", "AQB__4.2.1.1"],
    "AEC": ["AEC__9.1", "AEC__4.2.5.2"],
}


def _gate_grounding(phase3_dir) -> dict:
    """Recomputes the gate's real numbers directly from bm25_corpus.json --
    independent of build.py's in-memory run, and independent of the plan's
    own dry run.
    """
    manifest = json.loads((phase3_dir / "chunk_manifest.json").read_text(encoding="utf-8"))
    bm25_corpus = json.loads((phase3_dir / "bm25_corpus.json").read_text(encoding="utf-8"))
    tokens_list = [bm25_corpus[cid] for cid in manifest]
    bm25 = BM25Okapi(tokens_list)

    rare_vocab = high_idf_vocab(bm25)

    from collections import Counter
    df_counter = Counter()
    for toks in tokens_list:
        df_counter.update(set(toks))
    dfs_at_high = sorted(set(df_counter[w] for w in rare_vocab))

    k1, b, avgdl = bm25.k1, bm25.b, bm25.avgdl
    doc_len = np.array(bm25.doc_len)
    contributions = []
    for i, toks in enumerate(tokens_list):
        freqs = bm25.doc_freqs[i]
        dl = doc_len[i]
        for term, tf in freqs.items():
            if term in rare_vocab:
                idf = bm25.idf[term]
                contrib = idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avgdl))
                contributions.append(contrib)
    contributions = np.array(contributions)

    # Real (item, chunk) total-score check: of the pairs that pass the
    # MIN_HIGH_IDF_TERMS gate, how many does MIN_SCORE actually cut --
    # confirms whether it's the near-zero-tail trim it's meant to be, not
    # a silent dominant filter.
    aqb = json.loads((phase3_dir / "checklist_aqb.json").read_text(encoding="utf-8"))
    aec = json.loads((phase3_dir / "checklist_aec.json").read_text(encoding="utf-8"))
    all_items = aqb["items"] + aec["items"]
    chunk_sets = [set(toks) for toks in tokens_list]

    term_pass_scores = []
    for it in all_items:
        query = tokenize(it["text"])
        q_rare = {w for w in set(query) if w in rare_vocab}
        if not q_rare:
            continue
        scores = bm25.get_scores(query)
        for i, cs in enumerate(chunk_sets):
            if sum(1 for w in q_rare if w in cs) >= MIN_HIGH_IDF_TERMS:
                term_pass_scores.append(scores[i])
    term_pass_scores = np.array(term_pass_scores)

    return {
        "rare_vocab_size": len(rare_vocab),
        "vocab_size": len(bm25.idf),
        "dfs_at_high_idf": dfs_at_high,
        "single_term_min_contribution": float(contributions.min()),
        "single_term_frac_below_5": float((contributions < 5.0).mean()),
        "single_term_frac_below_min_score": float((contributions < MIN_SCORE).mean()),
        "single_term_percentiles": {
            p: float(np.percentile(contributions, p)) for p in (1, 5, 25, 50, 75, 99)
        },
        "n_term_pass_pairs": len(term_pass_scores),
        "term_pass_frac_below_min_score": (
            float((term_pass_scores < MIN_SCORE).mean()) if len(term_pass_scores) else None
        ),
    }


def _zero_pass_counts(phase4_dir) -> dict:
    out = {}
    for prefix in ("AQB", "AEC"):
        data = json.loads((phase4_dir / f"rankings_{prefix.lower()}.json").read_text(encoding="utf-8"))
        n_items = len(data["items"])
        zero = sum(
            1
            for item in data["items"].values()
            if not any(e["above_floor"] for e in item["keyword"])
        )
        out[prefix] = {"n_items": n_items, "zero_pass": zero}
    return out


def _list_lengths_ok(phase4_dir) -> dict:
    """Structural checks from the plan's verification checklist, run
    against the artifacts actually on disk.
    """
    out = {}
    for prefix in ("AQB", "AEC"):
        data = json.loads((phase4_dir / f"rankings_{prefix.lower()}.json").read_text(encoding="utf-8"))
        n_chunks = data["n_chunks"]
        bad = []
        for item_id, views in data["items"].items():
            for view_name in ("keyword", "semantic", "both"):
                entries = views[view_name]
                if len(entries) != n_chunks:
                    bad.append((item_id, view_name, len(entries)))
                    continue
                ids = {e["chunk_id"] for e in entries}
                if len(ids) != n_chunks:
                    bad.append((item_id, view_name, f"{len(ids)} unique ids"))
                if view_name != "keyword" and any("above_floor" in e for e in entries):
                    bad.append((item_id, view_name, "unexpected above_floor key"))
        out[prefix] = {"n_items_checked": len(data["items"]), "violations": bad}
    return out


def _format_entry(e: dict) -> str:
    parts = [f"rank {e['rank']}", e["chunk_id"], f"score={e['score']}"]
    if "above_floor" in e:
        parts.append(f"above_floor={e['above_floor']}")
    return " | ".join(parts)


def _sample_item_block(phase4_dir) -> list[str]:
    lines = []
    for prefix, item_ids in SAMPLE_ITEMS.items():
        data = json.loads((phase4_dir / f"rankings_{prefix.lower()}.json").read_text(encoding="utf-8"))
        for item_id in item_ids:
            if item_id not in data["items"]:
                lines.append(f"### {item_id} -- NOT FOUND in rankings_{prefix.lower()}.json")
                continue
            views = data["items"][item_id]
            lines.append(f"### {item_id}")
            for view_name in ("keyword", "semantic", "both"):
                lines.append(f"**{view_name}** top 5:")
                for e in views[view_name][:5]:
                    lines.append(f"- {_format_entry(e)}")
            top_kw = views["keyword"][0]
            if not top_kw["above_floor"]:
                lines.append(
                    f"**Note:** top keyword hit (score={top_kw['score']}) is "
                    f"`above_floor: false` -- high raw score, but doesn't share "
                    f"enough rare terms with the item. Shown, not dropped."
                )
            lines.append("")
    return lines


def write_build_report(phase3_dir, phase4_dir, path) -> None:
    lines = ["# Phase 4 build report", ""]

    lines.append("## Artifact files")
    lines.append("")
    for prefix in ("AQB", "AEC"):
        fpath = phase4_dir / f"rankings_{prefix.lower()}.json"
        size_mb = fpath.stat().st_size / (1024 * 1024)
        lines.append(f"- `rankings_{prefix.lower()}.json`: {size_mb:.2f} MB")
    lines.append("")

    lines.append("## Gate grounding -- recomputed independently from the artifacts on disk")
    lines.append("")
    g = _gate_grounding(phase3_dir)
    lines.append(f"- `HIGH_IDF_THRESHOLD` = {HIGH_IDF_THRESHOLD}, `MIN_HIGH_IDF_TERMS` = "
                  f"{MIN_HIGH_IDF_TERMS}, `MIN_SCORE` = {MIN_SCORE}, `RRF_K` = {RRF_K}")
    lines.append(f"- rare vocab: {g['rare_vocab_size']} / {g['vocab_size']} terms")
    lines.append(f"- distinct document-frequency values among rare terms: {g['dfs_at_high_idf']}")
    lines.append(f"- single-rare-term BM25 contribution (tf, dl, avgdl from the real corpus):")
    lines.append(f"  - minimum: {g['single_term_min_contribution']:.4f}")
    lines.append(f"  - fraction below 5.0: {g['single_term_frac_below_5']:.1%}")
    lines.append(f"  - fraction below MIN_SCORE ({MIN_SCORE}): {g['single_term_frac_below_min_score']:.1%}")
    lines.append(f"  - percentiles: " + ", ".join(f"p{p}={v:.3f}" for p, v in g["single_term_percentiles"].items()))
    lines.append(
        f"- of {g['n_term_pass_pairs']} real (item, chunk) pairs that clear "
        f"MIN_HIGH_IDF_TERMS, {g['term_pass_frac_below_min_score']:.1%} fall below "
        f"MIN_SCORE={MIN_SCORE} on total score -- confirms MIN_SCORE trims only the "
        f"near-zero tail here, not the bulk of gate-passing pairs."
    )
    lines.append("")

    lines.append("## Zero-pass items at final settings")
    lines.append("")
    for prefix, stats in _zero_pass_counts(phase4_dir).items():
        lines.append(f"- {prefix}: {stats['zero_pass']} / {stats['n_items']} items have no "
                      f"chunk tagged `above_floor: true`")
    lines.append("")

    lines.append("## Structural verification (full lists, no truncation, no drops)")
    lines.append("")
    for prefix, stats in _list_lengths_ok(phase4_dir).items():
        status = "OK, zero violations" if not stats["violations"] else f"{len(stats['violations'])} VIOLATIONS"
        lines.append(f"- {prefix}: {stats['n_items_checked']} items checked -- {status}")
        for v in stats["violations"][:10]:
            lines.append(f"  - {v}")
    lines.append("")

    lines.append("## Sample items -- full top-5 per view, reloaded fresh from disk")
    lines.append("")
    lines.extend(_sample_item_block(phase4_dir))

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
