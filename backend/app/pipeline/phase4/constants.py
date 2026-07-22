"""Grounded constants for Phase 4's BM25 floor gate and RRF fusion. Every
value here traces back to a real computation against the Phase 3 artifacts
(phases/v2_phase4.md, "Grounding pass"), not a default picked by feel.

The floor gate is explicitly an unvalidated, inspection-tuned heuristic
(master_contextB.md: no gold set, eval out of scope). These constants are
a live, one-line-editable knob set -- rebuilding Phase 4 after a change is
cheap, since this is a precompute-at-upload index, never a runtime query.
"""

# --- RRF -----------------------------------------------------------------
# Locked, not a tuning knob: master_contextC.md specifies k=60 explicitly.
RRF_K = 60

# --- BM25 floor gate -------------------------------------------------------
# A chunk is tagged `above_floor: true` only if it shares at least
# MIN_HIGH_IDF_TERMS "rare" (high-IDF) terms with the checklist item AND
# its raw BM25 score clears MIN_SCORE. Tagging never removes a chunk from
# its ranked list (master_contextC.md: "the gate tags, it never drops").

# A term counts as "rare" at idf >= 5.0. Grounded directly against the real
# 501-chunk corpus, not a percentile guess: BM25Okapi's idf here is
# ln(N - df + 0.5) - ln(df + 0.5), N=501. Checked which df values actually
# clear 5.0: df=2 -> idf=5.297 (clears), df=3 -> idf=4.959 (does NOT clear).
# So idf >= 5.0 means "appears in at most 2 of 501 chunks" -- confirmed by
# listing the distinct df values among every term at or above this
# threshold: {1, 2}, nothing else. Real domain nouns that recur across many
# procedures ("calibration" idf=2.26 df=47, "ndt" idf=2.07 df=56, "iso"
# idf=1.91 df=64, "9001" idf=2.17 df=51, "qms" idf=2.52 df=37) sit well
# below this line -- only terms specific to one or two procedures count as
# rare.
HIGH_IDF_THRESHOLD = 5.0

# Corpus-wide dry run against all 212 real checklist items (158 AQB + 54
# AEC), at HIGH_IDF_THRESHOLD=5.0: requiring 2 shared rare terms leaves 151
# of 212 items (71%) with zero chunks passing the gate at all -- the gate
# would be close to useless at this corpus size. Requiring 1 leaves 37/212
# (17%) with zero passing chunks, which is expected and fine (the gate
# tags, it never drops -- those items just show every chunk as
# above_floor: false and the auditor sees the full list regardless).
MIN_HIGH_IDF_TERMS = 1

# NOT a redundant backstop -- checked directly, and the first draft of this
# constant (5.0) was wrong. A single rare-term match's own BM25 contribution
# (idf * tf*(k1+1) / (tf + k1*(1-b+b*dl/avgdl)), tf=1) was computed for
# every real (chunk, rare-term) pair in the corpus: minimum contribution
# ~0.62 (a df=2 term, tf=1, in a 1,654-token chunk), and ~58% of all such
# single-term contributions fall below 5.0. A MIN_SCORE of 5.0 would have
# flipped most MIN_HIGH_IDF_TERMS=1 passers back to above_floor: false,
# silently overriding the N=1 decision above and becoming the dominant
# filter instead of a backstop.
#
# Set to 0.5 instead: on this corpus it trims only the bottom ~1% of the
# single-rare-term-contribution distribution (1st percentile ~0.63, right
# at this line) -- the near-zero tail, by design, not the bulk of real
# matches. It is kept as an independently tunable knob per the two-part
# gate spec (term specificity and aggregate score are conceptually
# different checks), in case a future, larger corpus needs it to do more
# work than it does here. It must not be read as the primary filter at
# these settings -- MIN_HIGH_IDF_TERMS is.
MIN_SCORE = 0.5
