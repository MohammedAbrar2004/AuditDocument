# Plan — six phases

Each phase reads the previous phase's artifact. **Never re-parse the PDF after Phase 1.**
Each phase's plan and build report lives in `phases/v2_phaseN.md`.

Read `master_contextC.md` first. Every rule referenced below is defined there.

---

## Phase 1 — Extract, segment, clean

**Status: BUILT.** Full plan, review rounds, and build report: `phases/v2_phase1.md`.

**Carries the most weight. Everything downstream depends on it.**

**Does:** turns a PDF into clean, content-shaped blocks with full per-span metadata.

**How:**
1. **Extract with PyMuPDF (fitz).** Every span keeps `{text, page, font_size, bold,
   bbox}`. All five fields. Nothing dropped. `page` is the **PDF page** — absolute
   position in the file.
2. **Extract tables with pdfplumber.** Stitch tables that continue across pages into one.
3. **Segment subdocuments from header blocks.** Read the header → capture `doc_id`,
   `doc_name`, `revision`, PDF page span, and the document-relative page span → then
   strip it. Read before strip, one operation. A new header block with a new `doc_id`
   starts a new subdocument. ~57 expected in `COMBINED_Complete_QMS.pdf`.
4. **Strip footers** by pattern (`Page N of M`).
5. **Remove junk:** empty tables (fully empty, or blank-last-column form replicas) and
   diagram-only pages. **Every removal is logged** — page, rule, what was removed.
6. **Assemble content-shaped blocks.** Shaped by headings and structure, never by where
   the cleaner cut.

**Artifact:** `data/artifacts/phase1/<doc-slug>.json` — one file per source document.
Subdocuments with their metadata, their blocks with per-span data, tables, and the
removal log.

**Before Phase 2 starts:**
- The empty-table rule is **grounded against every table in the corpus and reported.**
  Sign-off required on what it deletes. The Annex D case (p. 36) is checked explicitly.
- No span has lost `page`, `font_size`, or `bold`.
- Header text appears in zero blocks.
- Subdocument count and `doc_id` list match the real PDF — report what you actually
  find, don't assume ~57.
- **The artifact is verified before Phase 2 runs.**

---

## Phase 2 — Chunk

**Status: BUILT.** Full plan, review rounds, fix rounds, and build report:
phases/v2_phase2.md.

**Does:** turns Phase 1's blocks into the final chunk set.

**How:**
- Build the heading tree. Numbered headings by number; unnumbered headings by **font**.
  Enumerated list items are not clauses. The ToC is not a structure source.
- **Ancestor-prefix leaf chunks.** Ancestors contribute heading lines only. The leaf
  contributes its own heading and its body. No rollup. **No empty parent chunks.**
- **Orphans attach to the nearest existing ancestor.** Skipped levels and skipped
  siblings are normal.
- **Tables inline** as chunk content. No separate field. Titled by any heading above.
- **Page ranges derived** per chunk from its own spans, in **PDF pages**. Never
  inherited.
- Annex headings act as ancestors, which makes `Annex B/1.0` distinct from `1`.

**Artifact:** `data/artifacts/phase2/<doc-slug>.json` — chunks with:

| Field | |
|---|---|
| `chunk_id` | unique |
| `doc_id` | e.g. `AEI-QP-T-07` — which subdocument this came from |
| `doc_name` | e.g. "CONDUCT OF PCN QUALIFICATION EXAMINATIONS" |
| `clause_no` | e.g. `4.2.1`, `Annex B/1.0`, or null for unnumbered |
| `clause_title` | e.g. "Relevant Interested Parties" |
| `ancestor_path` | the heading chain above this leaf |
| `text` | ancestor headings + own heading + body + any tables, inline |
| `page_start`, `page_end` | **PDF pages**, derived from this chunk's own spans |

**Before Phase 3 starts:**
- Zero empty chunks.
- Every chunk has a `doc_id`.
- Every chunk's page range is inside the range of its own spans.
- The Quality Manual's chunks match the few-shot examples in `master_contextC.md`.
  **Show the disagreements, not just the matches.**

---

## Phase 3 — Embed + index

**Status: BUILT.** Full plan, grounding pass, and build report:
`phases/v2_phase3.md`.

**Does:** parses the checklists, then builds both search structures.

**How:**

**Checklist parsing comes first, and it is real work — not a one-liner.**
- Only **leaf items** are checklist items. Parent headings are section titles with no
  requirement text and must never enter the dropdown.
- **Ground this against the real checklist PDFs before writing the parser.** Report how
  many headings, how many leaf items, and every ambiguous heading-vs-item call.
- Do not assume the ~159 / ~52 counts. Verify and report what you find. **If your count
  differs, show the differing rows and say why — do not adjust the parser to hit the
  expected number.**

**Then:**
- Embed every chunk and every checklist item with `BAAI/bge-m3` on GPU.
- Build the BM25 index over chunk text.

**Artifact:** `data/artifacts/phase3/` — parsed checklist items, chunk vectors, item
vectors, BM25 index.

**Before Phase 4 starts:**
- Chunks in = vectors out.
- Checklist item counts reported and signed off — headings excluded, and the exclusion
  list shown.

---

## Phase 4 — Rank

**Does:** precomputes the three ranked lists per checklist item.

**How:**
- **Keyword:** BM25 score every chunk. Apply the gate (min high-IDF terms + min score)
  and **tag `above_floor: true | false`. Do not drop.** The slider filters at view time.
- **Semantic:** cosine similarity, descending.
- **Both:** RRF on **ranks only**, `k=60`. No score normalization. No alpha.
- **Full list per view, never truncated.** Nothing is dropped on the basis of a score
  anywhere in this phase.

**Artifact:** `data/artifacts/phase4/` — three ranked lists per checklist item, each
entry with `chunk_id`, rank, and raw score in native units. Keyword entries also carry
`above_floor`.

**Before Phase 5 starts:**
- All three lists exist for every item.
- RRF uses ranks only.
- No list is truncated and no chunk was dropped for scoring low.

---

## Phase 5 — API

**Does:** serves the stored index. **No computation at request time.**

Endpoints to list checklists, list items, and return an item's three ranked lists —
each entry with chunk text, `doc_id`, `doc_name`, `clause_no`, PDF page range, raw
score, and (for keyword) `above_floor`.

**Before Phase 6 starts:** every endpoint reads only from `data/artifacts/`.

---

## Phase 6 — UI integration

**Does:** wires the existing frontend to the API.

- View toggle: Keyword / Semantic / Both.
- Per-view **raw-score** slider, native units, data-driven bounds. **Never a
  percentage.**
- Each result shows its **`doc_id` and clause** — an auditor must know which of ~57
  subdocuments a hit came from.
- **Visible copy** stating that Both is a **consensus** lens, not a superset — an
  auditor treating Both as ≥ either alone will systematically miss single-signal
  paraphrase catches.
- Frontend needs small edits: the chunk shape has `doc_id`, an ancestor path, and no
  separate tables field.

**Done when:** an auditor can pick an item, switch views, drag the slider, and open the
PDF at a page that is actually inside the chunk's own range.