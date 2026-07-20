"""CLI entrypoint — builds both Phase 1 artifacts and the two sign-off
reports (empty_table_report.md, diagram_page_report.md) from the real
pipeline code, not the grounding scratch scripts. Run from `backend/`:

    conda run -n audit python -m app.pipeline.phase1.run
"""
import json
import sys

from app.config import settings
from app.pipeline.phase1.build import build_artifact
from app.pipeline.phase1.reports import write_diagram_page_report, write_empty_table_report

SOURCES = [
    ("QUALITY_MANUAL.pdf", "quality_manual.json"),
    ("COMBINED_Complete_QMS.pdf", "combined_complete_qms.json"),
]


def main():
    phase1_dir = settings.ARTIFACTS_DIR / "phase1"
    phase1_dir.mkdir(parents=True, exist_ok=True)

    artifacts = {}
    for pdf_name, out_name in SOURCES:
        pdf_path = settings.DOCS_DIR / pdf_name
        print(f"Processing {pdf_name} ...", flush=True)
        artifact = build_artifact(pdf_path, pdf_name)

        stats = artifact["_table_stats"]
        persisted = {k: v for k, v in artifact.items() if not k.startswith("_")}

        out_path = phase1_dir / out_name
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(persisted, f, indent=2, ensure_ascii=False)

        n_subdocs = len(persisted["subdocuments"])
        n_blocks = sum(len(sd["blocks"]) for sd in persisted["subdocuments"])
        n_tables_kept = sum(len(sd["tables"]) for sd in persisted["subdocuments"])
        print(
            f"  -> {out_path.name}: {n_subdocs} subdocuments, {n_blocks} blocks, "
            f"{n_tables_kept} tables kept, {stats['discarded']} tables discarded "
            f"(of {stats['total_stitched_tables']} stitched)",
            flush=True,
        )

        artifacts[pdf_name] = artifact  # keeps _table_stats / _diagram_page_report for reports

    report_path = write_empty_table_report(artifacts, phase1_dir)
    print(f"Wrote {report_path}", flush=True)

    diagram_report_path = write_diagram_page_report(artifacts, phase1_dir)
    print(f"Wrote {diagram_report_path}", flush=True)


if __name__ == "__main__":
    sys.exit(main() or 0)
