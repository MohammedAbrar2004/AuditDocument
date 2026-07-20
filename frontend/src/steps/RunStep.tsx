import { useEffect, useRef } from "react";
import type { ChecklistListEntryOut, ChunkResponse } from "../api/types";
import type { useChecklistMapping } from "../pipeline/useIndexingPipeline";

const ICONS: Record<string, string> = {
  pending: "○",
  running: "◐",
  done: "●",
  skipped: "✓",
  error: "✕",
};

interface RunStepProps {
  mapping: ReturnType<typeof useChecklistMapping>;
  docFilename: string;
  chunks: ChunkResponse;
  checklist: ChecklistListEntryOut;
  onDone: () => void;
  onBack: () => void;
}

export function RunStep({ mapping, docFilename, chunks, checklist, onDone, onBack }: RunStepProps) {
  // React 18 StrictMode double-invokes effects in dev — without this guard the mapping
  // chain (and every real POST inside it) would fire twice per visit to this step.
  const firedForRef = useRef<string | null>(null);

  useEffect(() => {
    const key = `${docFilename}__${checklist.checklist_name}`;
    if (firedForRef.current === key) return;
    firedForRef.current = key;
    void mapping.run({ docFilename, chunks, checklist });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [docFilename, checklist.checklist_name]);

  useEffect(() => {
    if (mapping.result) onDone();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mapping.result]);

  return (
    <div className="panel wizard-panel run-panel">
      {!mapping.error && (
        <>
          <div className="spinner" aria-hidden="true" />
          <h2>Mapping checklist to document…</h2>
          <p className="hint-text">
            Builds the keyword, semantic, and fused views for every item in{" "}
            <strong>{checklist.checklist_name}</strong>. Steps already built for this
            document/checklist pair are skipped instantly.
          </p>
        </>
      )}

      <ul className="run-steps">
        {mapping.steps.map((s) => (
          <li key={s.key} className={`step step-${s.status}`}>
            <span className="step-icon">{ICONS[s.status]}</span> {s.label}
          </li>
        ))}
      </ul>

      {mapping.error && (
        <>
          <p className="error-text">{mapping.error}</p>
          <div className="field-row">
            <button onClick={onBack}>← Back to checklist</button>
            <button
              className="primary-btn"
              onClick={() => {
                firedForRef.current = null;
                void mapping.run({ docFilename, chunks, checklist });
              }}
            >
              Retry
            </button>
          </div>
        </>
      )}
    </div>
  );
}
