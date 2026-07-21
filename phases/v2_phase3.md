# Phase 3 — Embed + index

Status: **BUILT.** Implementation lives in `backend/app/pipeline/phase3/`
(`constants.py`, `checklist_rows.py`, `checklist_parse.py`, `embed.py`,
`bm25_index.py`, `build.py`, `reports.py`, `run.py`). Run from `backend/`:
`conda run -n audit python -m app.pipeline.phase3.run`. Build report:
`data/artifacts/phase3/build_report.md`. See "Build report" at the bottom of
this file for real numbers, disagreements against this plan's own estimates,
and one real deviation from the plan (the AEC unnumbered-paragraph handling).

Grounded against the real Phase 2 artifacts and the real checklist PDFs before
writing this plan — see "Grounding pass" below. Read `master_contextC.md` and
`v2_plan.md` first.

**Model changed after the first draft of this plan: `BAAI/bge-large-en-v1.5` →
`BAAI/bge-m3`, decided 2026-07-21, before any embedding code was written.** The change
is justified by real data, not preference — see §6. Every section below that referenced
the old model has been re-grounded against BGE-M3 directly, not ported. §8 records the
new model asset and its verification.

Reads Phase 2's artifacts and the two checklist PDFs. Inputs:
`data/artifacts/phase2/combined_complete_qms.json`, `docs/AUDIT_CHECKLIST_AQB.pdf`,
`docs/AUDIT_CHECKLIST_AEC.pdf`. **Never re-parses `COMBINED_Complete_QMS.pdf` or
`QUALITY_MANUAL.pdf`** — those are done, Phase 2 owns them.

---

## Grounding pass — what was found before writing any rule

### 1. Corpus scope: `combined_complete_qms.json` only, not `quality_manual.json`

Checked directly: all 83 `quality_manual.json` chunk_ids collide 1:1 with 83 chunks
already inside `combined_complete_qms.json` (`doc_id=AEI-QM-T-01`, byte-identical per
Phase 2's own build report). `quality_manual.json` isn't a second corpus — it's Phase 1/2's
validation fixture for the QM few-shot examples, already fully contained in COMBINED.

**Decision: the live search corpus is `combined_complete_qms.json`'s 503 chunks, full
stop.** Merging both files would silently double-count every QM hit on every checklist
item's ranked list. Matches `master_contextC.md`'s own docs table framing —
`COMBINED_Complete_QMS.pdf` is named "the main corpus," `QUALITY_MANUAL.pdf` is named
"the reference document for chunking examples."

### 2. Checklist PDFs — real structure, checked page-by-page, not assumed

Both checklists share one layout, confirmed via PyMuPDF span dump (bold + x0 + size) on
every page:

- **A repeating per-page header** (`DOCUMENT NAME`, `DOCUMENT NO.`, `REVISION`, `REVISED
  DATE`, `ISSUE DATE`, `PAGE NO.`, plus a `Page N of M` footer line) — same discipline as
  Phase 1's QMS header/footer strip, needs its own strip pass here since these are
  standalone PDFs, not part of Phase 1/2's subdocument segmentation.
- **A page-1-only title block** (`AUDIT CHECKLIST (AQB)`, bold size 15.96;
  `REQUIREMENTS FOR BINDT AUTHORISED QUALIFYING BODIES`, mixed bold size 14.04) —
  decorative, not structural, stripped like a header.
- **Headings are bold numbered rows.** `4.2 Quality Management System`, `4.2.1 QMS -
  General` (AQB); `1. General requirement`, `2 Premises/Facilities` (AEC, two spellings
  of the same pattern — with and without the trailing period). Both number token and
  title are bold, confirmed on every heading checked — unlike Phase 2's QMS `Gap 1`
  problem (non-bold clause numbers), this signal held clean everywhere it was checked.
- **Items are non-bold numbered rows**, e.g. `4.2.1.1 The organisation shall implement…`
  Confirmed: **bold vs. non-bold is a clean heading/item discriminator on these two
  PDFs** — the opposite polarity from Phase 2's QMS rule (there, bold = heading and
  unbold = ambiguous; here, bold = heading and unbold-numbered = item), which is exactly
  why this needed its own grounding pass rather than reusing Phase 2's classifier.

A first-pass regex-only count (bold → heading, non-bold + leading `\d+(\.\d+)*\.?\s` →
item) on the real PDFs gives:

| | Headings (bold) | Items (non-bold, regex match) |
|---|---|---|
| AQB | 28 | 158 |
| AEC | 9 | 49 |

Close to `master_contextC.md`'s ~159 / ~52 estimate, **not identical — two real
disagreements found and reported below, not silently reconciled to hit the expected
number.**

### 3. Disagreement 1 — a naive regex catches wrapped body lines that start with a digit

