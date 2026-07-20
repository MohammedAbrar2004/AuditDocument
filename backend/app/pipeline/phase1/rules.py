"""Step 4 — empty-table rule, step 5 — diagram-only-page rule. Both are
removal rules with real content at stake; per master_contextC.md's ⚠, both
get grounded and reported before they're trusted. Three rounds of review
(phases/v2_phase1.md) validated the empty-table rule itself is correct as
written -- what changed across rounds was entirely upstream (extraction),
never this rule.
"""
from .constants import DIAGRAM_PAGE_MAX_BLOCKS, DIAGRAM_PAGE_MAX_CHARS


def _cell_empty(c) -> bool:
    return c is None or str(c).strip() == ""


def empty_table_verdict(filtered_table: dict) -> tuple[str, str]:
    """Unchanged since review round 1: discard if entirely empty, OR the
    rightmost column is blank on every data row. No fill-rate, no other
    heuristics."""
    rows = filtered_table["rows"]
    total_cells = sum(len(r) for r in rows)
    empty_cells = sum(1 for r in rows for c in r if _cell_empty(c))
    if total_cells > 0 and empty_cells == total_cells:
        return "DISCARD", "entirely empty"

    data_rows = rows[1:] if len(rows) > 1 else rows
    if data_rows and filtered_table["ncols"] > 0:
        rightmost_blank = all(_cell_empty(r[-1]) if r else True for r in data_rows)
        if rightmost_blank:
            return "DISCARD", "rightmost column blank on every data row"

    return "KEEP", "has content"


def is_diagram_only_page(remaining_blocks: list[dict], image_count: int, has_table: bool) -> bool:
    """A page is diagram-only when, after header/footer/table strip, it
    contributes ~zero body text (a lone heading line, or nothing) and
    carries at least one image. Grounded: Annex C (p.35) reduces to ~27
    chars, 2 images -> True. Annex A (p.28) has 589 chars of real body text,
    1 image -> False. Never OCRs or embeds image bytes -- out of scope.

    has_table: True if any pdfplumber table (kept or discarded) overlaps this
    page. A page's table content is always carved out of `remaining_blocks`
    before this check ever runs (blocks.py), so a page whose only real
    content is a table looks identical to a genuine diagram page -- zero
    remaining blocks, image(s) present -- without this guard. Found on the
    real corpus: pp.1-2 (signature block), pp.3-5 (Revision Control), p.36
    (Annex D) all false-positived as diagram-only until this check was
    added. A table page is never a diagram page, regardless of that table's
    keep/discard verdict."""
    if has_table:
        return False
    if image_count < 1:
        return False
    if len(remaining_blocks) > DIAGRAM_PAGE_MAX_BLOCKS:
        return False
    total_chars = sum(
        len(line["text"].strip())
        for b in remaining_blocks
        for line in b["lines"]
    )
    return total_chars <= DIAGRAM_PAGE_MAX_CHARS
