import { useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import pdfWorkerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import { originalFileUrl } from "../api/client";

// Worker bundled locally via Vite's `?url` import, never fetched from a CDN — keeps the
// app fully offline-runnable, same posture as every other dependency in this project.
pdfjs.GlobalWorkerOptions.workerSrc = pdfWorkerUrl;

interface PdfViewerProps {
  docFilename: string;
  pageStart: number;
  pageEnd: number;
  clauseLabel: string;
  onClose: () => void;
}

export function PdfViewer({ docFilename, pageStart, pageEnd, clauseLabel, onClose }: PdfViewerProps) {
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState(pageStart);
  const [loadError, setLoadError] = useState<string | null>(null);

  const inMatch = pageNumber >= pageStart && pageNumber <= pageEnd;

  return (
    <div className="pdf-viewer panel">
      <div className="pdf-viewer-header">
        <div>
          <strong>{clauseLabel}</strong>
          <span className="hint-text"> pp. {pageStart}-{pageEnd}</span>
        </div>
        <button onClick={onClose} aria-label="Close PDF viewer">
          ✕
        </button>
      </div>

      {loadError ? (
        <p className="error-text">Could not load the PDF: {loadError}</p>
      ) : (
        <div className="pdf-page-area">
          <Document
            file={originalFileUrl(docFilename)}
            onLoadSuccess={({ numPages: n }) => setNumPages(n)}
            onLoadError={(err) => setLoadError(err.message)}
            loading={<p className="hint-text">Loading PDF…</p>}
          >
            <Page pageNumber={pageNumber} width={440} />
          </Document>
        </div>
      )}

      <div className="pdf-viewer-nav">
        <button onClick={() => setPageNumber((p) => Math.max(1, p - 1))} disabled={pageNumber <= 1}>
          ‹ Prev
        </button>
        <span>
          Page {pageNumber}
          {numPages ? ` / ${numPages}` : ""} {inMatch && <em>(in match)</em>}
        </span>
        <button
          onClick={() => setPageNumber((p) => Math.min(numPages ?? p, p + 1))}
          disabled={numPages !== null && pageNumber >= numPages}
        >
          Next ›
        </button>
      </div>
    </div>
  );
}
