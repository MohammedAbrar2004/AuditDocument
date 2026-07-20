import type { DisplayCandidate, ViewName } from "../api/types";

interface CandidateCardProps {
  candidate: DisplayCandidate;
  view: ViewName;
  onViewPdf: (candidate: DisplayCandidate) => void;
}

function ScoreBreakdown({ candidate, view }: { candidate: DisplayCandidate; view: ViewName }) {
  if (view === "keyword") {
    return (
      <ul>
        <li>BM25 score: {candidate.score.toFixed(4)} — higher means more/rarer term overlap with this item's text.</li>
        <li>High-IDF (distinctive) terms matched: {candidate.high_idf_terms_matched ?? 0}.</li>
        <li>
          Configured floor: {candidate.above_floor === false ? "NOT cleared" : "cleared"} (
          <code>bm25.min_score</code>/<code>bm25.min_high_idf_terms</code>, still uncalibrated
          placeholders).
        </li>
      </ul>
    );
  }
  if (view === "semantic") {
    return (
      <ul>
        <li>
          Cosine similarity: {candidate.score.toFixed(4)} — meaning-vector closeness between this
          chunk and the checklist item, range roughly 0-1. No configured floor exists for this
          view.
        </li>
      </ul>
    );
  }
  return (
    <ul>
      <li>RRF (fused) score: {candidate.score.toFixed(4)} — reciprocal-rank-fusion of the two ranks below.</li>
      <li>
        Keyword: rank {candidate.keyword_rank ?? "—"}, score{" "}
        {candidate.keyword_score?.toFixed(3) ?? "—"}.
      </li>
      <li>
        Semantic: rank {candidate.semantic_rank ?? "—"}, score{" "}
        {candidate.semantic_score?.toFixed(3) ?? "—"}.
      </li>
      <li>A strong fused rank requires both components to be reasonably strong — see the Both view note above.</li>
    </ul>
  );
}

export function CandidateCard({ candidate, view, onViewPdf }: CandidateCardProps) {
  return (
    <div className={`candidate-card${candidate.above_floor === false ? " below-floor" : ""}`}>
      <div className="candidate-header">
        <span className="clause">
          {candidate.doc_id} {candidate.clause_no ?? ""}
          {candidate.clause_title ? ` — ${candidate.clause_title}` : ""}
        </span>
        <span className="pages">
          p.{candidate.page_start}
          {candidate.page_end !== candidate.page_start ? `-${candidate.page_end}` : ""}
        </span>
      </div>

      <div className="candidate-scores">
        {view === "keyword" && (
          <span className={`badge ${candidate.above_floor === false ? "badge-weak" : "badge-strong"}`}>
            {candidate.above_floor === false ? "below floor" : "above floor"}
          </span>
        )}
        <span className="score-badge">
          {view === "keyword" ? "score" : view === "semantic" ? "cosine" : "rrf"}{" "}
          {candidate.score.toFixed(view === "rrf" ? 4 : 3)}
        </span>
        {view === "rrf" && (
          <>
            <span className="score-badge">
              keyword #{candidate.keyword_rank ?? "—"}
            </span>
            <span className="score-badge">
              semantic #{candidate.semantic_rank ?? "—"}
            </span>
          </>
        )}
        <button className="pdf-link-btn" onClick={() => onViewPdf(candidate)}>
          View in PDF
        </button>
      </div>

      {candidate.joinMissing ? (
        // Never silently drop a candidate whose text join failed.
        <p className="error-text">
          Could not find this chunk's text in the document's chunk index (join on
          doc_id + clause_no + pages missed). Showing metadata only — data may be out of
          sync; try re-indexing the document.
        </p>
      ) : (
        <p className="candidate-text">{candidate.text}</p>
      )}

      {candidate.evidence_tables.length > 0 &&
        candidate.evidence_tables.map((table, i) => (
          <table key={i} className="evidence-table">
            {table.caption && <caption>{table.caption}</caption>}
            <tbody>
              {table.rows.map((row, r) => (
                <tr key={r}>
                  {row.map((cell, c) => (
                    <td key={c}>{cell ?? ""}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        ))}

      <details className="score-breakdown">
        <summary>Score breakdown</summary>
        <ScoreBreakdown candidate={candidate} view={view} />
      </details>
    </div>
  );
}
