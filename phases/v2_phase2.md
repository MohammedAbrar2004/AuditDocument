# Phase 2 — Chunk

Status: **PLANNED.** Grounded against the real Phase 1 artifacts below. No code written
yet, no review round yet — this is the draft for Abrar's first pass, same shape Phase
1's plan started from before its three review rounds.

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
| `4.2.2 External and Internal Issues Affecting the QMS` (real numbered heading) | 79.9 | all-bold | 11.04 | **mid-block** — `b058`, sandwiched between `4.2.1`'s body (before) and `4.2.2`'s own body (after), in the *same native block* |
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

## Open questions for review (flagging, not deciding silently)

**Q1 — DECIDED (Abrar): unnumbered headings can act as ancestors.** A zero-body,
all-bold unnumbered heading that's immediately followed by other headings is an
ancestor, not a dropped line — its heading text goes into `ancestor_path` for the
chunks beneath it, contributing a heading line only, same as any numbered ancestor.
`QUALITY & SAFETY POLICY STATEMENT` (p.7, confirmed its own clean block, all-bold, zero
body) is the concrete case: both `QUALITY POLICY` and `SAFETY POLICY` (p.8) carry it in
`ancestor_path`. "No empty parent chunks" still holds — the ancestor itself emits no
chunk. The p.8 orphan parenthetical `(Applicable for all locations...)` is a different
shape (a stray body-less line with no heading rows following it, not a heading with
children) and stays dropped, per the original call.

**Follow-up this decision surfaces, not yet resolved:** when does an unnumbered
ancestor's scope *close*? Numbered headings close by dot-depth (`4.2` closes when `4.3`
or `4` reopens); unnumbered headings carry no depth number, so nothing mechanical says
where the scope ends. Concretely: `QUALITY & SAFETY POLICY STATEMENT` → `QUALITY
POLICY` (child, has body) → `SAFETY POLICY` (child, has body) → **`Organisational
Quality Objectives`** (p.9, also unnumbered, also has its own body) — is *this* also a
child of the p.7 statement, or does it start a new flat top-level section? Nothing in
the span data (font, size, x0, bold) distinguishes "this heading closes the previous
ancestor's scope" from "this heading extends it" — `Organisational Quality Objectives`
looks exactly as heading-shaped as `QUALITY POLICY` did. Proposed default, pending
confirmation: **an unnumbered ancestor's scope stays open only across the immediately
following run of leaf headings that make sense as siblings under it — closes at the
next zero-body unnumbered heading (which opens as a new sibling ancestor at the same
flat level) or at a numbered heading (root reset).** Under that default, nothing
currently closes the scope between `SAFETY POLICY` and `Organisational Quality
Objectives` (neither is zero-body, neither is numbered) — so the naive version of this
rule would incorrectly nest `Organisational Quality Objectives` under the p.7 statement
too. **Flagging this rather than picking silently** — need either a confirmed rule for
where flat unnumbered scope ends, or confirmation that over-nesting this one case is
acceptable collateral (small blast radius: one extra ancestor-path entry on one
chunk).

**Q2 — table serialization format inside chunk text.** No format is specified anywhere
in `master_contextC.md` or `v2_plan.md` beyond "inline, no separate field." Proposing
` | `-joined cells, one row per line, blank for `None`/empty cells — reasonable for both
BM25 and the embedding model to read as text, but this is an implementation choice, not
a grounded rule. Open to a different serialization if there's a preference (e.g.
markdown-table pipes with a header separator row).

