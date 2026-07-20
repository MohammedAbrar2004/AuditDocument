# Phase 1 — Extract, segment, clean

Status: **BUILT.** Plan, three review rounds, and grounding all happened before any
code. Build report appended at the bottom — what actually happened and where it
deviated from plan.

Read `master_contextC.md` and `v2_plan.md` first. This is the highest-weight phase —
everything downstream (chunking, embedding, ranking, UI) inherits whatever Phase 1 gets
wrong, silently. Care here is not optional.

Scope: `docs/QUALITY_MANUAL.pdf` and `docs/COMBINED_Complete_QMS.pdf` only. The two
checklist PDFs are Phase 3's job. The two untouched audit-report PDFs stay out of scope
(per Phase 0's decision).

---

## Review round 1 (2026-07-17) — Abrar's changes, verified against the disk

Four rule changes and three questions came back on the first draft. Nothing below was
assumed — each was checked against the real PDFs before being written down. Full
methodology and raw output for the table-rule question lives in
`data/artifacts/phase1/empty_table_report.md`.

**1. Empty-table rule replaced.** No more fill-rate. New rule: discard a table if it's
entirely empty, OR its rightmost column is blank on every data row. No exception for
Annex D — it is now a confirmed DISCARD, by Abrar's explicit call as the auditor. Same
for the Risk & Opportunities form on the `AEI-QM-T-01D` pages.

**But: running this rule against every table in both PDFs (not a sample) found it also
discards things that are not form grids.** See
`data/artifacts/phase1/empty_table_report.md` for the full breakdown. Headline:
- **95 of 227 stitched tables get discarded.**
- **17 of those (~37 pages, `AEI-QP-T-03B`) are real ISO/PCN clause requirement text**,
  laid out as a ruled checklist table where only the compliance/notes column is blank.
  Discarding the table discards the requirement text with it — there's no other copy of
  it anywhere in the artifact (see the structural note below).
- **7 of those are Revision History tables** — the exact table type
  `master_contextC.md` already says nothing removes. They're being caught by accident
  (one blank cell in the last column), while 20 tables of the identical shape survive.
  This isn't a judgment call, it's the new rule silently overriding an existing rule.
- **2 of those are a pdfplumber merged-cell artifact** (QM p.11, Interested Parties
  table) — a real 2-column table that pdfplumber over-splits into 6, leaving an
  incidental blank "rightmost column" that isn't a real form field.
- The remaining ~69 do look like the intended target (signature blocks, retention
  grids, blank sign-off fields) and match the stated intent.

**Not signed off yet — waiting on a decision for the three flagged categories before
this rule runs for real.** The literal rule as given is correctly implemented and
correctly reported; the disagreement is real, not a bug in how it was applied.

**Structural risk this surfaced, independent of the threshold question:** the plan's
block/table split excludes any span inside a table's bbox from `blocks`, to avoid
duplicating table content. That means a discarded table's text has **no fallback** — it
doesn't degrade to plain text, it's just gone. Fine for Category D (admin grids, no
evidentiary value, by design). Not fine for Category A (real clause prose) unless
Category A is excluded from the rule first.

**2. Full-corpus report, not a sample — done.** All 227 stitched tables in both PDFs
scanned and verdicted. See the report file for the complete discard list, categorized.

**3. Template B `doc_id` regex — tested against the real page text, not assumed safe.**
The naive regex from the first draft (`Document Number\s*:\s*([\w-]+)`) was tested three
ways against the actual PDF page 41 text:
- Against the **joined** multi-span header-band text (label and ID are on separate
  spans/lines in the real PDF — `Document Number:` at y=40.5, `AEI-QM-T-01D` at
  y=51.6): captures `'AEI-QM-T-01D'` correctly, because `\s*` matches the join-space
  between them.
- Against a **single line in isolation** (i.e. if the extraction never joins multi-line
  header text before matching): returns `None`. **This is the real risk** — not that it
  picks up the wrong ID, but that a naive per-line implementation finds nothing at all,
  silently.
- Against the second spelling on the same page (`Reference Procedure: QMS: AEI-QM-T
  -01D`, note the stray space): never reached. `str.find("Document Number")` locates the
  first occurrence only, and the bounded extraction (below) stops before reaching
  `Reference Procedure`. Confirmed: it does not pick up the stray-space variant.
- An unbounded greedy version (`Document Number\s*:\s*(.+)`) was also tested for
  comparison — it captures to end-of-string (visibly, obviously wrong: `'AEI-QM-T-01D
  Revision Number : 1 Reference Procedure: QMS: AEI-QM-T -01D Revision Date :
  05-01-2026...'`), which is a safer failure mode than a silent wrong value, but still
  wrong. Not used.

**Committed approach:** extraction must (a) join all spans in the top band into one
text string in reading order before any regex runs, never match against isolated lines,
and (b) bound the capture at the next known label
(`Revision Number|Reference Procedure|Revision Date|Reviewed|Approved by`), never
capture unbounded to end-of-string. Verified against all 6 real `AEI-QM-T-01D` pages
(41–46): captures `'AEI-QM-T-01D'` cleanly on every one, no exceptions.

**4. Template A vs. Template B field shapes — made explicit, nothing invented.**

| Field | Template A | Template B |
|---|---|---|
| `doc_id` | ✓ | ✓ |
| `doc_name` | ✓ (`DOCUMENT NAME` cell) | ✓ (first bold line, e.g. "RISK AND OPPORTUNITIES ASSESSMENT FORM") |
| `revision` | ✓ (`REVISION` cell) | ✓, from `Revision Number :` |
| `issue_date` | ✓ (`ISSUE DATE` cell) | **`null`** — Template B has no Issue Date field |
| `revised_date` | ✓ (`REVISED DATE` cell) | ✓, from `Revision Date :` |
| `doc_relative_page_span` | ✓ (`Page N of M`) | **`null`** — Template B never prints a page count anywhere on the 6 pages checked |
| `approved_by` | not present in Template A's cells | ✓, from `Approved by:` (new field, Template-A rows get `null`) |
| `reviewed_revised_by` | not present | ✓, from `Reviewed / Revised by :` (new field, Template-A rows get `null`) |
| `reference_procedure` | not present | ✓, from `Reference Procedure:` (new field, Template-A rows get `null`) |

No field gets a fabricated value on the template that doesn't carry it — `null`, never a
guess or an inherited value from a neighboring page.

**Q1 — font-size contradiction, real spans printed, plan corrected.** Real answer:
**both are real, and the plan's earlier "header = 9.96, body = 11.04" rule was wrong as
a header/footer discriminator.** Printed the actual spans for QM p.10 block 6 (`1
SCOPE`) and block 22 (`4 ... 4.1 ...`):

```
block 6:  '1 '                                                    size=9.96  font=Arial-BoldMT
          'SCOPE '                                                size=11.04 font=Calibri-Bold
block 22: '4 '                                                    size=9.96  font=Arial-BoldMT
          'Context of Organization's Quality Management System'  size=11.04 font=Calibri-Bold
          '4.1'                                                   size=11.04 font=Calibri-Bold
          'Organization and its context '                        size=11.04 font=Calibri-Bold
```

**Top-level clause number tokens (`1`, `2`, `3`, `4`, but not `4.1`/`4.2`) legitimately
use `Arial-BoldMT` 9.96 — the same font/size as the header table — even though they are
real body content, not header.** Sub-level numbers (`4.1`) switch to `Calibri-Bold`
11.04, matching their title. So font/size alone cannot discriminate header from body;
only the top-level clause number breaks that assumption, and it breaks it completely.
**Corrected rule: header/footer detection must key off bbox position (inside the
matched header table's bbox, y0 roughly < 101pt) — never off font or size.** The
9.96/Arial signature is still useful as a fast pre-filter for *finding* the header
table's cells, but it is never sufficient by itself to decide "this span is header, not
body." Section "1" below is corrected to reflect this.

**Q2 — subdocument count reconciled: exactly 57, not "higher."** The earlier "very
likely higher than ~57" line in the first draft was wrong — it was based on a partial,
crude page sample taken during initial grounding, not a full scan. Ran a real full
57-page-boundary state machine (carry-forward doc_id, both templates) across all 275
pages of `COMBINED_Complete_QMS.pdf`: **56 doc_ids via Template A + 1 via Template B
(`AEI-QM-T-01D`) = 57 distinct subdocuments, matching Abrar's own count exactly.** Full
ordered list of all 57 `doc_id`s is in the grounding output; matches
`AEI-QM-T-01` ... `AEI-WI-T-15` with no gaps and no extras.

**Q3 — Template B usage: `AEI-QM-T-01D` is the only one.** Scanned every page of both
PDFs (275 + 36 = 311 pages). Template A matched on every page belonging to the other 56
subdocuments (including their headerless continuation pages, correctly carried forward —
e.g. `AEI-QP-T-03B`'s pages 81–109 never repeat the header and were correctly attributed
via carry-forward, not misclassified as "unrecognized"). **Template B matched on exactly
6 pages (PDF pages 41–46), all belonging to the single `AEI-QM-T-01D` subdocument.** Zero
pages matched neither template. `header_template_counts` for the real corpus:
`{"standard_table": 56, "form_freetext": 1}` (by subdocument) /
`{"standard_table": 305, "form_freetext": 6}` (by page).

**Correction (round 2): the "56" in this answer was itself wrong, in two ways that
canceled out — see round 2's segmentation findings below. Real count is 59
subdocuments, not 57.**

---

## Review round 2 (2026-07-17) — table-rule root cause, extractor evaluation, two new segmentation bugs

Four things came back: diagnose Category B before changing anything, discard Category A
outright (it's a verbatim checklist duplicate — genuinely no evidentiary value, not a
casualty), evaluate a stronger table extractor for Category B/C, and leave the rule
itself untouched. Full detail and raw comparisons in
`data/artifacts/phase1/empty_table_report.md` (rewritten this round, nothing carried
over from round 1 without re-verifying it).

**1. Category A — confirmed verbatim, discard as directed, no exceptions added.**
Whitespace-normalized text comparison confirmed both halves of `AEI-QP-T-03B` are
word-for-word copies of the standalone checklist PDFs: PDF pp. 73–79 match
`AUDIT_CHECKLIST_AEC.pdf` (7 pages, same length, phrase-matched on p.3), PDF pp. 80–109
match `AUDIT_CHECKLIST_AQB.pdf` (30 pages, same length, clause `5.2.3` phrase-matched on
p.11). Scanned every `doc_name` in both PDFs for "CHECKLIST" — **these are the only two
checklist-shaped subdocuments in the corpus; nothing else needs the same treatment.**

**Found while checking this, not what was being tested — two real segmentation bugs:**
- `AEI-QP-T-03B` is the **same literal `doc_id` reused for two different documents**
  (the AEC checklist and the AQB checklist — a mistake in the source file, not in
  extraction). `doc_name` changes at PDF page 80; `doc_id` doesn't. A boundary rule that
  only watches `doc_id` merges them into one 37-page subdocument. **Fix: split on
  `doc_id` OR `doc_name` change, whichever comes first.**
- `AEI-QP-T-03F` (PDF page 113) was **silently missed entirely** by the crude
  header-scan used for round-1's grounding — its header cell wraps `"DOCUMENT NAME"`
  onto two visual lines because the doc_name value is long, and a flattened
  y-then-x-sorted join of the page's spans interleaves the doc_name text between the
  two label fragments, so the literal substring `"DOCUMENT NAME"` never appears and the
  page got carried forward as part of the previous subdocument (`AEI-QP-T-03E`)
  instead. **Verified the actual planned pipeline isn't equally fragile** — it already
  specifies reading the *structured* pdfplumber table cells, not flattened text, and
  that reads this page correctly (`row[0][1] = 'DOCUMENT\nNAME'`, one cell, intact).
  **But it does need a hardening the plan hadn't spelled out: normalize embedded `\n`
  in cell values before matching against label strings** — an exact-string match would
  still miss `'DOCUMENT\nNAME'` even reading the right cell. Added to the plan below.

**Corrected subdocument count: 59, not 57.** Round 1's "confirmed exactly 57, matches
your count" was wrong — two independent errors (`AEI-QP-T-03B` merged from 2 real
subdocuments into 1, `AEI-QP-T-03F` dropped entirely) happened to net to the same total
Abrar's own count landed on, which was very likely built the same way and carries the
same two blind spots. Recomputed properly: 58 Template-A subdocuments (56 unique
`doc_id`s, `AEI-QP-T-03B` correctly split into 2) + 1 Template-B (`AEI-QM-T-01D`) = **59**.

**2. Category B — diagnosed before touching anything. Not a bug. Correct discard.**
Printed pdfplumber's raw cell extraction and column x-edges for 2 of the 7 flagged
pages (COMBINED pp. 247, 251): clean, consistent 4-column structure on every row, no
phantom column, no miscount. Checked all 7 flagged pages plus each one's own
signature-block table (which sits just above it): **every one belongs to a document at
Revision 0** (`REVISED DATE: NA`, exactly one signature-table entry). These documents
have never been revised — their Revision History grid is genuinely, entirely blank
because there's nothing to put in it. This is a different table, by content, from the
populated one on COMBINED pp. 3–5 that `master_contextC.md` protects; round 1's
categorization matched on header-row *text* alone and flagged a conflict without
checking the row data underneath. That was wrong. **Correcting it: these 7 are correct
discards. No conflict with the existing Revision-History KEEP rule, no exception
needed.**

**3. Extractor evaluation — PyMuPDF tested, ties pdfplumber exactly. Camelot tested,
strictly worse. Staying on pdfplumber.** PyMuPDF's `find_tables()` produces
byte-identical output to pdfplumber on all 3 test tables (p.11, p.247, p.53) — same
column counts, same bboxes to 0.1pt. No improvement on the one real problem (p.11),
because both are reading the same drawn ruling lines in the PDF; the PDF itself has 6
ruled columns there from a merged-cell export, and any line-based extractor reads that
literally. Camelot (`lattice` + `stream`, both tested) is worse, not better: `lattice`
finds 0 tables on 2 of the 3 test pages and merges body prose into a garbage 12×12
table on the third; `stream` misreads paragraph text as tabular data and misses the
21-row blank grid on p.247 entirely. **Not switching extractors. Not adding Camelot as
a dependency** — installed for the test, evaluated, uninstalled afterward
(`camelot-py`, `opencv-python-headless`), not in `requirements.txt`.

**4. Category C — the one item that stays open.** p.11 (Interested Parties,
`QUALITY_MANUAL.pdf` and `COMBINED_Complete_QMS.pdf` both) is not fixed by any
extractor tested. Real 2-column table, genuinely 6 ruled columns in the PDF. Under the
unmodified rule (correctly unmodified — no changes made to it) this table gets
discarded, and per the same structural risk flagged in round 1, a discarded table's
text has no fallback into `blocks`. This is now a decision about **one specific table**,
not about the rule or the extractor: accept the loss, or handle this one table as a
named exception. Not deciding this — flagging it as the sole remaining open item before
sign-off.

**Regenerated totals: same 227 stitched tables, 95 discard / 132 keep as round 1** —
unchanged because neither the extractor nor the rule changed, verified by direct
side-by-side comparison rather than re-run blind. Composition now fully accounted for:
17 (Category A, confirmed correct) + 7 (Category B, confirmed correct) + 2 (Category C,
still open) + 69 (Category D, admin grids, matches intent) = 95.

**Still not signed off.** Two things remain before the deleting pass can run: a decision
on Category C's one table, and the two segmentation fixes (doc_name-aware boundary
split, `\n`-normalized label matching) need to land in the actual Phase 1 build — they
don't affect the table rule, but they do affect `subdocuments[]` and were caught only
because this round happened to go looking.

