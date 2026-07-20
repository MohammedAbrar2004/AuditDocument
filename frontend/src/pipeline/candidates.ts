import type {
  ChunkOut,
  ChunkResponse,
  DisplayCandidate,
  FusedResponse,
  KeywordResponse,
  SemanticResponse,
  ViewName,
} from "../api/types";

// Phase 7 Grounding #2: ranked-chunk schemas never carry chunk body text, only
// (doc_id, clause_no, clause_title, score(s), page_start, page_end). This is the exact
// key Phase 5's own RRF fusion already proved collision-free across all 672 real chunks.
export function chunkKey(
  docId: string,
  clauseNo: string | null,
  pageStart: number,
  pageEnd: number,
): string {
  return `${docId}|${clauseNo ?? ""}|${pageStart}|${pageEnd}`;
}

export function buildChunkMap(chunks: ChunkResponse): Map<string, ChunkOut> {
  const map = new Map<string, ChunkOut>();
  for (const c of chunks.chunks) {
    map.set(chunkKey(c.doc_id, c.clause_no, c.page_start, c.page_end), c);
  }
  return map;
}

export interface RankedLike {
  doc_id: string;
  clause_no: string | null;
  clause_title: string | null;
  page_start: number;
  page_end: number;
  score: number;
  above_floor?: boolean;
  high_idf_terms_matched?: number;
  keyword_rank?: number | null;
  keyword_score?: number | null;
  semantic_rank?: number | null;
  semantic_score?: number | null;
}

export function getRankedForItem(
  view: ViewName,
  itemId: string | null,
  keyword: KeywordResponse,
  semantic: SemanticResponse,
  rrf: FusedResponse,
): RankedLike[] {
  if (view === "keyword") {
    const item = keyword.results.find((r) => r.item_id === itemId);
    return (item?.ranked ?? []).map((r) => ({ ...r }));
  }
  if (view === "semantic") {
    const item = semantic.results.find((r) => r.item_id === itemId);
    return (item?.ranked ?? []).map((r) => ({ ...r }));
  }
  const item = rrf.results.find((r) => r.item_id === itemId);
  return (item?.ranked ?? []).map((r) => ({
    doc_id: r.doc_id,
    clause_no: r.clause_no,
    clause_title: r.clause_title,
    page_start: r.page_start,
    page_end: r.page_end,
    score: r.rrf_score,
    keyword_rank: r.keyword_rank,
    keyword_score: r.keyword_score,
    semantic_rank: r.semantic_rank,
    semantic_score: r.semantic_score,
  }));
}

/** Keyword view defaults to above_floor-only (Phase 3's calibrated gate); `belowFloor`
 * is the approved escape hatch (phases/phase7.md decision 5 amendment) since the floor
 * values are still uncalibrated Phase-0 placeholders. Semantic/RRF have no analogous
 * floor, so they always see the full ranked list. */
export function eligiblePool(
  view: ViewName,
  ranked: RankedLike[],
  belowFloor: boolean,
): RankedLike[] {
  if (view === "keyword" && !belowFloor) {
    return ranked.filter((r) => r.above_floor !== false);
  }
  return ranked;
}

/** Default slider position = the score at rank `topK` within the eligible pool (Open
 * decision 4) -- ties the UI default to the same config value Phase 6's eval already
 * calibrates against, no new magic number. Falls back to "show everything" when the
 * pool is smaller than topK (edge case 10). */
export function defaultSliderValue(pool: RankedLike[], topK: number): number {
  if (pool.length === 0) return 0;
  const idx = Math.min(topK, pool.length) - 1;
  return pool[idx].score;
}

export function sliderBounds(pool: RankedLike[]): { min: number; max: number } {
  if (pool.length === 0) return { min: 0, max: 0 };
  let min = pool[0].score;
  let max = pool[0].score;
  for (const r of pool) {
    if (r.score < min) min = r.score;
    if (r.score > max) max = r.score;
  }
  return { min, max };
}

export function toDisplayCandidates(
  pool: RankedLike[],
  floorValue: number,
  chunkMap: Map<string, ChunkOut>,
): DisplayCandidate[] {
  return pool
    .filter((r) => r.score >= floorValue)
    .map((r) => {
      const key = chunkKey(r.doc_id, r.clause_no, r.page_start, r.page_end);
      const chunk = chunkMap.get(key);
      return {
        doc_id: r.doc_id,
        clause_no: r.clause_no,
        clause_title: r.clause_title,
        page_start: r.page_start,
        page_end: r.page_end,
        score: r.score,
        above_floor: r.above_floor,
        high_idf_terms_matched: r.high_idf_terms_matched,
        keyword_rank: r.keyword_rank,
        keyword_score: r.keyword_score,
        semantic_rank: r.semantic_rank,
        semantic_score: r.semantic_score,
        text: chunk ? chunk.text : null,
        evidence_tables: chunk ? chunk.evidence_tables : [],
        joinMissing: !chunk,
      };
    });
}
