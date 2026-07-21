# Phase 2 — Chunk

Status: **BUILT.** Rules locked after three rounds of review against real chunk output
(not hypothetical rules) — see "Locked decisions" and the build report at the bottom.

Read `master_contextC.md` and `v2_plan.md` first. Reads Phase 1's artifacts only —
**never re-parses the PDFs.** Inputs: `data/artifacts/phase1/quality_manual.json`,
`data/artifacts/phase1/combined_complete_qms.json`.

---

## Grounding pass — what was found in the real Phase 1 output

Everything below was checked against the actual `quality_manual.json` artifact
(59-page-QM subset, 1 subdocument, 451 blocks, 9 tables) before being written down —
not inferred from the plan or from `master_contextC.md`'s prose alone.

### 1. Heading detection: all-bold-line is necessary but not sufficient — real signal is block homogeneity

**Correction — the first draft of this section misread the data.** It claimed
`External Issues` (QM p.11) shares its line with non-bold continuation text. Re-checked
at actual `line` granularity (not spans flattened across the whole block) and that's
false: `External Issues` and `Internal Issues` are each **alone on their own line,
fully bold, nothing else on that line**:

```
line 0: x0=120.6 bold=True  'External Issues'
line 1: x0=102.6 bold=False '� '                          (bullet marker, next line)
line 2: x0=120.6 bold=True  'Regulatory & Certification Requirements'
        x0=306.4 bold=False ' � Changes in PCN documents, ISO standards or '   (same line, different span)
```

Line 2 is genuinely mixed (bold label + non-bold continuation, one line) — but line 0
(`External Issues` itself) is not. **The all-bold-line rule as originally stated tags
`External Issues` and `Internal Issues` as headings.** They are not — `master_contextC`
names them explicitly as the trap. The rule was wrong; fixing it for real instead of
patching around this one case.

**What actually separates them, checked side by side:**

| Row | x0 | bold | font size | Own block, or mid-block with body? |
|---|---|---|---|---|
| `Foreword` | 70.9 | all-bold | 11.04 | **own block** — block `b006` contains only this one line |
| `QUALITY POLICY` | 70.9 | all-bold | 11.04 | **own block** — `b022` contains only this line + the orphan parenthetical (also all-bold) |
| `SAFETY POLICY` | 70.9 | all-bold | 11.04 | **own block** — `b027`, one line, nothing else |
| `Organisational Quality Objectives` (centered) | 239.2 | all-bold | 11.04 | **own block** — `b030`, one line, nothing else |
| `QUALITY & SAFETY POLICY STATEMENT` | 207.9 | all-bold | 11.04 | **own block** — `b021`, one line, nothing else |
| `Annex B: Specific Terms of Reference...` | 70.9 | all-bold | 11.04 | **own block** — `b330`, one line, nothing else |
| `1  SCOPE` | 75.5 / 115.2 | all-bold | 9.96 / 11.04 | own block, `b037` |
| `4` / `4.1` (glued, FLAG-1) | 79.9 | all-bold | 9.96 / 11.04 | own block, `b051` — shares its block **only with another heading row**, no body |
| `4.2.2 External and Internal Issues Affecting the QMS` (real numbered heading) | 79.9 | **mixed — corrected, see below** | 11.04 | **mid-block** — `b058`, sandwiched between `4.2.1`'s body (before) and `4.2.2`'s own body (after), in the *same native block* |
| `External Issues` (sub-label, false positive) | 120.6 | all-bold | 11.04 | **mid-block** — `b059`, line 0 of a 29-line block, lines 2–28 are ordinary bullet body |
| `Internal Issues` (sub-label, false positive) | 120.6 | all-bold | 11.04 | **mid-block** — same `b059`, line 19, preceded by 18 lines of unrelated bullet body in the same block |

Font size is confirmed **not** part of the signal, same conclusion as the original
draft, no contradiction: `9.96` (root clause numbers) and `11.04` (Annex clause
numbers, all unnumbered headings) both occur on genuine headings.

x0 alone still doesn't cleanly separate them (`Organisational Quality Objectives` at
239.2 is a real heading; `External Issues` at 120.6 is not — magnitude alone gives no
threshold that admits one and excludes the other).

**The signal that actually holds:** a numbered row (matches the regex in §4 below) is
always a heading, regardless of block placement — `4.2.2` proves numbered headings can
sit mid-block next to body text and are still real. An **unnumbered** bold row is a
heading only if **every other row in its containing native PyMuPDF block is also a
heading-shaped (fully-bold) row** — i.e. the block contains no ordinary body row at
all. Every confirmed real unnumbered heading in the sample is the sole content of a
clean block, or shares its block only with another heading row (the FLAG-1 gluing
case). Both false positives (`External Issues`, `Internal Issues`) sit inside a block
that is mostly non-bold body — that block-composition check is what excludes them, not
anything about the row itself in isolation.

**Rule (revised):**

```
is_all_bold_row(row)   = all(span.bold for span in row.spans if span.text.strip())
is_numbered(row)       = NUMBERED_HEADING_RE.match(row.text)          # see §4
block_is_homogeneous(blk) = all(is_all_bold_row(row) for row in blk.rows)

is_heading_row(row) =
    is_all_bold_row(row) and (is_numbered(row) or block_is_homogeneous(row.block))
```

This requires the row classifier to carry a reference to its originating native block
(so the homogeneity check has something to test against) — noted in the pipeline
section below.

**Not yet verified beyond this one block.** `b059` is the only mid-block false-positive
case actually checked. Whether block-homogeneity holds cleanly across all 59
`COMBINED` subdocuments — not just this one QM page — needs a full-corpus dry run
before this rule is trusted, same discipline Phase 1 applied to the empty-table rule.
Flagged in the verification checklist below, not assumed safe from one example.

**Correction, caught during the build's own verification pass, not before:** the row
above for `4.2.2 External and Internal Issues Affecting the QMS` was wrong. Re-checked
the real spans directly: `x0=79.9 bold=False text='4.2.2'` — the **number token itself
is not bold**; only the title `'External and Internal Issues Affecting the QMS'`
(x0=113.5) is bold. The row as a whole therefore fails `is_all_bold_row`, the same as
any of Gap 1's rows (build report below) — `4.2.2` was never actually a clean example
of "numbered headings bypass block-homogeneity," it's an instance of the same
non-bold/mixed-bold clause-number problem the build later found at larger scale. Left
here rather than quietly deleted, because it's a real instance of exactly the failure
mode this whole document argues for guarding against: a claim that looked
straightforward from a hand-read span dump, carried through several rounds unchallenged,
until a full build-and-verify pass actually checked it against the artifact.

### 2. FLAG-2 confirmed directly: number and title tokens land in separate `line` entries

`4  Context of Organization's Quality Management System  4.1  Organization and its
context` (QM p.10) is one PyMuPDF block with 4 `line` entries — `4`, the title,
`4.1`, its title — even though `4`/title sit at y0 470.7/469.7 (1pt apart, same visual
row). Confirms the plan needs to **regroup lines by y-proximity before reading heading
text**, not trust PyMuPDF's own `line` boundaries as the row boundary. Tolerance: group
consecutive lines whose bboxes' y0 are within **3pt** of each other into one row (1pt
observed, 3pt gives margin without risking merging two real stacked lines — QM body
line spacing is ~14.7pt, well clear of 3pt).

### 3. FLAG-1 confirmed directly: ancestor + child glued into one block, no body between

Same p.10 block (`4` immediately followed by `4.1`, no body row in between) is a single
native PyMuPDF block. **Resolution: Phase 2 must operate at row level across the whole
subdocument's block/line stream, not at block level.** Block boundaries carry no
structural meaning for chunking — only the row sequence does. A block is just PyMuPDF's
container; once flattened into rows, this case is a non-event (two consecutive heading
rows, zero body rows between them — same shape as any other zero-body ancestor).

### 4. Numbered heading regex, grounded against real rows

