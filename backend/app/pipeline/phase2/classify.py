"""Classifies each flattened row into a chunk-tree event kind. Parenthetical
check runs first and overrides everything else -- a parenthetical is never a
heading even when it happens to be all-bold and sit in a homogeneous block
(locked decision, rule 4).

Numbered-heading detection is bold-independent (build report: real clauses
render non-bold or mixed-bold in the source -- 4.2.2, 5.2.1-5.3.5,
6.2.1.1-6.3.1.1, and the AEI-WI-T-01B/05B/15 period-style headings). Two
guards replace bold as the thing keeping this safe:
  - shape: the regex itself requires real trailing content after the
    number (rejects a bare wrapped reference like "64." with nothing
    after it).
  - sequence: a numbered candidate must be a plausible next number given
    the numbering context open so far in this subdocument (child, sibling
    increment, or a nearby fresh top-level number) -- rejects wild jumps.
  - title-shape (period-style only): a period-style candidate's trailing
    text must be short (real WI headings are 1-4 words; the one real
    period-style false-positive risk in the corpus, QM's non-heading
    enumerated objectives, run 9-17 words). Not applied to space-style,
    which has real clauses with long sentence-shaped titles (5.2.1).
"""
from .constants import (
    ANNEX_RE,
    ANNEXURE_RE,
    MAX_NUMBERED_ROWS_PER_BLOCK,
    NUMBERED_RE,
    PAREN_RE,
    PERIOD_NUMBERED_RE,
    PERIOD_STYLE_TITLE_MAX_WORDS,
    TOP_LEVEL_ABSOLUTE_MAX,
    TOP_LEVEL_JUMP_MAX,
)


def clause_tuple(clause_no: str) -> tuple[int, ...]:
    return tuple(int(p) for p in clause_no.split("."))


def clause_depth(clause_no: str) -> int:
    return len(clause_no.split("."))


class _SequenceContext:
    """Tracks numbering state across one subdocument's row stream. Sanity-
    checks only the TOP-LEVEL segment against the running max seen so far --
    real document numbering skips constantly at every level (4.3 not
    existing, 5.1.1 not existing, 6.2.1 not existing, a whole top-level `5`
    not existing) and master_contextC.md is explicit that these are normal
    and must not break the tree. A first version of this guard also
    required deeper segments to increment by exactly 1 from the last
    heading seen -- caught immediately on real data: it rejected `4.4`
    after `4.2.2` (no `4.3` in between), `5.1` after `4.4` (no bare `5`),
    and `6.0`/`6.1` after `5.3.5`. The top-level segment is the only part
    that stays in a genuinely small, bounded range in real documents, and
    it's also the only part that actually matters for catching a real wild
    outlier (a wrapped reference number like "64" when the document's own
    numbering never goes near that high).
    """

    def __init__(self):
        self.max_top_level = 0

    def is_plausible(self, cand: tuple[int, ...], is_bold: bool) -> bool:
        if self.max_top_level == 0:
            # No numbering context established yet in this subdocument --
            # confirmed real, corpus-wide (build report): the company's own
            # letterhead address ("18 Boon Lay Way, ...") is non-bold and
            # otherwise shape- and range-plausible as a first heading,
            # wrongly matching "18" as a clause number in 26 of 59
            # COMBINED subdocuments before this guard existed. Real first
            # headings in this corpus are always bold (confirmed: QM's
            # "1 SCOPE", every WI doc's "1. Purpose:"-style opener) --
            # requiring it here costs nothing real and blocks this exact
            # false positive. Not required once context exists (below) --
            # Gap 1's non-bold deep clauses (5.2.1 etc.) never open a
            # subdocument, they always follow real established numbering.
            return is_bold and cand[0] <= TOP_LEVEL_ABSOLUTE_MAX
        return cand[0] <= self.max_top_level + TOP_LEVEL_JUMP_MAX

    def record(self, cand: tuple[int, ...]) -> None:
        self.max_top_level = max(self.max_top_level, cand[0])


def _period_title_ok(title: str) -> bool:
    return len(title.split()) <= PERIOD_STYLE_TITLE_MAX_WORDS


