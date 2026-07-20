import { useEffect, useState } from "react";
import { getConfig } from "./api/client";
import type { ChecklistListEntryOut } from "./api/types";
import { StepIndicator, type WizardStep } from "./components/StepIndicator";
import { ChecklistStep } from "./steps/ChecklistStep";
import { ResultsStep } from "./steps/ResultsStep";
import { RunStep } from "./steps/RunStep";
import { UploadStep } from "./steps/UploadStep";
import { fetchChecklists, useChecklistMapping, useDocumentIndexing } from "./pipeline/useIndexingPipeline";

const DEFAULT_TOP_K = 10; // fallback only if /config is unreachable

export default function App() {
  const [step, setStep] = useState<WizardStep>("upload");

  const [checklists, setChecklists] = useState<ChecklistListEntryOut[]>([]);
  const [checklistsLoading, setChecklistsLoading] = useState(true);
  const [checklistsError, setChecklistsError] = useState<string | null>(null);
  const [selectedChecklist, setSelectedChecklist] = useState<ChecklistListEntryOut | null>(null);
  const [topK, setTopK] = useState(DEFAULT_TOP_K);

  const docIndexing = useDocumentIndexing();
  const mapping = useChecklistMapping();

  useEffect(() => {
    fetchChecklists()
      .then((list) => {
        setChecklists(list);
        setChecklistsLoading(false);
      })
      .catch((err) => {
        setChecklistsError((err as Error).message);
        setChecklistsLoading(false);
      });

    getConfig()
      .then((cfg) => setTopK(cfg.retrieval?.top_k ?? DEFAULT_TOP_K))
      .catch(() => setTopK(DEFAULT_TOP_K)); // non-fatal — keep the documented fallback
  }, []);

  function handlePickRecent(filename: string, checklistName: string) {
    void docIndexing.run({ docFilename: filename });
    const match = checklists.find((c) => c.checklist_name === checklistName);
    if (match) setSelectedChecklist(match);
  }

  function handleRestart() {
    docIndexing.reset();
    mapping.reset();
    setSelectedChecklist(null);
    setStep("upload");
  }

  return (
    <div className="app">
      <header>
        <h1>Audit Mapping</h1>
        <p className="hint-text">
          AI-suggested document sections per checklist item — every match needs human
          review; nothing here is a compliance verdict.
        </p>
      </header>

      <StepIndicator current={step} />

      {step === "upload" && (
        <UploadStep
          docIndexing={docIndexing}
          onContinue={() => setStep("checklist")}
          onPickRecent={handlePickRecent}
        />
      )}

      {step === "checklist" && (
        <ChecklistStep
          checklists={checklists}
          loading={checklistsLoading}
          error={checklistsError}
          selected={selectedChecklist}
          onSelect={setSelectedChecklist}
          onRun={() => setStep("run")}
        />
      )}

      {step === "run" && docIndexing.result && selectedChecklist && (
        <RunStep
          mapping={mapping}
          docFilename={docIndexing.result.docFilename}
          chunks={docIndexing.result.chunks}
          checklist={selectedChecklist}
          onDone={() => setStep("results")}
          onBack={() => setStep("checklist")}
        />
      )}

      {step === "results" && mapping.result && (
        <ResultsStep result={mapping.result} topK={topK} onRestart={handleRestart} />
      )}
    </div>
  );
}