Row text after concatenation, leading token: `^(\d+(?:\.\d+)*)\s+(.+)$` — captures `1`,
`4.2`, `1.0`, `6.2.1.1` (the skipped-level case) uniformly. Verified against `1  SCOPE`,
`4.2  Needs & Expectations of Interested Parties`, `1.0  CEO`, and the deeper QM
examples in `master_contextC.md`'s few-shot section (`5.1.2`, `6.2.1.1`). Applied
**only** to rows that already passed the all-bold check above — enumerated items
(`1. To achieve...`) and lettered items (`a.  Administration...`) never reach this
regex because they're non-bold; the regex alone would have matched their leading digit
incorrectly if it ran unconditionally on all rows, which is exactly the trap
`master_contextC.md` names.

Annex ancestor regex: `^Annex\s+([A-Z])\b` — matches `Annex A (Functional organisation
chart...)`, `Annex B: Specific Terms of Reference...`, `Annex D: Maximum Number of
Candidates...`. All three confirmed all-bold in the artifact. An Annex heading opens a
**fresh numbering scope**: `1.0` under `Annex B` is a different clause identity than a
document-root `1`, exactly per `master_contextC.md`'s pp.29–34 example. No special
collision handling needed beyond scoping numbered-heading lookups to "nearest open
Annex ancestor, or document root if none."

### 5. Table ownership — grounded on the two named few-shot cases

- QM p.11's untitled Interested-Parties table (`AEI-QM-T-01__t03`, `page_start=11,
  page_end=11`) sits between heading rows `4.2.1  Relevant Interested Parties...` and
  `4.2.2  External and Internal Issues...`. Nearest-preceding-heading lookup by
  document order correctly attaches it to `4.2.1`.
- pp.1–2 signature-block table (`t01`) has no heading before it *except* the bold title
  line `Altair Engineering Inspections Pte Ltd` (p.1, x0=212.4, confirmed all-bold) —
  checked directly, this line **is** detected as an unnumbered heading under the rule
  above, so the "table before any heading" edge case does not actually occur on p.1.
  **Not yet verified corpus-wide** — flagged as a build-time check across all 59
  `COMBINED` subdocuments, not assumed safe from the QM sample alone. Fallback if it
  ever does occur: synthesize a `doc_name`-titled front-matter chunk rather than drop
  the table silently.

**Rule:** a table attaches to the most recent heading row (any level) that precedes the
table's own start page/position in document order. Rendered inline in that chunk's
`text` as a plain row-per-line table (cells joined by ` | `, `None`/blank cells emitted
as empty string) — no separate `tables` field, per `master_contextC.md`.

### 6. Artifact convention — one JSON per source PDF, not per subdocument

Phase 1's own artifact schema section is explicit: *"per `master_contextC.md`'s 'one
JSON per source document' convention"* — and then names exactly **two** files
(`quality_manual.json`, `combined_complete_qms.json`), one per **source PDF**, each
containing all of that PDF's subdocuments. Phase 2 follows the identical convention:
two output files, not 59+1. `v2_plan.md`'s `<doc-slug>.json` phrasing is read as
"named by source-PDF slug," matching Phase 1's own resolution of the same phrasing.

---

## Locked decisions — unnumbered headings, zero-body absorption, parentheticals

Q1 went through two more rounds after the initial "unnumbered headings can be
ancestors" draft — a side-by-side run of that exact rule against real rows (pp.7–9)
showed it didn't do what it was supposed to: the p.8 orphan parenthetical
`(Applicable for all locations...)` is *itself* zero-body, all-bold, own-block, and
immediately followed by more headings — structurally identical to a real ancestor
banner — so it **clobbered** `QUALITY & SAFETY POLICY STATEMENT` as the open ancestor
before `QUALITY POLICY` was even reached. A flat-only counter-rule (never nested) then
lost `QUALITY & SAFETY POLICY STATEMENT`'s text entirely — worse than the one orphan
fragment `master_contextC.md` already accepted losing. Both real runs, not hypothetical
— see the conversation history for the full before/after tables. **Final rule,
replacing both:**

1. **Numbered headings: unchanged.** Ancestor nesting by dot-depth, exactly as already
   specified (§4 below) — confirmed identical output before and after every later
   change to the unnumbered rule, no regression.
2. **Unnumbered headings: flat, never ancestors.** Each becomes its own heading+body
   leaf chunk (`ancestor_path: []`), bounded by the next heading of any kind — no
   unnumbered-heading nesting, ever.
3. **Zero-body heading → absorbed as a leading line of the next chunk, never its own
   chunk, never dropped.** "Zero-body" is decided by scanning forward **past any
   parenthetical rows** to the next real body row or the next heading row — a heading
   followed only by a parenthetical and then real body (e.g. `Organisational Quality
   Objectives` → paren → the numbered list) is **not** zero-body; it gets its own chunk
   normally. Absorbed text lands in a chunk's `lead_lines` (schema below) — visible,
   searchable, but the chunk's own `clause_title` stays the heading it actually opened
   on.
4. **Parenthetical annotation lines (`^\(.*\)$`) are never a heading and never their own
   chunk.** If a chunk is currently open when one is hit, it folds inline into that
   chunk's body at that position. If none is open, it queues in the same absorption
   buffer as #3, to land in whatever chunk opens next.
5. **Enumerated list items stay body, not clauses.** Confirmed on real spans: `1. To
   achieve ZERO...` etc. (QM p.9) are non-bold — the numbered-heading regex requires
   `is_all_bold_row`, so these never match it and never split into their own chunks.
   This was checked against a stated expectation that they *would* split (they don't) —
   real spans win, per `master_contextC.md`'s own "enumerated list items are not
   clauses" rule.

**A real implementation bug surfaced and got fixed while validating this**, worth
recording since it changes concrete output: a zero-body heading must **still close**
whatever chunk was previously accumulating before it defers to the absorption buffer —
missing that close left the *previous* chunk's `current` reference dangling, so the
next parenthetical silently leaked into the wrong chunk's body (`Foreword` picked up
p.8's parenthetical instead of it landing near `QUALITY POLICY`). Fixed: every heading
row (zero-body or not) closes the previously-open chunk first, unconditionally.

**Table serialization** (previously Q2): ` | `-joined cells, one row per line, blank
for `None`/empty cells. No objection raised — kept as proposed.

**Front-matter-before-any-heading fallback** (previously Q3): checked at build time
across the full corpus, not just QM — see the build report below for the real result.

---

## Artifact schema

Two files, one per source PDF, matching Phase 1's own convention:

```
data/artifacts/phase2/quality_manual.json
data/artifacts/phase2/combined_complete_qms.json
```

Top level:

```json
{
  "source_pdf": "COMBINED_Complete_QMS.pdf",
  "chunks": [ /* see below */ ]
}
```

Per chunk:

```json
{
  "chunk_id": "AEI-QM-T-01__c014",
  "doc_id": "AEI-QM-T-01",
  "doc_name": "QUALITY MANUAL",
  "clause_no": "4.2.1",
  "clause_title": "Relevant Interested Parties",
  "ancestor_path": [
    {"clause_no": "4", "clause_title": "Context of Organization's Quality Management System"},
    {"clause_no": "4.2", "clause_title": "Needs & Expectations of Interested Parties"}
  ],
  "lead_lines": [],
  "text": "4 Context of Organization's Quality Management System\n4.2 Needs & Expectations of Interested Parties\n4.2.1 Relevant Interested Parties\n<body text>\n<inline table rows>",
  "page_start": 11,
  "page_end": 11
}
```

- `clause_no` is `null` for unnumbered headings (e.g. `Foreword`), and takes the
  `Annex X/N.N` form inside an Annex scope (e.g. `Annex B/1.0`).
- `ancestor_path` holds heading-only entries (no body) for every **numbered/Annex**
  level above the leaf, root first (numbered nesting only — unnumbered headings are
  flat and never appear here, per the locked decision above). Annex ancestors appear
  with `clause_no: null` and their full heading text as `clause_title` (e.g. `"Annex B:
  Specific Terms of Reference for Training & Examination Staff"`).
