"""Step 2 — header detection, both templates.

Template A (standard_table): the top-band pdfplumber table with cells
DOCUMENT NAME / DOCUMENT NO. / REVISION / REVISED DATE / ISSUE DATE / PAGE NO.
Read from STRUCTURED table cells, never flattened text (round 2: a flattened
y-then-x join interleaves a wrapped doc_name between label fragments and
silently drops pages like AEI-QP-T-03F, PDF p.113).

Template B (form_freetext): free-running bold text, `Document Number:` style
labels. Spans must be joined in reading order before any regex runs -- label
and value sit on separate spans/lines in the real PDF (round 1, item 3).
"""
import re

from .constants import HEADER_LABELS, TEMPLATE_B_BAND_Y1_MAX, TEMPLATE_B_LABELS
from .spans import extract_page_blocks


def normalize_cell(value):
    if value is None:
        return None
    return re.sub(r"\s+", " ", value).strip()


def is_header_band_table(rows) -> bool:
    """True if a pdfplumber-extracted table is the header/metadata table
    itself (checked on the first 2 rows, normalized -- catches the
    'DOCUMENT\\nNAME' wrap case)."""
    for row in rows[:2]:
        for cell in row:
            norm = normalize_cell(cell)
            if norm and norm.upper() in ("DOCUMENT NAME", "DOCUMENT NO."):
                return True
    return False


def detect_template_a(pdfplumber_page):
    """Returns a dict of parsed header fields + bbox, or None if this page's
    top table isn't the header/metadata table."""
    tables = pdfplumber_page.find_tables()
    t = None
    rows = None
    for candidate in tables:
        candidate_rows = candidate.extract()
        if is_header_band_table(candidate_rows):
            t = candidate
            rows = candidate_rows
            break
    if t is None:
        return None

    label_pos = {}
    for ri, row in enumerate(rows):
        for ci, cell in enumerate(row):
            norm = normalize_cell(cell)
            if norm and norm.upper() in HEADER_LABELS:
                label_pos[norm.upper()] = (ri, ci)

    if "DOCUMENT NAME" not in label_pos or "DOCUMENT NO." not in label_pos:
        return None

    def value_after(label):
        pos = label_pos.get(label)
        if pos is None:
            return None
        ri, ci = pos
        row = rows[ri]
        if ci + 1 < len(row):
            return normalize_cell(row[ci + 1])
        return None

    page_span = value_after("PAGE NO.")
    if page_span:
        page_span = re.sub(r"^Page\s+", "", page_span, flags=re.IGNORECASE)

    return {
        "header_template": "standard_table",
        "doc_id": value_after("DOCUMENT NO."),
        "doc_name": value_after("DOCUMENT NAME"),
        "revision": value_after("REVISION"),
        "issue_date": value_after("ISSUE DATE"),
        "revised_date": value_after("REVISED DATE"),
        "doc_relative_page_span": page_span,
        "approved_by": None,
        "reviewed_revised_by": None,
        "reference_procedure": None,
        "bbox": list(t.bbox),
    }


def _extract_bounded(text: str, start_label: str, all_labels: list[str]):
    idx = text.upper().find(start_label.upper())
    if idx == -1:
        return None
    rest = text[idx + len(start_label):]
    rest = re.sub(r"^\s*:?\s*", "", rest)
    cut = len(rest)
    rest_upper = rest.upper()
    for lab in all_labels:
        if lab == start_label:
            continue
        pos = rest_upper.find(lab.upper())
        if pos != -1 and pos < cut:
            cut = pos
    return rest[:cut].strip()


def detect_template_b(fitz_page, pdf_page_no: int):
    """Free-text form header. Joins spans in reading order (y0 then x0) --
    this reproduces the exact validated join from round 1's grounding."""
    blocks = extract_page_blocks(fitz_page, pdf_page_no)
    band_spans = []
    for b in blocks:
        for line in b["lines"]:
            for span in line["spans"]:
                if span["bbox"][3] <= TEMPLATE_B_BAND_Y1_MAX and span["text"].strip():
                    band_spans.append(span)
    if not band_spans:
        return None

    band_spans.sort(key=lambda s: (s["bbox"][1], s["bbox"][0]))
    joined = " ".join(s["text"].strip() for s in band_spans)

    if "Document Number" not in joined or not any(s["bold"] for s in band_spans):
        return None

    doc_id = _extract_bounded(joined, "Document Number", TEMPLATE_B_LABELS)
    if not doc_id:
        return None

    doc_name = band_spans[0]["text"].strip()
    bbox = [
        min(s["bbox"][0] for s in band_spans),
        min(s["bbox"][1] for s in band_spans),
        max(s["bbox"][2] for s in band_spans),
        max(s["bbox"][3] for s in band_spans),
    ]

    return {
        "header_template": "form_freetext",
        "doc_id": doc_id,
        "doc_name": doc_name,
        "revision": _extract_bounded(joined, "Revision Number", TEMPLATE_B_LABELS),
        "issue_date": None,
        "revised_date": _extract_bounded(joined, "Revision Date", TEMPLATE_B_LABELS),
        "doc_relative_page_span": None,
        "approved_by": _extract_bounded(joined, "Approved by", TEMPLATE_B_LABELS),
        "reviewed_revised_by": _extract_bounded(joined, "Reviewed / Revised by", TEMPLATE_B_LABELS),
        "reference_procedure": _extract_bounded(joined, "Reference Procedure", TEMPLATE_B_LABELS),
        "bbox": bbox,
    }


def detect_header(pdfplumber_page, fitz_page, pdf_page_no: int):
    """Try Template A, then Template B. Returns the parsed header dict or
    None if this page has no header of either shape (a continuation page)."""
    result = detect_template_a(pdfplumber_page)
    if result is not None:
        return result
    return detect_template_b(fitz_page, pdf_page_no)
