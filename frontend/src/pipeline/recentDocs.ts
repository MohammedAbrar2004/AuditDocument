// Open decision 7: no backend "list uploaded docs" endpoint exists, so the frontend
// keeps a small local record of filenames it has indexed this browser, letting the
// auditor reselect a doc/checklist pair without re-uploading bytes. The idempotent
// GET-then-POST chain (useIndexingPipeline) makes revisiting instant regardless — this
// list only saves the auditor from having to remember/retype the exact filename.

const STORAGE_KEY = "audit-evidence-mapping:indexed-docs";
const MAX_ENTRIES = 20;

export interface RecentDoc {
  filename: string;
  checklistName: string;
  indexedAt: string;
}

export function loadRecentDocs(): RecentDoc[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as RecentDoc[]) : [];
  } catch {
    return [];
  }
}

export function rememberIndexedDoc(filename: string, checklistName: string): void {
  const rest = loadRecentDocs().filter(
    (d) => !(d.filename === filename && d.checklistName === checklistName),
  );
  const updated: RecentDoc[] = [
    { filename, checklistName, indexedAt: new Date().toISOString() },
    ...rest,
  ].slice(0, MAX_ENTRIES);
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  } catch {
    // localStorage unavailable (private mode, quota) — non-fatal, just skip remembering.
  }
}
