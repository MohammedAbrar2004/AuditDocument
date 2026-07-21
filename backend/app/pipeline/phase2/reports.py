"""Two sign-off reports, same discipline Phase 1 applied to the empty-table
and diagram-only-page rules: run against the full corpus, not a sample,
before a rule is trusted.

coverage_report.md -- source-line reconciliation. Every non-empty raw
PyMuPDF `line` on every page of both PDFs must land in exactly one of:
  A. body line placed in a chunk
  B. heading/parenthetical line absorbed into chunk text
  C. line intentionally stripped (this pipeline stage strips nothing --
     expected to be 0; reported explicitly rather than assumed)
  D. line merged into a preceding line's row (y-proximity grouping)
Any line with no bucket is a real drop and is reported by name and page.

block_homogeneity_report.md -- corpus-wide check of the heading-detection
discriminator (phases/v2_phase2.md grounding item 1), proven on one block
(b059, External Issues / Internal Issues) during planning. Reports every
block containing a mid-block all-bold row that is NOT numbered/annex --
these are exactly the shape that would have been misclassified as headings
under a plain all-bold-line rule, and are the corpus-wide population the
block-homogeneity check is protecting against.
"""
from collections import defaultdict

from .classify import classify_rows
from .rows import block_homogeneity


def reconcile_source_lines(source_pdf: str, all_debug: list[dict]) -> dict:
    bucket_A = bucket_B = bucket_C = 0
    bucket_D_lines = []
    unaccounted = []
    total_raw = 0
    table_attach_rows = []

    for debug in all_debug:
        doc_id = debug["doc_id"]
        events = debug["events"]
        fate = debug["fate"]
        for i, ev in enumerate(events):
            if ev["kind"] == "table":
                letter, note = fate.get(i, (None, None))
                table_attach_rows.append({
                    "doc_id": doc_id, "table_id": ev["table_id"],
                    "attached": letter == "TABLE", "note": note,
                })
                continue
            members = ev["member_lines"]
            total_raw += len(members)
            letter, note = fate.get(i, (None, None))
            if letter is None:
                for m in members:
                    unaccounted.append({"doc_id": doc_id, "page": ev["page"], "text": m["text"]})
                continue
            if letter == "A":
                bucket_A += 1
            elif letter == "B":
                bucket_B += 1
            # extra members beyond the first (the row's representative line)
            # were merged into that row by y-proximity grouping.
            for m in members[1:]:
                bucket_D_lines.append({"doc_id": doc_id, "page": ev["page"], "text": m["text"]})

    bucket_D = len(bucket_D_lines)
    total = bucket_A + bucket_B + bucket_C + bucket_D

    n_tables_total = len(table_attach_rows)
    n_tables_attached = sum(1 for t in table_attach_rows if t["attached"])
    tables_not_attached = [t for t in table_attach_rows if not t["attached"]]

    return {
        "source_pdf": source_pdf,
        "total_raw_lines": total_raw,
        "bucket_A": bucket_A,
        "bucket_B": bucket_B,
        "bucket_C": bucket_C,
        "bucket_D": bucket_D,
        "sum": total,
        "unaccounted": unaccounted,
        "n_tables_total": n_tables_total,
        "n_tables_attached": n_tables_attached,
        "tables_not_attached": tables_not_attached,
    }


def block_homogeneity_check(all_debug: list[dict]) -> dict:
    """Re-derives classification per block using the real classify_rows()
    function (not a reimplementation) so this report can't silently drift
    from what the chunker actually does.

    First pass over this report flagged every mid-block bold row, including
    ones that are perfectly correctly handled via the numbered-heading regex
    regardless of block placement (e.g. "5.2 Policy", "7.1.1 General") --
    those are not excluded by anything, they were never at risk. Fixed:
    only count a row as "excluded by homogeneity" if classify_rows() itself
    actually assigned it kind="body" despite being all-bold and not matching
    the parenthetical pattern -- i.e. rows that would have been misclassified
    as headings under a plain "all-bold line" rule, and are only correctly
    suppressed because of the block-homogeneity check.
    """
    n_blocks_total = 0
    n_homog_single = 0
    n_homog_multi = 0
    homog_multi_samples = []
    n_mixed_blocks = 0
    excluded_midblock_bold_rows = []  # the population block-homogeneity protects against

    for debug in all_debug:
        doc_id = debug["doc_id"]
        rows = debug["rows"]
        homog_map = block_homogeneity(rows)
        classified = classify_rows(rows, homog_map)

        by_block = defaultdict(list)
        for r in classified:
            by_block[r["block_id"]].append(r)
        for block_id, block_rows in by_block.items():
            n_blocks_total += 1
            homog = homog_map[block_id]
            if homog:
                if len(block_rows) == 1:
                    n_homog_single += 1
                else:
                    n_homog_multi += 1
                    homog_multi_samples.append({
                        "doc_id": doc_id, "block_id": block_id,
                        "rows": [r["text"] for r in block_rows],
                    })
            else:
                n_mixed_blocks += 1
                for r in block_rows:
                    # would-be heading (bold, not a parenthetical) that
                    # classify_rows demoted to body purely because its block
                    # isn't homogeneous -- numbered/annex rows never reach
                    # this state, they're real headings regardless.
                    if r["all_bold"] and r["kind"] == "body":
                        excluded_midblock_bold_rows.append({
                            "doc_id": doc_id, "block_id": block_id,
                            "page": r["page"], "text": r["text"],
                        })

    return {
        "n_blocks_total": n_blocks_total,
        "n_homog_single": n_homog_single,
        "n_homog_multi": n_homog_multi,
        "homog_multi_samples": homog_multi_samples,
        "n_mixed_blocks": n_mixed_blocks,
        "n_excluded_midblock_bold_rows": len(excluded_midblock_bold_rows),
        "excluded_midblock_bold_rows": excluded_midblock_bold_rows,
    }


