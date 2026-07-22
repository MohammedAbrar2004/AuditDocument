"""Orchestrates chunk building into one artifact dict per source PDF. Reads
a Phase 1 artifact only -- never re-parses the PDF.
"""
from .chunks import build_chunks_for_subdocument, format_chunk_text
from .rows import flatten_blocks_to_rows


def _dedup_clause_nos(out_chunks: list[dict]) -> None:
    """Safety net, not the primary fix -- real restarts (e.g. AEI-WI-T-05B's
    "ANNEXURE - I" mini-procedure) get a structural "Annex X/..." namespace
    from classify.py/chunks.py so their clause_nos are meaningfully distinct
    on their own. This catches what a namespace can't: a genuine in-sequence
    document typo, one number reused where the author should have
    incremented (confirmed real: AEI-WI-T-01B p189-190, "5. Terms and
    Definitions:" then "5. Qualification Requirement:" a page later, with
    "6. Identify possible exemptions" already correctly using 6 right after
    -- both clauses are real, both belong in the same flat sequence, neither
    is more "canonical" than the other, so there is no more-correct number
    to synthesize; disambiguating without inventing structure that isn't in
    the source means suffixing.
    (doc_id, clause_no) is the citation/eval key (spec requirement) -- only
    clause_no is mutated, never clause_title/text/ancestor_path, so nothing
    about *where the content came from* changes, only the id used to address
    it. clause_no=None (flat/front-matter chunks, distinguished by title and
    page range instead) is left alone -- confirmed real, not a citation key.
    """
    seen: dict[str, int] = {}
    for c in out_chunks:
        clause_no = c["clause_no"]
        if clause_no is None:
            continue
        seen[clause_no] = seen.get(clause_no, 0) + 1
        if seen[clause_no] > 1:
            c["clause_no"] = f"{clause_no}#{seen[clause_no]}"


def build_subdocument_chunks(subdoc: dict, chunk_id_key: str | None = None) -> tuple[list[dict], dict]:
    """`chunk_id_key` defaults to `doc_id` -- identical to every existing
    call site's behavior. `build_artifact` below passes a `#N`-suffixed key
    only when this subdocument's `doc_id` repeats across the corpus
    (confirmed real and singular: AEI-QP-T-03B is reused for two distinct
    real documents, the AEC and AQB checklists -- a source-file fact, not a
    parsing defect). `doc_id` itself, on every emitted chunk, always stays
    the true, unsuffixed source doc_id -- only the chunk_id join key is
    disambiguated, since chunk_id (not doc_id) is what downstream phases
    rely on for uniqueness (Phase 3's assert_chunk_id_uniqueness).
    """
    doc_id = subdoc["doc_id"]
    id_key = chunk_id_key if chunk_id_key is not None else doc_id
    rows = flatten_blocks_to_rows(subdoc["blocks"])
    chunks, events, fate, trailing_absorbed = build_chunks_for_subdocument(
        rows, subdoc["tables"], doc_name=subdoc["doc_name"]
    )

    out_chunks = []
    for seq, c in enumerate(chunks, start=1):
        out_chunks.append({
            "chunk_id": f"{id_key}__c{seq:03d}",
            "doc_id": doc_id,
            "doc_name": subdoc["doc_name"],
            "clause_no": c["clause_no"],
            "clause_title": c["clause_title"],
            "ancestor_path": c["ancestor_path"],
            "lead_lines": c["lead_lines"],
            "text": format_chunk_text(c),
            "page_start": c["page_start"],
            "page_end": c["page_end"],
            "table_ids": c["table_ids"],
        })
    _dedup_clause_nos(out_chunks)

    debug = {
        "doc_id": doc_id,
        "n_rows": len(rows),
        "n_events": len(events),
        "n_chunks": len(out_chunks),
        "n_tables_in": len(subdoc["tables"]),
        "n_tables_attached": sum(len(c["table_ids"]) for c in out_chunks),
        "trailing_absorbed": trailing_absorbed,
        "rows": rows,
        "events": events,
        "fate": fate,
    }
    return out_chunks, debug


def build_artifact(phase1_artifact: dict) -> tuple[dict, list[dict]]:
    all_chunks = []
    all_debug = []
    doc_id_occurrence: dict[str, int] = {}
    for subdoc in phase1_artifact["subdocuments"]:
        doc_id = subdoc["doc_id"]
        doc_id_occurrence[doc_id] = doc_id_occurrence.get(doc_id, 0) + 1
        n = doc_id_occurrence[doc_id]
        # First occurrence of any doc_id is unchanged (id_key == doc_id) --
        # only a real repeat gets a #N-suffixed chunk_id key. Confirmed the
        # only repeat in the real corpus is AEI-QP-T-03B (see build.py's
        # docstring / this fix's own verification).
        chunk_id_key = doc_id if n == 1 else f"{doc_id}#{n}"
        chunks, debug = build_subdocument_chunks(subdoc, chunk_id_key=chunk_id_key)
        all_chunks.extend(chunks)
        all_debug.append(debug)

    artifact = {
        "source_pdf": phase1_artifact["source_pdf"],
        "chunks": all_chunks,
    }
    return artifact, all_debug
