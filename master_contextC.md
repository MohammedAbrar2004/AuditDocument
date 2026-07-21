# Audit Evidence Mapping — System Context

Permanent reference. Read this before writing any code or any phase plan.

## What this is

An auditor holds a checklist. Each checklist item is a requirement. For each item, the
auditor must find the section of the company's Quality Management System (QMS) that
answers it, and then decide whether the company complies.

Finding that section is the hard part. Ctrl-F fails, because the words never match:

- Checklist says: *"shall establish and maintain a procedure to control documents"*
- QMS says: *"defines the process for control of documents"*

Same requirement. Zero shared distinctive words. This paraphrase gap is why the system
exists.

## What this is NOT

**The auditor decides compliance. The system never infers, scores, or judges
compliance.** It surfaces candidate sections and stops. Human in the loop, always.

## Indexing, not retrieval

Checklist items are fixed and known in advance. There is no user-typed query, ever.

Everything is precomputed at upload time. The UI filters a stored index. **No runtime
queries. No live search.**

---

## The three views

Three independent ranked lists per checklist item. **Never merged into one list.** The
auditor toggles between them.

1. **Keyword** — BM25 over word overlap, rare words weighted higher. A gate marks weak
   hits: a chunk that fails to match at least N rare (high-IDF) terms, or falls below a
   minimum score, is **tagged `above_floor: false` — never dropped.** See "The gate
   tags, it never drops" below.
   *"Keyword" and "BM25" are the same view, not two things.*

2. **Semantic** — every chunk and every checklist item becomes a vector via
   `BAAI/bge-large-en-v1.5`. Cosine similarity ranks them. **This is what catches
   paraphrase** — the reason the project exists.

3. **Both** — RRF fuses the two *rankings*. Each chunk scores `1/(k + rank)` per view,
   summed. **k = 60.** **Ranks only. No score normalization. No alpha weighting. The
   `α·semantic + (1−α)·keyword` approach is explicitly not used.**

**The Both view is a consensus lens, not a superset.** RRF's harmonic sum means one bad
rank caps a chunk regardless of the other signal — a chunk at keyword-rank-6 /
semantic-rank-661 lands at fused ~47, not top-10. Single-signal paraphrase catches
systematically land at fused rank ~30–50. **This is why all three views ship. Shipping
only the fused view would quietly defeat the system's purpose.**

## The gate tags, it never drops

The BM25 floor (`min_high_idf_terms`, `min_score`) marks each chunk `above_floor:
true | false`. **It does not remove anything from the ranked list.**

Filtering is the slider's job, at view time, in the UI. A borderline hit the auditor
could have recognized must never be deleted before they see it. Nothing is dropped
anywhere in the pipeline on the basis of a score.

## The slider

Per-view **raw score**. Native units per view (BM25 score / cosine / RRF score).
Switching views changes the scale, and that is accepted — auditors are experts who
prefer honesty over cosmetic consistency.

It is a **relative ranking dial. Not a probability. Never labeled as a percentage.**

---

## Locked decisions

### Clean first, then chunk

Junk in the stream corrupts chunk boundaries. Nothing in cleaning needs clause context.

**The header is read before it is stripped.** The header block identifies the
subdocument (`doc_id`, name, revision, page span). Read → capture as metadata → strip
from text. One operation, not two.

**Footers are pattern-matched and dropped.** Nothing to capture.

### Per-span metadata survives to Phase 2

Extraction pulls spans from PyMuPDF and keeps **`{text, page, font_size, bold, bbox}`**
for every span. All five fields. Carried from extraction through to chunking.

Font is how unnumbered headings ("QUALITY POLICY", "Foreword") are detected. Page is how
page ranges are derived. Neither is recoverable later if dropped.

### Page numbers — one canonical system

There are two page numbering systems in play and they must never be confused:

| | Meaning | Where it lives |
|---|---|---|
| **PDF page** | Absolute position in the uploaded file. Quality Manual's page 5 is PDF page 5; `AEI-QP-T-07`'s page 5 is PDF page 134. | **Canonical.** Every span, every chunk, every API response, the UI. |
| **Document-relative page** | What the header says — `Page 5 of 36`. Restarts at 1 in every subdocument. | **Subdocument metadata only.** Never on a chunk. |

**Chunks carry PDF page numbers.** `page_start` and `page_end` mean PDF pages, always.
This is what "View in PDF" opens to, so it must be the one the file actually uses.

The document-relative span is captured once as subdocument metadata (from the header)
and used for nothing else.

### Every chunk carries its subdocument

`COMBINED_Complete_QMS.pdf` holds 59 subdocuments (confirmed, Phase 1 build — computed
at build time, never hardcoded). A chunk is meaningless without knowing which one it
came from.

