"""Joins Phase 4-shaped ranking entries ({chunk_id, rank, score[,
above_floor]}) to this document's own Phase 2 chunk artifact by chunk_id
(v2_plan.md, Phase 4 artifact section: "No chunk text stored -- Phase 5
hydrates from Phase 2's artifact by chunk_id"). The join-integrity
assertion already ran once, at the end of Stage B (orchestrate.py) -- this
module trusts that and just joins; a KeyError here would mean that
assertion was wrong, not that this request is malformed.
"""
import json

from . import store

_CHUNK_FIELDS = (
    "doc_id",
    "doc_name",
    "clause_no",
    "clause_title",
    "page_start",
    "page_end",
    "text",
)


def load_chunk_map() -> dict[str, dict]:
    p2 = json.loads(store.phase2_path().read_text(encoding="utf-8"))
    return {c["chunk_id"]: c for c in p2["chunks"]}


def hydrate_entries(entries: list[dict], chunk_map: dict[str, dict]) -> list[dict]:
    out = []
    for e in entries:
        chunk = chunk_map[e["chunk_id"]]
        hydrated = {f: chunk[f] for f in _CHUNK_FIELDS}
        hydrated["rank"] = e["rank"]
        hydrated["score"] = e["score"]
        if "above_floor" in e:
            hydrated["above_floor"] = e["above_floor"]
        out.append(hydrated)
    return out


def load_and_hydrate_mapping(prefix: str, item_id: str) -> dict:
    rankings = json.loads(store.rankings_path(prefix).read_text(encoding="utf-8"))
    if item_id not in rankings["items"]:
        raise KeyError(item_id)
    chunk_map = load_chunk_map()
    views = rankings["items"][item_id]
    return {
        "keyword": hydrate_entries(views["keyword"], chunk_map),
        "semantic": hydrate_entries(views["semantic"], chunk_map),
        "both": hydrate_entries(views["both"], chunk_map),
    }