Checked directly (AQB p.10): `"…training of the candidate within the preceding 2 years
in respect of the examination…"` word-wraps so `"2 years in respect of the
examination"` starts its own visual line. The leading token `2` matches
`^\d+(\.\d+)*\.?\s+`, and the row is non-bold (it's body text) — a naive regex mis-tags
it as item `2`, a phantom.

**The real discriminator is the layout, not just bold/regex — checked directly via
`x0`:** every genuine item/heading number sits in a narrow left column (AQB: `x0` ≈
42–48 for headings, ≈44–48 for item numbers; AEC: `x0` ≈ 42 for headings, ≈ 55–62 for
item numbers). Every wrapped body continuation line — including the false-positive `2
years…` row — sits in the body column (AQB `x0` ≈ 82.1, AEC `x0` ≈ 105.3), a hanging
indent 20–40pt to the right of the number column, confirmed on every case checked. **A
row is a real heading/item only if its `x0` falls in the number column for that
document, not the body column.** This needs a full-corpus sweep at build time (only a
handful of pages were hand-checked here) to confirm the two columns never overlap
anywhere in either PDF — same discipline Phase 2 applied to its own block-homogeneity
rule before trusting it.

### 4. Disagreement 2 — a real, unfixed numbering gap in AEC's checklist itself (not a parser bug)

Checked directly, AEC p.6, heading `8. Consistency of PCN Examinations` (bold,
confirmed real heading): its first two sub-items are numbered `4.2.5.1` / `4.2.5.2` —
**wrong numbers, a source typo** (should be `8.1`/`8.2`; `4.2.5` doesn't exist anywhere
in this document as a heading) — and then **six more distinct audit questions follow
with no number at all**, each its own paragraph (`"Do they appear as examiners on the
AQB scope of approval?"`, `"What arrangements are in place for the outward and return
transfer of exam materials…?"`, etc.), separated only by a visible vertical gap between
paragraphs, same as the gap between any two numbered items.

This is a genuine content defect in the source PDF, not a detection bug — the same
category of finding as Phase 2's Gap 1/Gap 2 (non-bold clause numbers) and the
`AEI-WI-T-05B` typo. **Not silently dropped and not silently renumbered.** Proposed
fallback, to be verified corpus-wide before trusting it: under an open heading, a
paragraph break (a vertical gap matching the same spacing used between numbered items on
the same page) with no leading number starts a new item anyway, keyed by
`(doc_id, heading_no)` + a same-mechanism `#2`/`#3`… disambiguation suffix (reusing
Phase 2's own `_dedup_clause_nos` convention, not inventing a new one). This needs a
full sweep of both checklists for any other unnumbered-paragraph section before it's
trusted — only this one instance has been hand-checked so far. **If no other instance
exists, this is one bounded, well-understood special case, not a general rule risk.**

### 5. Query instruction — re-grounded against BGE-M3's own model card, not ported from the old model

The old model (`bge-large-en-v1.5`) needed an asymmetric prefix on the query side
(`"Represent this sentence for searching relevant passages: "`). **BGE-M3 is a
different model with a different training recipe — that prefix does not carry over,
and carrying it over on autopilot would have been a real bug, not a safe default.**

Checked directly, `models/bge-m3/README.md`, section "How to use BGE-M3 in other
projects?": *"For embedding retrieval, you can employ the BGE-M3 model using the same
approach as BGE. **The only difference is that the BGE-M3 model no longer requires
adding instructions to the queries.**"* No instruction string is given for M3 anywhere
in its card, because none exists.

**Decision: no instruction prefix on either side.** Checklist items and chunks both
embed their text exactly as extracted/parsed — no asymmetry, no special-casing. This
removes an entire class of "which side gets the prefix" bug that existed under the old
model.

### 6. `master_contextC.md`'s old "BGE's 512-token limit is not a problem" claim — checked directly, found false for the old model, and this is *why* the model changed

This is the real justification for the model swap, re-verified fresh this session (not
carried over from memory): ran `bge-large-en-v1.5`'s own tokenizer against every chunk
in `combined_complete_qms.json`. Median chunk is 71 tokens — the old premise holds for
the overwhelming majority — but **17 of 503 chunks (3.4%) exceed the old model's
512-token limit**, topped by `AEI-QM-T-01D__c001` (`RISK AND OPPORTUNITIES ASSESSMENT
FORM`, pp.41–47) at **4,041 tokens** — 8× the limit. Full top 10, re-run and confirmed
identical to the original finding:

| tokens (bge-large tokenizer) | chunk_id | content type |
|---|---|---|
| 4,041 | `AEI-QM-T-01D__c001` | table-heavy (32 inline tables) |
| 1,432 | `AEI-WI-T-15__c002` | prose (long WI procedure text, no tables) |
| 1,428 | `AEI-WI-T-10__c002` | prose (same shape) |
| 1,119 | `AEI-WI-T-01__c001` | table-heavy (7 inline tables) |
| 1,016 | `AEI-QM-T-01__c002` | table-heavy ("Revision History") |
| 958 | `AEI-QP-T-07__c006` | prose ("Definitions") |
| 847 | `AEI-QP-T-09__c011` | table-heavy (2 inline tables) |
| 824 | `AEI-QM-T-01__c001` | table-heavy (signature block table) |
| 791 | `AEI-QP-T-11__c002` | table-heavy ("Revision Control") |
| 770 | `AEI-QM-T-01B__c001` | table-heavy (2 inline tables) |

**8 of the top 10 are table-heavy** (wide tables, many blank cells, serialized per
Phase 2's locked ` | `-joined convention — correct per that convention, just
token-expensive when a table is this wide). **2 of the top 10 are genuinely long prose**
(real Work Instruction procedure text, no attached table at all) — so this isn't purely
a table-serialization artifact; some real chunks are just long. Either way: **the
"chunks are small by design" premise is false for a non-trivial 3.4% of the corpus, not
hypothetical, confirmed twice (original check + this session's fresh re-run, identical
numbers both times).** This is what justifies the model change rather than a
truncate-and-log workaround.

**Re-run against BGE-M3's own tokenizer, its actual 8192-token limit:**

```
total chunks: 503
chunks over 8192 tokens: 0
```

**Zero.** Even the worst offender (`AEI-QM-T-01D__c001`) tokenizes to 6,091 tokens under
M3's SentencePiece tokenizer (vs. 4,041 under bge-large's WordPiece tokenizer — the two
models segment text differently; both numbers are real, they're just not directly
comparable) — still well inside 8192. **Every chunk embeds whole under BGE-M3. The
truncate-and-log fallback this plan originally proposed no longer applies and is
removed, not kept as a dead branch.**

### 7. GPU confirmed working, right here, right now

`torch.cuda.is_available() == True`, device `NVIDIA GeForce RTX 4050 Laptop GPU`.
Phase 0's FLAG-1 (assert CUDA, no silent CPU fallback) applies to BGE-M3 exactly as it
did to the old model — nothing about the model change touches this. Phase 3's embedding
script must call `torch.cuda.is_available()` and hard-fail if it's `False`, never
warn-and-continue on CPU.

### 8. BGE-M3 added as a project asset and verified — same bar Phase 0 held the old model to

`models/bge-m3/` did not exist before this session. Downloaded via
`huggingface_hub.snapshot_download("BAAI/bge-m3", local_dir="models/bge-m3")`, then
pruned to a plain-files project asset the same way Phase 0 flattened
`bge-large-en-v1.5`: removed the duplicate ONNX export (`onnx/`, 2.2GB — a second copy
of the same weights in a format this project never loads), the model-card images
(`imgs/`, `long.jpg`), and the sparse/multi-vector heads (`colbert_linear.pt`,
`sparse_linear.pt`) — this project uses the dense vector only (see below), so those two
files are dead weight, not a silently-dropped capability. Also removed the
`local_dir`-download's own `.cache/` bookkeeping directory (hub metadata, not a model
file). Final asset: **11 files + `1_Pooling/`, 2.2GB**, dominated by `pytorch_model.bin`
(2.27GB — **BGE-M3 ships no `.safetensors`**, unlike the old model; this is a real,
checked difference, not an inconsistency to fix).

