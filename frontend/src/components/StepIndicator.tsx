export type WizardStep = "upload" | "checklist" | "run" | "results";

const STEPS: { key: WizardStep; label: string }[] = [
  { key: "upload", label: "1. Upload document" },
  { key: "checklist", label: "2. Pick checklist" },
  { key: "run", label: "3. Run mapping" },
  { key: "results", label: "4. Review results" },
];

interface StepIndicatorProps {
  current: WizardStep;
}

export function StepIndicator({ current }: StepIndicatorProps) {
  return (
    <nav className="step-indicator">
      {STEPS.map((s, i) => (
        <span key={s.key} className={s.key === current ? "step-crumb active" : "step-crumb"}>
          {s.label}
          {i < STEPS.length - 1 && <span className="step-arrow"> →</span>}
        </span>
      ))}
    </nav>
  );
}
