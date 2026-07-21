"""CLI entrypoint -- builds both Phase 2 artifacts plus the two sign-off
reports (coverage_report.md, block_homogeneity_report.md) from the real
pipeline code. Run from `backend/`:

    conda run -n audit python -m app.pipeline.phase2.run
"""
import json
import sys

from app.config import settings
from app.pipeline.phase2.build import build_artifact
from app.pipeline.phase2.reports import (
    block_homogeneity_check,
    reconcile_source_lines,
    write_block_homogeneity_report,
    write_coverage_report,
)

SOURCES = [
    ("quality_manual.json", "quality_manual.json"),
    ("combined_complete_qms.json", "combined_complete_qms.json"),
]


def main():
    phase1_dir = settings.ARTIFACTS_DIR / "phase1"
    phase2_dir = settings.ARTIFACTS_DIR / "phase2"
    phase2_dir.mkdir(parents=True, exist_ok=True)

    coverage_results = []
    all_debug_combined = []

    for in_name, out_name in SOURCES:
        in_path = phase1_dir / in_name
        print(f"Processing {in_name} ...", flush=True)
        with open(in_path, "r", encoding="utf-8") as f:
            phase1_artifact = json.load(f)

        artifact, all_debug = build_artifact(phase1_artifact)
        all_debug_combined.append((artifact["source_pdf"], all_debug))

        out_path = phase2_dir / out_name
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(artifact, f, indent=2, ensure_ascii=False)

        n_chunks = len(artifact["chunks"])
        n_with_ancestor = sum(1 for c in artifact["chunks"] if c["ancestor_path"])
        n_trailing = sum(1 for d in all_debug if d["trailing_absorbed"])
        print(
            f"  -> {out_path.name}: {n_chunks} chunks, "
            f"{n_with_ancestor} with a non-empty ancestor_path, "
            f"{n_trailing} subdocuments hit the trailing-absorb fallback",
            flush=True,
        )

        coverage_results.append(reconcile_source_lines(artifact["source_pdf"], all_debug))

    coverage_path = phase2_dir / "coverage_report.md"
    write_coverage_report(coverage_results, coverage_path)
    print(f"Wrote {coverage_path}", flush=True)

    all_debug_flat = [d for _, debugs in all_debug_combined for d in debugs]
    homog_result = block_homogeneity_check(all_debug_flat)
    homog_path = phase2_dir / "block_homogeneity_report.md"
    write_block_homogeneity_report(homog_result, homog_path)
    print(f"Wrote {homog_path}", flush=True)

    total_unaccounted = sum(len(r["unaccounted"]) for r in coverage_results)
    total_tables_missing = sum(len(r["tables_not_attached"]) for r in coverage_results)
    print(
        f"\nCoverage: {total_unaccounted} unaccounted source lines, "
        f"{total_tables_missing} tables not attached (both should be 0).",
        flush=True,
    )


if __name__ == "__main__":
    sys.exit(main() or 0)