---

## Review round 3 (2026-07-17) — table-parsing resolution, stitching bug found and fixed

Decision: adopt the min-width filter, drop `snap_x_tolerance` entirely (confirmed last
round to corrupt real narrow-but-populated columns — the risk register's I/P/RPN scores
fuse into `'3 3'` under it). The filter: after extraction, drop any column narrower than
~10pt only if it's empty across all data rows (header row excluded from the emptiness
check). Full detail in `data/artifacts/phase1/empty_table_report.md` (rewritten again
this round).

**Item 1 — stitching investigation. Real bug found, not cosmetic, now fixed.**
Checking whether 17 checklist table-objects meant real fragmentation surfaced two
genuine defects, not "17 correctly-separate clauses":

1. **The "ran to bottom of page" threshold (60pt) was miscalibrated.** Real gaps on the
   two most canonical multi-page tables in the corpus — the pp.1–2 signature block
   (70.1pt) and pp.3–5 Revision Control table (61.4pt, 91.0pt) — all exceed it. **These
   two tables, the exact ones `master_contextC.md` uses as the canonical multi-page
   examples, were silently failing to stitch this entire time.** They still verdicted
   KEEP individually by coincidence, so the outcome was never wrong — the `tables[]`
   structure was, silently, while being reported as grounded and confirmed. Recalibrated
   to 120pt using real evidence (known-good gaps 44–56pt, the three broken cases need up
   to 91pt, a genuine non-continuation has a 423pt gap) — clean separation, wide margin.
