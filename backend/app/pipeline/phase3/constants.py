"""Grounded constants for Phase 3. Checklist-parsing values trace back to a
full-corpus scan of both real checklist PDFs (phases/v2_phase3.md); embedding
values trace back to BGE-M3's own shipped config and this session's model-card
check, not assumption.
"""
import re

# --- Row grouping ------------------------------------------------------------
# Same tolerance and same rationale as Phase 2 (phases/v2_phase2.md grounding
# item 2): checklist body line spacing is ~11pt, well clear of 3pt.
ROW_Y_TOLERANCE = 3.0

# --- Header/footer/title stripping -----------------------------------------
# Grounded directly (phases/v2_phase3.md, checklist header dump): both
# checklists share one header layout, four label rows at y0 in
# {38.0, 67.3, 90.5, 95.1}. AQB only repeats this on page 1 (round-1 finding,
# confirmed again here); AEC repeats it on every page. Stripping by a fixed
# y-band unconditionally is unsafe -- AQB's headerless pages 2-30 have real
# body content starting at y0=38.4, right where the header sits on page 1.
# So the header labels are matched by exact text first; only once a page is
# confirmed to actually carry a header do we strip everything up to the
# label band's bottom (handles the interleaved value cells, which have no
# distinctive text of their own to match on).
HEADER_LABELS = frozenset({
    "DOCUMENT NAME", "DOCUMENT NO.", "REVISION", "REVISED DATE",
    "ISSUE DATE", "PAGE NO.",
})
HEADER_BAND_MARGIN = 2.0  # pt, past the lowest matched label's y0 on that page

# Bottom-of-page footer, e.g. "Page 1 of 30" -- also catches the header's own
# PAGE NO. value cell as a side effect (harmless overlap with the band strip).
PAGE_FOOTER_RE = re.compile(r"^Page \d+ of \d+$")

# Page-1-only decorative title block ("AUDIT CHECKLIST (AQB)" size 15.96,
# "REQUIREMENTS FOR BINDT..." mixed size 14.04). Every real heading/body row
# checked in the full-corpus scan tops out at 11.04 -- wide margin either
# side of this cutoff. Size-gated, not page-gated, so it's a no-op (and safe)
# anywhere else it might theoretically occur.
TITLE_FONT_SIZE_MIN = 13.0

# --- Row classification ------------------------------------------------------
# Numbered row, either style: "4.2 Quality..." (AQB, space after number) or
# "1. General requirement" (AEC, period after number). `\.?` makes the period
# optional, `\S.*` requires real trailing content (excludes a bare wrapped
# fragment with nothing after the number). Grounded against every page of
# both PDFs, not a sample.
NUMBERED_RE = re.compile(r"^(\d+(?:\.\d+)*)\.?\s+(\S.*)$")

# Paragraph-break gap (pt), used to split an item's accumulated body into
# separate synthesized items when the source drops numbering mid-section
# (grounded case: AEC "8. Consistency of PCN Examinations", 6 real audit
# questions with no number at all, phases/v2_phase3.md build report). Real
# within-paragraph line-wrap gap measured at ~11.0pt everywhere checked;
# real between-paragraph/between-item gap measured at ~17.0-17.5pt
# everywhere checked. 14.0pt sits with ~3pt margin on both sides, same
# margin discipline as ROW_Y_TOLERANCE above. Generic, not hardcoded to one
# item -- grounded corpus-wide at build time to confirm it fires only where
# intended (see build report for the corpus-wide check).
PARAGRAPH_GAP_MIN = 14.0

# Minimum required gap (pt) between the real number column and the
# body/continuation column, used to sanity-check the per-document threshold
# auto-detected at parse time (see checklist_parse.py). Grounded: the
# smallest real gap found corpus-wide was ~30pt (AQB); AEC's was ~43pt. 15pt
# is a wide safety margin under both -- if a future document doesn't clear
# it, that's a sign the auto-threshold isn't safe to trust blindly and the
# parser should say so rather than silently produce garbage.
MIN_COLUMN_GAP = 15.0
