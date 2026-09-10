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
  MessageSquare,
  GraduationCap,
  Users,
  Sparkles,
} from 'lucide-react';
import { useReaderStore } from '@/store/readerStore';

interface ReaderToolbarProps {
  documentTitle?: string;
  isChatOpen?: boolean;
  sidebarMode?: 'chat' | 'study';
  characterPanelOpen?: boolean;
  onToggleChat?: () => void;
  onToggleStudy?: () => void;
  onToggleCharacters?: () => void;
}

export const ReaderToolbar: React.FC<ReaderToolbarProps> = ({
  documentTitle,
  isChatOpen = true,
  sidebarMode = 'chat',
  characterPanelOpen = false,
  onToggleChat,
  onToggleStudy,
  onToggleCharacters,
}) => {
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
    <header className="h-14 bg-slate-950/90 backdrop-blur-md border-b border-slate-800/80 px-4 flex items-center justify-between text-slate-200 select-none shadow-sm z-30 shrink-0">
      {/* Left: Library Back & Document Title */}
      <div className="flex items-center space-x-3 min-w-0 max-w-[30%]">
        <Link
          href="/dashboard"
          className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-xs font-semibold text-slate-300 hover:text-white transition-all shrink-0"
          title="Return to Dashboard"
        >
          <ArrowLeft className="w-3.5 h-3.5 text-slate-400" />
          <span className="hidden sm:inline">Dashboard</span>
        </Link>
        <div className="h-4 w-px bg-slate-800/80 hidden sm:block shrink-0" />
        <h1 className="text-xs sm:text-sm font-semibold text-slate-200 truncate tracking-tight">
          {documentTitle || 'PDF Reader'}
        </h1>
      </div>

      {/* Center: Clean Page Navigation & Zoom Controls */}
      <div className="flex items-center space-x-2 sm:space-x-3">
        {/* Page Nav */}
        <div className="flex items-center bg-slate-900/90 border border-slate-800/80 rounded-lg p-0.5 shadow-inner">
          <button
            onClick={prevPage}
            disabled={currentPage <= 1}
            className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            title="Previous Page"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>

          <form onSubmit={handlePageSubmit} className="flex items-center px-1.5 space-x-1">
            <input
              type="text"
              value={pageInput}
              onChange={(e) => setPageInput(e.target.value)}
              className="w-9 py-0.5 text-center bg-slate-950 border border-slate-800 rounded text-xs font-semibold text-indigo-300 focus:outline-none focus:border-indigo-500/80 transition-colors"
            />
            <span className="text-xs text-slate-500 font-medium">/ {totalPages || 1}</span>
          </form>

          <button
            onClick={nextPage}
            disabled={currentPage >= totalPages}
            className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            title="Next Page"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        {/* Zoom Controls */}
        <div className="hidden md:flex items-center bg-slate-900/90 border border-slate-800/80 rounded-lg p-0.5 shadow-inner">
          <button
            onClick={zoomOut}
            className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            title="Zoom Out"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>

          <span className="text-xs font-semibold text-slate-300 w-11 text-center font-mono">
            {Math.round(zoomLevel * 100)}%
          </span>

          <button
            onClick={zoomIn}
            className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            title="Zoom In"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Fit Width */}
        <button
          onClick={() => setFitMode('width')}
          className="hidden lg:block px-2 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-xs font-medium text-slate-400 hover:text-slate-200 transition-colors"
          title="Fit page width"
        >
          Fit Width
        </button>

        {/* Fullscreen */}
        <button
          onClick={toggleFullscreen}
          className="p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
          title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
        >
          {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
        </button>
      </div>

      {/* Right: Integrated Workspace Toggle Pills */}
      <div className="flex items-center space-x-1.5">
        {onToggleChat && (
          <button
            onClick={onToggleChat}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all ${
              isChatOpen && sidebarMode === 'chat'
                ? 'bg-indigo-600/20 border-indigo-500/60 text-indigo-300 shadow-sm shadow-indigo-950'
                : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5 text-indigo-400" />
            <span className="hidden sm:inline">Ask AI</span>
          </button>
        )}

        {onToggleStudy && (
          <button
            onClick={onToggleStudy}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all ${
              isChatOpen && sidebarMode === 'study'
                ? 'bg-purple-600/20 border-purple-500/60 text-purple-300 shadow-sm shadow-purple-950'
                : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
          >
            <GraduationCap className="w-3.5 h-3.5 text-purple-400" />
            <span className="hidden sm:inline">AI Study Mode</span>
          </button>
        )}

        {onToggleCharacters && (
          <button
            onClick={onToggleCharacters}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all ${
              characterPanelOpen
                ? 'bg-cyan-600/20 border-cyan-500/60 text-cyan-300 shadow-sm shadow-cyan-950'
                : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
          >
            <Users className="w-3.5 h-3.5 text-cyan-400" />
            <span className="hidden sm:inline">Characters</span>
          </button>
        )}
      </div>
    </header>
  );
};