**Every chunk carries `doc_id` and `doc_name`** (e.g. `AEI-QP-T-07`, "CONDUCT OF PCN
QUALIFICATION EXAMINATIONS"), captured from the header block during segmentation. The
UI displays it. It is not optional metadata — it is part of the chunk's identity.

### Ancestor-prefix leaf chunks

Only leaves become chunks. Ancestors contribute **heading lines only**.

- The leaf contributes its own heading **and** its body.
- No rollup. No summarizing.
- **No empty parent chunks.** A heading whose body all went to its children never
  becomes a chunk of its own.

### Orphans attach to the nearest existing ancestor

Numbering skips levels and skips siblings. Both are normal and must not break the tree.
An orphan attaches to its nearest ancestor that actually exists. Missing levels simply
do not appear.

### Tables are inline content

- No separate `evidence_tables` field. A table is part of its chunk's text.
- **Stitched across pages** — a table spanning pp. 3–5 is one table, not three.
- **Titled by any heading above it.** Real titles are "Revision History",
  "Responsibility Matrix", "Organisational Quality Objectives". Do not look for lines
  starting with `Table X` — that pattern does not occur here.
- Some tables have **no title at all**. Those just live inside their clause's chunk.

### Page ranges are derived, never inherited

A chunk's range is `min(PDF pages of its own spans)` to `max(PDF pages of its own
spans)`. Never inherited from a parent, a block, or a neighbor.

**Both directions are real and must both work:**
- One page can hold multiple chunks (p. 8 has QUALITY POLICY *and* SAFETY POLICY).
- One chunk can span multiple pages (Revision History runs pp. 3–5).

### Content-shaped blocks

Blocks are shaped like content — by headings and structure. Never shaped by where the
cleaner happened to cut something out.

---

## What gets removed

- Page headers (after reading them for subdocument metadata)
- Page footers (`Page N of M`)
- **empty tables** — entirely empty, OR rightmost column blank on every data row (header
  row excluded from that check)
- Diagram-only pages

**Every removal goes into a removal log in the Phase 1 artifact.** What was removed,
which page, which rule fired.

## Tables: kept or discarded by content alone

**No protected table types. No named exceptions.** A table is kept or discarded solely
by the empty-table rule above — never by what it's called or what shape it is. A
populated "Revision History" or "Revision Control" table is kept because it has data
rows, not because of its name. The identical table with only a header and zero data
rows is discarded because it's empty — same test, same table type, opposite verdict,
because the content differs. Do not write dedicated logic to protect any table by
identity.

## ⚠ Any rule that writes to the removal log needs grounding + sign-off first

Not just the empty-table rule. **Every rule that can remove or flag real content —
empty tables, diagram-only pages, anything added later — must be grounded against the
full corpus and reported before it's trusted.** Show what it would remove or flag. Wait
for sign-off. A rule that looks obviously safe from a couple of hand-picked examples is
exactly the one that needs this most.

---

## Few-shot examples — from the real Quality Manual

`AEI-QM-T-01`, "QUALITY MANUAL", Revision 23, 36 pages. It is the first 36 pages of
`COMBINED_Complete_QMS.pdf`. **This is the reference for what correct output looks
like.** These are real pages, walked page by page.

*Page numbers below are Quality Manual pages. Since the Quality Manual is the first 36
pages of COMBINED, they happen to equal PDF pages here. For every other subdocument they
will not — chunks always carry PDF pages.*

**Page header (every page) — read, capture, strip**
DOCUMENT NAME | QUALITY MANUAL
DOCUMENT NO.  | AEI-QM-T-01 | REVISION | 23 | REVISED DATE | 09-04-2025
ISSUE DATE    | 07-12-2009  | PAGE NO. | Page 1 of 36
→ Metadata: `doc_id=AEI-QM-T-01`, `doc_name=QUALITY MANUAL`, `revision=23`, page span.
→ Stripped from all chunk text. **Never appears in a chunk.**

**Page footer** — `Page N of 36` → dropped.

**pp. 1–2 — signature block table — KEEP**
Title "Altair Engineering Inspections Pte Ltd", spans 2 pages, columns
`[Revision | Prepared by | Reviewed by | Approved by]`. Continuation rows on p. 2 carry
real revision numbers (17–23).
→ **ONE chunk spanning pp. 1–2**: title + address line + the full table.
→ **Multi-page table stitching case.**

**pp. 3–5 — "Revision History" table — KEEP**
Title is loose prose above the table. Spans 3 pages. Columns
`[Revision | Date | Pages | Summary of change]`, populated with real revision rows.
**Kept because it has data rows — not because it's named "Revision History."** A
same-shaped table with a header row and zero data rows discards, regardless of name
(see p. 36 below).
→ **ONE chunk spanning pp. 3–5**, title bound to body.
→ **The canonical multi-page-table + non-`Table X` title case.**

**p. 6 — Table of Contents**
Contains numbered lines (`1 Scope`, `4.2 Understanding the needs…`) that **are not
clauses.** Must not be chunked as clauses.
→ **One chunk**, ToC and everything under it.
→ **TRAP:** the ToC lists `4.1, 4.2, 4.4` (no 4.3) and omits `7.3`, which exists in the
body. **The ToC is not a reliable structure source. Do not build the tree from it.**

**p. 7 — "Foreword"**
Unnumbered heading. Real content.
→ **One chunk**, heading + body. Detected by **font**, not by number.
→ Content below the signature line (`Sincerely`, signature image, name/title) can be
excluded.

**p. 8 — TWO chunks on ONE page**
(Applicable for all locations administered by AEI)   ← orphan line, low stakes
QUALITY POLICY  + body     → chunk 1
SAFETY POLICY   + body     → chunk 2
→ Both unnumbered. Both detected by font. Both real evidence.
→ The orphan parenthetical ideally belongs to neither; landing in the previous or next
chunk is acceptable and **not worth engineering around**.

**p. 9 — "Organisational Quality Objectives"**
Unnumbered heading + a numbered list (1–4). The `1.` `2.` `3.` `4.` are **enumerated
list items, not clauses.** Do not open chunks on them.
→ **One chunk.**

**pp. 10–12 — numbered clauses begin, and the numbering lies**
1   SCOPE                          → chunk: [1 hdg][1 body]
2   REFERENCES                     → chunk: [2 hdg][2 body]
3   ABBREVIATIONS AND DEFINITIONS  → chunk: [3 hdg][3 body]
4   Context of Organization's QMS  → ANCESTOR — heading line only, never a chunk
4.1  Organization and its context
→ chunk: [4 hdg][4.1 hdg][4.1 body]
4.2  Needs & Expectations        → ANCESTOR — heading line only, never a chunk
4.2.1  Relevant Interested Parties
→ chunk: [4 hdg][4.2 hdg][4.2.1 hdg][4.2.1 body + its untitled table inline]
4.2.2  External and Internal Issues
→ chunk: [4 hdg][4.2 hdg][4.2.2 hdg][4.2.2 body]
4.3  ** DOES NOT EXIST **        → skipped sibling. Normal. Must not break the tree.
4.4  Quality management system
→ chunk: [4 hdg][4.4 hdg][4.4 body]
→ **`4` and `4.2` NEVER become chunks of their own.** They contribute heading lines
only.
→ **4.2.1 has a table with no title.** It just lives inside 4.2.1's chunk, inline.

**p. 12 — missing intermediate level**
5.1    Leadership                  ← ancestor heading
5.1.2  Leadership and Commitment   ← no 5.1.1 exists
→ `5.1.2` attaches to `5.1`. Chunk: `[5 hdg][5.1 hdg][5.1.2 hdg][5.1.2 body]`. Normal.

**p. 15 — SKIPPED LEVEL (the harder case)**
6.2      Quality Objectives and Planning   ← ancestor heading
6.2.1.1  AEI has established measurable…   ← no 6.2.1 exists ANYWHERE
→ `6.2.1.1` attaches to its **nearest existing ancestor**, `6.2`.
→ Chunk: `[6 hdg][6.2 hdg][6.2.1.1 hdg][6.2.1.1 body]`. **The `6.2.1` level simply does
not appear.**

**p. 14 — heading + table = one chunk**
5.3.2  Responsibility Matrix – Examination Services
[table: Role/Designation | Responsibilities | Authority]
→ **One chunk:** `[5 hdg][5.3 hdg][5.3.2 hdg][5.3.2 body + table inline]`.

**p. 36 — Annex D — DISCARD**
[NDT Method | Number of Candidates per batch | Remarks]
Remarks blank on every row, every data row — rightmost column blank on every data row,
so the empty-table rule fires. **Confirmed discard, by explicit decision.** No exception
carved out for this table; same test as pp. 3–5 above, opposite result, because this
one has no data in its last column.

**pp. 29–34 — Annex B, restarting numbering**
Annex B: Specific Terms of Reference for Training & Examination Staff
1.0  CEO
2.0  COO
3.0  PCN COORDINATOR
…
12.0 QUALITY COORDINATOR
→ Numbering restarts at 1 inside the Annex, colliding with the document's top-level
`1 SCOPE`.
→ **The ancestor prefix already solves this.** Annex B is the ancestor:
`[Annex B hdg][1.0 hdg][1.0 body]` → clause id `Annex B/1.0`. Document-level `1 SCOPE`
has no Annex ancestor → id stays `1`. **Unique, no collision, no special rule needed.**

**Uniqueness is enforced two other ways, confirmed real in the built corpus (Phase 2
build report, fix round 2026-07-21b) — not hypothetical, not special-cased per
document:**
- **`Annex X/` prefix for a numbering restart under a heading that isn't literally
  spelled "Annex"** — e.g. `AEI-WI-T-05B`'s `ANNEXURE – I` restarts a mini-procedure at
  `1`, producing `Annex I/1`, `Annex I/2`, etc., distinct from the document's own plain
  `1`, `2`. Same mechanism as `Annex B/1.0` above, just a different spelling of the
  boundary heading.
- **`#2`, `#3`, ... suffix for a genuine in-sequence duplicate** — a real source typo
  where the same number is reused rather than incremented (e.g. `AEI-WI-T-01B` reuses
  `5` for both "Terms and Definitions" and "Qualification Requirement"; the first
  keeps `5`, the second becomes `5#2`). Not a restart, not a new namespace — there is no
  more-correct number to synthesize, so the id is disambiguated directly.

