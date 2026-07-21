"""Extracts rows directly from a checklist PDF via PyMuPDF. These PDFs never
went through Phase 1 -- no subdocument segmentation, no header capture-then-
strip discipline to reuse -- so this module owns its own, simpler strip pass.
"""
import fitz

from .constants import (
    HEADER_BAND_MARGIN,
    HEADER_LABELS,
    PAGE_FOOTER_RE,
    ROW_Y_TOLERANCE,
    TITLE_FONT_SIZE_MIN,
)


def _extract_page_lines(page, page_no: int) -> list[dict]:
    lines = []
    d = page.get_text("dict")
    for block in d["blocks"]:
        if "lines" not in block:
            continue
        for line in block["lines"]:
            spans = [s for s in line["spans"] if s["text"].strip()]
            if not spans:
                continue
            text = "".join(s["text"] for s in line["spans"]).strip()
            y0 = line["bbox"][1]
            x0 = line["bbox"][0]
            bold = all((s["flags"] & 2**4) or "bold" in s["font"].lower() for s in spans)
            size = max(s["size"] for s in spans)
            lines.append({
                "page": page_no, "y0": y0, "x0": x0, "bold": bold,
                "size": size, "text": text,
            })
    return lines


def _strip_header_footer_title(lines: list[dict]) -> list[dict]:
    by_page: dict[int, list[dict]] = {}
    for ln in lines:
        by_page.setdefault(ln["page"], []).append(ln)

    kept = []
    for page_no, page_lines in by_page.items():
        label_ys = [ln["y0"] for ln in page_lines if ln["text"] in HEADER_LABELS]
        band_bottom = max(label_ys) + HEADER_BAND_MARGIN if label_ys else None

        for ln in page_lines:
            if band_bottom is not None and ln["y0"] <= band_bottom:
                continue  # header label or an interleaved value cell
            if PAGE_FOOTER_RE.match(ln["text"]):
                continue  # bottom-of-page footer (or a stray header PAGE NO. value)
            if ln["size"] >= TITLE_FONT_SIZE_MIN:
                continue  # page-1 decorative title block
            kept.append(ln)
    return kept


def _group_rows(lines: list[dict]) -> list[dict]:
    lines = sorted(lines, key=lambda ln: (ln["page"], ln["y0"]))
    rows = []
    cur: list[dict] = []
    for ln in lines:
        if cur and (ln["page"] != cur[-1]["page"] or abs(ln["y0"] - cur[0]["y0"]) > ROW_Y_TOLERANCE):
            rows.append(_make_row(cur))
            cur = []
        cur.append(ln)
    if cur:
        rows.append(_make_row(cur))
    return rows


def _make_row(member_lines: list[dict]) -> dict:
    member_lines = sorted(member_lines, key=lambda ln: ln["x0"])
    text = " ".join(ln["text"] for ln in member_lines).strip()
    return {
        "page": member_lines[0]["page"],
        "y0": min(ln["y0"] for ln in member_lines),
        "x0": min(ln["x0"] for ln in member_lines),
        "bold": all(ln["bold"] for ln in member_lines),
        "text": text,
    }


def extract_rows(pdf_path: str) -> list[dict]:
    """One row per y-proximity group of PyMuPDF lines, in document order,
    header/footer/title-block lines already stripped. Each row:
    {page, y0, x0, bold, text}.
    """
    doc = fitz.open(pdf_path)
    try:
        lines = []
        for page_no in range(len(doc)):
            lines.extend(_extract_page_lines(doc[page_no], page_no + 1))
    finally:
        doc.close()
    lines = _strip_header_footer_title(lines)
    return _group_rows(lines)
