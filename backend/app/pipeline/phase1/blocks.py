"""Step 6 — assemble blocks from whatever spans survive the header, footer,
and table-region carve-outs. Keeps PyMuPDF's native block as the container
but exposes the full `lines` array (FLAG-1/FLAG-2 for Phase 2: a block is
not always one structural unit, and a heading's number/title can land in
separate line entries even at nearly-identical y -- never flatten to
block-level text as the only representation).
"""
from .footer import strip_footer_lines
from .spans import extract_page_blocks


def _point_in_bbox(x: float, y: float, bbox) -> bool:
    return bbox[0] <= x <= bbox[2] and bbox[1] <= y <= bbox[3]


def _line_in_any_region(line: dict, regions: list) -> bool:
    bbox = line["bbox"]
    cx = (bbox[0] + bbox[2]) / 2
    cy = (bbox[1] + bbox[3]) / 2
    return any(_point_in_bbox(cx, cy, r) for r in regions)


def assemble_page_blocks(fitz_page, pdf_page_no: int, header_bbox, table_bboxes: list, page_height: float) -> list[dict]:
    """header_bbox: the matched header region for this page (either
    template), or None on a headerless continuation page. table_bboxes: every
    raw (pre-stitch, pre-filter) table bbox found on this page -- table
    content never duplicates into blocks, regardless of that table's
    eventual keep/discard verdict (round 3: Category A's verbatim-duplicate
    checklist content is exactly the case where losing the fallback is
    correct, not a gap)."""
    excluded_regions = table_bboxes[:]
    if header_bbox:
        excluded_regions.append(header_bbox)

    raw_blocks = extract_page_blocks(fitz_page, pdf_page_no)
    filtered = []
    for b in raw_blocks:
        kept_lines = [
            ln for ln in b["lines"]
            if ln["text"].strip() and not _line_in_any_region(ln, excluded_regions)
        ]
        if kept_lines:
            new_b = dict(b)
            new_b["lines"] = kept_lines
            filtered.append(new_b)

    filtered = strip_footer_lines(filtered, page_height)

    for b in filtered:
        b["text"] = " ".join(ln["text"] for ln in b["lines"])

    return filtered
