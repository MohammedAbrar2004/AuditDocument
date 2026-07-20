"""Generates the two mandatory sign-off report files from real pipeline
output (build.py's artifact dicts), not from grounding scratch scripts.
Both rules delete real page content per master_contextC.md's ⚠ -- these
reports are what gets reviewed before either rule's output is trusted.
"""
from pathlib import Path


def _all_table_ranges(artifact: dict):
    ranges = []
    for sd in artifact["subdocuments"]:
        for t in sd["tables"]:
            ranges.append((t["page_start"], t["page_end"], "KEEP", sd["doc_id"]))
    for e in artifact["removal_log"]:
        if e["rule"] == "empty_table":
            pages = e["pages"]
            ranges.append((pages[0], pages[-1], "DISCARD", None))
    return sorted(ranges)


def _canonical_stitch_check(artifact: dict, source_pdf: str) -> list[str]:
    ranges = _all_table_ranges(artifact)
    lines = []
    sig = next((r for r in ranges if r[0] == 1 and r[1] >= 2), None)
    lines.append(
        f"- pp.1-2 signature block ({source_pdf}): "
        + (f"stitched as pp.{sig[0]}-{sig[1]} -> {sig[2]}" if sig else "NOT STITCHED (regression)")
    )
    rev = next((r for r in ranges if r[0] == 3 and r[1] >= 5), None)
    lines.append(
        f"- pp.3-5 Revision Control ({source_pdf}): "
        + (f"stitched as pp.{rev[0]}-{rev[1]} -> {rev[2]}" if rev else "NOT STITCHED (regression)")
    )
    return lines


def write_empty_table_report(artifacts: dict, out_dir: Path) -> Path:
    lines = []
    lines.append("# Empty-table rule — build output (real pipeline, not scratch scripts)")
    lines.append("")
    lines.append(
        "Rule: discard a table if it is entirely empty, OR its rightmost column is "
        "blank on every data row (header row excluded). Unchanged since review round 1 "
        "of phases/v2_phase1.md."
    )
    lines.append("")
    lines.append(
        "Extraction: pdfplumber `find_tables()`, cross-page stitching (120pt bottom-margin "
        "gap + footer-pattern exclusion), min-width column filter (drop columns <10pt wide "
        "that are empty across all data rows, header row excluded). Full grounding history "
        "in phases/v2_phase1.md's three review rounds."
    )
    lines.append("")

    grand_total = grand_discard = grand_keep = 0
    for pdf_name, artifact in artifacts.items():
        stats = artifact["_table_stats"]
        grand_total += stats["total_stitched_tables"]
        grand_discard += stats["discarded"]
        grand_keep += stats["kept"]

        lines.append(f"## {pdf_name}")
        lines.append("")
        lines.append(
            f"{stats['total_stitched_tables']} stitched tables total. "
            f"{stats['kept']} KEEP / {stats['discarded']} DISCARD."
        )
        lines.append("")
        lines.append("**Canonical multi-page stitch check:**")
        lines.extend(_canonical_stitch_check(artifact, pdf_name))
        lines.append("")

        discards = [e for e in artifact["removal_log"] if e["rule"] == "empty_table"]
        if discards:
            lines.append("**Discarded tables:**")
            lines.append("")
            for e in discards:
                pages = e["pages"]
                page_str = f"p.{pages[0]}" if len(pages) == 1 else f"pp.{pages[0]}-{pages[-1]}"
                lines.append(f"- {page_str}: {e['detail']}")
            lines.append("")

    lines.append("## Totals across both PDFs")
    lines.append("")
    lines.append(f"{grand_total} stitched tables. {grand_keep} KEEP / {grand_discard} DISCARD.")
    lines.append("")
    lines.append(
        "Still gated per master_contextC.md's ⚠: this file is the artifact for review. "
        "The removal_log in each JSON artifact is the authoritative, already-applied record "
        "for this build."
    )

    out_path = out_dir / "empty_table_report.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def write_diagram_page_report(artifacts: dict, out_dir: Path) -> Path:
    lines = []
    lines.append("# Diagram-only-page rule — build output (full corpus)")
    lines.append("")
    lines.append(
        "Rule: a page is diagram-only when, after header/footer/table strip, it "
        "contributes ~zero body text (at most one heading-shaped block, <=150 chars) "
        "and carries >=1 image. The heading line is kept as a heading-only block; only "
        "the fact of the page being diagram-only is logged. Never OCRs or embeds image "
        "bytes."
    )
    lines.append("")

    grand_flagged = grand_pages = 0
    for pdf_name, artifact in artifacts.items():
        report = artifact["_diagram_page_report"]
        flagged = [r for r in report if r["diagram_only"]]
        grand_flagged += len(flagged)
        grand_pages += len(report)

        lines.append(f"## {pdf_name}")
        lines.append("")
        lines.append(f"{len(report)} pages scanned. {len(flagged)} flagged diagram-only.")
        lines.append("")

        p28 = next((r for r in report if r["page"] == 28), None)
        p35 = next((r for r in report if r["page"] == 35), None)
        if p28:
            lines.append(
                f"- p.28 (Annex A, functional org chart): diagram_only={p28['diagram_only']} "
                f"(expected False)"
            )
        if p35:
            lines.append(
                f"- p.35 (Annex C, office floor plan): diagram_only={p35['diagram_only']} "
                f"(expected True)"
            )
        lines.append("")

        if flagged:
            lines.append("**Flagged pages:**")
            for r in flagged:
                lines.append(
                    f"- p.{r['page']} (doc_id={r['doc_id']}): {r['image_count']} image(s), "
                    f"{r['remaining_blocks']} remaining block(s)"
                )
            lines.append("")

    lines.append("## Totals across both PDFs")
    lines.append("")
    lines.append(f"{grand_pages} pages scanned. {grand_flagged} flagged diagram-only.")

    out_path = out_dir / "diagram_page_report.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path