**`clause_no` is an opaque unique string, not a bare dotted number.** Any phase
matching, sorting, or displaying by `clause_no` must treat it as an id, not parse it
as pure `\d+(\.\d+)*` — it may carry an `Annex X/` prefix or a `#N` suffix.

---

## The checklists

Two checklists. The auditor picks one from a dropdown. Every item in it gets three
ranked lists.

| File | Items |
|---|---|
| `AUDIT_CHECKLIST_AQB.pdf` | ~159 |
| `AUDIT_CHECKLIST_AEC.pdf` | ~52 |

**The checklists have the same structural disease as the QMS.** Parent headings and leaf
items look alike. IDs go up to four levels (`4.2.1.3`). Numbering has gaps.
4.2      Quality Management System   ← HEADING, not an item
4.2.1    QMS - General               ← HEADING, not an item
4.2.1.1  The purpose of the QMS…     ← ITEM
4.2.1.2  …                           ← ITEM

**Only leaf items are checklist items.** A heading is a section title — it has no
requirement text of its own and must never enter the dropdown. If headings are parsed as
items, the dropdown fills with junk and every one of them gets a meaningless ranked list.

**This is not a one-liner. Ground it against the real checklist PDFs before writing the
parser.** Report: how many headings, how many leaf items, and every case where the
heading-vs-item call was ambiguous. Do not assume the counts above are exact — verify
them and report what you actually find.

