"""CLI entrypoint -- builds every Phase 3 artifact from the real pipeline
code. Run from `backend/`:

    conda run -n audit python -m app.pipeline.phase3.run
"""
import json
import sys

import numpy as np

from app.config import settings
from app.pipeline.phase3.build import build_artifacts
from app.pipeline.phase3.reports import write_build_report


def main():
    phase3_dir = settings.ARTIFACTS_DIR / "phase3"
    phase3_dir.mkdir(parents=True, exist_ok=True)
    phase2_dir = settings.ARTIFACTS_DIR / "phase2"

    print("Parsing checklists, loading chunks, embedding on GPU ...", flush=True)
    artifacts = build_artifacts(settings.DOCS_DIR, phase2_dir)

    for prefix in ("AQB", "AEC"):
        data = artifacts["checklists"][prefix]
        out = {"source_pdf": data["source_pdf"], "items": data["items"]}
        path = phase3_dir / f"checklist_{prefix.lower()}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
        print(f"  -> {path.name}: {len(data['items'])} items", flush=True)

    np.save(phase3_dir / "chunk_embeddings.npy", artifacts["chunk_embeddings"])
    with open(phase3_dir / "chunk_manifest.json", "w", encoding="utf-8") as f:
        json.dump(artifacts["chunk_manifest"], f, indent=2, ensure_ascii=False)
    print(f"  -> chunk_embeddings.npy: {artifacts['chunk_embeddings'].shape}", flush=True)

    for prefix in ("AQB", "AEC"):
        vecs = artifacts["item_embeddings"][prefix]
        path = phase3_dir / f"item_embeddings_{prefix.lower()}.npy"
        np.save(path, vecs)
        print(f"  -> {path.name}: {vecs.shape}", flush=True)

    with open(phase3_dir / "bm25_corpus.json", "w", encoding="utf-8") as f:
        json.dump(artifacts["bm25_corpus"], f, ensure_ascii=False)
    print("  -> bm25_corpus.json", flush=True)

    report_path = phase3_dir / "build_report.md"
    write_build_report(artifacts, report_path)
    print(f"  -> {report_path.name}", flush=True)

    print("\nDone.", flush=True)


if __name__ == "__main__":
    sys.exit(main() or 0)
