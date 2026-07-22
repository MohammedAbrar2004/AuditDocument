from typing import Literal

from pydantic import BaseModel


class SubdocumentOut(BaseModel):
    doc_id: str
    doc_name: str


class UploadResponse(BaseModel):
    filename: str
    subdocument_count: int
    subdocuments: list[SubdocumentOut]
    chunk_count: int
    elapsed_seconds: float


class ZeroPassOut(BaseModel):
    n_items: int
    zero_pass: int


class GateOut(BaseModel):
    high_idf_threshold: float
    min_high_idf_terms: int
    min_score: float
    n_chunks: int
    rare_vocab_size: int
    vocab_size: int
    single_term_contribution_min: float | None = None
    single_term_contribution_n: int


class IndexResponse(BaseModel):
    n_chunks: int
    embed_elapsed_seconds: float
    total_elapsed_seconds: float
    gate: GateOut
    zero_pass: dict[str, ZeroPassOut]


class StatusResponse(BaseModel):
    state: Literal["none", "uploaded", "indexed"]
    filename: str | None = None
    subdocument_count: int | None = None
    chunk_count: int | None = None
    gate: GateOut | None = None
    zero_pass: dict[str, ZeroPassOut] | None = None
