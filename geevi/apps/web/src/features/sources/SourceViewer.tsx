"use client";

import { useEffect, useRef, useState } from "react";
import { Button, Empty } from "@/components/ui";
import { ApiError, fetchBinary } from "@/lib/api/client";

export type Highlight = { page: number; region: number[]; pageSize?: number[] | null; units?: string | null; label?: string };
type Fraction = [number, number, number, number];

function toFraction(h: Highlight): Fraction | null {
  if (!h.region || h.region.length !== 4) return null;
  const [x0, y0, x1, y1] = h.region;
  if (h.units === "fraction" || !h.pageSize) return [x0, y0, x1, y1];
  const [w, hgt] = h.pageSize;
  return [x0 / w, y0 / hgt, x1 / w, y1 / hgt];
}

/**
 * Client-only viewer for the authenticated original. PDF pages are rendered with PDF.js using the
 * worker bundled from the pinned dependency (no CDN). Bytes come from the API content endpoint and
 * are only ever drawn to a canvas or shown as an image: source content is never injected as markup.
 */
export function SourceViewer({ contentPath, mediaType, available, highlight, selecting, onSelect, fallbackText }: {
  contentPath: string; mediaType: string | null; available: boolean; highlight: Highlight | null; selecting?: boolean;
  onSelect?: (page: number, region: Fraction) => void; fallbackText?: string[] | null;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const frameRef = useRef<HTMLDivElement>(null);
  const [doc, setDoc] = useState<{ numPages: number; getPage: (n: number) => Promise<any> } | null>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [pageCount, setPageCount] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [sha, setSha] = useState<string | null>(null);
  const [drag, setDrag] = useState<{ x: number; y: number; x2: number; y2: number } | null>(null);

  useEffect(() => {
    if (!available) return;
    let cancelled = false;
    let objectUrl: string | null = null;
    (async () => {
      try {
        const { bytes, sha256 } = await fetchBinary(contentPath);
        if (cancelled) return;
        setSha(sha256);
        if (mediaType === "application/pdf") {
          const pdfjs = await import("pdfjs-dist");
          pdfjs.GlobalWorkerOptions.workerSrc = new URL("pdfjs-dist/build/pdf.worker.min.mjs", import.meta.url).toString();
          const loaded = await pdfjs.getDocument({ data: new Uint8Array(bytes) }).promise;
          if (cancelled) return;
          setDoc(loaded as never);
          setPageCount(loaded.numPages);
        } else {
          objectUrl = URL.createObjectURL(new Blob([bytes], { type: mediaType ?? "image/png" }));
          setImageUrl(objectUrl);
        }
      } catch (caught) {
        if (!cancelled) setError(caught instanceof ApiError ? caught.message : "The original could not be displayed.");
      }
    })();
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [contentPath, mediaType, available]);

  // Follow the highlighted region to its page (adjusting state during render, not in an effect).
  const [followed, setFollowed] = useState<Highlight | null>(null);
  if (highlight !== followed) {
    setFollowed(highlight);
    if (highlight?.page) setPageNumber(highlight.page);
  }

  useEffect(() => {
    if (!doc || !canvasRef.current) return;
    let task: { cancel: () => void; promise: Promise<void> } | null = null;
    let cancelled = false;
    (async () => {
      const page = await doc.getPage(Math.min(pageNumber, doc.numPages));
      if (cancelled || !canvasRef.current) return;
      const viewport = page.getViewport({ scale: 1.6 });
      const canvas = canvasRef.current;
      canvas.width = viewport.width;
      canvas.height = viewport.height;
      task = page.render({ canvasContext: canvas.getContext("2d")!, canvas, viewport });
      await task!.promise.catch(() => undefined);
      if (!cancelled) canvas.dataset.rendered = String(pageNumber);
    })();
    return () => {
      cancelled = true;
      task?.cancel();
    };
  }, [doc, pageNumber]);

  const box = highlight && highlight.page === pageNumber ? toFraction(highlight) : null;
  useEffect(() => {
    if (box && frameRef.current) {
      frameRef.current.focus({ preventScroll: true });
      frameRef.current.querySelector(".highlight")?.scrollIntoView({ block: "center", behavior: "auto" });
    }
  }, [highlight]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!available) {
    return (
      <div className="card card-warn" data-testid="original-unavailable">
        <h3>Original unavailable</h3>
        <p>The original bytes for this document were not supplied, so findings cannot be verified against it. Supply the exact original file (matching hash).</p>
        {fallbackText?.length ? (
          <>
            <p className="small">Text captured by the legacy prototype (shown as plain text, not verified):</p>
            {fallbackText.map((text, i) => <pre className="quote" key={i}>{text}</pre>)}
          </>
        ) : null}
      </div>
    );
  }
  if (error) return <div className="error-summary" role="alert">{error}</div>;

  const point = (e: React.MouseEvent) => {
    const rect = e.currentTarget.getBoundingClientRect();
    return { x: (e.clientX - rect.left) / rect.width, y: (e.clientY - rect.top) / rect.height };
  };
  return (
    <div>
      <div className="row" style={{ marginBottom: ".5rem" }}>
        <Button onClick={() => setPageNumber((n) => Math.max(1, n - 1))} disabled={pageNumber <= 1}>Previous page</Button>
        <span aria-live="polite" data-testid="page-indicator">Page {pageNumber} of {pageCount}</span>
        <Button onClick={() => setPageNumber((n) => Math.min(pageCount, n + 1))} disabled={pageNumber >= pageCount}>Next page</Button>
        {sha ? <span className="small mono" title="SHA-256 of the served original">sha256 {sha.slice(0, 16)}…</span> : null}
      </div>
      <div ref={frameRef} className="page-frame" tabIndex={-1} data-testid="source-frame"
        aria-label={`Original document, page ${pageNumber}${box && highlight?.label ? `. Highlighted source region: ${highlight.label}` : ""}`}>
        <div className="page-surface">
          {mediaType === "application/pdf" ? <canvas ref={canvasRef} data-testid="source-canvas" /> : imageUrl
            // eslint-disable-next-line @next/next/no-img-element
            ? <img src={imageUrl} alt="Scanned original document (image-only; no text layer)" data-testid="source-image" /> : <Empty>Loading original…</Empty>}
          {box ? <div className="highlight" data-testid="source-highlight" style={{ left: `${box[0] * 100}%`, top: `${box[1] * 100}%`, width: `${(box[2] - box[0]) * 100}%`, height: `${(box[3] - box[1]) * 100}%` }} /> : null}
          {selecting ? (
            <div className="select-layer" data-testid="select-layer" aria-hidden="true"
              onMouseDown={(e) => { const p = point(e); setDrag({ x: p.x, y: p.y, x2: p.x, y2: p.y }); }}
              onMouseMove={(e) => { if (drag) { const p = point(e); setDrag({ ...drag, x2: p.x, y2: p.y }); } }}
              onMouseUp={() => {
                if (drag && onSelect) {
                  const r: Fraction = [Math.min(drag.x, drag.x2), Math.min(drag.y, drag.y2), Math.max(drag.x, drag.x2), Math.max(drag.y, drag.y2)];
                  if (r[2] - r[0] > 0.01 && r[3] - r[1] > 0.005) onSelect(pageNumber, r.map((v) => Math.round(v * 10000) / 10000) as Fraction);
                }
                setDrag(null);
              }}>
              {drag ? <div className="highlight" style={{ left: `${Math.min(drag.x, drag.x2) * 100}%`, top: `${Math.min(drag.y, drag.y2) * 100}%`, width: `${Math.abs(drag.x2 - drag.x) * 100}%`, height: `${Math.abs(drag.y2 - drag.y) * 100}%` }} /> : null}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
