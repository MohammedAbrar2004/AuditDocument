"""Step 2 (footer half) — separate pass, not folded into header detection.

Round 3 finding: round 1's "header and footer are the same region" claim was
only ever checked against QUALITY_MANUAL.pdf pages and explicitly flagged as
unverified corpus-wide. It's false for AEI-QP-T-03B: PDF pp.81-83 each carry
a genuine bottom-of-page footer ("Page N of 30" at y~801), physically
distinct from the top header table. Most subdocuments' page-count string
lives inside the header table's own cells (already excluded via the header
bbox carve-out before this ever runs) -- this pass only catches the loose,
free-standing footer text that sits outside any table.
"""
from .constants import FOOTER_BAND_Y0_MIN_FROM_BOTTOM, FOOTER_RE


def _is_footer_line(line: dict, page_height: float) -> bool:
    text = line["text"].strip()
    if not text:
        return False
    from_bottom = page_height - line["bbox"][3]
    return 0 <= from_bottom <= FOOTER_BAND_Y0_MIN_FROM_BOTTOM and bool(FOOTER_RE.match(text))


def strip_footer_lines(blocks: list[dict], page_height: float) -> list[dict]:
    """Drops footer-pattern lines from each block's `lines` array. A block
    that becomes empty after stripping is dropped entirely."""
    kept_blocks = []
    for b in blocks:
        kept_lines = [ln for ln in b["lines"] if not _is_footer_line(ln, page_height)]
        if kept_lines:
            new_b = dict(b)
            new_b["lines"] = kept_lines
            kept_blocks.append(new_b)
    return kept_blocks
