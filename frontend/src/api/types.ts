// Hand-mirrored from backend/app/schemas/*.py — field-for-field, no codegen.
// Keep in sync by hand when a backend schema changes (see phases/phase7.md Part B).

export interface RankedChunkOut {
  doc_id: string;
  clause_no: string | null;
  clause_title: string | null;
  score: number;
  high_idf_terms_matched: number;
  above_floor: boolean;
  page_start: number;
  page_end: number;
}

export interface KeywordItemResultOut {
  item_id: string | null;
  item_text: string;
  ranked: RankedChunkOut[];
}

export interface KeywordResponse {
  source_file: string;
  checklist_name: string;
  results: KeywordItemResultOut[];
}

export interface SemanticRankedChunkOut {
  doc_id: string;
  clause_no: string | null;
  clause_title: string | null;
  score: number;
  page_start: number;
  page_end: number;
}

export interface SemanticItemResultOut {
  item_id: string | null;
  item_text: string;
  ranked: SemanticRankedChunkOut[];
}

export interface SemanticResponse {
  source_file: string;
  checklist_name: string;
  results: SemanticItemResultOut[];
}

export interface FusedRankedChunkOut {
  doc_id: string;
  clause_no: string | null;
  clause_title: string | null;
  page_start: number;
  page_end: number;
  rrf_score: number;
  keyword_rank: number | null;
  keyword_score: number | null;
  semantic_rank: number | null;
  semantic_score: number | null;
}

export interface FusedItemResultOut {
  item_id: string | null;
  item_text: string;
  ranked: FusedRankedChunkOut[];
}

export interface FusedResponse {
  source_file: string;
  checklist_name: string;
  results: FusedItemResultOut[];
}

export interface ChecklistItemOut {
  item_id: string | null;
  text: string;
}

export interface ChecklistOut {
  checklist_name: string;
  source_file: string;
  items: ChecklistItemOut[];
}

export interface ChecklistListEntryOut {
  filename: string;
  checklist_name: string;
  parsed: boolean;
}

export interface EvidenceTableBlockOut {
  type: "evidence_table";
  page_start: number;
  page_end: number;
  caption: string | null;
  rows: (string | null)[][];
}

export interface ChunkOut {
  doc_id: string;
  clause_no: string | null;
  clause_title: string | null;
  text: string;
  evidence_tables: EvidenceTableBlockOut[];
  page_start: number;
  page_end: number;
}

export interface ChunkResponse {
  source_file: string;
  chunks: ChunkOut[];
}

export interface ChunkEmbeddingsMetaOut {
  source_file: string;
  model_name: string;
  dims: number;
  count: number;
}

export interface ChecklistEmbeddingsMetaOut {
  checklist_name: string;
  source_file: string;
  model_name: string;
  dims: number;
  count: number;
}

export interface ParseResponseMinimal {
  source_file: string;
}

export type ViewName = "keyword" | "semantic" | "rrf";

// Client-side shape after joining a ranked chunk (whichever view) against chunks.json
// text by (doc_id, clause_no, page_start, page_end) — see phases/phase7.md Grounding #2.
export interface DisplayCandidate {
  doc_id: string;
  clause_no: string | null;
  clause_title: string | null;
  page_start: number;
  page_end: number;
  score: number; // the active view's primary sort score
  above_floor?: boolean; // keyword only
  high_idf_terms_matched?: number; // keyword only
  keyword_rank?: number | null; // rrf only
  keyword_score?: number | null; // rrf only
  semantic_rank?: number | null; // rrf only
  semantic_score?: number | null; // rrf only
  text: string | null; // null when the join misses (edge case 7)
  evidence_tables: EvidenceTableBlockOut[];
  joinMissing: boolean;
}
