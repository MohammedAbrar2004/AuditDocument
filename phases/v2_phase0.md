# Phase 0 — Environment & scaffolding setup

Status: **DONE.** Built and verified. See "Build report" at the bottom for what actually
happened and where it deviated from plan.

Read `master_context.md` and `plan.md` first. This phase exists because Phase 1 needs a
running backend, a verified environment, and known-good file paths before any chunking
logic gets written. Phase 0 builds none of the pipeline. No extraction, no chunking, no
embedding code. Setup only.

---

## Environment audit — done, findings below

Ran directly against the `audit` conda env on this machine. Not assumed — checked.

| Component | Found | Status |
|---|---|---|
| Python | 3.11.15 | matches master_context |
| conda env | `audit` exists | ready |
| GPU | RTX 4050 Laptop, 6141 MiB VRAM | confirmed working |
| torch | 2.13.0+cu132, `cuda.is_available() == True` | confirmed |
| PyMuPDF (`fitz`) | 1.28.0 | installed |
| pdfplumber | 0.11.4 | installed |
| sentence-transformers | 5.6.0 | installed |
| transformers | 5.13.1 | installed |
| rank-bm25 | 0.2.2 | installed |
| fastapi | 0.115.6 | installed |
| uvicorn | 0.34.0 | installed |
| pydantic / pydantic-settings | 2.10.4 / 2.7.1 | installed |
| python-multipart | 0.0.32 | installed (needed for FastAPI file upload) |
| python-dotenv | 1.0.1 | installed |
| numpy / scipy / scikit-learn | 2.2.1 / 1.17.1 / 1.9.0 | installed |
| pytest | 8.3.3 | installed |
| node / npm | v24.15.0 / 11.12.1 | installed |
| frontend `node_modules` | present | already `npm install`-ed |
| frontend `dist/` | present | already built once |

**Conclusion: zero new installs required.** Everything master_context's tech-stack section
promises is already present and working, including GPU+CUDA and the embedding model
weights. Phase 0 does not need a `pip install` step. If Phase 1+ needs something not
listed above (e.g. a specific tokenizer extra), install it then, not speculatively now.

---

## What Phase 0 actually builds

### 1. Git — out of scope
User handles git/github themselves. Claude Code does not run `git init`, `add`, or
`commit` in this project. Not part of Phase 0.

### 2. Rename source PDFs to the underscore convention
`docs/` filenames currently use spaces/parens; master_context.md and plan.md reference
underscore names. **Decision: rename the files on disk** to match:

| Current name | Renamed to |
|---|---|
| `COMBINED Complete QMS.pdf` | `COMBINED_Complete_QMS.pdf` |
| `QUALITY MANUAL.pdf` | `QUALITY_MANUAL.pdf` |
| `AUDIT CHECKLIST (AQB).pdf` | `AUDIT_CHECKLIST_AQB.pdf` |
| `AUDIT CHECKLIST (AEC).pdf` | `AUDIT_CHECKLIST_AEC.pdf` |

The 2 unreferenced PDFs (`Audit Report PCN24-CP09A NDT AQB.pdf`,
`Audit Report PCN24-CP14C.pdf`) are left untouched and ignored — out of scope per your
call, revisit later if needed.

### 3. Backend scaffold
`backend/` is currently an empty directory. Phase 0 creates the minimum skeleton Phase 1
will import into — not pipeline logic, just wiring:

```
backend/
  app/
    main.py           # FastAPI() instance, CORS middleware, /health route
    config.py          # pydantic-settings: DOCS_DIR, ARTIFACTS_DIR, MODEL_DIR, CORS origins
  requirements.txt     # pinned versions, documents the audit env (see table above)
```

- CORS configured to allow `http://127.0.0.1:5173` / `http://localhost:5173` (frontend
  dev origin) — otherwise the frontend's `fetch` calls in `src/api/client.ts` will be
  blocked by the browser once Phase 5 wires them up.
- `config.py` resolves `DOCS_DIR` → `../docs`, `ARTIFACTS_DIR` → `../data/artifacts`,
  `MODEL_DIR` → `../models/bge-large-en-v1.5` (see "BGE model as a project asset" below)
  so Phase 1/3 never hardcode paths.
