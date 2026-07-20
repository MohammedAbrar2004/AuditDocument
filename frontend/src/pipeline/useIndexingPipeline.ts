import { useCallback, useState } from "react";
import { ApiError, enc, get, post, tryGet, uploadPdf, type ParseSummary } from "../api/client";
import type {
  ChecklistEmbeddingsMetaOut,
  ChecklistListEntryOut,
  ChecklistOut,
  ChunkEmbeddingsMetaOut,
  ChunkResponse,
  FusedResponse,
  KeywordResponse,
  SemanticResponse,
} from "../api/types";
import { rememberIndexedDoc } from "./recentDocs";

// Phase 7 wizard redesign: the original single "index everything" chain is split into
// two phases matching what the backend actually requires — Phase 1/2 (parse+chunk) need
// no checklist at all, so that work happens at the Upload step. Everything from Phase 3
// onward (checklist parse, both embeddings, all three views) genuinely needs a chosen
// checklist, so it happens at the Run-mapping step. Both chains keep the same
// GET-then-POST idempotent-skip pattern as before.

export type StepStatus = "pending" | "running" | "done" | "skipped" | "error";

export interface PipelineStep {
  key: string;
  label: string;
  status: StepStatus;
}

function toSteps(defs: { key: string; label: string }[]): PipelineStep[] {
  return defs.map((d) => ({ ...d, status: "pending" as StepStatus }));
}

// --- Phase A: document indexing (parse + chunk) — no checklist required ------------

export interface DocumentIndexResult {
  docFilename: string;
  chunks: ChunkResponse;
  subDocumentCount: number;
  elapsedSeconds: number;
}

const DOC_STEP_DEFS = [
  { key: "parse", label: "Parsing document" },
  { key: "chunk", label: "Chunking document" },
];

export interface DocumentIndexRunOptions {
  file?: File; // present for a fresh upload; absent when revisiting a known filename
  docFilename?: string;
}

export function useDocumentIndexing() {
  const [steps, setSteps] = useState<PipelineStep[]>(toSteps(DOC_STEP_DEFS));
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<DocumentIndexResult | null>(null);

  const setStepStatus = useCallback((key: string, status: StepStatus) => {
    setSteps((prev) => prev.map((s) => (s.key === key ? { ...s, status } : s)));
  }, []);

  const reset = useCallback(() => {
    setSteps(toSteps(DOC_STEP_DEFS));
    setError(null);
    setResult(null);
  }, []);

  const run = useCallback(async ({ file, docFilename }: DocumentIndexRunOptions) => {
    setRunning(true);
    setError(null);
    setResult(null);
    setSteps(toSteps(DOC_STEP_DEFS));
    const startedAt = Date.now();

    try {
      setStepStatus("parse", "running");
      let effectiveFilename = docFilename ?? "";
      let subDocumentCount: number;
      if (file) {
        const uploaded = await uploadPdf(file);
        effectiveFilename = uploaded.source_file;
        subDocumentCount = uploaded.sub_documents.length;
        setStepStatus("parse", "done");
      } else {
        const parsed = await tryGet<ParseSummary>(`/parse/${enc(effectiveFilename)}`);
        if (!parsed) {
          throw new Error(
            `No parsed data found for "${effectiveFilename}". Please upload the PDF again.`,
          );
        }
        subDocumentCount = parsed.sub_documents.length;
        setStepStatus("parse", "skipped");
      }

      setStepStatus("chunk", "running");
      let chunks = await tryGet<ChunkResponse>(`/chunks/${enc(effectiveFilename)}`);
      if (chunks) {
        setStepStatus("chunk", "skipped");
      } else {
        chunks = await post<ChunkResponse>(`/chunks/${enc(effectiveFilename)}`);
        setStepStatus("chunk", "done");
      }

      const finalResult: DocumentIndexResult = {
        docFilename: effectiveFilename,
        chunks,
        subDocumentCount,
        elapsedSeconds: (Date.now() - startedAt) / 1000,
      };
      setResult(finalResult);
      return finalResult;
    } catch (err) {
      const message =
        err instanceof ApiError ? `${err.message} (HTTP ${err.status})` : (err as Error).message;
      setError(message);
      setSteps((prev) =>
        prev.map((s) => (s.status === "running" ? { ...s, status: "error" } : s)),
      );
      throw err;
    } finally {
      setRunning(false);
    }
  }, [setStepStatus]);

  return { steps, error, running, result, run, reset };
}

// --- Phase B: checklist mapping (checklist parse + both embeddings + 3 views) -----

export interface ChecklistMappingResult {
  docFilename: string;
  checklistName: string;
  chunks: ChunkResponse;
  keyword: KeywordResponse;
  semantic: SemanticResponse;
  rrf: FusedResponse;
  elapsedSeconds: number;
}

const MAP_STEP_DEFS = [
  { key: "checklist", label: "Preparing checklist" },
  { key: "embed_chunks", label: "Embedding document (slowest step)" },
  { key: "embed_checklist", label: "Embedding checklist" },
  { key: "keyword", label: "Building keyword view" },
  { key: "semantic", label: "Building semantic view" },
  { key: "rrf", label: "Building fused (Both) view" },
];

