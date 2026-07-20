import type { PipelineStep, StepStatus } from "../pipeline/useIndexingPipeline";

const ICONS: Record<StepStatus, string> = {
  pending: "○", // ○
  running: "◐", // ◐
  done: "●", // ●
  skipped: "✓", // ✓ (already built, GET succeeded — no POST needed)
  error: "✕", // ✕
};

interface IndexingProgressProps {
  steps: PipelineStep[];
  error: string | null;
}

export function IndexingProgress({ steps, error }: IndexingProgressProps) {
  const started = steps.some((s) => s.status !== "pending");
  if (!started) return null;

  return (
    <div className="panel indexing-progress">
      <h2>Indexing</h2>
      <ul>
        {steps.map((s) => (
          <li key={s.key} className={`step step-${s.status}`}>
            <span className="step-icon">{ICONS[s.status]}</span> {s.label}
          </li>
        ))}
      </ul>
      {error && <p className="error-text">{error}</p>}
    </div>
  );
}
