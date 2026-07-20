"""Grounded constants for Phase 1 extraction. Every threshold here traces back
to a specific measurement against the real PDFs, documented in
phases/v2_phase1.md and data/artifacts/phase1/empty_table_report.md — none of
these are guesses.
"""
import re

# --- Header (Template A: standard 3x7 table) ------------------------------
HEADER_LABELS = [
    "DOCUMENT NAME",
    "DOCUMENT NO.",
    "REVISION",
    "REVISED DATE",
    "ISSUE DATE",
    "PAGE NO.",
]

# --- Header (Template B: free-text form, e.g. AEI-QM-T-01D) ---------------
# Grounded on PDF pages 41-46 (round 1, item 3): header spans all sit at
# y1 <= 101; body content (table column headings) starts at y0 = 103. Wide
# enough gap that a fixed cutoff is safe without per-page table geometry.
TEMPLATE_B_BAND_Y1_MAX = 101.0

TEMPLATE_B_LABELS = [
    "Document Number",
    "Revision Number",
    "Reference Procedure",
    "Revision Date",
    "Reviewed / Revised by",
    "Approved by",
]

# --- Bold detection ---------------------------------------------------------
# Grounded: combined check correctly classified every sampled span
# (Arial-BoldMT, Calibri-Bold -> True; ArialMT, Calibri -> False).
def is_bold(span: dict) -> bool:
    return "Bold" in span["font"] or bool(span["flags"] & 16)


# --- Footer pattern ---------------------------------------------------------
# Grounded (round 3): AEI-QP-T-03B pp.81-83 carry "Page N of 30" at y~801,
# distinct from the top header table. Also covers the "N | P a g e" variant
# used by AEI-WI-T-15 (though that one lives inside the header table cell,
# not as a distinct bottom footer -- this regex is reused for both contexts).
FOOTER_RE = re.compile(
    r'^\s*(page\s+\d+\s+of\s+\d+|\d+\s*\|\s*p\s*a\s*g\s*e|\d+\s*of\s*\d+)\s*$',
    re.IGNORECASE,
)

# Bottom-of-page band to scan for a distinct footer, separate from the header
# table. Grounded: AEI-QP-T-03B's footer sits at y~801 on a ~842pt-tall page
# (near-bottom); a generous band avoids missing a footer at a slightly
# different y on other subdocuments not yet individually checked.
FOOTER_BAND_Y0_MIN_FROM_BOTTOM = 100.0

# --- Table stitching (round 3, corrected) -----------------------------------
# Original 60pt threshold silently failed on the corpus's own canonical
# multi-page tables (pp.1-2 gap=70.1, pp.3-5 gaps=61.4/91.0). Recalibrated
# against real evidence: known-good gaps 44-56pt, broken cases need up to
# 91pt, a genuine non-continuation measured 423pt. 120pt clears every real
# continuation with wide margin on both sides.
TABLE_STITCH_GAP_MAX = 120.0
TABLE_STITCH_X_TOLERANCE = 15.0
TABLE_STITCH_NEXT_TOP_MAX = 150.0

# --- Min-width column filter (round 3, adopted; snap_x_tolerance rejected) -
# Drop a column only if BOTH: narrower than this AND empty across every data
# row (header row excluded). Never drops a narrow column holding real data
# (confirmed safe against the risk register's I/P/RPN score columns).
MIN_COL_WIDTH = 10.0

# --- Diagram-only-page rule --------------------------------------------------
# Grounded: Annex C (p.35) reduces to ~27 chars of heading-only text after
# header strip, 2 images -> flagged. Annex A (p.28) has 589 chars of real
# body text, 1 image -> not flagged. Wide margin between the two real cases.
DIAGRAM_PAGE_MAX_BLOCKS = 1
DIAGRAM_PAGE_MAX_CHARS = 150