- No routers, services, or models beyond `/health` — those get added by the phase that
  needs them (Phase 5 per plan.md), not speculatively now.

**`.env` — contents, or why there isn't one.** There are no secrets anywhere in this
system: no API keys, no credentials, nothing external is called. If `config.py` needs
local overrides at all, they're just path overrides
(`DOCS_DIR=`, `ARTIFACTS_DIR=`, `MODEL_DIR=`) with the same defaults baked into
`config.py` already — so a `.env` file adds no real value at Phase 0. **Decision: don't
create one.** `config.py`'s defaults are the only source of truth for now. If a later
phase actually needs a local override, it goes at the **project root** (`v2/.env`), never
inside `backend/`, and Abrar handles `.gitignore` for it himself — Phase 0 doesn't touch
git.

### 4. Data artifact directories
Per master_context's "Where to look for what" table, `data/artifacts/phaseN/` is a
top-level sibling of `docs/`, `backend/`, `frontend/`, `phases/`. Phase 0 creates:

```
data/artifacts/phase1/.gitkeep
data/artifacts/phase2/.gitkeep
data/artifacts/phase3/.gitkeep
data/artifacts/phase4/.gitkeep
```

Empty. Phase 1 writes the first real file here.

### 5. Frontend verification (no code changes) + delete stale `dist/`
Frontend is already built per master_context. Phase 0 *verifies*, doesn't modify source:
- `npm run dev` boots on 5173.
- `.env`'s `VITE_API_BASE_URL=http://127.0.0.1:8000` matches the backend's actual port.
- No component changes — Phase 6 is where frontend wiring happens.

**Delete `frontend/dist/`.** It's a stale build from before the chunk shape in
plan.md was settled — it expects response fields that don't match plan.md's schema
(`doc_id`, ancestor path, tables inline, no separate tables field). Nobody should serve
it. Deleting it in Phase 0 means there's no ghost build lying around to accidentally
open and debug against later. **Frontend is `npm run dev` only until Phase 6** rebuilds
it against the real API.

### 6. BGE model as a project asset — done, verified below

`BAAI/bge-large-en-v1.5` used to live only in the global HF hub cache, outside the
project, resolved by revision hash. That makes the one asset the entire semantic view
depends on invisible to the project and silently swappable — if the cache is cleared or
upstream serves a different revision, every vector changes and nothing downstream
notices. **Fixed:** the resolved snapshot has been copied out of the cache into
`models/bge-large-en-v1.5/` at the project root, as plain files. This is deliberate —
the model is a project asset, the same way the PDFs in `docs/` are. Phase 3 loads it
from disk by path. No revision resolution, no cache lookup, no upstream involved, ever.

**Source:** HF cache snapshot `d4aa6901d3a41ba39fb536a557fa166f842b0e09` (the `main` ref
at copy time). Confirmed real files, not symlinks, before copying (`find -type l` on the
snapshot dir returned nothing).

**Destination:** `models/bge-large-en-v1.5/` — **1.3 GB**, 11 files:

```
models/bge-large-en-v1.5/
  1_Pooling/config.json
  README.md
  config.json
  config_sentence_transformers.json
  model.safetensors          (1,340,616,616 bytes — the weights)
  modules.json
  sentence_bert_config.json
  special_tokens_map.json
  tokenizer.json
  tokenizer_config.json
  vocab.txt
```

**Verified, not assumed** — ran with `HF_HUB_OFFLINE`/`HF_HOME`/`HF_HUB_CACHE` all
unset (so nothing could quietly fall back to offline-cache behavior):
- `SentenceTransformer("models/bge-large-en-v1.5", device="cuda")` loads successfully
  from the plain path.
- No hub warning printed (contrast: loading the same model *by repo id* from the HF
  cache, even with `HF_HUB_OFFLINE=1` set, prints `"unauthenticated requests to the HF
  Hub"` — this local-path load printed nothing of the sort, confirming the hub is never
  contacted).
- Loaded on `cuda:0`.
- Embedding dimension: **1024**, confirmed via `.encode()` on a test string
  (`encode shape: (1, 1024)`).