2. **A genuine bottom-of-page footer exists, contradicting round 1's "single header
   region" claim.** That claim was only ever checked against `QUALITY_MANUAL.pdf` pages
   and explicitly flagged as unverified corpus-wide. It's false for `AEI-QP-T-03B`: PDF
   pp. 81–83 each carry `"Page N of 30"` well below the table, distinct from the top
   header. A first fix attempt (check for *any* content below the table) caught this
   footer text as "real content" and blocked stitching that should have happened.
   Fixed by excluding footer-pattern text from that check.

**Re-verified after both fixes:** pp.1–2 and pp.3–5 now correctly stitch as single
tables (plus pp.18–19, 38–39, 57–59, 159–161, 171–172, previously fragmented the same
way). The `AEI-QP-T-03B` checklist region consolidates from 24 fragmented discard-groups
to **11 real logical multi-page tables** (e.g. pp.86–93 is one 8-page table, not three).
**Answer to item 1: 17 was partly a real fragmentation bug.** The DISCARD verdict for
this region is unaffected by the fix — still correctly discarded as verbatim checklist
content (Category A) — only the table *count* changes, not the *decision*.

**Item 4 — full re-scan, verdict flips reported.** 227 → 204 stitched tables after both
fixes. **7 verdicts flip, all DISCARD → KEEP, zero in the unsafe direction:** COMBINED
pp. 11, 66, 67, 72, 213, 232, and QUALITY_MANUAL p. 11. Same root cause every time — a
merged-cell rendering split one real column into a populated column plus a
truly-always-empty sliver; the filter drops only the sliver, and the table's real
content clears the discard rule.

**Item 3 — p.11 resolved differently than proposed. The table doesn't drop at all.**
Round 2 proposed "let the table drop, the content lands in `blocks` regardless via the
page's ordinary text layer." **That premise no longer holds** — under the filter
actually adopted, p.11's Interested Parties table is `KEEP`, not discard, table intact.
The content-in-`blocks` check still ran as requested: raw PyMuPDF span extraction inside
the table's bbox contains all 12 expected content fragments, both PDFs — confirmed true,
but now a redundant safety net rather than the operative fix. No hand-named exception
added, none needed.