export interface ChecklistMappingRunOptions {
  docFilename: string;
  chunks: ChunkResponse;
  checklist: ChecklistListEntryOut;
}

export function useChecklistMapping() {
  const [steps, setSteps] = useState<PipelineStep[]>(toSteps(MAP_STEP_DEFS));
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<ChecklistMappingResult | null>(null);

  const setStepStatus = useCallback((key: string, status: StepStatus) => {
    setSteps((prev) => prev.map((s) => (s.key === key ? { ...s, status } : s)));
  }, []);

  const reset = useCallback(() => {
    setSteps(toSteps(MAP_STEP_DEFS));
    setError(null);
    setResult(null);
  }, []);

  const run = useCallback(async ({ docFilename, chunks, checklist }: ChecklistMappingRunOptions) => {
    setRunning(true);
    setError(null);
    setResult(null);
    setSteps(toSteps(MAP_STEP_DEFS));
    const startedAt = Date.now();

    try {
      // Step 1: checklist parsed
      setStepStatus("checklist", "running");
      let checklistOut = await tryGet<ChecklistOut>(`/checklists/${enc(checklist.checklist_name)}`);
      if (checklistOut) {
        setStepStatus("checklist", "skipped");
      } else {
        checklistOut = await post<ChecklistOut>(`/checklists/parse/${enc(checklist.filename)}`);
        setStepStatus("checklist", "done");
      }

      // Step 2: doc chunk embeddings
      setStepStatus("embed_chunks", "running");
      const chunkEmbMeta = await tryGet<ChunkEmbeddingsMetaOut>(
        `/embeddings/chunks/${enc(docFilename)}`,
      );
      if (chunkEmbMeta) {
        setStepStatus("embed_chunks", "skipped");
      } else {
        await post<ChunkEmbeddingsMetaOut>(`/embeddings/chunks/${enc(docFilename)}`);
        setStepStatus("embed_chunks", "done");
      }

      // Step 3: checklist embeddings
      setStepStatus("embed_checklist", "running");
      const checklistEmbMeta = await tryGet<ChecklistEmbeddingsMetaOut>(
        `/embeddings/checklist/${enc(checklist.checklist_name)}`,
      );
      if (checklistEmbMeta) {
        setStepStatus("embed_checklist", "skipped");
      } else {
        await post<ChecklistEmbeddingsMetaOut>(
          `/embeddings/checklist/${enc(checklist.checklist_name)}`,
        );
        setStepStatus("embed_checklist", "done");
      }

      // Step 4: keyword view
      setStepStatus("keyword", "running");
      let keyword = await tryGet<KeywordResponse>(
        `/keyword/${enc(docFilename)}/${enc(checklist.checklist_name)}`,
      );
      if (keyword) {
        setStepStatus("keyword", "skipped");
      } else {
        keyword = await post<KeywordResponse>(
          `/keyword/${enc(docFilename)}?checklist=${enc(checklist.checklist_name)}`,
        );
        setStepStatus("keyword", "done");
      }

      // Step 5: semantic view
      setStepStatus("semantic", "running");
      let semantic = await tryGet<SemanticResponse>(
        `/semantic/${enc(docFilename)}/${enc(checklist.checklist_name)}`,
      );
      if (semantic) {
        setStepStatus("semantic", "skipped");
      } else {
        semantic = await post<SemanticResponse>(
          `/semantic/${enc(docFilename)}?checklist=${enc(checklist.checklist_name)}`,
        );
        setStepStatus("semantic", "done");
      }

      // Step 6: rrf view
      setStepStatus("rrf", "running");
      let rrf = await tryGet<FusedResponse>(`/rrf/${enc(docFilename)}/${enc(checklist.checklist_name)}`);
      if (rrf) {
        setStepStatus("rrf", "skipped");
      } else {
        rrf = await post<FusedResponse>(
          `/rrf/${enc(docFilename)}?checklist=${enc(checklist.checklist_name)}`,
        );
        setStepStatus("rrf", "done");
      }

      const finalResult: ChecklistMappingResult = {
        docFilename,
        checklistName: checklist.checklist_name,
        chunks,
        keyword,
        semantic,
        rrf,
        elapsedSeconds: (Date.now() - startedAt) / 1000,
      };
      rememberIndexedDoc(docFilename, checklist.checklist_name);
      setResult(finalResult);
      return finalResult;
    } catch (err) {
      const message =
        err instanceof ApiError ? `${err.message} (HTTP ${err.status})` : (err as Error).message;
      setError(message);
      setSteps((prev) =>
        prev.map((s) => (s.status === "running" ? { ...s, status: "error" } : s)),
      );
      throw err;
    } finally {
      setRunning(false);
    }
  }, [setStepStatus]);

  return { steps, error, running, result, run, reset };
}

export function fetchChecklists(): Promise<ChecklistListEntryOut[]> {
  return get<ChecklistListEntryOut[]>("/checklists");
}