- `lead_lines` holds zero-body unnumbered heading text and/or parenthetical annotation
  text absorbed onto this chunk (locked decision, rules 3–4) — `[]` when nothing was
  absorbed. Rendered as the first line(s) of `text`, ahead of the chunk's own heading.
- `page_start`/`page_end` are `min`/`max` PDF page across the chunk's own heading rows,
  body rows, and any inline table's `bbox_by_page` — never inherited from a parent or
  neighbor, per `master_contextC.md`.
- `chunk_id` follows Phase 1's `<doc_id>__<short-code>` convention (`t01`/`b022` style),
  using `c` for chunk: `<doc_id>__cNNN`, sequential within the subdocument in document
  order.

---

## Pipeline

1. **Load** the relevant Phase 1 artifact (never re-parse PDFs). Process one
   subdocument at a time.

2. **Flatten to rows.** Walk every block's `lines` in document order (blocks are
   already page-ascending, reading-order within a page — confirmed directly). Regroup
   `line` entries into rows by y0 proximity (≤3pt gap → same row, per grounding item 2),
   concatenating each row's text left-to-right by x0. This discards block boundaries as
   a structural signal entirely (grounding item 3) — only the row sequence matters from
   here on.

3. **Classify each row.** Every row keeps a reference to its originating native
   PyMuPDF block (needed for the homogeneity check below):
   - `is_parenthetical`: text matches `^\(.*\)$` — checked **first**, overrides
     everything else below (a parenthetical is never a heading even if all-bold and
     block-homogeneous).
   - `is_all_bold_row`: every non-whitespace span in the row is bold.
   - `is_numbered`: `is_all_bold_row` and matches `^\d+(\.\d+)*\s+` (§4 above).
   - `is_annex`: `is_all_bold_row` and matches `^Annex\s+[A-Z]\b` (§4 above).
   - `is_unnumbered_heading`: `is_all_bold_row`, not numbered, not Annex, not
     parenthetical, **and every other row in this row's containing block is also
     `is_all_bold_row`** (block homogeneity — grounding item 1's revised rule; this is
     what excludes `External Issues`/`Internal Issues`-shaped sub-labels).
   - Everything else is body content, accumulated under whichever chunk is currently
     open.