def _shape_match(text: str):
    """Regex-shape check only (no sequence/block-count guards yet) -- used
    both to build the per-block candidate count and, in the second pass, as
    the actual match. Returns (clause_no, clause_title) or None."""
    m = NUMBERED_RE.match(text)
    if m:
        return m.group(1), m.group(2).strip()
    m = PERIOD_NUMBERED_RE.match(text)
    if m and _period_title_ok(m.group(2)):
        return m.group(1), m.group(2).strip()
    return None


def _next_shape_is_fresh_restart(rows: list[dict], i: int) -> bool:
    """Looks past row i (skipping parentheticals) for the next shape-valid
    numbered row and reports whether it opens at top-level 1 -- the signal
    that a solo-block "Annexure" heading is a real restart boundary, not a
    decorative trailing label (see ANNEXURE_RE's comment for the grounded
    false-positive this guards against)."""
    j = i + 1
    while j < len(rows):
        text = rows[j]["text"]
        if PAREN_RE.match(text):
            j += 1
            continue
        shape = _shape_match(text)
        if shape is None:
            return False
        return clause_tuple(shape[0])[0] == 1
    return False


def classify_rows(rows: list[dict], block_homog: dict[str, bool]) -> list[dict]:
    # Pass 1: count shape-valid numbered candidates per block. Grounded
    # necessity (build report): removing the bold gate reopened the exact
    # trap master_contextC.md names -- the Table of Contents mirrors real
    # structure, so it's sequence-plausible too. Real ToC block packs 22
    # numbered-shaped rows into one native block; the largest legitimate
    # case (real sub-clauses glued into one block with real prose between
    # them) is 3. A block over the threshold is a listing, not structure --
    # none of its candidates count as headings.
    candidates_per_block: dict[str, int] = {}
    rows_per_block: dict[str, int] = {}
    for r in rows:
        rows_per_block[r["block_id"]] = rows_per_block.get(r["block_id"], 0) + 1
        if not PAREN_RE.match(r["text"]) and _shape_match(r["text"]):
            candidates_per_block[r["block_id"]] = candidates_per_block.get(r["block_id"], 0) + 1

    out = []
    seq = _SequenceContext()
    for i, r in enumerate(rows):
        text = r["text"]
        if not text:
            continue
        kind, clause_no, clause_title = "body", None, None

        m_annex = ANNEX_RE.match(text) if r["all_bold"] else None
        if m_annex is None and rows_per_block.get(r["block_id"], 0) == 1:
            m_annexure = ANNEXURE_RE.match(text)
            if m_annexure and _next_shape_is_fresh_restart(rows, i):
                m_annex = m_annexure
        shape = _shape_match(text)
        block_ok = candidates_per_block.get(r["block_id"], 0) <= MAX_NUMBERED_ROWS_PER_BLOCK

        if PAREN_RE.match(text):
            kind = "parenthetical"
        elif m_annex:
            kind = "annex"
            clause_title = text
            annex_letter = m_annex.group(1)
        elif shape and block_ok and seq.is_plausible(clause_tuple(shape[0]), r["all_bold"]):
            kind = "numbered"
            clause_no, clause_title = shape
        elif r["all_bold"] and block_homog.get(r["block_id"], False):
            kind = "unnumbered_heading"
            clause_title = text

        if kind == "numbered":
            seq.record(clause_tuple(clause_no))

        row = {**r, "kind": kind, "clause_no": clause_no, "clause_title": clause_title}
        if kind == "annex":
            row["annex_letter"] = annex_letter
        out.append(row)
    return out


def is_zero_body_ahead(rows: list[dict], i: int) -> bool:
    """Scan forward from i+1, skipping parentheticals (locked decision, rule
    3), until real content (a body row, or a table -- a table is content in
    exactly the same sense the locked rule means by "real body", confirmed
    on QM's Revision History heading: its table sits directly under it with
    no text body in between) or a heading row / end of stream (=> zero-body).
    """
    j = i + 1
    while j < len(rows):
        k = rows[j]["kind"]
        if k == "parenthetical":
            j += 1
            continue
        if k in ("body", "table"):
            return False
        return True
    return True
