"""CLI entrypoint -- builds every Phase 4 artifact from the real Phase 3
artifacts. Run from `backend/`:

    conda run -n audit python -m app.pipeline.phase4.run
"""
import json
import sys

from app.config import settings
from app.pipeline.phase4.build import build_artifacts
from app.pipeline.phase4.reports import write_build_report


def main():
    phase4_dir = settings.ARTIFACTS_DIR / "phase4"
    phase4_dir.mkdir(parents=True, exist_ok=True)
    phase3_dir = settings.ARTIFACTS_DIR / "phase3"

    print("Scoring + ranking every checklist item against the corpus ...", flush=True)
    artifacts = build_artifacts(phase3_dir)

    for prefix, data in artifacts.items():
        path = phase4_dir / f"rankings_{prefix.lower()}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        print(f"  -> {path.name}: {data['n_items']} items x {data['n_chunks']} chunks x 3 views", flush=True)

    report_path = phase4_dir / "build_report.md"
    write_build_report(phase3_dir, phase4_dir, report_path)
    print(f"  -> {report_path.name}", flush=True)

    print("\nDone.", flush=True)


if __name__ == "__main__":
    sys.exit(main() or 0)
