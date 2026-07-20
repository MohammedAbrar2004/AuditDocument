import type { ViewName } from "../api/types";

const VIEW_LABELS: Record<ViewName, string> = {
  keyword: "Keyword",
  semantic: "Semantic",
  rrf: "Both",
};

const VIEW_ORDER: ViewName[] = ["keyword", "semantic", "rrf"];

interface ViewToggleProps {
  view: ViewName;
  onChange: (view: ViewName) => void;
}

export function ViewToggle({ view, onChange }: ViewToggleProps) {
  return (
    <div className="panel view-toggle">
      <h2>View</h2>
      <div className="view-buttons">
        {VIEW_ORDER.map((v) => (
          <button
            key={v}
            className={v === view ? "view-btn active" : "view-btn"}
            onClick={() => onChange(v)}
          >
            {VIEW_LABELS[v]}
          </button>
        ))}
      </div>
      {view === "rrf" && (
        <p className="consensus-note">
          <strong>Both</strong> = consensus of Keyword <em>and</em> Semantic (chunks
          strong on both signals) — not their union. A candidate strong on only one
          signal can rank outside this view even though it's a genuine match. Check
          Keyword and Semantic individually too.
        </p>
      )}
    </div>
  );
}
