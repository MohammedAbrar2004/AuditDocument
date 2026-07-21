"""The tree builder -- turns a subdocument's classified row/table stream into
chunks. Implements the five locked decisions in phases/v2_phase2.md:

1. Numbered headings: ancestor nesting via the registry in ancestor.py (not
   plain depth-count popping -- see that module for why). A zero-body
   numbered heading (e.g. `4`, `4.2`, `6.0`) never gets its own chunk; it
   registers as a pure ancestor, exactly like `master_contextC.md` requires.
2. Unnumbered headings: flat leaf chunks, ancestor_path always [].
3. Zero-body headings (lookahead skips parentheticals): absorbed as
   lead_lines of the next chunk, never their own chunk, never dropped.
   Numbered zero-body headings use the ancestor registry's "consumed"
   tracking instead -- rescued into pending_prefix only if truly orphaned.
4. Parentheticals: folded into an open chunk, or queued for the next one.
5. Enumerated list items: not reclassified -- see classify.py's
   sequence/title-shape guards for why non-bold or period-style enumerated
   items still don't match.

Every heading row -- zero-body or not -- closes whatever chunk was
previously open before doing anything else. Skipping that for zero-body
headings was a real bug caught during validation: it left a stale `current`
that then absorbed the *next* chunk's parenthetical by mistake.
"""
from .ancestor import AncestorRegistry
from .classify import classify_rows, clause_tuple, is_zero_body_ahead
from .rows import block_homogeneity
from .tables import insert_tables


def _new_chunk(clause_no, clause_title, ancestor_path, ancestor_lines, heading_line, page):
    return {
        "clause_no": clause_no,
        "clause_title": clause_title,
        "ancestor_path": ancestor_path,
        "lead_lines": [],
        "body": [],
        "page_start": page,
        "page_end": page,
        "table_ids": [],
        "_ancestor_lines": ancestor_lines,
        "_heading_line": heading_line,
    }


