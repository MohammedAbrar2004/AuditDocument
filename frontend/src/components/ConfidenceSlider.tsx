import type { ViewName } from "../api/types";

const UNIT_LABELS: Record<ViewName, string> = {
  keyword: "BM25 score",
  semantic: "cosine similarity",
  rrf: "RRF score",
};

interface ConfidenceSliderProps {
  view: ViewName;
  min: number;
  max: number;
  value: number;
  onChange: (value: number) => void;
  visibleCount: number;
  totalCount: number;
  belowFloor: boolean;
  onBelowFloorChange: (value: boolean) => void;
}

export function ConfidenceSlider({
  view,
  min,
  max,
  value,
  onChange,
  visibleCount,
  totalCount,
  belowFloor,
  onBelowFloorChange,
}: ConfidenceSliderProps) {
  const degenerate = min >= max;
  const step = degenerate ? 1 : (max - min) / 200;

  return (
    <div className="panel confidence-slider">
      <h2>4. Confidence floor</h2>
      <input
        type="range"
        min={min}
        max={degenerate ? min + 1 : max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        disabled={degenerate}
      />
      <p className="hint-text">
        Showing <strong>{visibleCount}</strong> of {totalCount} candidates at or above{" "}
        <strong>{value.toFixed(4)}</strong> ({UNIT_LABELS[view]}). This is a raw,
        native-units score for this view — a relative ranking dial, not a probability.
      </p>
      {view === "keyword" && (
        <label className="below-floor-toggle">
          <input
            type="checkbox"
            checked={belowFloor}
            onChange={(e) => onBelowFloorChange(e.target.checked)}
          />
          Show chunks below the configured keyword floor too (the floor values are still
          uncalibrated placeholders until the gold set exists)
        </label>
      )}
    </div>
  );
}