`config.py`'s `MODEL_DIR` will point at `models/bge-large-en-v1.5` (resolved relative to
the project root). Phase 3 loads `SentenceTransformer(settings.MODEL_DIR)` — never a
hub repo id. **Abrar adds `models/` to `.gitignore` himself** — Phase 0 doesn't touch
git.

### 7. Smoke test — proves the two halves talk before Phase 1 starts
- Start backend (`uvicorn app.main:app --port 8000`), confirm `GET /health` → 200.
- Start frontend (`npm run dev`), load in browser, confirm a `fetch` to
  `http://127.0.0.1:8000/health` succeeds from the page (CORS actually works, not just
  configured).
- Both processes stopped cleanly after the check — Phase 0 doesn't leave servers
  running.

---

## Decisions — resolved

1. **Git** — out of scope. User handles git/github. No repo init, no commits, by Claude
   Code in this project, ever, unless explicitly asked later.
2. **Filenames** — rename to underscore convention (table above). Real on-disk names
   will match master_context/plan.md exactly after Phase 0 runs.
3. **The 2 unreferenced audit-report PDFs** — ignored for now. Left untouched in
   `docs/`, out of scope for Phases 1–6. Revisit later if needed.

---

## Verification checklist — before Phase 1 starts

- [x] `backend/` boots (`uvicorn app.main:app --port 8000`), `/health` → 200
- [x] `frontend/` boots (`npm run dev` on 5173), loads in browser
- [x] Frontend → backend `fetch` succeeds (CORS confirmed working, not just configured)
- [x] `data/artifacts/phase{1,2,3,4}/` exist, empty
- [x] `phases/` — already exists (this file lives in it); one of master_context's four
  top-level dirs, listed here so it's not silently assumed
- [x] The 4 core `docs/` PDFs renamed and match master_context.md's names exactly
- [x] `frontend/dist/` deleted — no stale build with the old chunk shape left to serve
- [x] `models/bge-large-en-v1.5/` present, loads by path on CUDA with zero hub
  involvement, dim 1024 — **done and verified above**

## Explicitly out of scope for Phase 0

- Any PDF extraction, segmentation, chunking, embedding, or ranking code — that's
  Phases 1–4.
- Any new frontend components or API wiring — that's Phases 5–6.
- Git init/add/commit — user's own domain, not Claude Code's.
- The 2 unreferenced audit-report PDFs.

---

## Build report

Everything in "What Phase 0 actually builds" was executed as planned. Details and the
handful of deviations below.

### What exists now

```
v2/
  docs/
    COMBINED_Complete_QMS.pdf
    QUALITY_MANUAL.pdf
    AUDIT_CHECKLIST_AQB.pdf
    AUDIT_CHECKLIST_AEC.pdf
    Audit Report PCN24-CP09A NDT AQB.pdf   (untouched, ignored)
    Audit Report PCN24-CP14C.pdf            (untouched, ignored)
  models/
    bge-large-en-v1.5/                      (1.3 GB, verified in Phase 0 planning pass)
  data/
    artifacts/
      phase1/.gitkeep
      phase2/.gitkeep
      phase3/.gitkeep
      phase4/.gitkeep
  backend/
    requirements.txt
    app/
      __init__.py
      config.py
      main.py
  frontend/                                 (dist/ deleted, source untouched)
  phases/
    v2_phase0.md
```

### Deviations from plan

1. **`backend/app/__init__.py` added.** Not called out explicitly in the original file
   tree in this doc. Empty file, makes `app` an explicit package rather than relying on
   Python 3's implicit namespace packages — one line of certainty, no behavior change.

2. **No `.env` created** — matches the decision already recorded above, confirmed as
   the final state. `config.py`'s defaults are the only source of truth.

3. **`requirements.txt` pins `torch==2.13.0`, not `2.13.0+cu132`.** The `+cu132` local
   version tag isn't resolvable from plain PyPI — installing this file elsewhere needs
   PyTorch's own index. Added a comment with the actual install command
   (`--index-url https://download.pytorch.org/whl/cu132`) instead of a version string
   pip can't act on.

