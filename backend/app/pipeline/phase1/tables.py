"""Step 3 — table extraction + cross-page stitching, step 3b — min-width
column filter. pdfplumber is the extractor (PyMuPDF's find_tables() ties it
byte-for-byte; Camelot is strictly worse -- both evaluated in round 2, not
switching). The header/footer metadata table is excluded here entirely, it
never enters the tables list (consumed as metadata in header.py).

Stitching algorithm corrected in round 3 -- see constants.py for the
grounded thresholds and phases/v2_phase1.md for the full incident writeup.
"""
from .constants import (
    FOOTER_RE,
    TABLE_STITCH_GAP_MAX,
    TABLE_STITCH_NEXT_TOP_MAX,
    TABLE_STITCH_X_TOLERANCE,
    MIN_COL_WIDTH,
)
from .header import is_header_band_table


def _cell_empty(c) -> bool:
    return c is None or str(c).strip() == ""


def _page_has_content_below(fitz_page, y1: float) -> bool:
    d = fitz_page.get_text("dict")
    for b in d["blocks"]:
        if b.get("type") != 0:
            continue
        for line in b["lines"]:
            for span in line["spans"]:
                txt = span["text"].strip()
                if span["bbox"][1] > y1 and txt and not FOOTER_RE.match(txt):
                    return True
    return False


def extract_raw_tables_per_page(pdfplumber_pdf, fitz_doc):
    """One entry per pdfplumber table found on any page, header table
    excluded. Each entry carries what the stitcher needs: column count,
    page-relative geometry, and per-row cell bboxes (for the min-width
    filter later)."""
    page_h = pdfplumber_pdf.pages[0].height
    raw = []
    for pno0, page in enumerate(pdfplumber_pdf.pages):
        pdf_page_no = pno0 + 1
        for t in page.find_tables():
            rows = t.extract()
            if not rows or is_header_band_table(rows):
                continue
            raw.append({
                "page": pdf_page_no,
                "bbox": list(t.bbox),
                "rows": rows,
                "ncols": len(rows[0]),
                "cell_bboxes": [r.cells for r in t.rows],
                "content_below": _page_has_content_below(fitz_doc[pno0], t.bbox[3]),
                "gap_to_bottom": page_h - t.bbox[3],
            })
    return raw


def stitch_tables(raw_tables: list[dict]) -> list[dict]:
    """Merge same-shaped tables across consecutive pages when the earlier
    table is genuinely the last real content on its page (bottom-margin gap
    + no non-footer content below) and the next table starts near the top of
    the following page. Assumes raw_tables is already in page order."""
    stitched = []
    for t in raw_tables:
        merged = False
        if stitched:
            prev = stitched[-1]
            prev_bbox = prev["bboxes"][-1]
            prev_page_no_content_below = prev["content_below_flags"][-1] is False
            prev_near_bottom = prev["gap_to_bottom_flags"][-1] < TABLE_STITCH_GAP_MAX
            same_cols = prev["ncols"] == t["ncols"]
            consecutive_page = t["page"] == prev["pages"][-1] + 1
            cur_starts_near_top = t["bbox"][1] < TABLE_STITCH_NEXT_TOP_MAX
            x_match = (
                abs(prev_bbox[0] - t["bbox"][0]) < TABLE_STITCH_X_TOLERANCE
                and abs(prev_bbox[2] - t["bbox"][2]) < TABLE_STITCH_X_TOLERANCE
            )
            if (same_cols and consecutive_page and prev_page_no_content_below
                    and prev_near_bottom and cur_starts_near_top and x_match):
                prev["pages"].append(t["page"])
                prev["bboxes"].append(t["bbox"])
                prev["rows"].extend(t["rows"])
                prev["cell_bboxes"].extend(t["cell_bboxes"])
                prev["content_below_flags"].append(t["content_below"])
                prev["gap_to_bottom_flags"].append(t["gap_to_bottom"])
                merged = True
        if not merged:
            stitched.append({
                "pages": [t["page"]],
                "bboxes": [t["bbox"]],
                "rows": list(t["rows"]),
                "ncols": t["ncols"],
                "cell_bboxes": list(t["cell_bboxes"]),
                "content_below_flags": [t["content_below"]],
                "gap_to_bottom_flags": [t["gap_to_bottom"]],
            })
    return stitched


def apply_min_width_filter(table: dict) -> dict:
    """Drop columns narrower than MIN_COL_WIDTH pt that are empty across
    every DATA row (row 0 / header row excluded from the emptiness check --
    a merged header cell attributed to a sliver column doesn't count as that
    column having content). Never drops a column holding real data."""
    rows = table["rows"]
    ncols = table["ncols"]
    cell_bboxes = table["cell_bboxes"]

    widths = [0.0] * ncols
    for row_cells in cell_bboxes:
        for ci, bb in enumerate(row_cells):
            if ci < ncols and bb is not None:
                widths[ci] = max(widths[ci], bb[2] - bb[0])

    all_empty = [True] * ncols
    for ri, row in enumerate(rows):
        if ri < 1:
            continue
        for ci, val in enumerate(row):
            if ci < ncols and not _cell_empty(val):
                all_empty[ci] = False

    dropped = [i for i in range(ncols) if widths[i] < MIN_COL_WIDTH and all_empty[i]]
    keep_idx = [i for i in range(ncols) if i not in dropped]
    filtered_rows = [[r[i] if i < len(r) else None for i in keep_idx] for r in rows]

    return {
        "pages": table["pages"],
        "bboxes": table["bboxes"],
        "rows": filtered_rows,
        "ncols": len(keep_idx),
        "dropped_cols": dropped,
        "ncols_before_filter": ncols,
    }


def extract_tables_for_pdf(pdfplumber_pdf, fitz_doc) -> list[dict]:
    """Full step 3 + 3b pipeline: extract, stitch, filter. Returns stitched,
    filtered table dicts keyed by their constituent PDF pages -- doc_id
    attribution and table_id assignment happen in build.py, once the page ->
    subdocument map exists."""
    raw = extract_raw_tables_per_page(pdfplumber_pdf, fitz_doc)
    stitched = stitch_tables(raw)
    return [apply_min_width_filter(t) for t in stitched]
