'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  ChevronLeft,
  ChevronRight,
  ArrowLeft,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Minimize2,
  Maximize,
  Sparkles
} from 'lucide-react';
import { useReaderStore } from '@/store/readerStore';

interface ReaderToolbarProps {
  documentTitle?: string;
}

export const ReaderToolbar: React.FC<ReaderToolbarProps> = ({ documentTitle }) => {
  const {
    currentPage,
    totalPages,
    zoomLevel,
    isFullscreen,
    setCurrentPage,
    nextPage,
    prevPage,
    zoomIn,
    zoomOut,
    setZoomLevel,
    setFitMode,
    toggleFullscreen,
  } = useReaderStore();

  const [pageInput, setPageInput] = useState(String(currentPage));

  useEffect(() => {
    setPageInput(String(currentPage));
  }, [currentPage]);

  const handlePageSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const parsed = parseInt(pageInput, 10);
    if (!isNaN(parsed) && parsed >= 1 && parsed <= totalPages) {
      setCurrentPage(parsed);
    } else {
      setPageInput(String(currentPage));
    }
  };

  return (
    <header className="h-14 bg-slate-900 border-b border-slate-800 px-4 flex items-center justify-between text-slate-200 select-none shadow-md z-30">
      {/* Left: Navigation back & Title */}
      <div className="flex items-center space-x-4 min-w-0">
        <Link
          href="/dashboard"
          className="flex items-center space-x-1 px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span className="hidden sm:inline">Library</span>
        </Link>
        <div className="h-4 w-px bg-slate-800 hidden sm:block" />
        <h2 className="text-sm font-bold text-white truncate max-w-xs sm:max-w-md">
          {documentTitle || 'PDF Reader'}
        </h2>
      </div>

      {/* Center: Page Controls */}
      <div className="flex items-center space-x-2">
        <button
          onClick={prevPage}
          disabled={currentPage <= 1}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          title="Previous Page"
        >
          <ChevronLeft className="w-5 h-5" />
        </button>

        <form onSubmit={handlePageSubmit} className="flex items-center space-x-1.5">
          <input
            type="text"
            value={pageInput}
            onChange={(e) => setPageInput(e.target.value)}
            className="w-11 py-1 text-center bg-slate-950 border border-slate-800 rounded-md text-xs font-bold text-white focus:outline-none focus:border-indigo-500"
          />
          <span className="text-xs text-slate-400 font-medium">/ {totalPages}</span>
        </form>

        <button
          onClick={nextPage}
          disabled={currentPage >= totalPages}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          title="Next Page"
        >
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>

      {/* Right: Zoom & Layout Controls */}
      <div className="flex items-center space-x-2 sm:space-x-3">
        <div className="hidden md:flex items-center space-x-1 bg-slate-950 p-1 rounded-lg border border-slate-800">
          <button
            onClick={zoomOut}
            className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            title="Zoom Out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>

          <span className="text-xs font-bold text-slate-300 w-12 text-center">
            {Math.round(zoomLevel * 100)}%
          </span>

          <button
            onClick={zoomIn}
            className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            title="Zoom In"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
        </div>

        <button
          onClick={() => setFitMode('width')}
          className="hidden lg:block px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 hover:text-white transition-colors"
        >
          Fit Width
        </button>

        <button
          onClick={toggleFullscreen}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
        >
          {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
        </button>

        {/* Reserved AI Panel Placeholder Badge */}
        <div
          className="hidden xl:flex items-center space-x-1 px-2.5 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-medium"
          title="AI Workspace reserved for future Phase 3/4"
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>AI Companion (Phase 3)</span>
        </div>
      </div>
    </header>
  );
};
