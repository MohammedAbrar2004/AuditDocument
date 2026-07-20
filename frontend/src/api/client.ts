// One place every backend call goes through (phases/phase7.md Part B).

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

// Real filenames/checklist names contain spaces (edge case 1) — every path segment
// built from user data must go through this.
export function enc(segment: string): string {
  return encodeURIComponent(segment);
}

async function extractDetail(res: Response): Promise<string> {
  try {
    const body = await res.json();
    return typeof body?.detail === "string" ? body.detail : res.statusText;
  } catch {
    return res.statusText;
  }
}

async function request<T>(method: string, path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, { method, ...init });
  if (!res.ok) {
    throw new ApiError(res.status, await extractDetail(res));
  }
  return (await res.json()) as T;
}

export function get<T>(path: string): Promise<T> {
  return request<T>("GET", path);
}

export function post<T>(path: string): Promise<T> {
  return request<T>("POST", path, { method: "POST" });
}

/** GET that treats 404 as "not built yet" (null) instead of throwing — the backbone of
 * the Part C idempotent check-then-build chain. Any other error still throws. */
export async function tryGet<T>(path: string): Promise<T | null> {
  try {
    return await request<T>("GET", path);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
}

export interface ParseSummary {
  source_file: string;
  sub_documents: { doc_id: string }[];
}

export async function uploadPdf(file: File): Promise<ParseSummary> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE_URL}/parse/upload`, { method: "POST", body: form });
  if (!res.ok) {
    throw new ApiError(res.status, await extractDetail(res));
  }
  return (await res.json()) as ParseSummary;
}

/** URL for the raw uploaded PDF bytes (Phase 7 UI redesign — inline PDF viewer). Passed
 * straight to react-pdf's `<Document file={...}>`, which fetches it itself. */
export function originalFileUrl(docFilename: string): string {
  return `${BASE_URL}/parse/${enc(docFilename)}/file`;
}

export interface ResolvedConfig {
  retrieval: { top_k: number };
  [key: string]: unknown;
}

export function getConfig(): Promise<ResolvedConfig> {
  return get<ResolvedConfig>("/config");
}