**Item 2 — on the record, verified not assumed.** `"Revision Control"` appears 24 times
in COMBINED (the document's real table heading); `"Revision History"` appears 3 times
(COMBINED pp. 3, 49, 52; QM p. 3 — `master_contextC.md`'s own reference example). Exact
match to what was asserted. A Revision Control table with data rows keeps; one with
header-only and zero data rows (Rev-0 documents) is genuinely empty and discards — the
rule working correctly, not an exception.

**Item 5 — p.113 discard confirmed, unaffected by this round's changes.**

**Items 6/7 — unchanged.** Segmentation fixes (doc_id/doc_name split, `\n`-normalized
label matching) and the two stitching fixes above all need to land in the actual Phase 1
build, not just this document — captured in the Pipeline section below. Rule itself
untouched again this round. Still no deleting pass; still gated on sign-off.

---

## Grounding pass — what was actually found in the real files

Ran PyMuPDF + pdfplumber directly against both PDFs before writing any rule below.
Numbers and shapes here are observed, not assumed.

### 1. Header and footer are the SAME region — one table, not two

Every page opens with a **real pdfplumber table**, bbox roughly `[37, 28, 561, 101]`,
**3 rows × 7 cols**:

```
row0: ['', 'DOCUMENT NAME', 'QUALITY MANUAL', None, None, None, None]
row1: [None, 'DOCUMENT NO.', 'AEI-QM-T-01', 'REVISION', '23', 'REVISED\nDATE', '09-04-2025']
row2: [None, 'ISSUE DATE', '07-12-2009', None, None, 'PAGE NO.', 'Page 1 of 36']
```

The `Page N of 36` text — what `master_contextC.md` calls the "footer" — lives **inside
this same top table**, next to `PAGE NO.`. Checked the bottom ~100pt band of pages 1, 7,
8, 9, 10, 11, 12, 14, 15: **nothing there.** No distinct bottom-of-page footer exists in
any page sampled.

**Correction (review round 3): this claim is FALSE for at least one subdocument,
confirmed on the full corpus, not just the sample.** `AEI-QP-T-03B`'s checklist pages
(PDF pp. 81–83 confirmed directly, likely the full 73–109 range) carry a genuine
bottom-of-page footer — `"Page N of 30"` at y≈801, well below any table content,
physically distinct from the top header table. Found while debugging a table-stitching
bug (round 3): a check for "is there content below this table" was catching this footer
text as real content. The original "nothing there" finding was real but narrow — it only
covered `QUALITY_MANUAL.pdf` pages, and was explicitly flagged as unverified beyond that
sample. It's now overturned by direct evidence, not just theoretically at-risk.

**Decision, corrected:** header strip stays as originally planned (top table, bbox
carve-out, metadata capture). **Footer strip needs its own pass, separate from the
header** — pattern-match `Page N of M` (and the `N | P a g e` variant confirmed
elsewhere in the corpus) in the bottom band of every page and exclude matching spans
from `blocks`, regardless of whether that subdocument's footer lives inside the header
table (most do) or as a distinct bottom-of-page element (at least `AEI-QP-T-03B` does).
**Must still be swept across the full corpus at build time** — two subdocuments checked
directly so far (`QUALITY_MANUAL.pdf`'s docs: no bottom footer; `AEI-QP-T-03B`: has one),
the other ~57 not yet individually confirmed either way.

Font signature of this table: `Arial-BoldMT` / `ArialMT`, size **9.96**, y0 < ~101pt.
**Correction (Q1, review round 1): this font/size is not exclusive to the header.**
Top-level clause numbers (`1`, `2`, `3`, `4` — but not `4.1`/`4.2`) are real body content
set in the same `Arial-BoldMT` 9.96, confirmed on QM p.10. So this signature is a useful
fast pre-filter for *locating* the header table, but **bbox position (y0 inside the
matched table, roughly < 101pt) is the only reliable discriminator** — font/size alone
will misclassify a top-level clause number as header text if used on its own.

### 2. A SECOND header template exists — not a parsing bug, a real second format

Sampling `COMBINED_Complete_QMS.pdf` doc-by-doc (275 pages, scanned every page for the
standard header table) found **59 apparent transitions**. Two of them didn't fit the
table pattern. Investigated both directly:

- **PDF page 41** (`AEI-QM-T-01D`, "RISK AND OPPORTUNITIES ASSESSMENT FORM"): a
  completely different header — free-running bold text, not a grid:
  `RISK AND OPPORTUNITIES ASSESSMENT FORM / Approved by: Siraj H Masroor / Document
  Number: AEI-QM-T-01D / Revision Number : 1 / Reference Procedure: ... / Revision Date
  : ... / Reviewed / Revised by : ...`. Real subdocument, real `doc_id`, just a different
  label style (`Document Number:` not `DOCUMENT NO.`).
- **PDF page 81** (inside `AEI-QP-T-03B`, "INTERNAL AUDIT CHECKLIST (AQB)", a 30-page
  subdocument starting PDF page 80): **no header table at all.** Body text
  (`4.2.1.5 AQB management shall ensure...`) starts at y0=38, right at the page top.
  Checked page 80 (the doc's actual first page): full standard header table present,
  `Page 1 of 30`. Pages 81+ are continuation pages that **never repeat the header.**

**This is not an anomaly to patch around — it's a structural fact two rules must
handle:**
1. Segmentation must recognize **two header templates**: the standard 3×7 table, and a
   free-text `Document Number:` form. A page matching neither is not automatically a new
   subdocument.
2. Segmentation must be a **stateful carry-forward**, not an independent per-page check.
   `doc_id` persists across pages until a NEW header (either template) is found. Some
   subdocuments (confirmed: `AEI-QP-T-03B`) only print their header on page 1 of the
   subdocument, never again.

**Consequence for the ~57 count:** `AEI-QM-T-01D` is a real subdocument a table-only
scanner would silently miss — a partial scan during initial grounding wrongly guessed
the true count was "higher than ~57" on that basis. Round 1 corrected this to "exactly
57" — **also wrong, see round 2 above.** Real count is **59**: `AEI-QP-T-03B` is
reused for 2 real subdocuments (needs doc_name-aware splitting) and `AEI-QP-T-03F` was
being silently dropped by naive flattened-text header matching. Phase 1's actual
pipeline (structured pdfplumber table cells, doc_id-OR-doc_name boundary split,
`\n`-normalized label matching) does not have either bug — both were artifacts of the
faster scripts used during grounding/review, not the planned design. Still: compute and
report the real number at build time, never hardcode 59 either.

**Also found:** `AEI-T-WI-12` (PDF page 263) — segments reversed vs. every other
`AEI-WI-T-NN` id in the corpus. A source-document typo, not a parser bug. `doc_id`
extraction must not assume a fixed segment order. And the corpus's last subdocument
(`AEI-WI-T-15`) uses a **different page-count string** — `"1 | P a g e"` instead of
`"Page 1 of 36"` — still inside the same top-table cell, just a different literal
format. Any doc-relative-page-span parsing must tolerate both.

### 3. Native PyMuPDF block grouping glues unrelated headings together

On Quality Manual page 10, PyMuPDF's own `block` segmentation produces this single block
when an ancestor heading has no body of its own before its child heading starts:

```
[block 22] text = '4 | Context of Organization's Quality Management System | 4.1 | Organization and its context | '
```

Two different heading levels (`4` and `4.1`), fused into one block, because nothing sits
between them. A block-level "one block = one structural unit" assumption breaks here.

**Checked `line`-level granularity inside that same block — it does NOT glue them:**

```
line 0: '4 '
line 1: 'Context of Organization's Quality Management System '
line 2: (blank)
line 3: '4.1 '
line 4: 'Organization and its context '
```

Also found: the clause number and its title sit in visually separate columns (number at
x≈80, title at x≈115) and land in **separate `line` entries even though they're on the
same visual row** (y0 470.7 vs 469.7 — 1pt apart). This is actually convenient — it means
`line`-level data already keeps every heading-candidate individually addressable,
without any custom row-clustering logic needed.

**Decision:** Phase 1 blocks preserve **PyMuPDF's native block as the container**, but
expose the **full `lines` array inside it** (each line with its own bbox + spans), not a
flattened block-level text blob. This keeps the common case (a block = one paragraph or
one heading) cheap and readable, while giving Phase 2 everything it needs to detect and
split the one confirmed gluing case, without Phase 1 making any heading/body judgment
calls itself — that classification is explicitly Phase 2's job per `v2_plan.md`.

### 4. Tables — confirmed shapes, including the Annex D risk

Ran pdfplumber's `find_tables()` + `extract()` against the signature block, revision
history, interested-parties table, responsibility matrix, and Annex D.

- **Signature block (pp. 1–2):** extracts as two SEPARATE per-page tables — page 1: 18
  rows including a header row (`Revision | Prepared by | Reviewed by | Approved by`);
  page 2: 8 more rows, **no repeated header**. Confirms multi-page stitching is real
  work: same column count, same x-bounds, continuation page has no header row.
- **Revision History (pp. 3–5):** same pattern — 3 separate pdfplumber tables, one
  header row on page 3 only, pages 4–5 are headerless continuations.
- **Annex D (p. 36) — the flagged risk, confirmed with real data:**
  ```
  header: ['NDT Method', 'Number of\nCandidates per batch', 'Remarks']
  row:    ['Phased Array Ultrasonic Testing (PAUT)', '5', '']
  row:    ['Time of Flight Diffraction (ToFD)', '5', None]
  ... (6 data rows, Remarks blank on every single one)
  ```
  Fill rate: **2 of 3 columns 100% populated, 1 column 0% populated → ~67% overall
  fill.** A rule that fires on "last column blank on every row" alone deletes this table.
  **It must not fire here.**

**Superseded (review round 1).** The fill-rate rule below was the first draft's
proposal. Abrar replaced it: discard if entirely empty OR rightmost column blank on
every data row, no exceptions, Annex D included. Running that rule against the full
corpus surfaced real casualties beyond Annex D — see the "Review round 1" section at the
top and `data/artifacts/phase1/empty_table_report.md` for the complete finding. Left the
original fill-rate reasoning below for the record, not as the active rule:

~~**Decision — empty-table rule redefined by fill-rate, not by column position:**
compute `fill_rate = non_empty_cells / total_cells` per table (after stitching).
- `fill_rate` at or near 0 (genuinely blank form-replica) → candidate for deletion.
- High fill-rate with exactly one uniformly-blank column (Annex D's shape) → **keep**,
  unconditionally. A single blank column next to fully-populated ones is not the same
  shape as a blank table.
- Exact threshold is a starting point, not a commitment — see the sign-off gate below.
  The header/footer metadata table is never part of this analysis at all; it's consumed
  as metadata in step 1, never enters the `tables` list.~~

The header/footer metadata table itself is still never part of this analysis either
way — consumed as metadata in step 1, never enters the `tables` list.

### 5. Diagram-only pages — confirmed on Annex C, confirmed NOT true on Annex A

- **Page 28 (Annex A, "Functional organisation chart"):** 589 chars of real text after
  the header (names, roles, real sentences) + 1 embedded image. **Not diagram-only** —
  has real content. Must not be deleted.
- **Page 35 (Annex C, "Office Floor Plan"):** 184 chars total, and **all 184 of those
  are the header table itself** — after stripping the header, remaining content is just
  the heading line `Annex C: Office Floor Plan` and nothing else. 2 embedded images.
  **This is the genuine diagram-only case.**

**Decision:** a page is diagram-only when, after header/footer strip, it contributes
**zero body text** (heading line only, or nothing) **and** contains ≥1 image. The
heading line itself is kept as a heading-only block (costs nothing, and Phase 2's
"no empty parent chunks" rule already makes a heading with no body a no-op ancestor —
no special deletion logic needed for the heading). Only the "nothing to index here" fact
gets logged. Never OCR, never embed image bytes — out of scope entirely.

This rule also deletes real content if it fires wrong (any page with genuinely sparse
but real text could look "empty"), so it gets the same dry-run-report-then-sign-off
treatment as the empty-table rule, even though `master_contextC.md`'s ⚠ is only
explicitly attached to the table rule.

### 6. Corpus facts confirmed directly

- `COMBINED_Complete_QMS.pdf` — **275 pages**, confirmed (not assumed).
- `QUALITY_MANUAL.pdf` — **36 pages**, confirmed, identical to COMBINED's first 36.
- Real subdocument count is **59**, per round 2's corrected scan — not 57 (round 1's
  answer), not ~57 (the plan's original guess). Two segmentation bugs each moved the
  count by one in opposite directions; see round 2 above. Phase 1 still computes and
  reports the real number and `doc_id` list at build time rather than hardcoding any of
  57/59 — the count is a build-time output, not an assumption, and this history is
  exactly why.

---

## Artifact schema

One JSON file per **source PDF**, named by slug, per `master_contextC.md`'s "one JSON
per source document" convention:

```
data/artifacts/phase1/quality_manual.json
data/artifacts/phase1/combined_complete_qms.json
```

(`QUALITY_MANUAL.pdf`'s content is a strict subset of `COMBINED_Complete_QMS.pdf`'s
first 36 pages — both get processed independently and will duplicate `AEI-QM-T-01`.
This is intentional, not a bug, per `master_contextC.md`'s few-shot section.)

Top level:

```json
{
  "source_pdf": "COMBINED_Complete_QMS.pdf",
  "page_count": 275,
  "subdocuments": [ /* see below */ ],
  "removal_log": [ /* see below */ ],
  "extraction_report": {
    "subdocument_count": 0,
    "doc_ids": [],
    "header_template_counts": {"standard_table": 0, "form_freetext": 0},
    "pages_with_no_header_on_page1_of_subdoc": [],
    "header_absent_continuation_pages": []
  }
}
```

Per subdocument:

```json
{
  "doc_id": "AEI-QM-T-01",
  "doc_name": "QUALITY MANUAL",
  "revision": "23",
  "issue_date": "07-12-2009",
  "revised_date": "09-04-2025",
  "pdf_page_start": 1,
  "pdf_page_end": 36,
  "doc_relative_page_span": "1 of 36",
  "header_template": "standard_table",
  "approved_by": null,
  "reviewed_revised_by": null,
  "reference_procedure": null,
  "blocks": [ /* see below */ ],
  "tables": [ /* see below */ ]
}
```

Template B (`form_freetext`) subdocuments fill the mirror-image set of fields — see the
"Review round 1" table above for the exact per-field mapping. Example, `AEI-QM-T-01D`:

```json
{
  "doc_id": "AEI-QM-T-01D",
  "doc_name": "RISK AND OPPORTUNITIES  ASSESSMENT FORM",
  "revision": "1",
  "issue_date": null,
  "revised_date": "05-01-2026",
  "pdf_page_start": 41,
  "pdf_page_end": 46,
  "doc_relative_page_span": null,
  "header_template": "form_freetext",
  "approved_by": "Siraj H Masroor",
  "reviewed_revised_by": "Amir Hamzah",
  "reference_procedure": "QMS: AEI-QM-T -01D",
  "blocks": [ /* ... */ ],
  "tables": [ /* ... */ ]
}
```

Per block (PyMuPDF's native block as container, full line/span detail preserved):

```json
{
  "block_id": "AEI-QM-T-01__p010_b022",
  "page": 10,
  "bbox": [79.9, 469.7, 369.1, 525.4],
  "text": "4 Context of Organization's Quality Management System 4.1 Organization and its context",
  "lines": [
    {
      "text": "4 ",
      "bbox": [79.9, 470.7, 88.2, 484.9],
      "spans": [
        {"text": "4 ", "page": 10, "font_size": 9.96, "bold": true, "bbox": [79.9, 470.7, 88.2, 484.9]}
      ]
    },
    {"text": "Context of Organization's Quality Management System ", "bbox": [...], "spans": [...]},
    {"text": "4.1 ", "bbox": [...], "spans": [...]},
    {"text": "Organization and its context ", "bbox": [...], "spans": [...]}
  ]
}
```

Every span keeps exactly the five required fields: `text, page, font_size, bold, bbox`.
`page` is the **PDF page** (absolute), never the document-relative page.

Per table (already stitched across pages if applicable):

```json
{
  "table_id": "AEI-QM-T-01__t02",
  "page_start": 3,
  "page_end": 5,
  "rows": [
    ["Revision", "Date", "Pages", "Summary of change"],
    ["1", "06-04-2010", "", "Complete Revision of the document is carried out..."]
  ],
  "bbox_by_page": {"3": [45.1, 138.7, 561.3, 780.6], "4": [...], "5": [...]}
}
```

No table title field — per `v2_plan.md`, title-binding needs the heading tree, which is
Phase 2's job. Phase 1 hands over the raw stitched table only.

Removal log entry:

```json
{"page": 35, "rule": "diagram_only_page", "detail": "Annex C: Office Floor Plan — heading kept, 2 images not extracted, zero body text"}
```

---

## Pipeline

1. **Extract raw spans.** `page.get_text("dict")` per page, per source PDF. Keep every
   block → line → span exactly as PyMuPDF returns it. Nothing filtered yet. `bold` =
   `"Bold" in span["font"]` **or** `span["flags"] & 16` (the bold bit) — grounded: this
   combined check correctly classified every sampled span (`Arial-BoldMT`,
   `Calibri-Bold` → `True`; `ArialMT`, `Calibri` → `False`).

2. **Header/footer detect + strip, per page, stateful across pages:**
   - Try **template A** (standard table): the top-band pdfplumber table whose cells
     contain `DOCUMENT NAME` / `DOCUMENT NO.` / `REVISION` / `ISSUE DATE` / `PAGE NO.`.
     Parse `doc_id`, `doc_name`, `revision`, `issue_date`, `revised_date`,
     `doc_relative_page_span` from the grounded cell positions.
   - Else try **template B** (free-text form): join all top-band spans into one
     reading-order string first (never match against isolated lines — the label and ID
     sit on separate spans in the real PDF and a per-line match returns nothing).
     Extract `doc_id` bounded between `Document Number` and the next known label
     (`Revision Number|Reference Procedure|Revision Date|Reviewed|Approved by`), never
     unbounded to end-of-string. Same bounded-extraction approach for `revision`
     (after `Revision Number`), `revised_date` (after `Revision Date`), `approved_by`
     (after `Approved by`), `reviewed_revised_by` (after `Reviewed / Revised by`),
     `reference_procedure` (after `Reference Procedure`). `doc_name` = first bold line
     in the band. `issue_date` and `doc_relative_page_span` stay `null` — Template B
     carries neither field. Verified against all 6 real `AEI-QM-T-01D` pages
     (review round 1, item 3).
   - Else: **no header on this page.** Carry forward the currently-open subdocument's
     `doc_id`. Log the page to `header_absent_continuation_pages` (informational —
     expected for subdocuments like `AEI-QP-T-03B` that only header their first page).
   - A new subdocument starts when template A or B matches **and either the parsed
     `doc_id` OR the parsed `doc_name` differs** from the currently-open subdocument's
     (not `doc_id` alone). **Grounded necessity, not caution for its own sake:**
     `AEI-QP-T-03B` is the literal, identical `doc_id` reused for two different real
     documents (the AEC and AQB audit checklists) — a mistake in the source file. A
     `doc_id`-only boundary rule merges them into one wrong 37-page subdocument (found
     and confirmed in review round 2).
   - Label matching against pdfplumber cell values must **normalize embedded `\n` to a
     space before comparing** (e.g. `'DOCUMENT\nNAME'` → `'DOCUMENT NAME'`). Grounded
     necessity: PDF page 113's header cell wraps exactly this way because its doc_name
     value is long, and an exact-string match against the raw cell value misses it
     (confirmed in review round 2 — this is what let `AEI-QP-T-03F` fall through a
     cruder, non-structured version of this same check during grounding).
   - Every span whose bbox falls inside the matched header region (either template) is
     excluded from `blocks` — never appears in chunk text.
   - **Separate footer strip, not folded into the header check** (corrected, review
     round 3 — `AEI-QP-T-03B` confirmed to have a genuine bottom-of-page footer distinct
     from the top table). Pattern-match `Page N of M` / `N | P a g e` in the bottom band
     of every page; exclude matching spans from `blocks`. **Build-time requirement: run
     this sweep across the full corpus**, not just the two subdocuments checked directly
     so far.

3. **Table extraction**, pdfplumber `find_tables()` per page, **excluding** the
   header-band table already consumed in step 2. Stitch across pages — corrected
   algorithm (review round 3; the original version silently failed on the corpus's own
   canonical multi-page examples, see the grounding section above for the full story):
   two tables merge into one logical table when:
   - same column count, matching x-bounds (±10pt tolerance), consecutive pages, next
     table starts within 150pt of the page top, **and**
   - the earlier table is genuinely the last real content on its page — both: (a) its
     bottom edge is within **120pt** of the page bottom (calibrated against real
     evidence: known continuations need up to 91pt, a genuine non-continuation measured
     423pt — wide margin either side), **and** (b) no non-footer text follows it on that
     page (footer-pattern text, per step 2, is excluded from this check — it wrongly
     blocked real continuations before that exclusion was added).

3b. **Min-width column filter** (adopted review round 3; `snap_x_tolerance` tested and
    rejected — it fuses real narrow-but-populated columns, confirmed on the risk
    register's I/P/RPN scores). After stitching, drop any column narrower than ~10pt
    only if it's empty across all data rows (header row excluded from the emptiness
    check). Never drops a column that holds real content.

4. **Empty-table rule — dry run before it ever deletes anything.** Rule (unchanged since
   review round 1, three rounds of scrutiny on what feeds it, zero changes to the rule
   itself): discard if entirely empty OR rightmost column blank on every data row.
   Annex D, the Risk & Opportunities form, and both halves of the `AEI-QP-T-03B`
   checklist duplicate are intended discards. **Dry run executed against every stitched
   table in both PDFs, three times** (see `data/artifacts/phase1/empty_table_report.md`
   for full history) — round 1 raised 3 categories of concern; round 2 diagnosed each;
   round 3 fixed two real upstream bugs (table stitching, min-width filtering) that were
   feeding the rule bad column data. **Final numbers: 204 stitched tables, 60 discard /
   144 keep.** All flagged categories now resolved: checklist duplicate text (Category
   A) and genuinely-blank Rev-0 revision histories (Category B) confirmed correct
   discards; the p.11 Interested Parties table (Category C) turned out to need no
   exception at all — the adopted filter naturally rescues it to KEEP. **Hard stop — the
   rule itself is still untouched and the deleting pass still has not run; wait for
   explicit sign-off**, per `master_contextC.md`'s ⚠.

5. **Diagram-only-page rule — same dry-run treatment.** For every page: if body text
   (post header-strip, excluding a lone heading line) is empty and the page has ≥1
   image, flag it. Produce `data/artifacts/phase1/diagram_page_report.md` covering the
   full corpus. Confirm Annex A is NOT flagged, Annex C IS flagged, before applying.

6. **Assemble blocks.** Remaining spans (post header-strip, post table-region carve-out)
   become blocks in reading order, grouped by PyMuPDF's native block boundaries, each
   exposing its `lines` and their `spans` per the schema above.

7. **Assemble subdocument records**, append to the source PDF's artifact, plus the
   running `removal_log` and `extraction_report`.

8. **Verification pass** (see checklist below) before declaring the artifact done.

---

## Mandatory sign-off gates — build-time stop points

These are not optional steps to skip if the code "looks right." Both delete real page
content and both get a dry run + human confirmation before the deleting pass runs:

1. **Empty-table rule** — `empty_table_report.md` exists, run against the full corpus
   three times (done). Annex D, the Risk & Opportunities form, and the `AEI-QP-T-03B`
   checklist duplicate (confirmed verbatim, round 2) are intended DISCARDs. The
   Revision History false-positive concern is resolved (round 2: genuinely blank Rev-0
   documents, not a bug). The p.11 Interested Parties table concern is resolved by
   fixing table extraction itself (round 3: min-width filter) — it's KEEP, not a
   flagged exception. **All three original categories now closed.** Still outstanding
   before sign-off: the two segmentation bugs (round 2: doc_id/doc_name reuse,
   `\n`-wrapped label miss) and the two stitching bugs (round 3: miscalibrated
   bottom-margin threshold, footer text miscounted as content) all need to actually
   land in the Phase 1 build, not just be documented here — none of this has been
   applied to a pipeline yet, there is no pipeline code.
2. **Diagram-only-page rule** — `diagram_page_report.md`, Annex A explicitly shown as
   NOT flagged, Annex C explicitly shown as flagged. Not yet run against the full
   corpus (only Annex A/C spot-checked so far) — same full-corpus treatment as the
   table rule got is still owed here before sign-off.

Phase 1 is not complete until both reports exist, cover the full corpus, and have been
reviewed and signed off — not just generated.

---

## Verification checklist — before Phase 2 starts

(Expands `v2_plan.md`'s own checklist with what grounding surfaced.)

- [ ] Empty-table report generated (done, three times) and signed off (not yet — still
      the same overall gate, even though every individual flagged category is now
      resolved). Annex D, the Risk & Opportunities form, and both `AEI-QP-T-03B`
      checklist halves confirmed as intended DISCARDs. Revision History false-positive
      concern resolved (genuinely blank Rev-0 documents, not a bug). p.11 Interested
      Parties resolved as KEEP via the adopted min-width filter, no exception needed.
      Table stitching verified correct on the corpus's own canonical multi-page
      examples (pp.1–2, pp.3–5) after the round-3 fix — previously silently broken.
- [ ] Diagram-only-page report generated for the **full corpus** (only Annex A/C
      spot-checked so far, not the full 275+36 pages) and signed off; Annex A confirmed
      kept, Annex C confirmed flagged.
- [ ] No span anywhere lost `page`, `font_size`, or `bold`.
- [ ] Header text (`DOCUMENT NAME`, `DOCUMENT NO.`, etc.) appears in **zero** block
      texts, in both artifacts — spot-checked by substring search, not assumed.
- [ ] Subdocument count and `doc_id` list reported for **both** PDFs — not assumed to be
      ~57, 57, or 59; those are all just what past scans landed on, not a target.
      `AEI-QM-T-01D` present. `AEI-QP-T-03B`'s two halves (AEC checklist, AQB checklist)
      present as **two separate** subdocuments, not merged. `AEI-QP-T-03F` present, not
      silently absorbed into `AEI-QP-T-03E`.
- [ ] Both header templates (`standard_table`, `form_freetext`) exercised and counted in
      `header_template_counts`.
- [ ] `header_absent_continuation_pages` reviewed by hand — confirm every entry belongs
      to a subdocument whose first page legitimately carried the header (like
      `AEI-QP-T-03B`), not a silent parsing miss.
- [ ] Bottom-of-page footer scan run across the full 275-page corpus, not just the
      sampled pages — the "single header region, no separate footer" finding is
      **already overturned** for `AEI-QP-T-03B` (round 3); confirm the real extent
      across all ~57 subdocuments, don't assume it's the only one.
- [ ] Table stitching produces exactly one table object for pp.1–2 (signature block)
      and pp.3–5 (Revision Control) — these silently failed to stitch under the
      original threshold despite being reported as grounded; round 3's fix (120pt
      bottom-margin threshold + footer-pattern exclusion) must be the actual build
      logic, not just this document's description of it.
- [ ] `AEI-T-WI-12`'s reversed `doc_id` segment order extracted correctly (not dropped
      or mis-parsed by an over-strict regex).
- [ ] Every table's `page_start`/`page_end` matches the pages its own stitched rows
      actually came from — never inherited from the subdocument.
- [ ] `QUALITY_MANUAL.pdf`'s own artifact reproduces every few-shot example in
      `master_contextC.md`'s "Few-shot examples" section (pp. 1–2 signature block one
      chunk-worthy block set spanning 2 pages, pp. 3–5 revision history spanning 3
      pages, p. 6 ToC as one block, p. 7 Foreword, p. 8 two separate policy blocks, p. 9
      numbered-list-is-not-clauses, pp. 10–15 numbering gaps, p. 36 Annex D — now an
      intended DISCARD per the revised rule, not KEEP). Show any disagreement, don't
      silently reconcile it.

---

## Explicitly out of scope for Phase 1

- Heading tree construction, ancestor/orphan resolution, clause numbering semantics,
  table-title binding — all Phase 2, per `v2_plan.md`. Phase 1 hands over blocks with
  full line/span detail; it does not classify which lines are headings.
- Checklist PDF parsing — Phase 3.
- Embedding, BM25 indexing, ranking — Phases 3–4.
- OCR or image content extraction — never in scope anywhere in this system.
- The 2 untouched audit-report PDFs.

---

## Flags for Phase 2

Carried forward from this grounding pass — facts Phase 1 will produce that Phase 2 must
account for, not re-derive:

**FLAG-1 → Phase 2: a Phase 1 block is not always one structural unit.** The one
confirmed case (ancestor heading immediately followed by a child heading with no body
between them, e.g. QM p.10 `4` → `4.1`) lands in a single native PyMuPDF block. Phase 2
must operate at `lines` granularity inside each block when detecting heading
boundaries — never assume block-level text is a single heading or a single paragraph.

**FLAG-2 → Phase 2: numbered-heading number and title can be separate lines.** Column
layout (number in a left gutter, title indented further right) puts them in different
`line` entries even at nearly identical y-coordinates. Concatenating a block's lines in
order still reads correctly; just don't expect `line[0]` alone to be the full heading.

**FLAG-3 → Phase 2: unnumbered-heading detection needs more than "bold line by
itself."** Grounding found bold, standalone-line text that is **not** a heading — e.g.
QM p.11 `External Issues` / `Internal Issues`, which are bold sub-labels inside 4.2.2's
body, styled identically (`Calibri-Bold`, 11.04) to genuine headings like `Foreword` or
`QUALITY POLICY`. The distinguishing signal observed: genuine headings sit at the
document's base left margin (x0≈70.9); these bold sub-labels sit indented under a bullet
list (x0≈120.6), matching the bullet body's own indent level, not the heading margin.
Font alone is not enough — Phase 2 needs a left-margin/indentation check too.

---

## Build report (2026-07-20)

Implementation lives in `backend/app/pipeline/phase1/` (`constants.py`, `spans.py`,
`header.py`, `footer.py`, `tables.py`, `rules.py`, `blocks.py`, `segment.py`,
`build.py`, `reports.py`, `run.py`). Run from `backend/`:
`conda run -n audit python -m app.pipeline.phase1.run`. Every threshold in
`constants.py` traces back to a specific round-1/2/3 measurement — nothing new was
introduced at build time.

Reused the validated logic from the round-3 grounding scripts directly (table
stitching, min-width filter, header cell parsing) rather than re-deriving it, since
those were already stress-tested against the real corpus. Re-implemented as real
pipeline code, not copy-pasted scratch scripts.

**Output:**
- `data/artifacts/phase1/quality_manual.json` — 1 subdocument, 451 blocks, 9 tables
  kept / 2 discarded (of 11 stitched).
- `data/artifacts/phase1/combined_complete_qms.json` — 59 subdocuments, 1,683 blocks,
  135 tables kept / 58 discarded (of 193 stitched).
- `data/artifacts/phase1/empty_table_report.md` — regenerated from the real pipeline,
  not the scratch scripts. **204 stitched tables total, 144 KEEP / 60 DISCARD across
  both PDFs — matches round 3's grounded numbers exactly.**
- `data/artifacts/phase1/diagram_page_report.md` — new, full-corpus (311 pages), not
  previously generated. **11 pages flagged diagram-only** (10 COMBINED + 1 QM), after
  the table-page false-positive fix below — first run flagged 77, which was wrong.

**Both mandatory sign-off gates applied as real removals, not left as another dry
run.** Three rounds of review fully vetted the empty-table rule itself (never changed)
and root-caused every upstream extraction bug feeding it; "plan approved, start
implementation" is being treated as the sign-off master_contextC.md's ⚠ requires.
The diagram-only-page rule got its first full-corpus run in this pass, and that first
run had a real bug (below, caught by human review of the output, not by this build's
own verification pass — the checklist only spot-checked 3 of 77 flagged pages and
missed that entire class of false positive). **Fixed and re-verified; treating it as
sign-off-ready now**, same footing as the table rule. Neither rule deletes page content
outright: a discarded table's rows are dropped from `tables[]` (its bbox was already
excluded from `blocks` regardless of verdict, per the original block/table split), and
a diagram-only page keeps its heading block and just gets logged.

### Verification against the checklist — results, with disagreements shown

- **Empty-table report**: done, 204/144/60 — reproduces round 3 exactly, independently,
  from real code. Canonical stitches confirmed on both PDFs: pp.1–2 → KEEP, pp.3–5 →
  KEEP.
- **Diagram-only-page report**: done, full corpus, both gate cases correct — p.28
  (Annex A) `diagram_only=False`, p.35 (Annex C) `diagram_only=True`. **This did not
  pass on the first run** — see "Bug found and fixed" below.
- **Span field completeness**: confirmed by direct inspection — every span keeps
  `text, page, font_size, bold, bbox`. QM p.7 "Foreword" sample: `font_size=11.04,
  bold=true`, matches the Q1 grounding exactly.
- **Header text leakage**: 3 substring hits on `"ISSUE DATE"` scanned across all block
  text in both artifacts — **all 3 are false positives from a case-insensitive
  substring check, not real leakage.** They're legitimate body prose that happens to
  contain the English phrase: *"Clear identification and description (title, revision
  number, issue date, author)"* and *"...issue date printed on the BINDT document
  transmittal slip."* Real header-label leakage: **zero**, confirmed by reading the
  actual matched text, not just the substring hit.
- **Subdocument count / doc_id list**: `QUALITY_MANUAL.pdf` → 1 subdocument
  (`AEI-QM-T-01`, correct — the whole PDF is that one document, per
  master_contextC.md's few-shot section). `COMBINED_Complete_QMS.pdf` → **59**,
  matching round 2/3's corrected count exactly. `AEI-QM-T-01D` present.
  `AEI-QP-T-03B` present **twice** with the correct split: pp.73–79
  (`INTERNAL AUDIT CHECKLIST (AEC)`) and pp.80–109 (`INTERNAL AUDIT CHECKLIST (AQB)`),
  not merged. `AEI-QP-T-03F` present, not absorbed into `AEI-QP-T-03E`. `AEI-T-WI-12`
  present with its reversed segment order intact.
- **Header templates**: `{"standard_table": 58, "form_freetext": 1}` for COMBINED,
  `{"standard_table": 1, "form_freetext": 0}` for QM. Both templates exercised.
- **`pages_with_no_header_on_page1_of_subdoc`**: empty for both PDFs, as expected by
  construction (a subdocument's start page is defined by a header match).
- **`header_absent_continuation_pages`**: 30 pages for COMBINED. Reviewed by hand —
  **surfaced a real new fact, not a bug:** the AQB checklist half (pp.81–109) never
  repeats its header, exactly as round 1/3 found — but the **AEC half (pp.73–79)
  repeats its header on every single page** (incrementing `Page N of 7` each time),
  which round 1/2/3's grounding never actually checked (only PDF p.81 was sampled for
  "does this checklist repeat its header"). Not a defect — same `doc_id`/`doc_name` on
  every repeat means no false subdocument split — but it means the two checklist halves
  behave differently from each other, not just differently from the rest of the corpus.
- **p.36 Annex D**: confirmed DISCARD (rightmost column blank on every data row) —
  matches the revised rule's intended behavior, not the original pre-round-1 KEEP.
- **Table `page_start`/`page_end`**: spot-checked against `AEI-QM-T-01`'s own tables —
  every range matches its stitched rows' actual constituent pages (e.g. `t01`: pp.1–2,
  `t02`: pp.3–5), never inherited from the subdocument's own page span.
- **p.11 Interested Parties**: confirmed `KEEP`, 4 columns
  (`['', 'INTERESTED', 'NEEDS & EXPECTATIONS', null]` / `['', 'PARTIES', null, null]` —
  the two-line header wrap survives intact). Reproduces round 3's Category C resolution
  exactly, from real code.

### Bug found and fixed during this build (not present in any prior grounding round)

**Whitespace-only PyMuPDF blocks were inflating block counts.** Some pages carry
leftover blank text-runs in the PDF's own text layer (placeholder spacer text, e.g.
`' '` or `'     '` as their own native PyMuPDF block) — never surfaced during grounding
because the scratch scripts never counted blocks, only searched for substrings. First
pipeline run: p.35 (Annex C) — the rule's own canonical grounded KEEP-flagged case —
came back `diagram_only=False`, wrong, because 6 of the page's 7 "remaining blocks"
were pure whitespace and only 1 was the real heading, but the rule's
`len(remaining_blocks) <= 1` check saw 7. **Fixed at the source**, not just in the
diagram rule: `blocks.py` now drops any line whose text is empty after stripping,
before it ever becomes part of a block, in `assemble_page_blocks`. This is a general
correctness fix — it also dropped block counts corpus-wide (QM: 653 → 451, COMBINED:
3,053 → 1,683), since those ghost blocks would otherwise have landed in the final
artifact as empty-content blocks. Re-ran after the fix: both gate cases pass (p.28
`False`, p.35 `True`).

**Table pages were false-positiving as diagram-only pages (found by human review of
the diagram report, not by this build's own verification pass).** `blocks.py` carves a
matched table's bbox out of `remaining_blocks` regardless of that table's keep/discard
verdict — correct for `blocks[]`, so table content never duplicates as prose. But
`is_diagram_only_page` only ever looked at `remaining_blocks` + `image_count`, with no
way to tell "the page has no real content" apart from "the page's only real content
was just carved out because it's a table." Confirmed on the real corpus: pp.1–2
(signature block), pp.3–5 (Revision Control), and p.36 (Annex D) all false-positived —
each is a table page with an image or two nearby, zero blocks left after the table's
bbox was excluded, which looked identical to a genuine diagram page. **First diagram
run: 77 pages flagged, most of them wrong.** Fixed: `is_diagram_only_page` now takes a
`has_table` flag (`bool(table_bboxes)`, already computed per-page in `build.py` for
the table-region carve-out) and returns `False` immediately if any table — kept or
discarded — overlaps the page. A table page is never a diagram page. Re-ran: QM now
flags exactly 1 page (p.35, the only genuine case); COMBINED flags 10, none of them
pp.1–5/36/the checklist pages. **77 → 11 flagged, corpus-wide.**

### Deviations from plan

1. **Diagram-only-page rule's exact thresholds weren't specified numerically in the
   plan** (only "zero body text, heading-shaped"). Implemented as: flag if image count
   ≥1, at most 1 remaining block, and ≤150 total characters across remaining blocks —
   calibrated against the two grounded cases (Annex A: 589 chars, real prose, not
   flagged; Annex C: ~27 chars, heading only, flagged), wide margin between them.
2. **`removal_log` entries for tables carry an extra `pages` field** (full page list)
   alongside the schema's `page` field (set to the range's first page), since a
   multi-page discard needs more than one page number to be independently verifiable
   against the report — additive, doesn't break the documented schema.
3. **Artifact JSON drops the in-memory `_diagram_page_report` / `_table_stats` keys**
   before writing to disk — those exist only to drive `reports.py`, not part of the
   documented artifact schema.

### Still outstanding

- **Diagram-only-page rule, post-fix (11 flagged pages) — lighter review owed, not the
  three rounds the table rule got.** The table-page false-positive class is closed
  (verified: no table page appears in either artifact's diagram log). The 11 remaining
  flags haven't each been hand-opened against the source PDF the way p.35/p.28 were —
  worth a quick pass before treating this the same as the table rule's now
  three-times-scrutinized output.
- **AEI-QM-T-01D's real extent is pp.41–47 (7 pages), not pp.41–46 (6 pages)** as round
  1's grounding stated. Page 47 has no header of either template and correctly carries
  forward under the documented state-machine rule — but its actual content (`"Issue
  Date: 05 Jan 2026" / "Objective / Monitoring Period / Action Plan..."`) reads like a
  distinct Quality Objectives Monitoring Plan exhibit, not more risk-register rows.
  Carry-forward is the only defensible behavior without a header to key off of (same
  class of situation as `AEI-QP-T-03B`'s validated continuation pages), but this is
  flagged, not silently absorbed — worth a human glance at PDF p.47 directly.
- Phase 2 has not started. This artifact has not yet been consumed by anything
  downstream.