4. **CORS verified by simulated `Origin` header, not a browser E2E test.** Ran
   `curl -H "Origin: http://localhost:5173"` against `/health` (both a plain GET and an
   `OPTIONS` preflight) and confirmed `Access-Control-Allow-Origin:
   http://localhost:5173` came back correctly — this is the exact check a browser
   performs, just driven from curl instead of an actual browser tab. No Playwright/
   headless-browser run, since there's no frontend code change yet to exercise beyond
   the static `/health` wiring.

5. **Vite binds `[::1]:5173` (IPv6), not `127.0.0.1:5173` (IPv4), on this machine.**
   `netstat` confirmed it: backend listens on `127.0.0.1:8000` explicitly, but
   `npm run dev` only listens on the IPv6 loopback. `curl http://127.0.0.1:5173/` got
   connection-refused (`000`); `curl http://localhost:5173/` got `200`. Not a bug — just
   means **use `http://localhost:5173`, not `http://127.0.0.1:5173`**, when opening the
   frontend by hand or scripting anything against it later. `docs`/`config.py` already
   only ever reference the *backend* by `127.0.0.1:8000`, which is unaffected.

6. **Both dev servers were started, checked, and force-killed** (`taskkill /F`) as part
   of the smoke test — bash job control (`kill %1`) didn't track the backgrounded
   processes across tool calls on this Windows/Git-Bash setup, so they were found by
   port via `netstat -ano` and killed by PID instead. Confirmed dead afterward (both
   endpoints returned connection-refused). No servers left running.

### Verified results

- `GET /health` → `200 {"status":"ok"}`.
- CORS: actual-request and preflight both return
  `access-control-allow-origin: http://localhost:5173`.
- Frontend (`npm run dev`) built and served `index.html` successfully on
  `http://localhost:5173/` (Vite v5.4.21, ready in 1141 ms).
- All 4 core `docs/` PDFs renamed, confirmed on disk.
- `frontend/dist/` confirmed deleted.
- `data/artifacts/phase{1,2,3,4}/` confirmed present and empty (`.gitkeep` only).

**Phase0 is completed**
**Phase 1 is unblocked.**

---

## Flags for later phases

Carried forward from Phase 0. These are not Phase 0 work — they are facts or risks that
Phase 0 uncovered and that a later phase must act on. Do not let them get lost.

### FLAG-1 → Phase 3: assert CUDA before embedding. Do not fall back to CPU.
**What's wrong.** `requirements.txt` pins `torch==2.13.0`, not `2.13.0+cu132`. The
`+cu132` local version tag is not resolvable from plain PyPI, so pinning it exactly
would make the file uninstallable. The correct install command is in a comment in
`requirements.txt` — but a comment does not stop `pip`.

**What that causes.** A plain `pip install -r requirements.txt` resolves `torch==2.13.0`
to the **CPU build**. Nothing errors. Phase 3 then embeds the whole corpus plus every
checklist item on CPU — hours instead of minutes — and silently succeeds. The vectors
are fine; only the time is wrong, so nothing downstream would ever notice.

**How to fix it.** Phase 3 must check `torch.cuda.is_available()` before loading the
model and **fail loudly** if it is False. No CPU fallback, no warning-and-continue.
A hard stop. If someone genuinely wants CPU later, that becomes an explicit, deliberate
override — never a default anyone can trip into.

### FLAG-2 → any phase that touches the frontend by URL: use `localhost:5173`.

On this machine Vite binds the **IPv6 loopback only** (`[::1]:5173`). Confirmed by
`netstat`: `curl http://127.0.0.1:5173/` → connection refused; `curl
http://localhost:5173/` → 200.

Scope: this affects **opening or scripting against the frontend**, nothing else. The
backend listens on `127.0.0.1:8000` explicitly and is unaffected — and that is the only
address the frontend ever calls, so `config.py` and the CORS origins need no change.

### FLAG-3 → provenance: this file is the only record of the model's origin.

`models/bge-large-en-v1.5/` was copied from HF cache snapshot
`d4aa6901d3a41ba39fb536a557fa166f842b0e09` (the `main` ref at copy time). The model
directory itself carries no revision marker — that was the point of flattening it. This
document is the only place that hash exists. Do not lose it.