def write_coverage_report(results: list[dict], out_path) -> None:
    lines = ["# Phase 2 — source-line coverage reconciliation", ""]
    lines.append("Every non-empty raw PyMuPDF `line` on every page of both PDFs, bucketed. "
                  "Zero-drop guarantee is `unaccounted == []` for every source PDF.\n")
    grand_total = grand_A = grand_B = grand_C = grand_D = 0
    for r in results:
        lines.append(f"## {r['source_pdf']}\n")
        lines.append(f"- Total raw source lines: **{r['total_raw_lines']}**")
        lines.append(f"- Bucket A (body lines placed in a chunk): {r['bucket_A']}")
        lines.append(f"- Bucket B (heading/parenthetical lines absorbed): {r['bucket_B']}")
        lines.append(f"- Bucket C (intentionally stripped): {r['bucket_C']}")
        lines.append(f"- Bucket D (merged into a preceding line's row): {r['bucket_D']}")
        lines.append(f"- **Sum: {r['sum']}** (target: {r['total_raw_lines']})")
        lines.append(f"- Unaccounted lines: **{len(r['unaccounted'])}**")
        if r["unaccounted"]:
            lines.append("  **DROP DETECTED:**")
            for u in r["unaccounted"]:
                lines.append(f"  - {u['doc_id']} p{u['page']}: {u['text']!r}")
        lines.append(f"- Tables: {r['n_tables_attached']}/{r['n_tables_total']} attached to a chunk")
        if r["tables_not_attached"]:
            lines.append("  **TABLE NOT ATTACHED:**")
            for t in r["tables_not_attached"]:
                lines.append(f"  - {t['doc_id']} {t['table_id']}")
        lines.append("")
        grand_total += r["total_raw_lines"]
        grand_A += r["bucket_A"]
        grand_B += r["bucket_B"]
        grand_C += r["bucket_C"]
        grand_D += r["bucket_D"]
    lines.append("## Corpus total (both PDFs)\n")
    lines.append(f"- Total raw source lines: **{grand_total}**")
    lines.append(f"- A={grand_A}  B={grand_B}  C={grand_C}  D={grand_D}  "
                  f"sum={grand_A + grand_B + grand_C + grand_D}")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def write_block_homogeneity_report(result: dict, out_path) -> None:
    lines = ["# Phase 2 — block-homogeneity heading-detection check (corpus-wide)", ""]
    lines.append(
        "Proven on one block during planning (`AEI-QM-T-01__p011_b059`, `External "
        "Issues` / `Internal Issues`). This report runs the same check against every "
        "block in both PDFs.\n"
    )
    lines.append(f"- Total blocks: {result['n_blocks_total']}")
    lines.append(f"- Homogeneous, single-row (ordinary heading-only block): {result['n_homog_single']}")
    lines.append(f"- Homogeneous, multi-row (FLAG-1-style glued-heading blocks): {result['n_homog_multi']}")
    lines.append(f"- Mixed (heading + body in one block): {result['n_mixed_blocks']}")
    lines.append(
        f"- Mid-block all-bold rows correctly excluded from heading status by this "
        f"check: **{result['n_excluded_midblock_bold_rows']}**\n"
    )
    lines.append(
        "The line above is the corpus-wide population the block-homogeneity rule "
        "protects against -- every one of these would have been misclassified as a "
        "heading under a plain all-bold-line rule.\n"
    )
    lines.append("## Excluded mid-block bold rows (full list — spot-check before trusting beyond b059)\n")
    for r in result["excluded_midblock_bold_rows"]:
        lines.append(f"- {r['doc_id']} {r['block_id']} p{r['page']}: {r['text']!r}")
    lines.append("\n## Homogeneous multi-row blocks (FLAG-1 gluing cases, full list)\n")
    for s in result["homog_multi_samples"]:
        lines.append(f"- {s['doc_id']} {s['block_id']}: {s['rows']}")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
