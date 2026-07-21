"""Turns a checklist PDF's rows into leaf checklist items. Only leaf items
are checklist items (master_contextC.md) -- a heading contributes to
ancestor_path only, never becomes an item itself, exactly like Phase 2's
"ancestors contribute heading lines only" rule for QMS clauses.

Simpler than Phase 2's QMS tree on purpose: these two PDFs are short, linear
documents with no Annex-style renumbering scope observed anywhere in a
full-corpus check (phases/v2_phase3.md) -- so this is Phase 2's proven
numbered_stack ancestor algorithm, without the Annex/absorption/table
machinery Phase 2 needs and this document shape never exercises.
"""
from .constants import MIN_COLUMN_GAP, NUMBERED_RE, PARAGRAPH_GAP_MIN


def _numbered_column_threshold(rows: list[dict]) -> tuple[float, list[dict]]:
    """The real number column and the body/wrap-continuation column are
    grounded (phases/v2_phase3.md, full-corpus x0 scan) to sit tens of
    points apart on both PDFs, with nothing in between -- a wrapped body
    line that happens to start with a digit (e.g. "2 years in respect of
    the examination") sits in the body column, not the number column, and
    is exactly what this threshold is for excluding. Computed per document,
    not hardcoded, from the real gap in that document's own candidate rows.
    """
    candidates = [r for r in rows if NUMBERED_RE.match(r["text"])]
    xs = sorted(r["x0"] for r in candidates)
    if len(xs) < 2:
        raise ValueError("too few numbered-shape rows to find a column split")

    gaps = [(xs[i + 1] - xs[i], xs[i], xs[i + 1]) for i in range(len(xs) - 1)]
    gap, left, right = max(gaps, key=lambda g: g[0])
    if gap < MIN_COLUMN_GAP:
        raise ValueError(
            f"no clean number/body column split found (largest gap {gap:.1f}pt "
            f"between x0={left:.1f} and x0={right:.1f}, need >= {MIN_COLUMN_GAP}pt) "
            "-- this document's layout needs a human look, not a guessed threshold"
        )
    threshold = (left + right) / 2
    return threshold, candidates


def classify_rows(rows: list[dict]) -> tuple[list[dict], float]:
    """Adds 'kind' ('heading' | 'item' | 'body') and, for heading/item rows,
    'clause_no' / 'title' to each row in place. Returns (rows, threshold).
    """
    threshold, _ = _numbered_column_threshold(rows)
    for r in rows:
        m = NUMBERED_RE.match(r["text"]) if r["x0"] < threshold else None
        if m is None:
            r["kind"] = "body"
            continue
        r["clause_no"] = m.group(1)
        r["title"] = m.group(2)
        r["kind"] = "heading" if r["bold"] else "item"
    return rows, threshold


def _nests_under(item_clause_no: str, heading_clause_no: str) -> bool:
    return item_clause_no == heading_clause_no or item_clause_no.startswith(heading_clause_no + ".")


def _split_paragraphs(body_lines: list[tuple[float, int, str]]) -> list[list[tuple[float, int, str]]]:
    """Splits an item's accumulated body lines into paragraph groups on a
    >PARAGRAPH_GAP_MIN vertical gap. Only ever called on an item whose own
    clause_no does not nest under its governing heading (see build_items) --
    gated, not blanket. A blanket version of this was tried first and
    rejected: corpus-wide, a plain paragraph-gap split fires 64 times in AQB
    and 17 extra times in AEC on completely healthy items (NOTE paragraphs,
    lettered/bulleted sub-clauses within one real requirement's body) --
    real false positives, not a hypothetical risk, found by actually running
    it (phases/v2_phase3.md build report). A trailing-"?" refinement alone
    still left 10 AEC false positives. The nesting-mismatch gate in
    build_items is what actually isolates this to the one grounded case
    (AEC "8. Consistency of PCN Examinations", 6 real audit questions,
    phases/v2_phase3.md) -- confirmed 0 false positives, exactly the
    approved 6, both PDFs, full corpus.
    """
    groups: list[list[tuple[float, int, str]]] = []
    cur: list[tuple[float, int, str]] = []
    prev_y0 = None
    for y0, page, text in body_lines:
        if cur and prev_y0 is not None and (y0 - prev_y0) > PARAGRAPH_GAP_MIN:
            groups.append(cur)
            cur = []
        cur.append((y0, page, text))
        prev_y0 = y0
    if cur:
        groups.append(cur)
    return groups


