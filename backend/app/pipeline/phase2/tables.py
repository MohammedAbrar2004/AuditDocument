"""Table serialization and stream insertion. A table is treated as a
pseudo-row in the same row stream the chunk builder walks, so it inherits the
identical no-drop / absorption rules as ordinary body text (locked decision,
pipeline step 5) instead of needing its own separate attachment logic.
"""
from .constants import TABLE_CELL_SEP


def serialize_table(table: dict) -> list[str]:
    lines = []
    for row in table["rows"]:
        cells = ["" if c in (None, "") else str(c) for c in row]
        lines.append(TABLE_CELL_SEP.join(cells))
    return lines


def insert_tables(rows: list[dict], tables: list[dict]) -> list[dict]:
    """Table-to-stream ordering uses the table's own y0 on its start page
    (from Phase 1's `bbox_by_page`), not just a page-boundary approximation.

    First version of this function placed a table after *every* row on its
    start page, which is wrong whenever more clause content follows the
    table on the same page -- confirmed on the real data: QM's Responsibility
    Matrix table (page 14, y0=117.5) landed under clause 6.1 instead of the
    5.3-region clause it actually sits under, because 6.0/6.1's page-14 rows
    came after it in the stream. Fixed: insert right after the last row that
    is strictly above the table (earlier page, or same page with a smaller
    y0), which is where the table actually sits in reading order.
    """
    result = list(rows)
    for t in sorted(tables, key=lambda t: (t["page_start"], t["bbox_by_page"][str(t["page_start"])][1])):
        t_page = t["page_start"]
        t_y0 = t["bbox_by_page"][str(t_page)][1]
        insert_idx = 0
        for idx, r in enumerate(result):
            r_page, r_y0 = r["page"], r.get("y0", 0.0)
            if r_page < t_page or (r_page == t_page and r_y0 <= t_y0):
                insert_idx = idx + 1
            else:
                break
        result.insert(insert_idx, {
            "kind": "table",
            "text": None,
            "page": t_page,
            "y0": t_y0,
            "page_end": t["page_end"],
            "table_id": t["table_id"],
            "serialized_lines": serialize_table(t),
        })
    return result
