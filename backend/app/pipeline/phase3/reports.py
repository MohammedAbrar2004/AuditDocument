"""Writes the Phase 3 build/sign-off report -- same convention as Phase 1's
empty_table_report.md / diagram_page_report.md and Phase 2's
coverage_report.md / block_homogeneity_report.md: one markdown file, real
numbers from the real run, not a template filled with assumptions.
"""
import torch


def write_build_report(artifacts: dict, path) -> None:
    lines = ["# Phase 3 build report", ""]

    lines.append("## Checklist parsing")
    lines.append("")
    for prefix, data in artifacts["checklists"].items():
        d = data["debug"]
        lines.append(f"### {prefix} (`{data['source_pdf']}`)")
        lines.append(f"- number/body column threshold (auto-detected): {d['threshold']:.2f}pt")
        lines.append(f"- headings (bold numbered rows, never items): {d['n_headings']}")
        lines.append(f"- leaf items emitted: {d['n_items_final']}")
        lines.append(f"- of which synthesized via paragraph-gap split: {d['n_synthesized_paragraph_splits']}")
        lines.append(f"- orphan body rows (arrived with nothing open, should be 0): {d['n_orphan_body_rows']}")
        lines.append("")

    lines.append("## Chunk embeddings")
    lines.append("")
    lines.append(f"- chunks embedded: {artifacts['n_chunks']}")
    lines.append(f"- chunk_id uniqueness: asserted, passed (see embed.py)")
    lines.append(f"- embedding dimension: {artifacts['model_dim']}")
    lines.append(f"- model max_seq_length: {artifacts['model_max_seq_length']}")
    lines.append(f"- CUDA device: {torch.cuda.get_device_name(0)}")
    lines.append("")

    lines.append("## Checklist item embeddings")
    lines.append("")
    for prefix, vecs in artifacts["item_embeddings"].items():
        lines.append(f"- {prefix}: {vecs.shape[0]} items, dim {vecs.shape[1]}")
    lines.append("")

    lines.append("## BM25 corpus")
    lines.append("")
    n_tokens = sum(len(toks) for toks in artifacts["bm25_corpus"].values())
    lines.append(f"- chunks tokenized: {len(artifacts['bm25_corpus'])}")
    lines.append(f"- total tokens: {n_tokens}")
    lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