**Q3 — front-matter-before-any-heading fallback.** Not observed in the QM sample (see
grounding item 5) but not yet checked across all 59 `COMBINED` subdocuments either.
Plan: run the check at build time and report any subdocument where a kept table (or any
body content) precedes the first detected heading row; only build the synthetic
front-matter fallback if that actually occurs, rather than adding unused code for a
case that may not exist.

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
  "text": "4 Context of Organization's Quality Management System\n4.2 Needs & Expectations of Interested Parties\n4.2.1 Relevant Interested Parties\n<body text>\n<inline table rows>",
  "page_start": 11,
  "page_end": 11
}
```

- `clause_no` is `null` for unnumbered headings (e.g. `Foreword`), and takes the
  `Annex X/N.N` form inside an Annex scope (e.g. `Annex B/1.0`).
- `ancestor_path` holds heading-only entries (no body) for every level above the leaf,
  root first. Annex ancestors appear with `clause_no: null` and their full heading text
  as `clause_title` (e.g. `"Annex B: Specific Terms of Reference for Training &
  Examination Staff"`).
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
   - `is_all_bold_row`: every non-whitespace span in the row is bold.
   - `is_numbered`: `is_all_bold_row` and matches `^\d+(\.\d+)*\s+` (§4 above).
   - `is_annex`: `is_all_bold_row` and matches `^Annex\s+[A-Z]\b` (§4 above).
   - `is_unnumbered_heading`: `is_all_bold_row`, not numbered, not Annex, **and every
     other row in this row's containing block is also `is_all_bold_row`** (block
     homogeneity — grounding item 1's revised rule; this is what excludes `External
     Issues`/`Internal Issues`-shaped sub-labels).
   - Everything else is body content, accumulated under whichever heading is currently
     open.

4. **Build the tree**, one subdocument at a time:
   - Numbered headings nest by dot-depth under the nearest open numbered heading of
     shallower depth, **within the current Annex scope** (document root if no Annex is
     open). Orphans (skipped levels, skipped siblings) attach to the nearest existing
     ancestor — normal, per `master_contextC.md`'s `6.2 → 6.2.1.1` case.
   - Annex headings are siblings of each other and act as ancestors for the numbered
     scope beneath them.
   - Unnumbered headings **can be ancestors** (Q1, decided): a zero-body unnumbered
     heading immediately followed by more headings becomes an ancestor, contributing
     only its heading line to `ancestor_path` — same "no empty parent chunks" treatment
     as any other ancestor, never a chunk of its own. Scope-closing rule still open
     (see Q1's follow-up above) — default proposed: closes at the next zero-body
     unnumbered heading or at a numbered heading, not yet confirmed.
   - A heading with a body becomes a leaf chunk: ancestor heading lines (own text only,
     no body) + its own heading + its own body. A heading with **no** body and no
     heading rows following it at all (the p.8 orphan parenthetical — a stray bold line
     with nothing structural after it, not an ancestor case) produces no chunk —
     consistent with `master_contextC.md`'s explicit acceptance of this loss, "no empty
     parent chunks."

5. **Attach tables inline.** For every kept table (already stitched, already
   filtered by Phase 1), find the nearest preceding heading row in document order
   (grounding item 5) and append the table's serialized rows (Q2) to that heading's
   accumulated body content, at the point in the body corresponding to the table's own
   page position.

6. **Emit chunks** as described in the artifact schema — `text` assembled from
   ancestor heading lines + own heading + own body + inline tables, `page_start`/
   `page_end` derived from the chunk's own content only.

7. **Verification pass** (see checklist) before declaring the artifact done.

---

## Verification checklist — before Phase 3 starts

(Per `v2_plan.md`'s own gate, expanded with what grounding surfaced.)

- [ ] Zero empty chunks — every emitted chunk has non-empty body content beyond its
      own heading line.
- [ ] Every chunk has a `doc_id` (inherited from its subdocument).
- [ ] Every chunk's `page_start`/`page_end` falls inside the range of its own
      heading/body/table content — never wider than that, never inherited.
- [ ] `QUALITY_MANUAL.pdf`'s chunks reproduce every few-shot example in
      `master_contextC.md`: pp.1–2 signature block as one chunk, pp.3–5 Revision
      History as one chunk, p.6 ToC as one chunk (not parsed as clauses), p.7 Foreword,
      p.8 two policy chunks (`QUALITY POLICY`, `SAFETY POLICY`) each carrying
      `QUALITY & SAFETY POLICY STATEMENT` in `ancestor_path` (Q1, decided), p.9
      numbered-list-is-not-clauses — and confirm whether `Organisational Quality
      Objectives` also picked up that same ancestor or correctly started fresh (Q1's
      open follow-up — report which happened, don't silently pick one), pp.10–15
      numbering gaps (`4.3` missing, `5.1.2` with no `5.1.1`, `6.2.1.1` with no
      `6.2.1`), pp.29–34 Annex B numbering restart (`Annex B/1.0` distinct from root
      `1`), p.36 Annex D **absent as a table** (Phase 1 already discarded it — confirm
      no phantom empty chunk is created for its heading either). **Show the
      disagreements, not just the matches.**
- [ ] `4.2.2 External and Internal Issues Affecting the QMS` chunks as a real leaf
      (numbered, mid-block) while `External Issues` / `Internal Issues` inside its body
      do **not** spawn chunks of their own — the block-homogeneity check (grounding
      item 1) holding in the actual build, not just in this document's description of
      it.
- [ ] Block-homogeneity rule run against the full corpus (both PDFs, all 59 `COMBINED`
      subdocuments) and any mid-block all-bold row reviewed by hand before trusting the
      rule beyond the one case (`b059`) actually checked while planning.
- [ ] `4` and `4.1` (QM p.10, the confirmed glued-block case) never become chunks of
      their own — heading lines only, contributing to `4.1`'s and `4.2.x`'s
      `ancestor_path`.
- [ ] Table-to-chunk attachment spot-checked: p.11 Interested Parties → `4.2.1`, p.14
      Responsibility Matrix → `5.3.2` (per `master_contextC.md`'s named examples).
- [ ] `AEI-QP-T-03B`'s two split subdocuments (AEC checklist, AQB checklist, confirmed
      as two `doc_id`-sharing subdocuments in Phase 1) each chunk independently — no
      cross-contamination between the two halves.
- [ ] Front-matter-before-any-heading check (Q3) run across all 59 `COMBINED`
      subdocuments; report any hits before assuming the fallback is unnecessary.
- [ ] Chunk count and a sample `doc_id` distribution reported for both artifacts — not
      assumed, per the project's standing discipline of reporting actual numbers rather
      than adjusting to hit an expectation.

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
