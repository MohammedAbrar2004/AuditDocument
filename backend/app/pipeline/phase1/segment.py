"""Step 2 (segmentation half) — stateful carry-forward subdocument boundary
detection. Reads structured pdfplumber table cells for Template A (never
flattened text -- round 2's AEI-QP-T-03F miss was a flattened-text artifact
of the grounding scripts, not the design), and normalizes embedded `\n` in
label matching (header.normalize_cell).

A new subdocument starts when a header (either template) is found AND either
the parsed doc_id OR doc_name differs from the currently-open subdocument's
-- not doc_id alone. Grounded necessity: AEI-QP-T-03B reuses the identical
doc_id for two different real documents (the AEC and AQB checklists, a
mistake in the source file); a doc_id-only rule silently merges them.
"""
from .header import detect_header


def segment_pdf(pdfplumber_pdf, fitz_doc) -> dict:
    page_count = len(pdfplumber_pdf.pages)

    page_header = {}          # pdf_page_no -> header dict or None
    page_doc_id = {}          # pdf_page_no -> doc_id (carried forward)
    header_absent_continuation_pages = []
    transitions = []          # list of (pdf_page_no, header_dict)

    current_doc_id = None
    current_doc_name = None

    for pno0 in range(page_count):
        pdf_page_no = pno0 + 1
        header = detect_header(pdfplumber_pdf.pages[pno0], fitz_doc[pno0], pdf_page_no)
        page_header[pdf_page_no] = header

        if header is not None:
            new_doc = (
                current_doc_id is None
                or header["doc_id"] != current_doc_id
                or header["doc_name"] != current_doc_name
            )
            if new_doc:
                transitions.append((pdf_page_no, header))
                current_doc_id = header["doc_id"]
                current_doc_name = header["doc_name"]
        else:
            header_absent_continuation_pages.append(pdf_page_no)

        page_doc_id[pdf_page_no] = current_doc_id

    subdocuments = []
    for i, (start_page, header) in enumerate(transitions):
        end_page = transitions[i + 1][0] - 1 if i + 1 < len(transitions) else page_count
        subdocuments.append({
            **header,
            "pdf_page_start": start_page,
            "pdf_page_end": end_page,
        })

    pages_with_no_header_on_page1_of_subdoc = [
        sd["pdf_page_start"] for sd in subdocuments
        if page_header.get(sd["pdf_page_start"]) is None
    ]

    header_template_counts = {"standard_table": 0, "form_freetext": 0}
    for sd in subdocuments:
        header_template_counts[sd["header_template"]] += 1

    return {
        "page_header": page_header,
        "page_doc_id": page_doc_id,
        "subdocuments": subdocuments,
        "extraction_report": {
            "subdocument_count": len(subdocuments),
            "doc_ids": [sd["doc_id"] for sd in subdocuments],
            "header_template_counts": header_template_counts,
            "pages_with_no_header_on_page1_of_subdoc": pages_with_no_header_on_page1_of_subdoc,
            "header_absent_continuation_pages": header_absent_continuation_pages,
        },
    }
