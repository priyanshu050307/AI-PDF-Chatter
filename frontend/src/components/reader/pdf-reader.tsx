'use client';

import React, { useEffect, useRef, useState } from 'react';
import * as pdfjsLib from 'pdfjs-dist';
import { Loader2, AlertCircle } from 'lucide-react';
import { useReaderStore } from '@/store/readerStore';
import { SelectionToolbar } from './selection-toolbar';
import { apiService } from '@/services/api';
import { HighlightColor, HighlightItem } from '@/types';

// Configure pdfjs worker source safely in browser environment
if (typeof window !== 'undefined' && pdfjsLib?.GlobalWorkerOptions) {
  pdfjsLib.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.js`;
}

interface PdfReaderProps {
  pdfData: ArrayBuffer;
  onDocumentLoaded?: (totalPages: number) => void;
}

const OVERLAY_COLOR_MAP: Record<HighlightColor, string> = {
  yellow: 'bg-yellow-400/35 border-b-2 border-yellow-500 hover:bg-yellow-400/50',
  green: 'bg-emerald-400/35 border-b-2 border-emerald-500 hover:bg-emerald-400/50',
  blue: 'bg-sky-400/35 border-b-2 border-sky-500 hover:bg-sky-400/50',
  pink: 'bg-pink-400/35 border-b-2 border-pink-500 hover:bg-pink-400/50',
  purple: 'bg-purple-400/35 border-b-2 border-purple-500 hover:bg-purple-400/50',
};

export const PdfReader: React.FC<PdfReaderProps> = ({ pdfData, onDocumentLoaded }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const renderTaskRef = useRef<any>(null);

  const [pdfDoc, setPdfDoc] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [canvasDimensions, setCanvasDimensions] = useState<{ width: number; height: number }>({ width: 0, height: 0 });

  // Selection Floating Position
  const [toolbarPos, setToolbarPos] = useState<{ x: number; y: number } | null>(null);

  const {
    documentId,
    currentPage,
    totalPages,
    zoomLevel,
    fitMode,
    highlights,
    setTotalPages,
    setSelection,
    clearSelection,
    setHighlights
  } = useReaderStore();

  // Load annotations from API when documentId changes
  useEffect(() => {
    if (!documentId) return;
    apiService
      .getHighlights(documentId)
      .then((data) => {
        setHighlights(data.items);
      })
      .catch((err) => {
        console.warn('Could not load document highlights:', err);
      });
  }, [documentId, setHighlights]);

  // Handle Text Selection in Document Container
  const handleMouseUp = () => {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed) {
      setToolbarPos(null);
      return;
    }

    const text = sel.toString().trim();
    if (text.length > 0 && containerRef.current && canvasRef.current) {
      const range = sel.getRangeAt(0);
      const rect = range.getBoundingClientRect();
      const containerRect = containerRef.current.getBoundingClientRect();
      const canvasRect = canvasRef.current.getBoundingClientRect();

      // Multi-line selection client rects
      const clientRects = Array.from(range.getClientRects());
      const rects = clientRects.map((r) => ({
        x: (r.left - canvasRect.left) / canvasRect.width,
        y: (r.top - canvasRect.top) / canvasRect.height,
        width: r.width / canvasRect.width,
        height: r.height / canvasRect.height,
      }));

      // Relative coordinates for floating toolbar
      const x = rect.left + rect.width / 2 - containerRect.left;
      const y = rect.top - containerRect.top;

      // Page-relative normalized coordinates
      const normX = (rect.left - canvasRect.left) / canvasRect.width;
      const normY = (rect.top - canvasRect.top) / canvasRect.height;
      const normWidth = rect.width / canvasRect.width;
      const normHeight = rect.height / canvasRect.height;

      setSelection({
        selected_text: text,
        page_number: currentPage,
        bounding_box: {
          x: normX,
          y: normY,
          width: normWidth,
          height: normHeight,
          page_width: canvasRect.width,
          page_height: canvasRect.height,
          rects: rects.length > 1 ? rects : undefined,
        },
      });

      setToolbarPos({ x, y });
    }
  };

  // Load PDF Document from ArrayBuffer
  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    setErrorMessage(null);

    const loadingTask = pdfjsLib.getDocument({ data: pdfData });
    loadingTask.promise
      .then((loadedDoc) => {
        if (!isMounted) return;
        setPdfDoc(loadedDoc);
        setTotalPages(loadedDoc.numPages);
        setIsLoading(false);
        if (onDocumentLoaded) {
          onDocumentLoaded(loadedDoc.numPages);
        }
      })
      .catch((err) => {
        if (!isMounted) return;
        setIsLoading(false);
        setErrorMessage(err?.message || 'Failed to render PDF document.');
      });

    return () => {
      isMounted = false;
      loadingTask.destroy();
    };
  }, [pdfData, setTotalPages, onDocumentLoaded]);

  // Render Current Page on Canvas
  useEffect(() => {
    if (!pdfDoc || !canvasRef.current || !containerRef.current) return;

    let isCancelled = false;
    setToolbarPos(null);

    pdfDoc.getPage(currentPage).then((page: any) => {
      if (isCancelled) return;

      const canvas = canvasRef.current!;
      const context = canvas.getContext('2d');
      if (!context) return;

      if (renderTaskRef.current) {
        renderTaskRef.current.cancel();
      }

      let scale = zoomLevel;
      if (fitMode === 'width' && containerRef.current) {
        const viewportUnscaled = page.getViewport({ scale: 1.0 });
        const containerWidth = containerRef.current.clientWidth - 48;
        scale = containerWidth / viewportUnscaled.width;
      }

      const viewport = page.getViewport({ scale });
      const devicePixelRatio = window.devicePixelRatio || 1;

      const cssWidth = Math.floor(viewport.width);
      const cssHeight = Math.floor(viewport.height);

      canvas.width = Math.floor(viewport.width * devicePixelRatio);
      canvas.height = Math.floor(viewport.height * devicePixelRatio);
      canvas.style.width = `${cssWidth}px`;
      canvas.style.height = `${cssHeight}px`;

      setCanvasDimensions({ width: cssWidth, height: cssHeight });

      context.scale(devicePixelRatio, devicePixelRatio);

      const renderContext = {
        canvasContext: context,
        viewport: viewport,
      };

      const renderTask = page.render(renderContext);
      renderTaskRef.current = renderTask;

      renderTask.promise.catch((err: any) => {
        if (err?.name !== 'RenderingCancelledException') {
          console.error('PDF Page Render Error:', err);
        }
      });
    });

    return () => {
      isCancelled = true;
      if (renderTaskRef.current) {
        renderTaskRef.current.cancel();
      }
    };
  }, [pdfDoc, currentPage, zoomLevel, fitMode]);

  // Filter current page annotations
  const pageHighlights = highlights.filter((h) => h.page_number === currentPage);

  return (
    <div
      ref={containerRef}
      onMouseUp={handleMouseUp}
      className="flex-1 w-full h-full bg-slate-950 overflow-auto flex flex-col items-center justify-start p-6 relative select-text"
    >
      <SelectionToolbar position={toolbarPos} />

      {isLoading ? (
        <div className="flex flex-col items-center justify-center h-full py-20 text-slate-400 select-none">
          <Loader2 className="w-10 h-10 text-indigo-500 animate-spin mb-3" />
          <p className="text-sm font-medium">Preparing document viewer...</p>
        </div>
      ) : errorMessage ? (
        <div className="flex flex-col items-center justify-center h-full py-16 text-center max-w-md select-none">
          <AlertCircle className="w-10 h-10 text-rose-500 mb-3" />
          <h3 className="text-base font-bold text-white">Rendering Error</h3>
          <p className="text-xs text-slate-400 mt-1">{errorMessage}</p>
        </div>
      ) : (
        <div
          ref={wrapperRef}
          className="relative shadow-2xl rounded-lg bg-white overflow-hidden my-auto border border-slate-800 transition-transform duration-150"
        >
          <canvas ref={canvasRef} className="block" />

          {/* Persistent Page-Local Highlight Overlay Layer */}
          <div
            className="absolute inset-0 pointer-events-none"
            style={{ width: `${canvasDimensions.width}px`, height: `${canvasDimensions.height}px` }}
          >
            {pageHighlights.map((item) => {
              if (!item.bounding_box) return null;

              const bbox = item.bounding_box;
              const colorClass = OVERLAY_COLOR_MAP[item.color] || OVERLAY_COLOR_MAP.yellow;

              // Render multi-rectangle selection boxes if present
              if (bbox.rects && bbox.rects.length > 0) {
                return bbox.rects.map((r, idx) => {
                  const left = r.x * canvasDimensions.width;
                  const top = r.y * canvasDimensions.height;
                  const width = r.width * canvasDimensions.width;
                  const height = r.height * canvasDimensions.height;

                  return (
                    <div
                      key={`${item.id}-rect-${idx}`}
                      style={{
                        position: 'absolute',
                        left: `${left}px`,
                        top: `${top}px`,
                        width: `${width}px`,
                        height: `${height}px`,
                      }}
                      className={`pointer-events-auto cursor-pointer transition-colors ${colorClass}`}
                      title={item.note_text ? `Note: ${item.note_text}` : item.selected_text}
                    />
                  );
                });
              }

              // Fallback single rectangle
              const left = bbox.x * canvasDimensions.width;
              const top = bbox.y * canvasDimensions.height;
              const width = bbox.width * canvasDimensions.width;
              const height = bbox.height * canvasDimensions.height;

              return (
                <div
                  key={item.id}
                  style={{
                    position: 'absolute',
                    left: `${left}px`,
                    top: `${top}px`,
                    width: `${width}px`,
                    height: `${height}px`,
                  }}
                  className={`pointer-events-auto cursor-pointer transition-colors ${colorClass}`}
                  title={item.note_text ? `Note: ${item.note_text}` : item.selected_text}
                />
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
