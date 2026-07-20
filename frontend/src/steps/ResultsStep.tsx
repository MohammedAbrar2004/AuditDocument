import { useEffect, useMemo, useState } from "react";
import type { ChunkOut, DisplayCandidate, ViewName } from "../api/types";
import { CandidateCard } from "../components/CandidateCard";
import { ConfidenceSlider } from "../components/ConfidenceSlider";
import { ItemList } from "../components/ItemList";
import { PdfViewer } from "../components/PdfViewer";
import { ViewToggle } from "../components/ViewToggle";
import {
  buildChunkMap,
  defaultSliderValue,
  eligiblePool,
  getRankedForItem,
  sliderBounds,
  toDisplayCandidates,
} from "../pipeline/candidates";
import type { ChecklistMappingResult } from "../pipeline/useIndexingPipeline";

interface ResultsStepProps {
  result: ChecklistMappingResult;
  topK: number;
  onRestart: () => void;
}

export function ResultsStep({ result, topK, onRestart }: ResultsStepProps) {
  const [currentItemIndex, setCurrentItemIndex] = useState(0);
  const [activeView, setActiveView] = useState<ViewName>("keyword");
  const [belowFloor, setBelowFloor] = useState(false);
  const [sliderOverride, setSliderOverride] = useState<number | null>(null);
  const [pdfCandidate, setPdfCandidate] = useState<DisplayCandidate | null>(null);

  useEffect(() => {
    setSliderOverride(null);
  }, [currentItemIndex, activeView, belowFloor]);

  const items = useMemo(
    () => result.keyword.results.map((r) => ({ item_id: r.item_id, text: r.item_text })),
    [result],
  );

  const chunkMap = useMemo<Map<string, ChunkOut>>(() => buildChunkMap(result.chunks), [result]);

  const currentItem = items[currentItemIndex] ?? null;

  const ranked = useMemo(() => {
    if (!currentItem) return [];
    return getRankedForItem(activeView, currentItem.item_id, result.keyword, result.semantic, result.rrf);
  }, [result, activeView, currentItem]);

  const pool = useMemo(() => eligiblePool(activeView, ranked, belowFloor), [activeView, ranked, belowFloor]);
  const bounds = useMemo(() => sliderBounds(pool), [pool]);
  const defaultValue = useMemo(() => defaultSliderValue(pool, topK), [pool, topK]);
  const sliderValue = sliderOverride ?? defaultValue;

  const candidates = useMemo(
    () => toDisplayCandidates(pool, sliderValue, chunkMap),
    [pool, sliderValue, chunkMap],
  );

  return (
    <div className="results-layout">
      <ItemList items={items} currentIndex={currentItemIndex} onSelect={setCurrentItemIndex} />

      <div className="results-main">
        <div className="results-toolbar panel">
          <ViewToggle view={activeView} onChange={setActiveView} />
          <ConfidenceSlider
            view={activeView}
            min={bounds.min}
            max={bounds.max}
            value={sliderValue}
            onChange={setSliderOverride}
            visibleCount={candidates.length}
            totalCount={pool.length}
            belowFloor={belowFloor}
            onBelowFloorChange={setBelowFloor}
          />
          <button className="restart-link" onClick={onRestart}>
            Start over with a new document
          </button>
        </div>

        <div className="candidate-list">
          {candidates.length === 0 ? (
            <p className="empty-state">
              No candidates at or above the current floor for this item/view. Lower the
              slider to see more.
            </p>
          ) : (
            candidates.map((c, i) => (
              <CandidateCard
                key={`${c.doc_id}-${c.clause_no}-${c.page_start}-${c.page_end}-${i}`}
                candidate={c}
                view={activeView}
                onViewPdf={setPdfCandidate}
              />
            ))
          )}
        </div>
      </div>

      {pdfCandidate && (
        <PdfViewer
          key={`${result.docFilename}-${pdfCandidate.page_start}-${pdfCandidate.page_end}`}
          docFilename={result.docFilename}
          pageStart={pdfCandidate.page_start}
          pageEnd={pdfCandidate.page_end}
          clauseLabel={`${pdfCandidate.doc_id} ${pdfCandidate.clause_no ?? ""}`}
          onClose={() => setPdfCandidate(null)}
        />
      )}
    </div>
  );
}