def build_items(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Walks classified rows in document order, maintaining a dot-depth
    ancestor stack of open headings (Phase 2's numbered_stack shape). Every
    'item' row opens a new leaf; every 'body' row extends whichever leaf is
    currently open.

    On close, a leaf's body is split into paragraph groups
    (_split_paragraphs) ONLY if the leaf's own clause_no does not nest under
    its governing heading's clause_no (_nests_under) -- the same numbering
    mismatch that is already the root cause of this item's clause_no being
    wrong in the first place (item "4.2.5.2" under heading "8", a source
    typo, phases/v2_phase3.md). A healthy item (clause_no nests under its
    heading, true for every item in AQB and all but one in AEC) is never
    split even if its body happens to contain a >PARAGRAPH_GAP_MIN gap --
    grounded corpus-wide, this gate is what keeps ordinary NOTE paragraphs
    and lettered/bulleted sub-clauses intact as one item's body, exactly as
    before. More than one group means the source dropped numbering entirely
    partway through a section; each extra group becomes its own item
    sharing the same clause_no, disambiguated by _dedup_clause_nos below
    (the existing #2/#3 mechanism, not a new one).

    Returns (items, orphan_body_rows) -- orphan_body_rows is body text that
    arrived with nothing open (should be empty; reported, not silently
    dropped, if it isn't).
    """
    stack: list[tuple[int, str, str]] = []  # (depth, clause_no, title)
    items: list[dict] = []
    current: dict | None = None
    orphans: list[dict] = []

    def close_current():
        nonlocal current
        if current is None:
            return
        groups = (
            _split_paragraphs(current["body_lines"])
            if not current["nests_under_heading"]
            else [current["body_lines"]]
        )
        for group in groups:
            items.append({
                "clause_no": current["clause_no"],
                "ancestor_path": current["ancestor_path"],
                "text_lines": [text for _, _, text in group],
                "pages": {page for _, page, _ in group},
            })
        current = None

    for r in rows:
        if r["kind"] == "heading":
            close_current()
            depth = r["clause_no"].count(".") + 1
            while stack and stack[-1][0] >= depth:
                stack.pop()
            stack.append((depth, r["clause_no"], r["title"]))
        elif r["kind"] == "item":
            close_current()
            heading_cn = stack[-1][1] if stack else None
            current = {
                "clause_no": r["clause_no"],
                "ancestor_path": [
                    {"clause_no": cn, "clause_title": t} for _, cn, t in stack
                ],
                "body_lines": [(r["y0"], r["page"], r["title"])],
                "nests_under_heading": heading_cn is not None and _nests_under(r["clause_no"], heading_cn),
            }
        else:  # body
            if current is not None:
                current["body_lines"].append((r["y0"], r["page"], r["text"]))
            else:
                orphans.append(r)
    close_current()
    return items, orphans


def _dedup_clause_nos(items: list[dict]) -> None:
    """Same safety net as Phase 2's build.py::_dedup_clause_nos (build.py's
    own docstring explains the rationale) -- not expected to fire on either
    checklist (no restart/renumbering shape found in the full-corpus scan),
    kept as a corpus-wide guarantee rather than an assumption.
    """
    seen: dict[str, int] = {}
    for it in items:
        cn = it["clause_no"]
        seen[cn] = seen.get(cn, 0) + 1
        if seen[cn] > 1:
            it["clause_no"] = f"{cn}#{seen[cn]}"


def parse_checklist(rows: list[dict], prefix: str) -> tuple[list[dict], dict]:
    """Full pipeline: classify -> build tree -> emit items. `prefix` is
    "AQB" or "AEC", used for item_id. Returns (items, debug) where debug
    carries the counts and threshold needed for the grounding/build report.
    """
    rows, threshold = classify_rows(rows)
    items, orphans = build_items(rows)
    _dedup_clause_nos(items)

    n_headings = sum(1 for r in rows if r["kind"] == "heading")
    n_items_raw = sum(1 for r in rows if r["kind"] == "item")

    n_synthesized = sum(1 for it in items) - n_items_raw  # paragraph-splits beyond the raw item count

    out = []
    for it in items:
        pages = sorted(it["pages"])
        out.append({
            "item_id": f"{prefix}__{it['clause_no']}",
            "clause_no": it["clause_no"],
            "ancestor_path": it["ancestor_path"],
            "text": "\n".join(it["text_lines"]),
            "page_start": pages[0],
            "page_end": pages[-1],
        })

    debug = {
        "threshold": threshold,
        "n_headings": n_headings,
        "n_items_raw": n_items_raw,
        "n_items_final": len(out),
        "n_synthesized_paragraph_splits": n_synthesized,
        "n_orphan_body_rows": len(orphans),
        "orphans": orphans,
    }
    return out, debug
