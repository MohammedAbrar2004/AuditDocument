"""Checklists + rankings endpoints -- the read side. No computation, ever:
everything here either comes from the checklist-persistent scope loaded
once at startup (app/state.py) or from this document's own per-document
rankings, already computed by Stage B and hydrated by chunk_id
(pipeline/upload/hydrate.py).
"""
from fastapi import APIRouter, HTTPException

from app.pipeline.upload import hydrate, store
from app.schemas.checklists import ChecklistEntryOut, ChecklistItemOut, MappingResponse
from app.state import app_state

router = APIRouter(prefix="/checklists", tags=["checklists"])


def _resolve_prefix(checklist_name: str) -> str:
    name = checklist_name.upper()
    if name not in app_state.checklists:
        raise HTTPException(status_code=404, detail=f"Unknown checklist '{checklist_name}'.")
    return name


@router.get("", response_model=list[ChecklistEntryOut])
def list_checklists():
    return [
        {"name": prefix, "item_count": len(data["items"])}
        for prefix, data in app_state.checklists.items()
    ]


@router.get("/{checklist_name}/items", response_model=list[ChecklistItemOut])
def list_items(checklist_name: str):
    prefix = _resolve_prefix(checklist_name)
    items = app_state.checklists[prefix]["items"]
    return [{"item_id": it["item_id"], "text": it["text"]} for it in items]


@router.get("/{checklist_name}/items/{item_id}/mapping", response_model=MappingResponse)
def get_mapping(checklist_name: str, item_id: str):
    prefix = _resolve_prefix(checklist_name)
    if not store.rankings_path(prefix).exists():
        raise HTTPException(
            status_code=409,
            detail="Document not indexed yet -- POST /documents/index first.",
        )
    try:
        return hydrate.load_and_hydrate_mapping(prefix, item_id)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown item_id '{item_id}' for checklist '{checklist_name}'.",
        )
