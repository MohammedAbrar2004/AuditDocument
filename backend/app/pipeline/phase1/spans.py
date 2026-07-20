"""Step 1 — raw span extraction. Every block -> line -> span exactly as
PyMuPDF returns it, nothing filtered. Each span keeps the five required
fields: text, page, font_size, bold, bbox. `page` is always the absolute PDF
page (1-indexed), never document-relative.
"""
from .constants import is_bold


def extract_page_blocks(fitz_page, pdf_page_no: int) -> list[dict]:
    """Returns native PyMuPDF blocks (type==0, text only) as a list of dicts,
    each with its full `lines` array preserved (FLAG-1/FLAG-2: block-level
    text alone is not always one structural unit -- Phase 2 needs line
    granularity).
    """
    raw = fitz_page.get_text("dict")
    blocks = []
    for b_idx, b in enumerate(raw["blocks"]):
        if b.get("type") != 0:
            continue
        lines = []
        for line in b["lines"]:
            spans = []
            for span in line["spans"]:
                spans.append({
                    "text": span["text"],
                    "page": pdf_page_no,
                    "font_size": round(span["size"], 2),
                    "bold": is_bold(span),
                    "bbox": list(span["bbox"]),
                })
            if not spans:
                continue
            line_bbox = [
                min(s["bbox"][0] for s in spans),
                min(s["bbox"][1] for s in spans),
                max(s["bbox"][2] for s in spans),
                max(s["bbox"][3] for s in spans),
            ]
            lines.append({
                "text": "".join(s["text"] for s in spans),
                "bbox": line_bbox,
                "spans": spans,
            })
        if not lines:
            continue
        block_bbox = list(b["bbox"])
        blocks.append({
            "block_no": b_idx,
            "page": pdf_page_no,
            "bbox": block_bbox,
            "lines": lines,
        })
    return blocks


def block_text(block: dict) -> str:
    return " ".join(line["text"] for line in block["lines"])
