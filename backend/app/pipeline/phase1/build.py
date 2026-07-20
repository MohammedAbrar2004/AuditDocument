"""Steps 3-8 — orchestrates extraction into one artifact dict per source PDF.
Ties together segmentation (subdocument boundaries), table extraction +
stitching + filtering, the empty-table and diagram-only-page removal rules,
and block assembly. Produces exactly the artifact shape documented in
phases/v2_phase1.md's "Artifact schema" section.
"""
from collections import defaultdict

import fitz
import pdfplumber

from . import tables as tables_mod
from .blocks import assemble_page_blocks
from .rules import empty_table_verdict, is_diagram_only_page
from .segment import segment_pdf


def _table_owner_doc_id(table: dict, page_doc_id: dict) -> str:
    return page_doc_id.get(table["pages"][0])


def build_artifact(pdf_path, source_pdf_name: str) -> dict:
    fitz_doc = fitz.open(pdf_path)
    with pdfplumber.open(pdf_path) as pdfplumber_pdf:
        page_count = len(pdfplumber_pdf.pages)
        page_height = pdfplumber_pdf.pages[0].height

        seg = segment_pdf(pdfplumber_pdf, fitz_doc)
        page_header = seg["page_header"]
        page_doc_id = seg["page_doc_id"]

        raw_tables = tables_mod.extract_raw_tables_per_page(pdfplumber_pdf, fitz_doc)
        raw_tables_by_page = defaultdict(list)
        for t in raw_tables:
            raw_tables_by_page[t["page"]].append(t["bbox"])

        stitched = tables_mod.stitch_tables(raw_tables)
        filtered_tables = [tables_mod.apply_min_width_filter(t) for t in stitched]

        removal_log = []
        tables_by_doc_id = defaultdict(list)
        table_counters = defaultdict(int)

        for ft in filtered_tables:
            owner = _table_owner_doc_id(ft, page_doc_id)
            verdict, reason = empty_table_verdict(ft)
            page_start, page_end = ft["pages"][0], ft["pages"][-1]
            if verdict == "DISCARD":
                removal_log.append({
                    "page": page_start,
                    "pages": ft["pages"],
                    "rule": "empty_table",
                    "detail": (
                        f"doc_id={owner} table pp.{page_start}-{page_end}: {reason} "
                        f"(ncols_before_filter={ft['ncols_before_filter']}, "
                        f"ncols_after_filter={ft['ncols']}, dropped_cols={ft['dropped_cols']})"
                    ),
                })
                continue
            table_counters[owner] += 1
            tables_by_doc_id[owner].append({
                "table_id": f"{owner}__t{table_counters[owner]:02d}",
                "page_start": page_start,
                "page_end": page_end,
                "rows": ft["rows"],
                "bbox_by_page": {p: b for p, b in zip(ft["pages"], ft["bboxes"])},
            })

        blocks_by_doc_id = defaultdict(list)
        block_counters = defaultdict(int)
        diagram_page_report = []

        for pno0 in range(page_count):
            pdf_page_no = pno0 + 1
            doc_id = page_doc_id.get(pdf_page_no)
            header = page_header.get(pdf_page_no)
            header_bbox = header["bbox"] if header else None
            table_bboxes = raw_tables_by_page.get(pdf_page_no, [])

            page_blocks = assemble_page_blocks(
                fitz_doc[pno0], pdf_page_no, header_bbox, table_bboxes, page_height
            )

            image_count = len(fitz_doc[pno0].get_images(full=True))
            diagram_only = is_diagram_only_page(page_blocks, image_count, has_table=bool(table_bboxes))
            diagram_page_report.append({
                "page": pdf_page_no,
                "doc_id": doc_id,
                "image_count": image_count,
                "remaining_blocks": len(page_blocks),
                "diagram_only": diagram_only,
            })
            if diagram_only:
                heading = page_blocks[0]["text"].strip() if page_blocks else ""
                removal_log.append({
                    "page": pdf_page_no,
                    "rule": "diagram_only_page",
                    "detail": (
                        f"doc_id={doc_id} — {heading!r} heading kept, "
                        f"{image_count} image(s) not extracted, zero body text"
                    ),
                })

            if doc_id is None:
                continue
            for b in page_blocks:
                block_counters[doc_id] += 1
                blocks_by_doc_id[doc_id].append({
                    "block_id": f"{doc_id}__p{pdf_page_no:03d}_b{block_counters[doc_id]:03d}",
                    "page": pdf_page_no,
                    "bbox": b["bbox"],
                    "text": b["text"],
                    "lines": b["lines"],
                })

        subdocuments = []
        for sd in seg["subdocuments"]:
            doc_id = sd["doc_id"]
            subdocuments.append({
                "doc_id": doc_id,
                "doc_name": sd["doc_name"],
                "revision": sd["revision"],
                "issue_date": sd["issue_date"],
                "revised_date": sd["revised_date"],
                "pdf_page_start": sd["pdf_page_start"],
                "pdf_page_end": sd["pdf_page_end"],
                "doc_relative_page_span": sd["doc_relative_page_span"],
                "header_template": sd["header_template"],
                "approved_by": sd["approved_by"],
                "reviewed_revised_by": sd["reviewed_revised_by"],
                "reference_procedure": sd["reference_procedure"],
                "blocks": blocks_by_doc_id.get(doc_id, []),
                "tables": tables_by_doc_id.get(doc_id, []),
            })

        return {
            "source_pdf": source_pdf_name,
            "page_count": page_count,
            "subdocuments": subdocuments,
            "removal_log": removal_log,
            "extraction_report": seg["extraction_report"],
            "_diagram_page_report": diagram_page_report,
            "_table_stats": {
                "total_stitched_tables": len(filtered_tables),
                "discarded": sum(1 for e in removal_log if e["rule"] == "empty_table"),
                "kept": sum(len(v) for v in tables_by_doc_id.values()),
            },
        }
