"""Flattens a subdocument's blocks into rows -- the unit Phase 2 actually
builds the tree from. Block boundaries carry no structural meaning (FLAG-1,
grounding item 3); only y-proximity within a block does (FLAG-2, item 2).

Kept deliberately shared between the chunk builder and the coverage
reconciliation report, so the two can never silently drift apart -- what gets
tested is exactly what ships.
"""
from .constants import ROW_Y_TOLERANCE


def flatten_blocks_to_rows(blocks: list[dict]) -> list[dict]:
    """One row per block-local group of `line` entries within ROW_Y_TOLERANCE
    of each other. Each row keeps `member_lines` -- the raw PyMuPDF line dicts
    that composed it, in document order -- so callers can recover exact
    source-line counts (needed by the coverage report) without re-deriving
    the grouping logic.
    """
    rows = []
    for b in blocks:
        cur_lines: list[dict] = []
        cur_y = None
        for ln in b["lines"]:
            if not ln["text"].strip():
                continue
            y0 = ln["bbox"][1]
            if cur_lines and abs(y0 - cur_y) > ROW_Y_TOLERANCE:
                rows.append(_make_row(b, cur_lines))
                cur_lines = []
                cur_y = None
            cur_lines.append(ln)
            cur_y = y0 if cur_y is None else min(cur_y, y0)
        if cur_lines:
            rows.append(_make_row(b, cur_lines))
    return rows


def _make_row(block: dict, member_lines: list[dict]) -> dict:
    spans = sorted(
        (sp for ln in member_lines for sp in ln["spans"]),
        key=lambda s: s["bbox"][0],
    )
    text = "".join(sp["text"] for sp in spans).strip()
    nonspace = [sp for sp in spans if sp["text"].strip()]
    all_bold = all(sp["bold"] for sp in nonspace) if nonspace else False
    y0 = min(ln["bbox"][1] for ln in member_lines)
    return {
        "text": text,
        "all_bold": all_bold,
        "page": block["page"],
        "block_id": block["block_id"],
        "member_lines": member_lines,
        "y0": y0,
    }


def block_homogeneity(rows: list[dict]) -> dict[str, bool]:
    """block_id -> True iff every row sourced from that block is all-bold.
    This is the discriminator between a real unnumbered heading and a
    mid-block bold sub-label (grounding item 1) -- proven on b059
    (External Issues / Internal Issues), verified corpus-wide in the build
    report.
    """
    by_block: dict[str, list[bool]] = {}
    for r in rows:
        by_block.setdefault(r["block_id"], []).append(r["all_bold"])
    return {bid: all(flags) for bid, flags in by_block.items()}
