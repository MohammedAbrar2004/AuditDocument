from pydantic import BaseModel


class ChecklistEntryOut(BaseModel):
    name: str
    item_count: int


class ChecklistItemOut(BaseModel):
    item_id: str
    text: str


class RankedChunkOut(BaseModel):
    doc_id: str
    doc_name: str
    clause_no: str | None
    clause_title: str | None
    page_start: int
    page_end: int
    text: str
    rank: int
    score: float
    above_floor: bool | None = None


class MappingResponse(BaseModel):
    keyword: list[RankedChunkOut]
    semantic: list[RankedChunkOut]
    both: list[RankedChunkOut]
