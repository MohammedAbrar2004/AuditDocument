import { useState, type ChangeEvent } from "react";
import { IndexingProgress } from "../components/IndexingProgress";
import type { useDocumentIndexing } from "../pipeline/useIndexingPipeline";
import { loadRecentDocs } from "../pipeline/recentDocs";

interface UploadStepProps {
  docIndexing: ReturnType<typeof useDocumentIndexing>;
  onContinue: () => void;
  onPickRecent: (filename: string, checklistName: string) => void;
}

export function UploadStep({ docIndexing, onContinue, onPickRecent }: UploadStepProps) {
  const [validationError, setValidationError] = useState<string | null>(null);
  const recentDocs = loadRecentDocs();

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    // Edge case: reject non-PDF client-side, before any network call.
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setValidationError(`"${file.name}" is not a .pdf file. Only .pdf files are accepted.`);
      e.target.value = "";
      return;
    }
    setValidationError(null);
    void docIndexing.run({ file });
  }

  if (docIndexing.result) {
    const { docFilename, subDocumentCount, elapsedSeconds } = docIndexing.result;
    return (
      <div className="panel wizard-panel">
        <h2>Document indexed</h2>
        <p className="hint-text">
          {docFilename} — {subDocumentCount} sub-document{subDocumentCount === 1 ? "" : "s"} found,
          indexed in {elapsedSeconds.toFixed(0)}s.
        </p>
        <button className="primary-btn" onClick={onContinue}>
          Continue — pick a checklist
        </button>
      </div>
    );
  }

  return (
    <div className="panel wizard-panel">
      <h2>Upload document</h2>
      <p className="hint-text">Upload the QMS PDF to index. Parsing and clause-chunking run now.</p>
      <div className="field-row">
        <input
          type="file"
          accept=".pdf"
          onChange={handleFileChange}
          disabled={docIndexing.running}
        />
      </div>
      {validationError && <p className="error-text">{validationError}</p>}

      <IndexingProgress steps={docIndexing.steps} error={docIndexing.error} />

      {recentDocs.length > 0 && !docIndexing.running && (
        <div className="recent-docs">
          <p className="hint-text">Previously indexed in this browser:</p>
          <ul>
            {recentDocs.map((d) => (
              <li key={`${d.filename}__${d.checklistName}`}>
                <button onClick={() => onPickRecent(d.filename, d.checklistName)}>
                  {d.filename} — {d.checklistName}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
