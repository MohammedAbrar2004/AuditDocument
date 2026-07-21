"""Ancestor registry for numbered clauses -- replaces plain depth-count stack
popping. Grounded on a real conflict found during verification: master_contextC.md's
own few-shot examples treat two kinds of "missing ancestor" differently:

- A missing TOP-LEVEL ancestor (`5` before `5.1`/`5.1.2`) is expected to still
  appear: `[5 hdg][5.1 hdg][5.1.2 hdg]`. Checked directly against the real
  PDF: "5" does not exist anywhere as text -- not non-bold, not missing due
  to a detection gap, genuinely absent. The only way to produce `[5 hdg]` is
  to synthesize a placeholder.
- A missing INTERMEDIATE ancestor (`6.2.1` before `6.2.1.1`, when only `6.2`
  exists) is explicitly NOT synthesized: "the `6.2.1` level simply does not
  appear" -- `6.2.1.1` attaches directly to `6.2`.

So: synthesize only at the top level, when nothing real is registered there.
Deeper gaps are skipped silently, same as the already-validated behavior.

A second real finding folds into the same mechanism: `6.0 Planning` is a
real, bold, titled heading, but its children `6.1`/`6.2`/`6.3` are also
written with two segments (`6.1` etc.), so plain segment-count comparison
treats them as siblings, not parent/child. Fix: a trailing `.0` segment
normalizes to one level shallower for lookup purposes -- `6.0`'s registry
key is `(6,)`, identical to what a bare `6` would use, and identical to the
key `1.0` already needed (Annex B's own entry, already validated with
`ancestor_path: []`). This isn't a new rule invented for `6.0` -- it's the
same normalization the Annex case already required, applied consistently.
"""


def effective_key(tup: tuple[int, ...]) -> tuple[int, ...]:
    if len(tup) >= 2 and tup[-1] == 0:
        return tup[:-1]
    return tup


class AncestorRegistry:
    """One per subdocument (and reset on entering an Annex scope -- a fresh
    numbering namespace). Entries persist for the registry's whole lifetime;
    nothing is popped. `rescue_unconsumed()` returns the heading text of any
    zero-body entry that registered but was never looked up by anything --
    the no-drop safety net for a genuinely orphaned ancestor.
    """

    def __init__(self):
        self._entries: dict[tuple[int, ...], dict] = {}

    def register(self, tup: tuple[int, ...], clause_no: str, clause_title: str,
                 heading_line: str, is_zero_body: bool) -> None:
        key = effective_key(tup)
        self._entries[key] = {
            "clause_no": clause_no, "clause_title": clause_title,
            "_heading_line": heading_line, "is_zero_body": is_zero_body,
            "is_synthetic": False, "consumed": False,
        }

    def ancestors_for(self, tup: tuple[int, ...]) -> list[dict]:
        """Root-to-immediate-parent list of ancestor entries needed for
        `tup`. Synthesizes (and registers) a bare top-level entry if none is
        registered yet; deeper gaps are skipped, never synthesized."""
        key = effective_key(tup)
        if len(key) == 1:
            return []
        top = key[:1]
        top_entry = self._entries.get(top)
        if top_entry is None:
            top_entry = {
                "clause_no": str(top[0]), "clause_title": None,
                "_heading_line": str(top[0]), "is_zero_body": True,
                "is_synthetic": True, "consumed": False,
            }
            self._entries[top] = top_entry
        top_entry["consumed"] = True
        result = [top_entry]
        for lvl in range(2, len(key)):
            prefix = key[:lvl]
            entry = self._entries.get(prefix)
            if entry is not None:
                entry["consumed"] = True
                result.append(entry)
            # else: intermediate level missing, skipped -- not synthesized,
            # matches master_contextC.md's explicit "does not appear" case.
        return result

    def rescue_unconsumed(self) -> list[str]:
        """Real, zero-body entries that never got reused as anyone's
        ancestor -- their text needs a home via the pending_prefix fallback
        or it's a real drop. Synthetic entries have no real text to rescue.
        """
        return [
            e["_heading_line"] for e in self._entries.values()
            if e["is_zero_body"] and not e["is_synthetic"] and not e["consumed"]
        ]
