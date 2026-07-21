"""Grounded constants for Phase 2 chunking. Every value here traces back to a
specific measurement against the real Phase 1 artifacts, documented in
phases/v2_phase2.md -- reused directly from the scratch scripts that
validated them (row-grouping tolerance, regexes) rather than re-derived.
"""
import re

# --- Row grouping ------------------------------------------------------------
# Grounded (phases/v2_phase2.md grounding item 2): FLAG-2's number/title split
# measured 1pt apart (QM p.10, "4"/"Context..."); QM body line spacing is
# ~14.7pt. 3pt clears the real case with wide margin on both sides.
ROW_Y_TOLERANCE = 3.0

# --- Row classification --------------------------------------------------
# Numbered heading, space style: leading dot-numbered token then whitespace
# then a non-empty title, e.g. "1  SCOPE", "4.2  Needs & Expectations...",
# "1.0  CEO", "6.2.1.1  AEI has established...". No bold requirement (build
# report: 4.2.2, 5.2.1-5.3.5, 6.2.1.1-6.3.1.1 are real clauses whose number
# and/or title render non-bold in the source -- bold was never a reliable
# signal here). `\S.*` requires real trailing content, not just whitespace.
NUMBERED_RE = re.compile(r"^(\d+(?:\.\d+)*)\s+(\S.*)$")

# Numbered heading, period style: same, but a literal period sits between
# the number and the whitespace, e.g. "1. Purpose:" (AEI-WI-T-01B/05B/15).
# Requires non-empty trailing content the same way -- this alone is what
# keeps it from matching a bare wrapped reference number like "64." with
# nothing after it (confirmed real: AEI-QP-T-08 p.151, "AEI-FORM- / 64. /
# •" -- "64." lands alone on its own PDF line, no trailing text at all, so
# this regex never matches it regardless of the sequence/title guards below).
PERIOD_NUMBERED_RE = re.compile(r"^(\d+(?:\.\d+)*)\.\s+(\S.*)$")

# Title-shape guard, period-style only (space-style already proven safe on
# real data without this -- 5.2.1's real title is a 25-word sentence and
# must NOT be excluded). Grounded: real WI period-style titles top out at
# 4 words ("Ultrasonic Testing Equipment (UFD):"); QM's non-heading
# enumerated objectives (the trap this guards against) run 9-17 words.
# Wide margin either side of this cutoff.
PERIOD_STYLE_TITLE_MAX_WORDS = 8

# Sequence/plausible-next guard: how far a fresh top-level number may jump
# from the highest top-level number seen so far in the same subdocument.
# Only the top-level segment is checked -- deeper segments skip constantly
# in real numbering (4.3 missing, 5.1.1 missing, a whole top-level 5
# missing) and master_contextC.md is explicit these are normal, so a first,
# stricter version of this guard (requiring +1 at whatever level changed)
# rejected real headings (4.4, 5.1, 6.0/6.1). Kept generous for the same
# reason -- this is defense in depth against "64." (AEI-QP-T-08), already
# excluded by the shape regex requiring real trailing content, not the
# primary guard.
TOP_LEVEL_JUMP_MAX = 15
# Absolute backstop when no numbering context exists yet in a subdocument.
TOP_LEVEL_ABSOLUTE_MAX = 30

# --- ToC guard -------------------------------------------------------------
# Grounded: removing the bold gate (build report) reopened exactly the trap
# master_contextC.md names -- "the ToC is not a reliable structure source" --
# because a ToC mirrors real structure and is therefore sequence-plausible
# too. Real corpus check: QM's ToC block packs 22 numbered-shaped rows into
# one native PyMuPDF block; the largest legitimate case found (real
# sub-clauses glued into one block, e.g. 8.4.2.1/8.4.2.2/8.4.2.3 with real
# prose between them) is 3. Wide margin between them.
MAX_NUMBERED_ROWS_PER_BLOCK = 5

# Annex ancestor heading, e.g. "Annex A (...)", "Annex B: ...", "Annex D: ...".
# Bold-gated (checked by the caller) -- proven safe corpus-wide as-is.
ANNEX_RE = re.compile(r"^Annex\s+([A-Z])\b")

# "Annexure" spelling with a dash/en-dash separator, e.g. "ANNEXURE - I".
# NOT bold-gated -- grounded case (AEI-WI-T-05B p227 "ANNEXURE - I ", the
# real restart boundary before its own "1. Purpose"/"2. Reference"/
# "3. Requirements"/"4. PA Instrument calibration" mini-procedure) renders
# non-bold in the source. Kept separate from ANNEX_RE (not merged/loosened)
# because dropping the bold gate on the plain "Annex" form re-triggers a
# real false positive: "...specifications defined in PCN24-CP09 \n Annex B."
# (QM p23, AEI-QM-T-01__p023_b216) is body prose that happens to line-wrap
# so "Annex B." starts its own row -- it is NOT alone in its block (3 other
# rows share b216). The caller gates this pattern on two things instead of
# bold: (1) the row is the ONLY row in its native block (real Annexure
# headings sit alone; the false-positive wrap line shares a block with its
# surrounding paragraph), and (2) the next shape-matched row starts a fresh
# "1"-numbered mini-sequence (real restarts open at 1; a decorative trailing
# label like AEI-WI-T-07's "Annexure A - Information Packages", which has no
# numbered content after it at all, must NOT be treated as a boundary --
# confirmed real: forcing it through would demote that heading into an
# absorbed lead-line of the unrelated chunk before it, a regression on a
# case that was already correct).
ANNEXURE_RE = re.compile(r"^Annexure\s*[–-]?\s*([A-Z])\b", re.IGNORECASE)

# Parenthetical annotation line, e.g. "(Applicable for all locations
# administered by AEI)". Checked before heading classification -- never a
# heading even if all-bold and block-homogeneous (locked decision, rule 4).
PAREN_RE = re.compile(r"^\(.*\)$")

# --- Table serialization (locked Q2 default) ----------------------------
TABLE_CELL_SEP = " | "
