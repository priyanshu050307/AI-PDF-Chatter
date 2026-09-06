'use client';

import React from 'react';
import { BookOpen } from 'lucide-react';
import { CitationItem } from '@/types';

interface CitationBadgeProps {
  citation: CitationItem;
  onNavigateToPage: (pageNumber: number) => void;
}

export const CitationBadge: React.FC<CitationBadgeProps> = ({ citation, onNavigateToPage }) => {
  const pageLabel =
    citation.page_start === citation.page_end
      ? `Page ${citation.page_start}`
      : `Pages ${citation.page_start}–${citation.page_end}`;

  const subtitle = [citation.chapter_title, citation.section_title].filter(Boolean).join(' • ');

  return (
    <button
      onClick={() => onNavigateToPage(citation.page_start)}
      className="group flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/30 text-xs text-indigo-300 font-medium transition-all hover:scale-[1.02]"
      title={`Jump to source in document (${pageLabel})`}
    >
      <BookOpen className="w-3.5 h-3.5 text-indigo-400 group-hover:text-indigo-200" />
      <span className="font-semibold text-white">{pageLabel}</span>
      {subtitle && <span className="text-[10px] text-slate-400 truncate max-w-[120px]">({subtitle})</span>}
    </button>
  );
};