def build_chunks_for_subdocument(rows: list[dict], tables: list[dict], doc_name: str = "(untitled)"):
    """Returns (chunks, events, fate, trailing_absorbed).
    `fate` maps event index -> (bucket_letter, note) for the coverage report.
    `events` is rows + table pseudo-rows, in final processed stream order.
    """
    block_homog = block_homogeneity(rows)
    classified = classify_rows(rows, block_homog)
    events = insert_tables(classified, tables)

    chunks: list[dict] = []
    registry = AncestorRegistry()
    annex_ancestor = None
    pending_prefix: list[str] = []
    current = None
    fate: dict[int, tuple] = {}

    def close_current():
        nonlocal current
        if current is not None:
            chunks.append(current)
        current = None

    def open_synthetic(page):
        nonlocal pending_prefix
        # Confirmed real (build report): 10 COMBINED subdocuments open with a
        # table or body text before any heading at all (Q3's front-matter
        # case) -- doc_name is a far more useful title than a bare
        # "(untitled)" placeholder for those.
        title = pending_prefix[-1] if pending_prefix else doc_name
        ancestor_lines = [annex_ancestor["_heading_line"]] if annex_ancestor else []
        ancestor_path = (
            [{"clause_no": None, "clause_title": annex_ancestor["clause_title"]}]
            if annex_ancestor else []
        )
        c = _new_chunk(None, title, ancestor_path, ancestor_lines, None, page)
        c["lead_lines"] = pending_prefix
        pending_prefix = []
        return c

    for i, ev in enumerate(events):
        kind = ev["kind"]

        if kind == "numbered":
            tup = clause_tuple(ev["clause_no"])
            ancestor_entries = registry.ancestors_for(tup)
            ancestor_lines = [annex_ancestor["_heading_line"]] if annex_ancestor else []
            ancestor_lines += [a["_heading_line"] for a in ancestor_entries]
            ancestor_path = (
                [{"clause_no": None, "clause_title": annex_ancestor["clause_title"]}]
                if annex_ancestor else []
            )
            ancestor_path += [
                {"clause_no": a["clause_no"], "clause_title": a["clause_title"]}
                for a in ancestor_entries
            ]
            full_no = (
                f"Annex {annex_ancestor['letter']}/{ev['clause_no']}"
                if annex_ancestor else ev["clause_no"]
            )
            zero_body = is_zero_body_ahead(events, i)
            close_current()
            if zero_body:
                # A pure ancestor (e.g. `4`, `4.2`, `6.0`) -- never its own
                # chunk, per master_contextC.md. Registered so descendants
                # can find it; rescued into pending_prefix later only if
                # nothing ever does (AncestorRegistry.rescue_unconsumed).
                registry.register(tup, ev["clause_no"], ev["clause_title"], ev["text"], is_zero_body=True)
                fate[i] = ("B", "zero-body numbered heading registered as ancestor (no chunk)")
            else:
                current = _new_chunk(
                    full_no, ev["clause_title"], ancestor_path, ancestor_lines, ev["text"], ev["page"]
                )
                current["lead_lines"] = pending_prefix
                pending_prefix = []
                registry.register(tup, ev["clause_no"], ev["clause_title"], ev["text"], is_zero_body=False)
                fate[i] = ("B", "own heading of new numbered chunk")

        elif kind == "annex":
            close_current()
            # Rescue anything from the outgoing numbering scope that never
            # found a real home before this fresh namespace replaces it.
            pending_prefix.extend(registry.rescue_unconsumed())
            annex_ancestor = {
                "letter": ev["annex_letter"], "clause_title": ev["clause_title"],
                "_heading_line": ev["text"],
            }
            registry = AncestorRegistry()
            pending_prefix.append(ev["clause_title"])
            fate[i] = ("B", "annex heading absorbed into pending_prefix (opens ancestor scope)")

        elif kind == "unnumbered_heading":
            close_current()
            if is_zero_body_ahead(events, i):
                pending_prefix.append(ev["clause_title"])
                fate[i] = ("B", "zero-body heading absorbed into pending_prefix")
            else:
                current = _new_chunk(None, ev["clause_title"], [], [], ev["text"], ev["page"])
                current["lead_lines"] = pending_prefix
                pending_prefix = []
                fate[i] = ("B", "own heading of new unnumbered chunk (flat)")

        elif kind == "parenthetical":
            if current is not None:
                current["body"].append(ev["text"])
                current["page_end"] = max(current["page_end"], ev["page"])
                fate[i] = ("B", "parenthetical folded into open chunk")
            else:
                pending_prefix.append(ev["text"])
                fate[i] = ("B", "parenthetical absorbed into pending_prefix")

        elif kind == "table":
            if current is None:
                current = open_synthetic(ev["page"])
            current["body"].extend(ev["serialized_lines"])
            current["page_end"] = max(current["page_end"], ev["page_end"])
            current["table_ids"].append(ev["table_id"])
            fate[i] = ("TABLE", f"attached table {ev['table_id']}")

        else:  # body
            if current is None:
                current = open_synthetic(ev["page"])
            current["body"].append(ev["text"])
            current["page_end"] = max(current["page_end"], ev["page"])
            fate[i] = ("A", "body of current chunk")

    close_current()
    pending_prefix.extend(registry.rescue_unconsumed())

    trailing_absorbed = False
    if pending_prefix:
        trailing_absorbed = True
        if chunks:
            chunks[-1]["lead_lines"] = chunks[-1]["lead_lines"] + list(pending_prefix)
        else:
            # A subdocument whose entire content is a heading with nothing else --
            # confirmed real, not hypothetical: e.g. AEI-QP-T-05A "CORRECTIVE ACTION
            # FORM", a blank form template whose only table Phase 1 correctly
            # discarded as empty, leaving no body and no table to attach anything to.
            # `lead_lines` must carry the *full* pending_prefix (not [:-1]) -- an
            # earlier version left it out of `text` entirely (heading_line=None and
            # lead_lines=[:-1] dropped the title from the rendered text, even though
            # it was still present in clause_title metadata -- a real gap for
            # anything reading `text`, e.g. search/embedding downstream).
            last_page = events[-1]["page"] if events else 1
            c = _new_chunk(None, pending_prefix[-1], [], [], None, last_page)
            c["lead_lines"] = list(pending_prefix)
            chunks.append(c)

    return chunks, events, fate, trailing_absorbed


def format_chunk_text(chunk: dict) -> str:
    lines = list(chunk["_ancestor_lines"]) + list(chunk["lead_lines"])
    if chunk["_heading_line"]:
        lines.append(chunk["_heading_line"])
    lines += chunk["body"]
    return "\n".join(lines)