---

## Where to look for what

**`docs/`** — the source PDFs.

| File | What it is |
|---|---|
| `COMBINED_Complete_QMS.pdf` | 275 pages, 59 subdocuments (confirmed). **The main corpus.** |
| `QUALITY_MANUAL.pdf` | `AEI-QM-T-01`, 36 pages. Also the first 36 pages of COMBINED. **The reference document for every chunking example above.** |
| `AUDIT_CHECKLIST_AQB.pdf` | ~159 items |
| `AUDIT_CHECKLIST_AEC.pdf` | ~52 items |

**`phases/`** — one markdown file per phase. **Naming convention: `v2_phaseN.md`.**
Each holds that phase's plan, the decisions made, and the build report. Written before
the code. Updated if the implementation deviates.

**`data/artifacts/phaseN/`** — one JSON per source document, named by slug. Phase N reads
Phase N−1's artifact. **Never re-parse the PDF.**

**`backend/`** — all code. **`frontend/`** — already built.

## Tech stack

- **Backend:** FastAPI, port 8000
- **Frontend:** Vite + React + TypeScript, port 5173
- **PDF text + font + geometry:** PyMuPDF (fitz)
- **PDF tables:** pdfplumber
- **Embeddings:** `BAAI/bge-large-en-v1.5`
- **Keyword:** BM25
- **Python:** 3.11, conda environment named **`audit`**
- **GPU:** RTX 4050, cu132 torch, CUDA confirmed working

The `audit` env may already have dependencies. **Install anything new freely — no need
to be stingy.**

BGE's 512-token limit is not a problem. Chunks are small by design. Do not swap models.

## No eval phase

There is no eval phase. It is out of scope.

---

## Working discipline

1. **Ground every rule in the REAL files before proposing it.** Open the PDF. Count the
   rows. A rule proposed from intuition is not a rule.
2. **Show the DISAGREEMENT cases, not just the agreements.** A list of examples where
   the rule works proves nothing. Show where it doesn't.
3. **Never reconcile silently.** If numbers differ from an expectation, show the
   differing rows and say why. Do not adjust the method to hit the number.
4. **Nothing is dropped on the basis of a score.** Weak hits get tagged, not deleted.