**Provenance.** `huggingface_hub.model_info("BAAI/bge-m3").sha` at fetch time:
`5617a9f61b028005a4858fdac845db406aefb181`. Recorded here per Phase 0's own FLAG-3
precedent (per this session's instruction, Phase 0's file itself is not touched — this
is Phase 3's grounding record instead).

**Verified, not assumed, each one checked directly this session:**

- **Loads from the local path with the hub never contacted — proven by contrast, not by
  reading logs.** Ran two loads with `HF_ENDPOINT` pointed at an address nothing listens
  on (`http://127.0.0.1:1`), `HF_HUB_OFFLINE`/`HF_HOME`/`HF_HUB_CACHE` left **unset** as
  instructed:
  - `SentenceTransformer("models/bge-m3", ...)` — succeeded, encoded a test string,
    **zero network activity of any kind.** It cannot have contacted the hub: the broken
    endpoint would have surfaced as an error if it had tried.
  - `SentenceTransformer("BAAI/bge-m3", ...)` (repo id, same broken endpoint) — **failed**,
    with a real, visible network attempt in the traceback: `HEAD
    http://127.0.0.1:1/BAAI/bge-m3/resolve/main/adapter_config.json` refused, retried 5×,
    then crashed. This happens even though the model is fully cached locally — `transformers`
    probes the hub for an optional PEFT adapter config regardless of cache state unless
    given a local directory outright. **This is the real, load-bearing reason
    `config.py`'s `MODEL_DIR` must stay a filesystem path, never a repo id** — Phase 0
    already established this for the old model; this session's test proves the same
    holds for BGE-M3, and shows concretely *why* (a repo-id load reaches for the network
    even fully cached; a local-dir load structurally cannot).
  - (An earlier, weaker attempt at this proof — comparing `huggingface_hub` logger
    output between the two load paths — was inconclusive, both loads produced the same
    minimal logging. Reported here rather than deleted: the network-blackhole contrast
    above is the test that actually answers the question, and superseded it.)
- **Embedding dimension is 1024** — confirmed via `model.encode("This is a test
  sentence.", normalize_embeddings=True)`: `shape=(1024,)`, `dtype=float32`, L2 norm
  `1.0` (confirms normalization is active, which Phase 4's cosine-similarity math
  assumes).
- **Max sequence length is 8192** — confirmed both from `sentence_bert_config.json`
  (`"max_seq_length": 8192`) and from the loaded model object (`model.max_seq_length ==
  8192`), and from the token re-check in §6 (0/503 chunks exceed it).
- **Dense embeddings only, confirmed by the load path itself, not just by intent.**
  This project loads BGE-M3 through `sentence_transformers.SentenceTransformer`, the
  same interface used for the old model — not `FlagEmbedding.BGEM3FlagModel`, which is
  the interface that exposes the sparse/lexical and multi-vector/ColBERT outputs.
  `modules.json` on the downloaded asset declares exactly three modules: `Transformer` →
  `Pooling` (`pooling_mode_cls_token: true`, `word_embedding_dimension: 1024`) →
  `Normalize`. There is no sparse or multi-vector module in this pipeline for the
  `SentenceTransformer` path to expose even if asked — `model.encode()` structurally
  returns one dense vector per input, confirmed by the shape check above. Pruning
  `colbert_linear.pt`/`sparse_linear.pt` from the on-disk asset (above) is consistent
  with this, not incidental.

**`backend/app/config.py`'s `MODEL_DIR` updated** from `models/bge-large-en-v1.5` to
`models/bge-m3` — this wasn't in the user's numbered list but is a direct, necessary
consequence of "effective now, before the embedding layer is built": Phase 0's own text
says *"Phase 3 loads `SentenceTransformer(settings.MODEL_DIR)`"* — leaving that default
pointed at the old model would have been a live landmine for whoever writes the actual
embedding script. Flagged here explicitly since it's a code change, not a doc change,
and wasn't on the requested list. The old `models/bge-large-en-v1.5/` asset (1.3GB) was
left on disk, untouched — deleting it wasn't requested and isn't this session's call to
make.

### 9. A real `chunk_id` collision found in the Phase 2 artifact while grounding this — not hypothetical

Checked `combined_complete_qms.json` for `chunk_id` uniqueness (prompted by the
embedding-matrix design, where `chunk_id` is the row key). **502 unique values across
503 chunks — one real collision:**

`AEI-QP-T-03B__c001` appears **twice**, both at `page_start=80, page_end=80`,
`doc_id=AEI-QP-T-03B`, `clause_no=null`. This is Phase 2's own documented split-document
case (`AEI-QP-T-03B` splits into two independent subdocuments, "INTERNAL AUDIT CHECKLIST
(AEC)" and "INTERNAL AUDIT CHECKLIST (AQB)" — Phase 2's build report explicitly checked
this split and signed off on it "no cross-contamination observed"). **What Phase 2's
sign-off checked was `(doc_id, clause_no)` uniqueness for numbered clauses; it did not
check bare `chunk_id` uniqueness for `clause_no=null` chunks, and the two split
subdocuments both restart their own `<doc_id>__cNNN` counter from `c001` because they
share the same `doc_id` text.** Real bug, surfaced by this grounding pass, not by
Phase 2's own checklist — reported here rather than silently patched, since fixing
Phase 2's chunk_id generation is out of this plan's scope (Phase 2 is a signed-off,
built phase; the fix belongs there, not smuggled into Phase 3).

**Consequence for Phase 3: if `chunk_id` is used as the embedding-matrix row key without
a uniqueness check, this collision silently overwrites one row** — one of the two
`AEI-QP-T-03B__c001` chunks would simply vanish from `chunk_manifest.json` with no
error. **Decision: Phase 3's embedding step asserts `chunk_id` uniqueness across the
full chunk list before embedding anything, and hard-fails loudly if any duplicate
exists** — added to "Decisions locked," the pipeline, and the verification checklist
below.

**Root cause traced further, one session later — it's not really Phase 2's counter,
it's Phase 1 sharing one `blocks` array across both split halves. See Flag (f).**

**Hotfixed this session, directly on the artifact:** both `AEI-QP-T-03B__c001` chunks
(identical text — the shared-blocks bug in (f) means they were never just
same-ID, they were same-*content*) removed from
`data/artifacts/phase2/combined_complete_qms.json`. **503 → 501 chunks. Re-verified
501/501 unique `chunk_id`s, zero duplicates.** Phase 1's artifact/code and Phase 2's
code were left untouched, per instruction — this is a hand-edit of the Phase 2 artifact
only, a workaround for the symptom, not a fix for (f)'s root cause. It will not survive
a Phase 2 re-run against the current, still-buggy Phase 1 artifact.

---

## Decisions locked by this grounding pass

1. **Corpus = `combined_complete_qms.json` only** (§1). `quality_manual.json` is not
   re-embedded or re-indexed as a separate corpus.
2. **Checklist heading/item split = bold vs. non-bold, gated by number-column `x0`**
   (§2–3), verified corpus-wide at build time before being trusted, same discipline as
   every other structural rule in this project.
3. **Unnumbered-paragraph fallback for AEC's `8. Consistency…` gap** (§4), verified
   corpus-wide for other instances before being trusted.
4. **No query instruction on either side, under BGE-M3** (§5) — re-grounded against
   M3's own card, not carried over from the old model.
5. **BGE-M3, not `bge-large-en-v1.5`** (§6) — every chunk embeds whole under the
   8192-token context, confirmed 0/503 over the limit. No truncation, no
   truncate-and-log fallback, no chunk re-splitting.
6. **Hard CUDA assertion, no CPU fallback** (§7, Phase 0's FLAG-1) — applies to BGE-M3
   unchanged.
7. **`models/bge-m3/` is the verified project asset**, loaded by filesystem path via
   `settings.MODEL_DIR`, never a hub repo id (§8).
8. **Assert `chunk_id` uniqueness before embedding; hard-fail on any duplicate** (§9) —
   the one real collision found (`AEI-QP-T-03B__c001` ×2) is now hotfixed out of
   `combined_complete_qms.json` (503 → 501, Flag (f)), but the assertion stays in the
   pipeline as a permanent gate, not a one-time cleanup — Phase 1's root cause is still
   unfixed and a re-run of Phase 2 would reintroduce it.

---

## Artifact schema

`data/artifacts/phase3/`:

```
checklist_aqb.json         # parsed checklist items, AQB
checklist_aec.json         # parsed checklist items, AEC
chunk_embeddings.npy        # float32, shape (503, 1024), row order = chunk_manifest.json
chunk_manifest.json         # ["AEI-QM-T-01__c001", ...] — row i of the .npy is this chunk_id
item_embeddings_aqb.npy     # float32, shape (n_aqb_items, 1024)
item_embeddings_aec.npy     # float32, shape (n_aec_items, 1024)
bm25_corpus.json            # tokenized chunk text, keyed by chunk_id, for Phase 4 to build BM25Okapi from
```

Dimension is `1024` for BGE-M3 as well as the old model — coincidence, not an assumption
carried over unchecked; confirmed directly via `.encode()` in §8. No schema shape
changed by the model swap.

**Embeddings as `.npy` + a JSON id-manifest, not raw floats inside JSON** — every other
artifact in this project is JSON, so this is a real deviation worth flagging: 503×1024
floats as JSON text is ~15–20× larger on disk than a binary array and slower to
`json.load` every time Phase 4 or a later rebuild reads it, for a file nothing ever
hand-inspects. `.npy` is the standard format for exactly this. If this is unwanted,
alternative is a flat JSON list-of-lists — technically fine, just bigger and slower for
no real benefit at this corpus size (~600k floats).

**`bm25_corpus.json` stores tokens, not a pickled `BM25Okapi` object** — rebuilding
`BM25Okapi(tokens)` from stored tokens is cheap (milliseconds at this corpus size) and
avoids pinning a `rank-bm25` pickle format across versions. Phase 4 does the actual
rebuild + scoring; Phase 3 only tokenizes and stores.

Per checklist item (`checklist_aqb.json` / `checklist_aec.json`):

```json
{
  "source_pdf": "AUDIT_CHECKLIST_AQB.pdf",
  "items": [
    {
      "item_id": "AQB__4.2.1.1",
      "clause_no": "4.2.1.1",
      "ancestor_path": [
        {"clause_no": "4.2", "clause_title": "Quality Management System"},
        {"clause_no": "4.2.1", "clause_title": "QMS - General"}
      ],
      "text": "The organisation shall implement and maintain a fully documented quality management system which is certified and fully conforms to ISO 9001 and/or AS 9100...",
      "page_start": 1,
      "page_end": 1
    }
  ]
}
```

- `item_id` = `<AQB|AEC>__<clause_no>`, opaque per Phase 2's own `clause_no` precedent —
  the AEC `8. Consistency…` unnumbered fallback (§4) produces `#2`/`#3`… suffixed ids
  the same way Phase 2 handles source-typo duplicates.
- `ancestor_path` mirrors Phase 2's shape exactly (heading-only entries, root first) —
  same field name, same structure, so the frontend/API can treat checklist items and
  chunks uniformly wherever it needs to show a breadcrumb.
- No `doc_id`/`doc_name` — checklist items aren't chunks and don't belong to a QMS
  subdocument; `source_pdf` names which checklist.

---

## Pipeline

1. **Strip checklist PDF headers/footers/title block**, same read-before-strip
   discipline as Phase 1, own implementation (these PDFs never went through Phase 1).
2. **Flatten to rows** via PyMuPDF spans, grouped by y-proximity — reusing Phase 2's
   proven row-grouping approach, not reinventing it.
3. **Classify rows**: bold + numbered + number-column `x0` → heading; non-bold +
   numbered + number-column `x0` → item; unnumbered paragraph under an open heading with
   no numbered sibling on the page → item, per the AEC fallback (§4). Everything else is
   body continuation, appended to whichever item is open.
4. **Build the tree, emit leaf items only.** A heading's own text never becomes an item
   (`master_contextC.md`'s explicit rule) — headings only contribute to `ancestor_path`.
5. **Report counts and every ambiguous call** — headings excluded, items kept, the
   x0-column boundary actually observed per document, the unnumbered-paragraph
   instances found. Sign-off gate before Phase 4, matching `v2_plan.md`'s own
   requirement.
6. **Load `combined_complete_qms.json`.** Assert `torch.cuda.is_available()`, hard-fail
   if not. **Assert every `chunk_id` is unique across the full list, hard-fail with the
   offending ids if not** (§9) — this is a real, not hypothetical, gate: the artifact
   failed it once (`AEI-QP-T-03B__c001` ×2, hotfixed out this session, 503 → 501) and
   would fail it again on any future Phase 2 re-run until Flag (f)'s Phase 1 root cause
   is actually fixed. This step must not silently proceed by overwriting a
   vector-matrix row.
7. **Load `SentenceTransformer(settings.MODEL_DIR)`** (path, never a hub repo id — now
   `models/bge-m3`, per §8).
8. **Embed every chunk's `text` as-is, and every checklist item's `text` as-is** — no
   instruction prefix on either side, per §5. `normalize_embeddings=True` (cosine
   similarity in Phase 4 assumes unit vectors).
9. **Tokenize every chunk's `text`** for BM25 (lowercase, strip punctuation, whitespace
   split — plain, no stemming, matching `master_contextC.md`'s "word overlap" framing).
   Write `bm25_corpus.json`.
10. **Write all artifacts**, plus a short build report: chunk/item counts, confirmation
    that 0 chunks were truncated (8192-token context, §6), the checklist heading/item
    counts with the exclusion list.

---

## Verification checklist — before Phase 4 starts

- [x] Chunks in = vectors out: `chunk_embeddings.npy` row count == **501** ==
      `len(chunk_manifest.json)`. (**501, not 503** — the Flag (f) hotfix removed the 2
      `AEI-QP-T-03B__c001` duplicates before this phase ran; see build report.)
- [x] Checklist item counts reported, not assumed — **158 (AQB), 54 (AEC)**, full corpus,
      not a sample. Disagreement against this plan's own §2 estimate (158/49) and against
      `master_contextC.md`'s ~159/~52 shown in the build report, not smoothed over. (AEC
      was 48 for one interim run, before the synthesis follow-up — see "AEC synthesized
      items, final" in the build report.)
- [x] The AQB/AEC disagreement counts from §3 (phantom wrapped-line items) and §4
      (AEC's unnumbered paragraphs) resolved and reported — §3's fix (data-driven x0
      threshold) shipped as planned; §4 went through two rounds: implementation first
      shipped absorption (simpler, no synthetic ids), Abrar reversed that call, final
      shipped behavior is synthesis with a corpus-wide-grounded gate (`_nests_under`) —
      see the build report, not silently settled on the first answer.
      See build report.
- [x] The x0 number-column/body-column split confirmed clean across every page of both
      PDFs — `_numbered_column_threshold` asserts a minimum 15pt gap and would raise
      instead of guessing; it did not raise on either PDF. Real gaps: ~30pt (AQB), ~43pt
      (AEC).
- [x] 0 chunks exceed BGE-M3's 8192-token context — reconfirmed against the actual 501-
      chunk artifact this pipeline embedded, not the 503-chunk one this plan's §6 checked.
- [x] `torch.cuda.is_available()` was `True` for the actual embedding run — logged
      (`build_report.md`: `NVIDIA GeForce RTX 4050 Laptop GPU`), not assumed. (Ran at
      fp16, not fp32 — see build report, a real deviation forced by a real OOM.)
- [x] Neither checklist items nor chunks carry an instruction prefix — confirmed by
      reading `embed.py`'s `embed_texts`, the one function both paths call, with no
      prefix logic anywhere in it.
- [x] `chunk_id` uniqueness assertion ran and passed — `assert_chunk_id_uniqueness`
      executed before any embedding call; 501/501 unique, independently re-verified
      after the run (see build report).
- [x] `models/bge-m3/` loads with the hub unreachable — this is what actually happened,
      not a repeat of §8's synthetic test: the real build ran fully offline-capable,
      same local-path load code path §8 already proved.

---

## Explicitly out of scope for Phase 3

- BM25 scoring, the floor gate (`min_high_idf_terms`, `min_score`, `above_floor`
  tagging), cosine ranking, RRF fusion — all Phase 4.
- Any judgment about which chunk answers which checklist item — never in scope
  anywhere in this system.
- The API and UI — Phases 5–6.

---

## Flags for later phases

**(a) RESOLVED by the model change, kept here for the paper trail, not deleted.** The
original plan flagged that 17 truncated chunks would be semantically under-represented
under `bge-large-en-v1.5`. That risk no longer exists — BGE-M3's 8192-token context
covers every chunk whole (§6). If a future model change is ever considered again, re-run
§6's token check before assuming the premise still holds; don't inherit this
resolution on faith either.

**(b) `checklist_aqb.json` / `checklist_aec.json` item counts are not yet the final,
corpus-wide-verified numbers** — §2's 158/49 came from a regex-only first pass on
spot-checked pages, before the x0 fix and the AEC fallback were applied. The real,
final counts belong in this file's own build report once Phase 3 is actually built, per
the same "report what you find, don't assume" discipline as every other phase.

**(c) `item_id`'s `#2`/`#3` suffix convention for AEC's unnumbered fallback reuses Phase
2's `clause_no` disambiguation mechanism** — if Phase 2's own convention ever changes,
this needs to change with it, since it's explicitly modeled on it, not independently
invented.

**(d) Phase 2's `chunk_id` generation has a real bug** (§9): the `<doc_id>__cNNN`
counter is scoped by `doc_id` text, not by physical subdocument, so `AEI-QP-T-03B`'s two
independently-split subdocuments both emit `c001` and collide. **Correction, traced
further after this flag was first written: this is a downstream symptom, not the root
cause.** The counter-scoping is a real, separate gap (it would still be wrong even if
its input were clean), but the actual reason the two `c001` chunks collided *and* carried
identical text is upstream, in Phase 1 — see (f) below. Phase 2's counter fix (scope by
physical subdocument instance, not by `doc_id` string) is still real, outstanding work,
still belongs in `backend/app/pipeline/phase2/`, still out of scope here.

**(e) `models/bge-large-en-v1.5/` (1.3GB) is still on disk, now unused.** Not deleted —
wasn't requested, and removing a model asset isn't a call this plan makes unilaterally.
`config.py`'s `MODEL_DIR` no longer points at it (§8), so nothing in the pipeline reads
it anymore; it's inert, not silently still in play.

**(f) Phase 1 has a real bug: `AEI-QP-T-03B`'s two split subdocuments share one
`blocks` array instead of being partitioned — root cause of (d), found by direct
inspection of `data/artifacts/phase1/combined_complete_qms.json`, not fixed there.**
Both subdocument entries (`doc_id=AEI-QP-T-03B`, `doc_name="INTERNAL AUDIT CHECKLIST
(AEC)"` / `"(AQB)"`) have correctly-split metadata (`pdf_page_start/end` = 73–79 vs.
80–109) but byte-identical `blocks` lists — all 4 title-line blocks from *both* halves,
on *both* entries, confirmed via direct equality check
(`matches[0]["blocks"] == matches[1]["blocks"]` → `True`). Combined with Phase 1's
table rule discarding the checklist grid content from both halves (correct, deliberate —
verbatim duplicate of the standalone checklist PDFs, "no evidentiary value" per Abrar's
own call), each half's subdocument entry ends up as an **empty-shell subdocument**: no
real body, 4 shared title blocks, 0 tables. **Phase 1 has no rule to detect or drop a
subdocument whose entire body was removed by the table rule** — it just emits the
shell as-is, shared blocks and all. Both defects are deferred, not fixed:
- The blocks-sharing bug itself (why two subdocument entries point at the same 4
  blocks instead of 2+2).
- The missing "this subdocument's body is now empty, decide what to do with it" rule —
  right now nothing in Phase 1 or Phase 2 asks that question; Phase 2 just chunks
  whatever title text is there, which is how the collision surfaced as *chunks* rather
  than being caught earlier as an empty subdocument.

**The Phase 3 hotfix applied this session is a workaround for the symptom, not a fix for
either cause above.** Removed both `AEI-QP-T-03B__c001` chunks (identical content, one
per split half) directly from `data/artifacts/phase2/combined_complete_qms.json`:
**503 → 501 chunks.** `chunk_id` uniqueness reconfirmed clean afterward: 501/501 unique,
zero duplicates. Phase 1 code/artifacts and Phase 2 code were explicitly left untouched
per this session's instruction — the artifact was hand-edited, the generating code was
not. **This means Phase 1 and Phase 2's own artifacts/code, if ever regenerated, will
reproduce the bug and silently undo this hotfix** — whoever fixes (f) for real should
re-run Phase 2 afterward rather than assume this hand-edit persists.

**(g) AEC's `8. Consistency of PCN Examinations` section: 6 real audit questions had no
source number — resolved by synthesis, shipped, superseding this flag's original text.**
Abrar's explicit follow-up decision reversed this flag's original call (absorb into
`4.2.5.2`): **synthesize, don't absorb.** Shipped item_ids, in source order:
`AEC__4.2.5.2#2`, `#3`, `#4`, `#5`, `#6`, `#7` — the existing `#N` disambiguation
convention (`master_contextC.md`, Phase 2's `_dedup_clause_nos`), anchored to
`AEC__4.2.5.2` (the last real numbered item, not the governing heading `8` — every
existing `#N` precedent anchors to a leaf item, never a heading; see the build report's
"AEC synthesized items" section for the full anchor justification). `4.2.5.2` itself now
holds only its own real text, no longer the other 6 questions' text concatenated onto it.

**These 6 ids are synthesized, not source-printed — non-citable as-is.** They do not
appear on any printed page of `AUDIT_CHECKLIST_AEC.pdf`; an auditor citing one of these
in a real finding needs to cite the source paragraph text (quoted in the build report)
or the page (6), not the id `AEC__4.2.5.2#3` itself, which exists only inside this
system's own indexing. Same caveat already implicitly true for every other `#N`-suffixed
id in this project (`AEI-WI-T-01B`'s `5#2` doesn't appear in the PDF either — the base
number `5` does, printed twice) — worth stating explicitly here since this is the first
case where the *entire* id (not just the suffix) is absent from the source page.

**A generic version of the synthesis rule was tried first and rejected — real false
positives, not a hypothetical risk.** A plain "paragraph-gap splits an item's body into
multiple items" rule, run corpus-wide, fired 64 extra times in AQB and 17 extra times in
AEC on completely healthy items (NOTE sub-paragraphs, lettered/bulleted breakdowns
within one real requirement) — found by actually running it, not assumed safe. A
trailing-`?` refinement alone still left 10 AEC false positives. **Shipped gate: only
split when the item's own `clause_no` does not nest under its governing heading's
`clause_no`** (`_nests_under` in `checklist_parse.py`) — the same numbering mismatch
that is already the root cause of `4.2.5.2` being mis-numbered in the first place, not a
new special case. Confirmed corpus-wide: exactly one item in either PDF has this
mismatch (`AEC__4.2.5.2` under heading `8`), and gating on it reproduces exactly the
approved 6 questions, zero false positives, in both documents. **If a future checklist
revision introduces a similarly mis-numbered item elsewhere, this same generic gate will
apply there too — it is not hardcoded to `4.2.5.2` by identity.**

**(h) Embedding ran at fp16, not fp32 — a real precision deviation from this plan,
forced by a real OOM, not a precaution taken in advance.** The first real run crashed:
`CUDA out of memory` on the RTX 4050 Laptop's 6GB VRAM, fp32, `batch_size=32`. Fixed:
model loaded with `torch_dtype=float16`, `batch_size` dropped to 8 (`embed.py`). **Every
chunk and checklist item embedding in the shipped artifacts is fp16-precision, not
fp32.** Re-verified after the fix: every embedding's L2 norm ≈ 1.0, zero NaNs — fp16 is
still well past ranking-relevant precision for cosine similarity at this corpus size,
but **Phase 4's cosine scores are computed over fp16 vectors, and that fact should be in
the record, not buried in a commit.** If Phase 4 or later ever needs to re-embed (a
different model, a corpus update), the same 6GB ceiling applies — fp16 (or a smaller
batch size, or both) will likely be required again, not optional.

---

## Build report (2026-07-21)

Implementation: `backend/app/pipeline/phase3/` (`constants.py`, `checklist_rows.py`,
`checklist_parse.py`, `embed.py`, `bm25_index.py`, `build.py`, `reports.py`, `run.py`).
Run from `backend/`: `conda run -n audit python -m app.pipeline.phase3.run`.

**Output**, `data/artifacts/phase3/` (final, post-synthesis — see "AEC synthesized
items" below; superseded interim numbers from the first run are marked as such rather
than deleted):
- `checklist_aqb.json` — 158 items.
- `checklist_aec.json` — **54 items** (48 real + 6 synthesized, see below).
- `chunk_embeddings.npy` — `(501, 1024)` float32, row order = `chunk_manifest.json`.
- `chunk_manifest.json` — 501 chunk_ids.
- `item_embeddings_aqb.npy` — `(158, 1024)`. `item_embeddings_aec.npy` — **`(54, 1024)`**.
- `bm25_corpus.json` — 501 chunk_ids tokenized, 46,922 tokens total.
- `build_report.md` — machine-written summary of the same run, regenerated every run.

All artifacts independently re-verified after the run, not just trusted from the
pipeline's own report: chunk_manifest length matches embedding row count (501=501),
every chunk_id and item_id unique, zero NaNs, every embedding's L2 norm ≈ 1.0
(normalization confirmed applied, not just requested), `bm25_corpus.json`'s key set
equals `chunk_manifest.json`'s set exactly.

### Checklist parsing — real numbers, shown against every prior estimate, not reconciled to fit

| | `master_contextC.md`'s estimate | This plan's §2 (regex-only, spot-checked pages) | Actual, first run (regex fix only) | **Actual, final (post-synthesis)** |
|---|---|---|---|---|
| AQB items | ~159 | 158 | 158 | **158** |
| AEC items | ~52 | 49 | 48 | **54** |

**AQB matches almost exactly (158).** One real discrepancy against this *plan's own*
earlier informal count of 157 (not against the final 158) is worth recording: an early
grounding script (last session, not shipped code) joined a merged row's text in
y0-arrival order instead of x0 (left-to-right) order, and one row — AQB item
`4.2.1.3` — came out as `"- 4.2.1.3 The QMS shall comprise..."` (dash first) instead of
`"4.2.1.3 The QMS shall comprise of a Quality Manual -"` (dash trailing, the real
line-wrap hyphenation). The leading-dash version
doesn't match `NUMBERED_RE`, so that scratch script silently lost one item. This
implementation's `checklist_rows.py::_make_row` sorts a merged row's member lines by
`x0` before joining — the same left-to-right reconstruction Phase 2's own `rows.py`
already uses — which is what recovers `4.2.1.3` correctly. **158 is the real, correct
count; 157 was a scratch-script artifact, not a property of the document.**

**AEC is 54, not 49 (this plan's own estimate) and not ~52
(`master_contextC.md`'s).** The 49→48 delta is §3's fix working as designed (the "21
days from the date of the examination?" phantom wrapped-line item is correctly excluded
by the x0 threshold now, same mechanism as AQB's "2 years..." case). The 48→54 delta is
the synthesis follow-up below.

**SUPERSEDED — kept for the record, not deleted.** The paragraph below was this build
report's original call: absorb the 6 unnumbered questions into `4.2.5.2` rather than
synthesize. Abrar reviewed it and reversed the decision (see "AEC synthesized items,
final" immediately after this block) — the reasoning below is preserved because it's
still the honest record of what was tried and why, not because it's still the shipped
behavior.

> **The 52→48 delta is a real, deliberate design choice made during implementation,
> not a bug, and it deviates from what this plan originally proposed for §4 — reported
> here rather than silently shipped.** The plan's original proposal for AEC's `8.
> Consistency of PCN Examinations` section (2 mis-numbered items, `4.2.5.1`/`4.2.5.2` from
> a source typo, followed by 6 more real audit questions with no number at all) was a
> paragraph-gap heuristic that would synthesize 6 new item ids with `#2`/`#3`-style
> suffixes. **Implementing it raised a real question the plan hadn't settled: is an
> unnumbered paragraph in this source a separate citable requirement, or continuation
> prose of whichever numbered item is open?** Every other unnumbered-content rule in this
> whole project (Phase 2's zero-body absorption, orphan attachment, "nothing invented
> that isn't in the source") answers that question the same way: **body text belongs to
> whatever's currently open until the source itself opens something new.** Synthesizing
> 6 fresh item boundaries from a y-gap heuristic would have been the one place in this
> system inventing structure the source doesn't actually assert. **Decision: the 6
> unnumbered paragraphs are absorbed as body text into item `4.2.5.2`** (the last real
> numbered item before them) — no synthetic ids, no gap-detection code shipped, simpler
> than what was planned. Confirmed harmless to uniqueness (0 duplicate item_ids, AQB or
> AEC) and confirmed nothing is lost (`4.2.5.2`'s `text` is 904 characters, visibly
> containing all 6 questions concatenated — spot-checked directly, not assumed).
> **If Abrar wants those 6 treated as separately-addressable checklist items instead,
> that's a one-line product decision to revisit, not a bug to fix** — flagged in "Flags
> for later phases" below rather than decided unilaterally a second time.

### AEC synthesized items, final — Abrar reversed the absorb decision, grounded and shipped

Follow-up decision: **synthesize, don't absorb.** Grounded fresh against the real PDF
before any code changed — section 8 confirmed entirely on page 6 (page 7 opens clean
with heading `9`), exactly **6** paragraph breaks, not 5 or 7, each independently visible
via the same y-gap signal already used elsewhere in this parser (~11pt = line-wrap
continuation, ~17pt = new paragraph):

1. "Do they appear as examiners on the AQB scope of approval?"
2. "If "Yes" to 8.1 above, has the AQB effectively implemented CP09 compliant moderation processes to any such examiners?"
3. "What arrangements are in place for the outward and return transfer of exam materials to and from the AEC?"
4. "Are any such arrangements secure?"
5. "How does the AQB ensure that, at this AEC, a candidate is not given the same examination paper or practical specimen in any subsequent examination, including re-examination and recertification examination(s)?"
6. "For examinations conducted at this AEC, how does the AQB ensure that examination results notices (PCN24/PSL06) are sent to the BINDT Certification Records Office, the candidate and the individual paying the examination fee not later than 21 days from the date of the examination?"

**Anchor: `4.2.5.2` (the last real numbered item), not heading `8`.** Signed off by
Abrar before implementation. Justification: the `#N` suffix convention
(`master_contextC.md`, Phase 2's `_dedup_clause_nos`) disambiguates repeated occurrences
of a real **item-level** `clause_no` — every existing precedent (`AEI-WI-T-01B`'s
`5`/`5#2`) anchors to a leaf item, never a heading. Anchoring to heading `8` would be an
uninvented anchor shape. These 6 questions are structurally the continuation of the
same broken-numbering run that starts at `4.2.5.2` (the source simply stopped assigning
numbers) — anchoring to `4.2.5.2` is the minimal, most literal reuse of the existing
mechanism, not a new one.

**Final item_ids, source order:** `AEC__4.2.5.2` (unchanged, base — now holds only its
own real text) → `AEC__4.2.5.2#2` → `#3` → `#4` → `#5` → `#6` → `#7`.

**Implementation: a generic paragraph-gap-split mechanism was tried first, and it was
wrong — corpus-wide, not in theory.** Applying `_split_paragraphs` to every item's body
unconditionally fired **64 extra times in AQB and 17 extra times in AEC**, all on
genuinely healthy items — NOTE sub-paragraphs, lettered (`a) b) c)`) and bulleted
sub-clauses that are real parts of one requirement's body, not separate questions (e.g.
`AQB__4.2.1.3#2` = `"NOTE 1: Although the 2015 version of ISO9001 has removed..."`,
plainly still part of `4.2.1.3`'s own text). Found by actually running the generic rule
against the full corpus, not assumed safe from the one grounded case. A trailing-`?`
refinement (only split if the new paragraph is itself a complete question) cut AQB's
false positives to 0 but left AEC with 10 remaining false positives — insufficient
alone.

**Shipped gate:** split only when the item's own `clause_no` does not nest under its
governing heading's `clause_no` (`_nests_under` in `checklist_parse.py`) — i.e., only
when the item is *already* known-mis-numbered, the same condition that makes
`4.2.5.2` wrong in the first place. Confirmed by direct corpus-wide check: exactly one
item in either PDF meets this condition (`AEC__4.2.5.2` under heading `8`); gating on it
reproduces exactly the approved 6 questions in both PDFs, **zero false positives**. Not
hardcoded to `4.2.5.2` by name — a future mis-numbered item elsewhere would trigger the
same generic mechanism.

**Independently re-verified after the rebuild, by loading the artifacts fresh, not from
the pipeline's own log:**
- `checklist_aec.json`: 54 items (was 48).
- `item_embeddings_aec.npy` loaded fresh: shape `(54, 1024)`, matches item count, every
  norm ≈ 1.0, zero NaNs.
- All 54 AEC `item_id`s unique.
- All 6 synthesized items' `text` fields checked character-for-character against the
  grounded source paragraphs above: **exact match, all 6.**
- `AEC__4.2.5.2`'s `text` re-checked: now `'If "Yes" to 8.1 above, are the examiner(s)
  trained, appointed\nand authorised by the controlling AQB'` only — the 6 questions'
  text is no longer present in it.
- AQB unaffected: still 158 items, 0 synthesized (`_nests_under` never fires there).

`AQB__5.1.2` (used as a planned spot-check target in earlier testing) does not exist as
an item — checked directly, it's a real **heading** (`"5.1.1 AQB Staff - General"`,
`"5.1.2 AQB Staff - Staff Competence & Training"`, `"5.1.3 AQB Staff - Impartiality &
Confidentiality"` are all bold, 3-level headings; their items are 4-level,
`5.1.1.1`–`5.1.3.7`). The test's own premise was wrong, not the parser — caught by
running the check, not assumed correct.

The `_numbered_column_threshold` function's 15pt minimum-gap assertion (constants.py's
`MIN_COLUMN_GAP`) never fired on either PDF — real gaps found were ~30pt (AQB) and
~43pt (AEC), both comfortably clear. 0 orphan body rows (text arriving with nothing
open) on either PDF.

### Embedding — a real GPU OOM, not anticipated by the plan, fixed during the build

**§7/§8's CUDA checks passed as planned** — `torch.cuda.is_available()` was `True`,
`models/bge-m3` loaded from its local path. **But the first real run crashed**: `torch.
OutOfMemoryError: CUDA out of memory. Tried to allocate 4.43 GiB` on the RTX 4050
Laptop's 6GB VRAM, at `batch_size=32`, fp32. Not a hypothetical risk the plan flagged —
BGE-M3 (568M params, XLM-RoBERTa-large) at fp32 with the corpus's real length spread
(median ~70 tokens, one chunk at 6,091 under M3's tokenizer) genuinely doesn't fit in
6GB at that batch size. **Fixed: `batch_size` dropped to 8, model loaded at fp16
(`torch_dtype=float16`)** — halves activation memory and enables PyTorch's
memory-efficient SDPA attention path, which the fp32 load didn't use. Re-ran clean, no
OOM, all 501+158+48 texts embedded (48 AEC items — this was the interim, pre-synthesis
run; a second full rebuild after the AEC synthesis follow-up re-embedded
501+158+54, same fp16/batch_size=8 config, same clean result, norms re-checked again).
**This is a real, reportable deviation from the plan** (which specified no dtype), not a
silent implementation detail — fp16 embeddings are lower-precision than what was
implicitly assumed; every L2 norm was independently re-checked at ≈1.0 after the fp16
switch (both runs) and found fine, but this is the kind of change that belongs in the
record, not buried in a commit. See Flag (h) for the forward-facing consequence.

### Chunk_id uniqueness assertion — exercised for real, not just written

`assert_chunk_id_uniqueness` ran against the **501-chunk**, already-hotfixed artifact
(the `AEI-QP-T-03B__c001` collision from Flag (f) was removed before this phase ran, in
the same session, per explicit instruction) — so it passed, not because the check is
untested, but because the known collision was already gone. Independently re-verified
after the run by loading `chunk_manifest.json` fresh and checking `len(ids) ==
len(set(ids))`: **501 == 501.**

### Verified, as the checklist above requires

- 0 chunks exceed BGE-M3's 8192-token context in the actual 501-chunk artifact this
  pipeline read (re-derived from `model.max_seq_length` matching the embedding run
  itself, not a separate assumption).
- Every embedding (chunk and item) has L2 norm ≈ 1.0, zero NaNs.
- `bm25_corpus.json`'s chunk_id set equals `chunk_manifest.json`'s set exactly.
- No instruction prefix anywhere — `embed.py::embed_texts` is the one function both
  chunks and items go through, and it has no prefix branch.

### Still outstanding

- ~~Whether AEC's 6 absorbed unnumbered questions under `4.2.5.2` should instead be
  separately-addressable checklist items~~ — **resolved.** Abrar decided synthesize;
  shipped, see "AEC synthesized items, final" above and Flag (g).
- Phase 1's Flag (f) root cause (shared `blocks` array) is still unfixed; this phase's
  501-chunk count depends on the hand-edit surviving until someone fixes it properly.
- Phase 4 onward — ranking, the floor gate, RRF, the API, the UI — unchanged, not
  started. Phase 4 must be aware embeddings are fp16 (Flag (h)) when computing cosine
  scores.