4. **Build the tree**, one subdocument at a time. State: `numbered_stack` (dot-depth
   nesting), `annex_ancestor` (current open Annex heading, or none), `pending_prefix`
   (ordered list of absorbed heading/parenthetical text awaiting a home), `current`
   (chunk being accumulated, or none).
   - **Numbered heading:** close `current` (always — see the closure-bug note above).
     Pop `numbered_stack` while its top's dot-depth ≥ this heading's. `ancestor_path` =
     `[annex_ancestor if open] + numbered_stack` (numbered nesting itself is
     **unchanged**, orphans/skips attach to the nearest existing ancestor per
     `master_contextC.md`'s `6.2 → 6.2.1.1` case). Open a new `current`, `lead_lines` =
     whatever's in `pending_prefix` (then clear it), push onto `numbered_stack`.
   - **Annex heading:** close `current`. Set `annex_ancestor` to this heading, reset
     `numbered_stack` to empty (fresh numbering scope). Push the Annex heading's own
     text into `pending_prefix` too — this reuses the same absorption mechanism as any
     zero-body heading (rule 3), so the common case (numbered sub-items follow
     immediately, e.g. `1.0 CEO`) absorbs it as their `lead_lines`, and the rare case
     (real intro prose directly under the Annex heading, before any numbered sub-item)
     still gets a home via the body-with-no-open-chunk path below, titled with the
     Annex heading text — **nothing about an Annex heading can be silently dropped
     either.**
   - **Unnumbered heading:** close `current` (always). Look ahead past any
     parenthetical rows (rule 3) to decide zero-body. If zero-body, push its text to
     `pending_prefix`, open nothing. Otherwise open a new `current` (`ancestor_path:
     []`, flat — locked decision), `lead_lines` = `pending_prefix` (then clear it).
   - **Parenthetical:** if `current` is open, append its text into `current`'s body
     inline, at that position. Otherwise push to `pending_prefix`.
   - **Body:** if `current` is open, append. If not (a body row arrives with nothing
     open — e.g. the Annex-intro-prose case, or a zero-body-then-immediately-body
     sequence), open a synthetic `current` titled from the last heading-shaped entry in
     `pending_prefix`, `lead_lines` = the full buffer, then append the body line —
     **this is what makes rule 3 actually hold: nothing pending ever reaches the end of
     the stream without a chunk to land in, unless the stream itself ends first.**
   - **End of subdocument:** close `current`. If `pending_prefix` is still non-empty
     (a trailing zero-body heading with nothing at all after it), append its text into
     the **last emitted chunk's** `lead_lines`/body rather than opening a new
     empty-bodied chunk — keeps "no empty chunks" intact while still not dropping the
     text. Report whenever this fallback actually fires (build report checks whether it
     ever does).

5. **Attach tables inline.** For every kept table (already stitched, already filtered
   by Phase 1), insert it as a pseudo-row in the same row stream (same open/absorb
   rules as a body row, so it inherits the identical no-drop guarantee) positioned by
   its own `y0` on its start page (from Phase 1's `bbox_by_page`) against each row's
   `y0` — **not** a page-boundary approximation. (Build report: the page-boundary
   version was tried first and produced a confirmed wrong attachment — QM's
   Responsibility Matrix table landed under an unrelated clause because more content
   followed it on the same page. Fixed before this was trusted.) Serialized as ` | `-
   joined cells, one row per line (locked Q2 default).

6. **Emit chunks** as described in the artifact schema — `text` assembled from
   ancestor heading lines + own heading + own body + inline tables, `page_start`/
   `page_end` derived from the chunk's own content only.

7. **Verification pass** (see checklist) before declaring the artifact done.

---

## Verification checklist — before Phase 3 starts

(Per `v2_plan.md`'s own gate, expanded with what grounding surfaced.)

- [x] Zero empty chunks — confirmed by direct query on the built artifacts (0/102,
      0/404) after fixing bug 4 above (was 3/404 before the fix).
- [x] Every chunk has a `doc_id` — confirmed, 0 missing in either artifact.
- [x] Every chunk's `page_start` ≤ `page_end` — confirmed, 0 violations in either
      artifact. (Containment within the chunk's own content is enforced by
      construction — `page_end` only ever grows via `max()` against the chunk's own
      rows/tables — not independently re-derived from spans as a separate check.)
- [x] `QUALITY_MANUAL.pdf`'s chunks reproduce every few-shot example in
      `master_contextC.md`: pp.1–2 signature block as one chunk, pp.3–5 Revision
      History as one chunk, p.6 ToC as one chunk (not parsed as clauses), p.7 Foreword,
      p.8 two **flat** policy chunks (`QUALITY POLICY`, `SAFETY POLICY`, each with
      `ancestor_path: []`) each carrying `QUALITY & SAFETY POLICY STATEMENT` (and, for
      `QUALITY POLICY`, the p.8 parenthetical too) in `lead_lines` — not
      `ancestor_path`, per the final locked rule, p.9 `Organisational Quality
      Objectives` as one chunk (numbered list stays body, parenthetical folds in,
      confirmed not zero-body since the lookahead skips the parenthetical to find real
      body beyond it), pp.10–15 numbering gaps (`4.3` missing, `5.1.2` with no `5.1.1`,
      `6.2.1.1` with no `6.2.1`), pp.29–34 Annex B numbering restart (`Annex B/1.0`
      distinct from root `1`), p.36 Annex D **absent as a table** (Phase 1 already
      discarded it — confirm no phantom empty chunk is created for its heading either).
      **Show the disagreements, not just the matches.**
      → **[x] done — matches confirmed for pp.1–9, pp.29–34 Annex B, p.36 Annex D;
      disagreements shown (not hidden) for `6.2.1.x`/`5.3.x`/`4.2.2` (Gap 1) and the
      `[4, 5.1]` vs `[5, 5.1]` ancestor case.** See build report.
- [x] Source-line coverage reconciliation run across **every page of both PDFs** — 0
      unaccounted lines (6,616/6,616 accounted, both PDFs). See build report.
- [x] ~~`4.2.2` chunks as a real leaf~~ — **it does not.** This checklist item's own
      premise was wrong, caught by actually running the check rather than assuming it:
      `4.2.2`'s number token is non-bold (mixed-bold row), so it never reaches the
      numbered path at all — same failure mode as Gap 1, not the clean proof case this
      item assumed. Corrected in the grounding section above and the build report.
- [x] Block-homogeneity rule run against the full corpus — 2,134 blocks checked, 32
      mid-block bold rows correctly excluded (includes the proven `b059` case). Full
      list in `data/artifacts/phase2/block_homogeneity_report.md`. One bug caught in the
      *report itself* before trusting it (was flagging real numbered headings as
      "excluded" — fixed to re-derive via the actual classifier).
- [x] `4` and `4.1` never become chunks of their own — confirmed, `4.1`'s
      `ancestor_path` is `["4"]`, no standalone `4` chunk exists.
- [x] Table-to-chunk attachment spot-checked: p.11 Interested Parties → `4.2.1` ✓. p.14
      Responsibility Matrix → **`5.3`, not `5.3.2`** (Gap 1) — disagreement shown, table
      itself confirmed not lost. A real bug was caught and fixed in this same check
      (table page-boundary approximation → precise y0-based positioning, bug 1 above).
- [x] `AEI-QP-T-03B`'s two split subdocuments chunk independently — confirmed, 2
      distinct `doc_name`s (`INTERNAL AUDIT CHECKLIST (AEC)` /
      `INTERNAL AUDIT CHECKLIST (AQB)`) both present under `doc_id=AEI-QP-T-03B`, no
      cross-contamination observed.
- [x] Front-matter-before-any-heading check (Q3) run across all `COMBINED`
      subdocuments — **10 real hits**, not zero. See build report; fallback confirmed
      working (no drop), title quality fixed (bug 5 above).
- [x] Chunk count reported, not assumed: **102** (`quality_manual.json`), **404**
      (`combined_complete_qms.json`).

---

## Explicitly out of scope for Phase 2

- Checklist PDF parsing — Phase 3.
- Embedding, BM25 indexing, ranking — Phases 3–4.
- Any judgment about which chunk answers which checklist item — never in scope anywhere
  in this system.

---

## Housekeeping

Fixed a misplaced empty directory found while grounding this plan:
`data/artifacts/phase1/phase2/` (a `.gitkeep`-only stray, evidently meant to be
`data/artifacts/phase2/`) moved to `data/artifacts/phase2/.gitkeep`. No artifact content
was in it.

---

## Build report (2026-07-21)

Implementation lives in `backend/app/pipeline/phase2/` (`constants.py`, `rows.py`,
`classify.py`, `chunks.py`, `tables.py`, `build.py`, `reports.py`, `run.py`). Run from
`backend/`: `conda run -n audit python -m app.pipeline.phase2.run`.

**Output:**
- `data/artifacts/phase2/quality_manual.json` — 102 chunks.
- `data/artifacts/phase2/combined_complete_qms.json` — 404 chunks.
- `data/artifacts/phase2/coverage_report.md` — source-line reconciliation, full corpus.
- `data/artifacts/phase2/block_homogeneity_report.md` — heading-detection check, full
  corpus.

### Coverage reconciliation — the zero-drop guarantee, corpus-wide

Requested explicitly: re-run the pp.7–10 reconciliation across every page of both
PDFs, not just the sample.

| | QUALITY_MANUAL.pdf | COMBINED_Complete_QMS.pdf | Total |
|---|---|---|---|
| Raw source lines | 1,253 | 5,363 | 6,616 |
| A (body in a chunk) | 807 | 3,400 | 4,207 |
| B (heading/parenthetical absorbed) | 112 | 469 | 581 |
| C (intentionally stripped) | 0 | 0 | 0 |
| D (merged by row-grouping) | 334 | 1,494 | 1,828 |
| Sum | 1,253 | 5,363 | 6,616 |
| **Unaccounted** | **0** | **0** | **0** |
| Tables attached | 9/9 | 135/135 | 144/144 |

**Zero-drop holds corpus-wide, not just on the pp.7–10 sample.** Bucket C is 0
everywhere, same finding as the sample: this pipeline stage strips nothing; real page
footers were already removed upstream by Phase 1 before this artifact existed.

### Block-homogeneity — proven on one block during planning, now checked on all 2,134

- 481 single-row homogeneous blocks (ordinary heading-only blocks).
- 12 multi-row homogeneous blocks (FLAG-1-style glued headings, e.g. `4`/`4.1` on one
  block with no body between).
- 1,641 mixed blocks (heading + body together).
- **32 mid-block all-bold rows correctly excluded from heading status** — the
  corpus-wide population the rule protects against. Includes the two rows it was
  proven on (`External Issues`, `Internal Issues`) plus real corpus repeats: `5.2
  Policy`, `7.1.1 General`, `7.4  Communication`, `Sources of Organizational Knowledge
  include:`, `External Communication`, and more — full list in the report. (32, not 16,
  because `AEI-QM-T-01` legitimately appears twice — once standalone, once as the first
  36 pages of `COMBINED` — per `master_contextC.md`'s explicit "intentional, not a bug"
  call on this duplication.)

**A bug was caught in the report itself before trusting it, not after.** The first
version flagged every mid-block bold row, including real numbered headings like `5.2
Policy` and `7.1.1 General` — those are correctly classified via the numbered-heading
regex regardless of block placement and were never actually at risk. Fixed: the report
now re-derives classification through the real `classify_rows()` function instead of a
parallel reimplementation, so it can't silently drift from what the chunker does.

### Five real implementation bugs found and fixed during this build (not present in the plan)

1. **Table attachment used a page-boundary approximation, flagged as a risk in the
   plan — turned out to be a real, confirmed defect, not just an approximation.** QM's
   Responsibility Matrix table (`t04`, page 14) attached to `6.1` (Actions to address
   risks and Opportunities) instead of the clause it actually sits under, because the
   original rule placed a table after *every* row on its start page, and `6.0`/`6.1`'s
   own page-14 content came after it in the stream. Fixed: table insertion now uses the
   table's own `y0` from Phase 1's `bbox_by_page`, compared against each row's `y0`
   (added to the row schema for this purpose) — inserted immediately after the last row
   genuinely above it, not after the whole page. Re-verified: `t04` now attaches to
   `5.3` (see the non-bold-subclause finding below for why not literally `5.3.2`); `t03`
   (p.11 Interested Parties → `4.2.1`) unaffected, confirms no regression.
2. **Zero-body lookahead didn't recognize a table as real content.** QM's `Revision
   History` heading sits directly above its table with no text body between — the
   lookahead saw the table pseudo-row, didn't recognize it, and concluded zero-body
   (wrongly), absorbing `Revision History` into a synthetic chunk instead of giving it
   its own proper heading line. Fixed: `is_zero_body_ahead` now treats a table exactly
   like a body row — real content, not a heading boundary. This is a direct extension
   of the locked rule's own stated intent ("scanning forward past parentheticals to the
   next real body row or heading row"), not a new judgment call.
3. **A zero-body heading wasn't closing the previously-open chunk** (caught during the
   pp.7–10 validation round, before this build — see conversation history — carried
   here for completeness since it's load-bearing for every subsequent run).
4. **The "subdocument produced zero chunks anywhere" defensive fallback rendered an
   empty `text` field.** Confirmed real, not hypothetical: 3 `COMBINED` subdocuments
   (`AEI-QP-T-05A` "CORRECTIVE ACTION FORM", `AEI-WI-T-03A`, `AEI-WI-T-03B`) are blank
   form templates whose only table Phase 1 correctly discarded as empty, leaving
   nothing behind but a title. The fallback set `clause_title` correctly but left
   `_heading_line=None` and dropped the title from `lead_lines` (only `pending_prefix
   [:-1]`, excluding the one real entry) — so `text` came out `""`, a real gap for
   anything reading `text` (search/embedding downstream) even though the coverage
   reconciliation's row-level bucketing didn't catch it (the row itself was correctly
   bucketed; the bug was in how the bucketed content got rendered into the artifact).
   Fixed: `lead_lines` now gets the *full* `pending_prefix`. Verified: 0 chunks with
   empty `text` in either artifact, was 3 before the fix.
5. **The Q3 front-matter-before-any-heading fallback used a bare `"(untitled)"`
   placeholder.** Confirmed real, not hypothetical: 10 `COMBINED` subdocuments open
   with a table or body row before any heading exists at all (e.g. `AEI-QM-T-01A`,
   page 37 — the subdocument's entire content is one personnel-qualification table,
   no heading text anywhere). Not a drop (the table was always attached), but
   `"(untitled)"` is a poor label for something with a perfectly good name available.
   Fixed: falls back to the subdocument's own `doc_name` instead (e.g. `AEI-QM-T-01A`'s
   synthetic chunk is now titled `"APPROVED EXAMINER LIST"`). 0 chunks titled
   `"(untitled)"` after the fix, was 10 before.

### Two real structural gaps found — reported, not silently patched

**Gap 1 — some deep QM clause numbers are not (fully) bold, so they never reach the
numbered-heading regex at all.** Checked directly (p.13–15): `5.2`, `5.3`, `6.0`,
`6.1`, `6.2`, `6.3` are bold and detected correctly. But `5.2.1`–`5.2.3`,
`5.3.1`–`5.3.5`, `6.2.1.1`–`6.2.1.3`, and `6.3.1.1` are **not bold at all** — a real
inconsistency in the source document's own styling, not a rule bug. **`4.2.2` is a
third, distinct variant of the same problem, and was misdiagnosed in this document's
own original grounding** (corrected above): its number token (`4.2.2`) is non-bold
while its title is bold — a *mixed*-bold row, not a fully non-bold one, and it fails
`is_all_bold_row` the same way. It was originally cited as proof that numbered headings
bypass block-homogeneity regardless of block placement; it never actually reached that
code path at all. Consequence, for all three shapes: these rows never match
`is_all_bold_row`, so they fall through to plain body text of whichever bold ancestor
is open — `5.3.2 Responsibility Matrix` and `4.2.2 External and Internal Issues` (both
named explicitly in `master_contextC.md`'s few-shot as their own chunks) end up as
undifferentiated body inside `5.3` and `4.2.1` respectively. **Not dropped** — `t04` is
still attached (to `5.3`), the text is still present and searchable, per the user's
stated priority (nothing dropped is the floor). But it disagrees with the specific
`master_contextC.md` worked examples for both clauses. Not fixed: a rule to recognize
non-bold/mixed-bold numbered rows as headings risks reintroducing the enumerated-list-
item trap (`1. To achieve ZERO...` on p.9 is also a non-bold, digit-led row, and must
**not** become a heading) — needs an explicit, grounded decision, not a quick regex
change.

**Gap 2 — a second, unrelated numbered-heading format exists in Work Instruction
subdocuments, and isn't matched either.** `AEI-WI-T-01B`, `AEI-WI-T-05B`, and
`AEI-WI-T-15` use bold headings shaped `"1. Purpose:"`, `"2. Reference:"` — a **period**
directly after the digit, where the locked regex (`^\d+(\.\d+)*\s+`) requires
whitespace directly after the digit. These are bold (unlike Gap 1's rows and unlike the
enumerated list items), so this is a pure regex-shape miss, not a bold/non-bold
ambiguity — lower-risk to fix than Gap 1, but still not something the locked rule set
covered, so left unfixed and flagged rather than expanded on the spot.

**Both gaps are real, both leave text in place (no-drop guarantee unaffected,
confirmed by the 0-unaccounted coverage result above), both need a decision before
the numbered-heading rule is touched again.**

### A third disagreement against `master_contextC.md`'s own worked example

`5.1.2`'s ancestor_path comes out `[4, 5.1]`, not `[5, 5.1]` as `master_contextC.md`'s
few-shot notation implies. Checked directly (p.12): there is **no bare `5` heading
anywhere in the real PDF** — the document goes straight from `4.4`'s body to `5.1`
`Leadership`. The algorithm is applying "orphans attach to the nearest existing
ancestor" exactly as specified — `4` is the nearest existing depth-1 ancestor, because
no real `5` heading ever closes or replaces it. `master_contextC.md`'s `[5 hdg]`
notation assumed a heading that, checked against the actual spans, does not exist.
Surfacing this because it was checked, not assumed.

### Trailing-absorb fallback (locked rule 3's end-of-stream case)

Fires for 1 of 1 QM subdocument and 11 of 59 `COMBINED` subdocuments — a zero-body
heading with genuinely nothing after it before the subdocument ends. Confirmed working
as designed, not a drop: QM's case is `Annex C: Office Floor Plan` and `Annex D:
Maximum Number of Candidates...` (both zero-body because Phase 1 already discarded
their only content — a diagram-only page and an empty table, respectively) — their
heading text lands in the lead_lines of the subdocument's actual last chunk (Annex B's
`Quality Coordinator` clause), not lost, but topically unrelated to where it landed.
Small blast radius (12 of 60 subdocuments, one trailing absorption each) but worth a
human glance rather than assuming it's always this benign.

### Few-shot verification against `master_contextC.md` — matches and disagreements

- pp.1–2 signature block: one chunk, `t01` attached. ✓
- pp.3–5 Revision History: one chunk, `t02` attached, proper heading line (post bug-2
  fix above — the zero-body lookahead not recognizing a table as content). ✓
- p.6 Table of Contents: one chunk, ToC lines never parsed as clauses (all non-bold,
  excluded automatically). ✓
- p.7 Foreword, p.8 `QUALITY POLICY`/`SAFETY POLICY` (flat, `ancestor_path: []`,
  `QUALITY & SAFETY POLICY STATEMENT` + the p.8 parenthetical both in `QUALITY
  POLICY`'s `lead_lines`), p.9 `Organisational Quality Objectives` (one chunk,
  numbered list stays body, parenthetical folds in): confirmed identical to the
  validated scratch-script output, now from the real pipeline. ✓
- pp.10–15 numbering gaps: `4.3` correctly absent (never existed). `5.1.2` present but
  see the ancestor-path disagreement above. `6.2.1.1`/`6.2.1.2`/`6.2.1.3` present as
  body text of `6.2`, not separate chunks — see Gap 1. ✗ (disagreement shown, not
  hidden)
- pp.29–34 Annex B: `Annex B/1.0` (`CEO`) confirmed distinct from root `1` (`SCOPE`),
  ancestor_path correctly shows the Annex heading. ✓
- p.36 Annex D: no chunk of its own for the discarded table; its heading text survives
  via the trailing-absorb fallback (see above) rather than vanishing. ✓ (no phantom
  empty chunk, and per the no-drop priority, better than the plan's original "produces
  no chunk" default which would have lost the heading text)
- p.11 Interested Parties table → `4.2.1`: ✓. p.14 Responsibility Matrix table → `5.3`
  (not literally `5.3.2`, per Gap 1): partial ✗, shown above, table itself not lost.
- `4.2.2 External and Internal Issues Affecting the QMS` does **not** chunk separately
  either (Gap 1, corrected grounding above) — its text, and `External Issues`/`Internal
  Issues` beneath it, all land as body inside `4.2.1`'s chunk instead. `4.2.1` itself is
  real and correct (`t03` attached, ancestor_path `[4, 4.2]`). ✗ for `4.2.2` specifically,
  shown not hidden — this was the plan's own original proof case for the
  block-homogeneity rule, and it turned out to need the correction above.

### Q3 (front-matter-before-any-heading) — confirmed real, not hypothetical

10 of 59 `COMBINED` subdocuments open with a table or body row before any heading
exists at all: `AEI-QM-T-01A/B/C/D`, `AEI-QP-T-01A`, `AEI-QP-T-01E`, `AEI-QP-T-09`,
`AEI-WI-T-01`, `AEI-WI-T-01A`, `AEI-T-WI-12`. Representative case checked directly:
`AEI-QM-T-01A` (page 37) is entirely one personnel-qualification table, no heading text
anywhere in the subdocument. The Q3 fallback (open a synthetic chunk) fires correctly
and nothing is lost — fixed to title these from `doc_name` instead of a bare
`"(untitled)"` placeholder (bug 5 above).

### Still outstanding (superseded below — Gap 1, Gap 2, and the ancestor-path
disagreement were all resolved in the fix round that follows)

- The 12 trailing-absorb cases and 10 Q3 front-matter cases haven't each been
  hand-opened against source PDF pages the way the QM representative case was for
  each — worth a lighter pass, same as Phase 1's own precedent for its
  diagram-only-page rule.
- Checklist PDF parsing, embedding, indexing, ranking — Phase 3 onward, unchanged.

---

## Fix round (2026-07-21) — Gap 1, Gap 2, and the ancestor-path disagreement

Requested: fix `4.2.2` (no chunk of its own) and `5.1.2` (wrong ancestors), on the
diagnosis that bold-gated numbered detection was the single root cause for both, fold
in Gap 2 (period-style WI numbering) via the same mechanism, keep every existing guard
(sequence, title-shape, enumerated items stay body), and prove the 6,616-line coverage
reconciliation doesn't move.

**The stated root cause for the `5.1.2` defect was checked and found wrong — reported,
not silently used.** Re-read against `master_contextC.md`'s own few-shot text (confirmed
verbatim: `` `5.1.2` attaches to `5.1`. Chunk: `[5 hdg][5.1 hdg][5.1.2 hdg]` ``) and
against the real PDF (p.12, full block dump): **`5` does not exist anywhere in the
document as text** — not non-bold, not merely undetected, genuinely absent between
`4.4`'s body and `5.1 Leadership`. Dropping the bold gate cannot recover text that was
never written. Fixing this needed a different mechanism: a registry that synthesizes a
placeholder top-level ancestor when the real one is missing, added in
`backend/app/pipeline/phase2/ancestor.py`.

**A second, related defect was found while tracing the first.** `4` and `4.2` — the
*already-locked, already-checked-off* "never become chunks of their own" rule — were
actually being violated in the previous build: they emitted zero-body chunks of their
own (confirmed directly: `clause_no="4"` existed as a real chunk with empty body,
contradicting the checklist item that had claimed otherwise). The numbered path never
had a zero-body check; only the unnumbered path did. Fixed as part of the same change,
since `5`'s fix requires exactly this mechanism (a heading that registers as an
ancestor without ever becoming its own chunk).

**A third, unrequested case was found and resolved as a side effect, not hand-carved.**
`6.0 Planning` is a real, bold, titled heading, but its children `6.1`/`6.2`/`6.3` are
written with the same segment count (`6.1`, not `6.0.1`), so plain depth-count
comparison treated them as siblings, not parent/child — `6.1` came out rooted at a
leaked `4` (wrong document section) even before this fix round. The same normalization
`5`'s fix already needed (a trailing `.0` segment is one level shallower for lookup
purposes — first required by the *already-validated* `Annex B/1.0` case, not invented
here) also fixes this: `6.0 Planning`'s real title now correctly serves as `6.1`'s real
ancestor. Not separately engineered — a consequence of applying one consistent rule.

### The registry mechanism (`ancestor.py`)

One `AncestorRegistry` per subdocument (reset on entering an Annex scope — a fresh
numbering namespace, unchanged). Entries are keyed by a normalized tuple (`effective_key`
strips a trailing `.0` segment). `ancestors_for(tup)`:
- Synthesizes (and registers) a bare top-level placeholder **only** when the top-level
  slot has no real entry yet — matches `master_contextC.md`'s `[5 hdg]`/`[6 hdg]`
  notation in both its worked examples.
- **Never** synthesizes a missing intermediate level — matches the same spec's explicit
  "`6.2.1` simply does not appear" for `6.2.1.1`, and the already-validated `5.1.2`
  attaching to `5.1` with no synthesized `5.1.1`. Re-verified this still holds after the
  fix (below).
- Tracks `consumed` per entry; anything that registers as a zero-body ancestor but is
  never looked up by any descendant gets rescued into `pending_prefix` (same no-drop
  fallback already used for unnumbered headings) rather than silently lost — checked at
  Annex transitions and end-of-subdocument.

### Three new real bugs found *during this fix*, caught before reporting

Dropping the bold gate is a broad change; each of these was a genuine regression, not
a hypothetical risk, confirmed on real output before being fixed:

1. **The Table of Contents trap reopened.** `master_contextC.md` explicitly warns the
   ToC is not a reliable structure source — it mirrors real structure, so it's
   sequence-plausible by construction. Confirmed: QM's `4.2` chunk briefly picked up
   the ToC's copy of the text (p.6) instead of the real one (p.10). Fixed: a per-block
   candidate count — QM's ToC packs 22 numbered-shaped rows into one native PyMuPDF
   block; the largest legitimate case found (real sub-clauses glued into one block with
   real prose between them, e.g. `8.4.2.1`/`8.4.2.2`/`8.4.2.3`) is 3. Threshold set at
   5, wide margin either side. A block over threshold: none of its candidates count as
   headings.
2. **The sequence/plausible-next guard, as first built, was too strict and rejected
   real headings.** Requiring an exact `+1` at whatever level changed rejected `4.4`
   after `4.2.2` (no `4.3` exists), `5.1` after `4.4` (no bare `5` exists), and
   `6.0`/`6.1` after `5.3.5` — exactly the numbering-gap behavior
   `master_contextC.md` says is normal and must not break the tree. Fixed: simplified
   to sanity-check only the top-level segment against the running max seen so far in
   the subdocument. Still catches the named `AEI-FORM-64` wrap case (already
   independently blocked by the shape regex requiring real trailing content — this
   guard is defense in depth, as requested, not the primary protection).
3. **A widespread false positive: the company's own letterhead address.** `"18 Boon Lay
   Way, #05-109, Tradehub 21, Singapore 609966"` — non-bold, shape-plausible, and (with
   no numbering context yet) range-plausible — was wrongly becoming clause `"18"` in
   **26 of 59** `COMBINED` subdocuments (every one whose cover page carries the
   company's standard address block). Real, corpus-wide, confirmed by direct query, not
   a one-off. Fixed by re-introducing bold as a requirement, but scoped precisely: only
   when **no numbering context exists yet** in the subdocument. Every real
   first-heading checked in this corpus is bold (`1 SCOPE`, every WI doc's `1.
   Purpose:`-style opener) — this costs nothing real. Once real context is established,
   Gap 1's non-bold deep clauses (which never open a subdocument, always follow
   already-real numbering) still pass through freely. Verified: 0 address false
   positives remaining, `4.2.2`/`5.1.2`/`6.1` all still correct after this change.

### Verification, as requested

- **`4.2.2` is now its own chunk**, ancestors `[4, 4.2]` — confirmed directly:
  `ancestor_path: [('4', "Context of Organization's Quality Management System"),
  ('4.2', 'Needs & Expectations of Interested Parties')]`.
- **`5.1.2`'s ancestors are now `[5, 5.1]`**, matching the spec few-shot exactly:
  `[('5', None), ('5.1', 'Leadership')]` — `5`'s `clause_title` is honestly `None`
  (synthesized, no real title exists to show; the heading *line* rendered in `text` is
  the bare number `"5"`, nothing fabricated).
- **Gap 1 is now fully resolved, not just `4.2.2`.** Every previously-missing deep
  clause chunks correctly: `5.2.1`, `5.2.2`, `5.3.1`–`5.3.5`, `6.2.1.1`–`6.2.1.3`,
  `6.3.1.1`, all with correct ancestors. `t04` (Responsibility Matrix) now attaches to
  `5.3.2` itself, not the `5.3` fallback reported earlier.
- **Gap 2 (WI period-style headings) now resolved**: `AEI-WI-T-01B`/`05B`/`15` all
  chunk their `"1. Purpose:"`-style headings correctly, with real bodies.
- **No enumerated-list ghost chunks.** QM's p.9 `Organisational Quality Objectives`
  confirmed still one chunk, numbered list (`1.`–`4.`) still plain body text. Corpus-wide
  scan for short (<80-char) or suspicious long-sentence clause titles: one hit
  (`AEI-WI-T-01B` clause `9`, `"Examination"`, 1-word title with a real 2-sentence
  body) — legitimate, not a false positive. Zero chunks under 60 characters anywhere.
- **6,616-line coverage reconciliation unchanged** — confirmed identical total before
  and after this entire fix round:

  | | Before this round | After |
  |---|---|---|
  | QM total / unaccounted | 1,253 / 0 | 1,253 / 0 |
  | COMBINED total / unaccounted | 5,363 / 0 | 5,363 / 0 |
  | Corpus sum | 6,616 | 6,616 |
  | Tables attached | 144/144 | 144/144 |

  A/B split shifted within the total, as expected (rows that used to fall to bucket A
  as undifferentiated body now correctly open their own numbered chunks, bucket B) —
  the sum never moved, confirming lines were relocated between chunks and gained
  ancestors, never dropped or duplicated.
- **Zero empty-text chunks, zero missing `doc_id`, zero bad page ranges** — reconfirmed
  after every change in this round, both artifacts.

### Final counts after this fix round

`quality_manual.json`: 83 chunks (was 102 — net decrease from `4`/`4.2`/`5.1`/etc. no
longer wrongly emitting their own zero-body chunks, more than offsetting the newly-real
Gap 1 clauses). `combined_complete_qms.json`: 503 chunks (was 404 — net increase, Gap 1
and Gap 2 clauses across the corpus outweigh the same zero-body-chunk removal).

### Still outstanding

- The 12 trailing-absorb cases and 10 Q3 front-matter cases still haven't each been
  hand-opened individually — unchanged from before this round, same lighter-pass note.
- `ancestor.py`'s top-level-only synthesis is grounded on QM's `5` and `6.0` cases
  specifically; corpus-wide, whether any *other* subdocument has a similarly-missing
  top-level ancestor with a different shape hasn't been individually hand-checked
  beyond confirming the coverage/empty-chunk/page-range invariants hold everywhere.
- Checklist PDF parsing, embedding, indexing, ranking — Phase 3 onward, unchanged.

## Fix round (2026-07-21b) — (doc_id, clause_no) uniqueness

The spec requires `(doc_id, clause_no)` to be the citation/eval key, so it must be
unique per subdocument. The prior round's build report was checked against a claim
that a "restart-prefix mechanism" already existed in the code (comments describing
`AEI-WI-T-05B` getting a `restart1/` prefix) — **that claim was false.** `grep -r
restart` across `backend/app/pipeline/phase2/` and `phases/v2_phase2.md` returns
zero matches; no such mechanism, or anything resembling it, existed anywhere on
disk. Reporting this rather than building around it, per this session's standing
rule. The only existing namespacing mechanism was the `Annex {letter}/{clause_no}`
prefix (for QM's `Annex A/B/C/D`), which was never wired to WI-T-05B's restart at
all.

**Real duplicate count found: 8 groups, not the "two docs" framing in the request.**
`AEI-WI-T-05B` alone has 7 duplicate `(doc_id, clause_no)` groups (`1`, `2`, `3`,
`4.1`, `4.2`, `4.3`, `6`) plus `AEI-WI-T-01B`'s reported `5`. The extra one (`6`,
`Magnetic Yoke...` at p.219-220 vs `Non-compliance` at p.236) wasn't named in the
request; it's the same restart, just one clause further along — resolved by the
same fix as the other six.

### AEI-WI-T-05B: real structure, checked directly against the PDF (pp.217-236)

Read every raw line, not just the chunk output. The document is **one continuous
1-11 numbered procedure** (p.217-224, covering seven pieces of equipment: UFD,
Magnetic Yoke, Radiographic Densitometer, PAUT, TOFD, Film Viewer, Light Meter),
followed at p.227 by a heading reading **`ANNEXURE – I`** (em-dash, not "Annex "),
under which the equipment-8 (PAUT) procedure restarts its own numbering from `1`
(`1. Purpose`, `2. Reference`, `3. Requirements`, `4. PA Instrument calibration`,
then continuing `5`/`6`/`7` — all one namespace, confirmed by the numbers
themselves: no second restart happens at p.234's `ANNEXURE-11` label, which is
almost certainly a garbled `ANNEXURE – II` OCR/extraction artifact — the earlier
forward-reference at `9.1` literally says "provided in Annexure – II", and the
numbering `4→5→6→7` flows straight through that label with no reset).

**Why this wasn't already caught:** `ANNEXURE – I` is non-bold in the source. The
existing `ANNEX_RE` requires bold *and* requires literal `"Annex "` (space, no
dash) directly after — it matches neither the missing bold nor the `"Annexure"` /
en-dash spelling. It was never reached.

**Why I didn't just drop the bold gate on the existing regex:** did that first,
checked the result, and it broke QM. `PCN24-CP09 Annex B.` (QM p.23,
`AEI-QM-T-01__p023_b216`, `8.4.2.2`'s body) is a sentence that word-wraps so
`"Annex B."` starts its own row — non-bold, shape-matches, and would have been
treated as a real Annex boundary, corrupting QM's approved output. Caught before
building on it, not after. Fixed instead by adding a **separate, narrower regex**
(`ANNEXURE_RE`, requires the `"Annexure"` spelling) gated on two things instead of
bold: (1) the row must be **alone in its native block** (real Annexure headings
sit in a block by themselves; the QM wrap-line shares its block with 3 other rows
of the same paragraph — checked directly, confirmed), and (2) the **next
shape-matched row must open at `1`** (a real restart always opens at 1; this also
protects `AEI-WI-T-07`'s trailing `"Annexure A - Information Packages"` label,
which has *no* numbered content after it at all — forcing that one through would
have demoted an already-correct standalone chunk into an absorbed lead-line, a
real regression, caught by checking that doc's chunk sequence before and after).

Result: `AEI-WI-T-05B`'s 7 duplicated clause numbers now render as `Annex I/1`,
`Annex I/2`, `Annex I/3`, `Annex I/4.1`, `Annex I/4.2`, `Annex I/4.3`, `Annex I/6`,
`Annex I/7` — distinct from the main procedure's plain `1`/`2`/`3`/`4.1`/`4.2`/
`4.3`/`6`. `AEI-WI-T-02` and `AEI-WI-T-07` (also spelled "Annexure", also checked)
are byte-identical before and after — the lookahead guard correctly declined both.

**A real defect found while grounding this, not fixed, reported instead:** inside
the `ANNEXURE – I` scope, two body lines (`"1.1 In order to achieve..."` at p.234
and `"1.5 mm drilled hole..."` at p.235) coincidentally start with what looks like
a heading number (`NUMBERED_RE` doesn't require bold once numbering context
exists — Gap 1's fix from the prior round) and get misclassified as their own
numbered chunks (`Annex I/1.1`, `Annex I/1.5`), each wrongly ancestored to
p.227's real `1. Purpose` heading via the registry's exact-tuple-key lookup. This
appears to be a genuine **source typo**: the real heading there is `"5. Purpose"`
(TOFD performance-check sub-procedure) but its body sub-clauses were left at
`1.1`/`1.5` instead of being renumbered `5.1`/`5.5` when the section was likely
copy-pasted from an earlier template — the same typo pattern shows up twice more
in the same block (`"6. Non-compliance"`'s body says `5.1`, `"7. Sample record"`'s
body says `6.1`, both one behind). This does **not** collide with anything (no
other `1.1` or `1.5` exists in this subdocument) so it doesn't block the
uniqueness requirement, and fixing it cleanly would need a stricter
monotonic-numbering guard whose corpus-wide blast radius wasn't part of this ask
— flagging it rather than quietly patching or quietly leaving it undocumented.

### AEI-WI-T-01B: real document typo, not a restart

Checked p.189-190 directly. The real sequence is `1 Purpose → 2 Scope → 3
References → 4 PCN document/CPs Reference → 5 Terms and Definitions → [author
reused "5" instead of incrementing] → 6 Identify possible exemptions → 7 → 8 → 9`
— `6` is already correctly used for the next heading, so there's no missing
number to "restore" and no structural boundary to namespace; it's one flat,
continuous sequence with a single reused digit.

**Rule chosen:** a corpus-wide dedup safety net (`build.py::_dedup_clause_nos`),
run after chunk assembly, per subdocument. First occurrence of a `clause_no` keeps
it unchanged (canonical — neither duplicate is more "correct" than the other, so
whichever comes first in document order keeps the plain citation form); every
later occurrence of the same `clause_no` gets a `#2`, `#3`, ... suffix. Only
`clause_no` is touched — `clause_title`, `text`, `ancestor_path` are untouched, so
nothing about *where the content came from* changes, only the id used to address
it. `clause_no=None` chunks are exempted (confirmed 119 corpus-wide, front-matter/
flat headings distinguished by title+page range instead — not a citation key).
Result: `5` (Terms and Definitions) unchanged, `5#2` (Qualification Requirement).

This same mechanism is a deliberate **safety net**, not just a point fix for
`01B` — it guarantees the corpus-wide uniqueness invariant even if a future
document has a duplicate-numbering shape not covered by the `Annexure` boundary
fix above.

### AEI-WI-T-02's `Reference #2.` — checked, not a bug

`"Reference #2."` (p.196, bold, alone in its block) does get its own chunk with
real (but topically unrelated) body text following it. Checked the source
directly: `"Reference #1."` on the previous line has its citation text **inline
on the same row** (non-bold tail, correctly classified as body); `"Reference #2."`
has no citation text at all — the source PDF itself never filled it in, so the
row is *entirely* bold with nothing to break its all-bold status, making it
heading-shaped by construction. The next real content (`"Name(s) and
qualifications..."`) is an unrelated new section, not `Reference #2`'s missing
citation. Per the locked zero-body rule, a heading followed by real (if
unrelated) body content must open its own chunk — this is the classifier working
correctly against a genuine gap in the source document, not a mis-detection.
Left as-is.

### Verification

- **Uniqueness: 8 duplicate `(doc_id, clause_no)` groups before, 0 after** (corpus-wide
  scan, both artifacts, `clause_no is not None`).
- **Coverage unchanged at the per-PDF level:** QM 1,253/1,253 (0 unaccounted, 9/9
  tables), COMBINED 5,363/5,363 (0 unaccounted, 135/135 tables), corpus sum 6,616
  both before and after. Internal A/B split moved by exactly 1 line inside COMBINED
  (`ANNEXURE – I` itself moved from bucket A, undifferentiated body, to bucket B,
  heading absorbed into the new Annex ancestor) — the total never moved.
- **QM: byte-for-byte unaffected.** Chunk count (83), ancestor-path count (58),
  trailing-absorb count (1), and the full coverage report are identical to the
  pre-fix build. Neither new code path fires anywhere in QM (no `"Annexure"`-spelled
  heading, no duplicate clause number) — confirmed by direct scan, not inferred.
- **Prefixed clause_nos that now exist** (24 total, all in COMBINED, 0 in QM):
  `Annex I/1`, `Annex I/2`, `Annex I/3`, `Annex I/4.1`, `Annex I/4.1.8`,
  `Annex I/4.2`, `Annex I/4.3`, `Annex I/4.3.7`, `Annex I/4.4`, `Annex I/4.4.6`,
  `Annex I/4.5`, `Annex I/4.5.8`, `Annex I/1.1`*, `Annex I/5.1`, `Annex I/5.2`,
  `Annex I/5.3`, `Annex I/1.5`*, `Annex I/5.4`, `Annex I/5.5`, `Annex I/5.6`,
  `Annex I/5.7`, `Annex I/6`, `Annex I/7` (all `AEI-WI-T-05B`), plus `5#2`
  (`AEI-WI-T-01B`). (*`Annex I/1.1` and `Annex I/1.5` are the misclassified-body-line
  defect reported above, not real headings — included here for completeness since
  they do carry the prefix.)
- **Zero empty-text chunks, zero missing `doc_id`, zero bad page ranges** —
  reconfirmed both artifacts after this round.
- No guard failed to hold on real data; no case required dropping a real clause or
  admitting a list-item false positive. The one thing that did surface (the
  `1.1`/`1.5` misclassification) doesn't threaten uniqueness and is reported above
  rather than silently fixed or silently left undocumented.

### Final counts

`quality_manual.json`: 83 chunks (unchanged). `combined_complete_qms.json`: 503
chunks (unchanged — this round renames/re-ancestors, it does not open or close any
chunk).

## Flags for later phases

Things downstream phases (3+) need to know about, that aren't otherwise findable by
reading the code.

**(a) Accepted, deferred defect: `AEI-WI-T-05B`'s `Annex I/1.1` and `Annex I/1.5`
misclassification.** Two body lines inside the `ANNEXURE – I` scope (p.234-235)
coincidentally shape-match as numbered headings and open their own (wrong) chunks,
ancestored to the wrong `1. Purpose` heading. Root cause is a genuine source typo (the
real heading there is `"5. Purpose"`; its sub-clauses were never renumbered from a
copy-pasted template — see the fix-round section above for the full trace). Does not
threaten `clause_no` uniqueness. Not fixed — a clean fix needs a monotonic-numbering
guard (a numbered candidate's top-level segment must not regress within an open
namespace) whose corpus-wide effect wasn't verified as part of this round. If a later
phase surfaces this (e.g. an auditor flags nonsense chunk text under `Annex I/1.1`),
that guard is the fix, and it needs the same corpus-wide grounding pass every other
guard in this file got before shipping.

**(b) `clause_no` is an opaque unique string, not a bare dotted number.** Two
disambiguation conventions exist beyond plain `\d+(\.\d+)*` and `Annex X/N`:
- `Annex X/` prefix for a numbering restart under any ancestor heading, spelled
  "Annex" (`Annex B/1.0`) or "Annexure" (`Annex I/1`) in the source.
- `#2`, `#3`, ... suffix for a genuine in-sequence source-typo duplicate (e.g.
  `AEI-WI-T-01B`'s `5#2`).

  Both are now also documented in `master_contextC.md`. Any downstream code that
  parses, sorts, or pattern-matches `clause_no` (Phase 3 checklist-to-chunk matching,
  Phase 5/6 display) must treat it as an opaque id — regex assuming pure dotted-number
  shape will silently mishandle these ~24 chunks (23 in `AEI-WI-T-05B`, 1 in
  `AEI-WI-T-01B`, corpus-wide as of this build).

**(c) `AEI-WI-T-02`'s `clause_no: null`, `"Reference #2."` chunk — correct, not a
bug.** Checked directly against the source: the citation text for reference #2 was
never filled in in the PDF itself (unlike reference #1, whose citation is inline and
correctly classifies as body). The row is entirely bold with nothing to break that
status, so it's heading-shaped by construction; the real content that follows it is
an unrelated new section, not a missing citation. The classifier is working correctly
against a genuine content gap in the source. No action needed downstream beyond not
being surprised that this chunk's body doesn't match its title.
