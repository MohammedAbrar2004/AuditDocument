"""Upload / indexing endpoints -- the write side of the per-document scope
(v2_phase5.md Design). `upload_document` and `index_document` are declared
as plain `def` (not `async def`) so Starlette dispatches them through its
worker thread pool (`run_in_threadpool`, confirmed by reading
starlette/routing.py directly) instead of running them on the single
asyncio event loop -- Stage A/B can then run for however long they need
without stalling concurrent requests like `/documents/status` or `/health`.
Neither uvicorn nor anyio's thread runner imposes any per-task execution
timeout (confirmed by reading both packages' source directly, v2_phase5.md
build report SS"300s timeout ceiling") -- there is nothing in this stack
that kills a long-running request on its own.
"""
import json

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.pipeline.upload import orchestrate, store
from app.schemas.documents import IndexResponse, StatusResponse, UploadResponse
from app.state import app_state

router = APIRouter(prefix="/documents", tags=["documents"])

MAX_UPLOAD_MB = 200


@router.post("/upload", response_model=UploadResponse)
def upload_document(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF uploads are accepted.")

    pdf_bytes = file.file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(pdf_bytes) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413, detail=f"File exceeds the {MAX_UPLOAD_MB}MB limit."
        )

    summary = orchestrate.run_stage_a(pdf_bytes, file.filename)
    return summary


@router.post("/index", response_model=IndexResponse)
def index_document():
    if not store.phase2_path().exists():
        raise HTTPException(
            status_code=409,
            detail="No uploaded document -- POST /documents/upload first.",
        )
    try:
        summary = orchestrate.run_stage_b(app_state.model, app_state.checklists)
    except ValueError as e:
        # e.g. a chunk_id collision from assert_chunk_id_uniqueness -- a real
        # pre-existing defect this document's own Phase 1/2 run surfaced, not
        # a malformed request. Surfaced as a clean 422, not a raw 500.
        raise HTTPException(status_code=422, detail=str(e))
    return summary


@router.get("/status", response_model=StatusResponse)
def document_status():
    if not store.phase1_path().exists():
        return {"state": "none"}

    p1 = json.loads(store.phase1_path().read_text(encoding="utf-8"))
    filename = p1["source_pdf"]
    subdoc_count = len(p1["subdocuments"])

    chunk_count = None
    if store.phase2_path().exists():
        p2 = json.loads(store.phase2_path().read_text(encoding="utf-8"))
        chunk_count = len(p2["chunks"])

    indexed = store.rankings_path("AQB").exists() and store.rankings_path("AEC").exists()
    if not indexed:
        return {
            "state": "uploaded",
            "filename": filename,
            "subdocument_count": subdoc_count,
            "chunk_count": chunk_count,
        }

    gate = json.loads(store.gate_path().read_text(encoding="utf-8"))
    zero_pass = {}
    for prefix in ("AQB", "AEC"):
        data = json.loads(store.rankings_path(prefix).read_text(encoding="utf-8"))
        zero = sum(
            1
            for item in data["items"].values()
            if not any(e["above_floor"] for e in item["keyword"])
        )
        zero_pass[prefix] = {"n_items": len(data["items"]), "zero_pass": zero}

    return {
        "state": "indexed",
        "filename": filename,
        "subdocument_count": subdoc_count,
        "chunk_count": chunk_count,
        "gate": gate,
        "zero_pass": zero_pass,
    }


@router.get("/file")
def document_file():
    path = store.source_pdf_path()
    if not path.exists():
        raise HTTPException(status_code=404, detail="No document uploaded.")
    return FileResponse(path, media_type="application/pdf")
