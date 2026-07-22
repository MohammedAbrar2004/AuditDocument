"""Paths into the per-document upload scope (v2_phase5.md SS2/SS3) --
physically separate from ARTIFACTS_DIR/phase{1,2,3,4}, which stay the
untouched reference-corpus fixtures every earlier phase's own numbers are
checked against.

Single-active-document model: `clear_scope()` deletes and recreates the
whole per-document folder before every new upload. Not accumulated, no
multi-document library (v2_plan.md, Phase 5 section: "Clean-rewrite on
every new upload: overwritten or cleared, not accumulated").
"""
import shutil

from app.config import settings

UPLOAD_DIR = settings.UPLOAD_DIR


def source_pdf_path():
    return UPLOAD_DIR / "source.pdf"


def phase1_path():
    return UPLOAD_DIR / "phase1.json"


def phase2_path():
    return UPLOAD_DIR / "phase2.json"


def chunk_manifest_path():
    return UPLOAD_DIR / "chunk_manifest.json"


def chunk_embeddings_path():
    return UPLOAD_DIR / "chunk_embeddings.npy"


def bm25_corpus_path():
    return UPLOAD_DIR / "bm25_corpus.json"


def gate_path():
    return UPLOAD_DIR / "gate.json"


def rankings_path(prefix: str):
    return UPLOAD_DIR / f"rankings_{prefix.lower()}.json"


def build_report_path():
    return UPLOAD_DIR / "build_report.md"


def clear_scope() -> None:
    if UPLOAD_DIR.exists():
        shutil.rmtree(UPLOAD_DIR)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
