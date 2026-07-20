import type { ChecklistListEntryOut } from "../api/types";

interface ChecklistStepProps {
  checklists: ChecklistListEntryOut[];
  loading: boolean;
  error: string | null;
  selected: ChecklistListEntryOut | null;
  onSelect: (entry: ChecklistListEntryOut) => void;
  onRun: () => void;
}

export function ChecklistStep({
  checklists,
  loading,
  error,
  selected,
  onSelect,
  onRun,
}: ChecklistStepProps) {
  return (
    <div className="panel wizard-panel">
      <h2>Pick a checklist</h2>
      <p className="hint-text">Every item in the chosen checklist will be mapped against the indexed document.</p>

      {loading && <p className="hint-text">Loading checklists…</p>}
      {error && <p className="error-text">Could not load checklists: {error}</p>}

      {!loading && !error && (
        <ul className="checklist-option-list">
          {checklists.map((c) => (
            <li key={c.checklist_name}>
              <button
                className={
                  selected?.checklist_name === c.checklist_name
                    ? "checklist-option active"
                    : "checklist-option"
                }
                onClick={() => onSelect(c)}
              >
                <span>
                  <strong>{c.checklist_name}</strong> — {c.filename.replace(/\.pdf$/i, "")}
                </span>
                <span className="hint-text">{c.parsed ? "already parsed" : "will parse now"}</span>
              </button>
            </li>
          ))}
        </ul>
      )}

      <button className="primary-btn" disabled={!selected} onClick={onRun}>
        Run mapping
      </button>
    </div>
  );
}
