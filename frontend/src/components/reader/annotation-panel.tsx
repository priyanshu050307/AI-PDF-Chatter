'use client';

import React, { useState } from 'react';
import {
  Highlighter,
  FileText,
  Search,
  X,
  Trash2,
  Edit2,
  Check,
  ChevronRight,
  BookOpen,
  Filter
} from 'lucide-react';
import { useReaderStore } from '@/store/readerStore';
import { HighlightItem, HighlightColor } from '@/types';
import { apiService } from '@/services/api';

interface AnnotationPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

const COLOR_MAP: Record<HighlightColor, { bg: string; border: string; text: string; dot: string }> = {
  yellow: { bg: 'bg-yellow-500/15', border: 'border-yellow-500/40', text: 'text-yellow-300', dot: 'bg-yellow-400' },
  green: { bg: 'bg-emerald-500/15', border: 'border-emerald-500/40', text: 'text-emerald-300', dot: 'bg-emerald-400' },
  blue: { bg: 'bg-sky-500/15', border: 'border-sky-500/40', text: 'text-sky-300', dot: 'bg-sky-400' },
  pink: { bg: 'bg-pink-500/15', border: 'border-pink-500/40', text: 'text-pink-300', dot: 'bg-pink-400' },
  purple: { bg: 'bg-purple-500/15', border: 'border-purple-500/40', text: 'text-purple-300', dot: 'bg-purple-400' },
};

export const AnnotationPanel: React.FC<AnnotationPanelProps> = ({ isOpen, onClose }) => {
  const { highlights, setCurrentPage, deleteHighlightFromState, updateHighlightInState } = useReaderStore();

  const [activeTab, setActiveTab] = useState<'ALL' | 'HIGHLIGHTS' | 'NOTES'>('ALL');
  const [selectedColorFilter, setSelectedColorFilter] = useState<HighlightColor | 'ALL'>('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  // Editing state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editNoteText, setEditNoteText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  // Filter highlights
  const filteredHighlights = highlights.filter((item) => {
    // Type tab filter
    if (activeTab === 'HIGHLIGHTS' && item.note_text) return false;
    if (activeTab === 'NOTES' && !item.note_text) return false;

    // Color filter
    if (selectedColorFilter !== 'ALL' && item.color !== selectedColorFilter) return false;

    // Search query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchText = item.selected_text.toLowerCase().includes(q);
      const matchNote = item.note_text?.toLowerCase().includes(q) || false;
      if (!matchText && !matchNote) return false;
    }

    return true;
  });

  const handleJumpToPage = (pageNumber: number) => {
    setCurrentPage(pageNumber);
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await apiService.deleteHighlight(id);
      deleteHighlightFromState(id);
    } catch (err) {
      console.error('Failed to delete annotation:', err);
    }
  };

  const handleStartEditNote = (item: HighlightItem, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(item.id);
    setEditNoteText(item.note_text || '');
  };

  const handleSaveNote = async (id: string, e: React.FormEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsSubmitting(true);
    try {
      const updated = await apiService.updateHighlight(id, { note_text: editNoteText });
      updateHighlightInState(id, { note_text: updated.note_text });
      setEditingId(null);
    } catch (err) {
      console.error('Failed to update note:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-y-0 right-0 w-80 sm:w-96 bg-slate-900/95 backdrop-blur-xl border-l border-slate-800 z-50 flex flex-col shadow-2xl animate-in slide-in-from-right duration-200">
      {/* Panel Header */}
      <div className="flex items-center justify-between px-4 py-3.5 border-b border-slate-800 bg-slate-950/60">
        <div className="flex items-center gap-2">
          <Highlighter className="w-4 h-4 text-amber-400" />
          <h2 className="text-sm font-bold text-slate-100">Annotations & Notes</h2>
          <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-slate-800 text-slate-300">
            {highlights.length}
          </span>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Tabs & Search */}
      <div className="p-3 border-b border-slate-800/80 space-y-3 bg-slate-900/40">
        {/* Type Tabs */}
        <div className="grid grid-cols-3 gap-1 p-1 bg-slate-950/80 rounded-lg text-xs font-medium border border-slate-800">
          <button
            onClick={() => setActiveTab('ALL')}
            className={`py-1.5 rounded-md transition-colors ${
              activeTab === 'ALL'
                ? 'bg-indigo-600 text-white font-semibold shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            All
          </button>
          <button
            onClick={() => setActiveTab('HIGHLIGHTS')}
            className={`py-1.5 rounded-md transition-colors ${
              activeTab === 'HIGHLIGHTS'
                ? 'bg-indigo-600 text-white font-semibold shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Highlights
          </button>
          <button
            onClick={() => setActiveTab('NOTES')}
            className={`py-1.5 rounded-md transition-colors ${
              activeTab === 'NOTES'
                ? 'bg-indigo-600 text-white font-semibold shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Notes
          </button>
        </div>

        {/* Color Palette Filter */}
        <div className="flex items-center justify-between px-1">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Filter Color</span>
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => setSelectedColorFilter('ALL')}
              className={`text-xs px-2 py-0.5 rounded-full transition-colors ${
                selectedColorFilter === 'ALL' ? 'bg-slate-700 text-white font-semibold' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              All
            </button>
            {(['yellow', 'green', 'blue', 'pink', 'purple'] as HighlightColor[]).map((col) => (
              <button
                key={col}
                onClick={() => setSelectedColorFilter(col)}
                className={`w-4 h-4 rounded-full ${COLOR_MAP[col].dot} transition-transform ${
                  selectedColorFilter === col ? 'ring-2 ring-white ring-offset-2 ring-offset-slate-900 scale-110' : 'opacity-70 hover:opacity-100'
                }`}
              />
            ))}
          </div>
        </div>

        {/* Search Input */}
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search highlights and notes..."
            className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500/80 transition-colors"
          />
        </div>
      </div>

      {/* Annotations List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
        {filteredHighlights.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center text-slate-500">
            <BookOpen className="w-8 h-8 text-slate-600 mb-2 stroke-[1.5]" />
            <p className="text-xs font-medium">No matching annotations found</p>
            <p className="text-[11px] text-slate-600 mt-1 max-w-[200px]">
              Select text in the document viewer to create your first highlight or note.
            </p>
          </div>
        ) : (
          filteredHighlights.map((item) => {
            const style = COLOR_MAP[item.color] || COLOR_MAP.yellow;
            const isEditing = editingId === item.id;

            return (
              <div
                key={item.id}
                onClick={() => handleJumpToPage(item.page_number)}
                className={`p-3 rounded-xl border ${style.bg} ${style.border} hover:border-slate-600 transition-all cursor-pointer group relative`}
              >
                {/* Meta Header */}
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${style.dot}`} />
                    <span className="text-[11px] font-semibold text-slate-300">
                      Page {item.page_number}
                    </span>
                    {item.chapter_title && (
                      <span className="text-[10px] text-slate-400 truncate max-w-[130px]">
                        • {item.chapter_title}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-1 opacity-80 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={(e) => handleStartEditNote(item, e)}
                      className="p-1 text-slate-400 hover:text-indigo-300 rounded transition-colors"
                      title="Edit note"
                    >
                      <Edit2 className="w-3 h-3" />
                    </button>
                    <button
                      onClick={(e) => handleDelete(item.id, e)}
                      className="p-1 text-slate-400 hover:text-rose-400 rounded transition-colors"
                      title="Delete highlight"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                </div>

                {/* Highlight Selected Text Quote */}
                <blockquote className={`text-xs ${style.text} line-clamp-3 italic pl-2 border-l-2 ${style.border}`}>
                  "{item.selected_text}"
                </blockquote>

                {/* Note Block */}
                {isEditing ? (
                  <form onSubmit={(e) => handleSaveNote(item.id, e)} className="mt-2 space-y-1.5" onClick={(e) => e.stopPropagation()}>
                    <textarea
                      value={editNoteText}
                      onChange={(e) => setEditNoteText(e.target.value)}
                      placeholder="Add or update your personal note..."
                      rows={2}
                      className="w-full p-2 text-xs bg-slate-950 border border-indigo-500/80 rounded-lg text-slate-200 focus:outline-none"
                      autoFocus
                    />
                    <div className="flex items-center justify-end gap-1">
                      <button
                        type="button"
                        onClick={() => setEditingId(null)}
                        className="px-2 py-1 text-[11px] font-medium text-slate-400 hover:text-white"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        disabled={isSubmitting}
                        className="flex items-center gap-1 px-2.5 py-1 text-[11px] font-semibold bg-indigo-600 hover:bg-indigo-500 text-white rounded-md transition-colors"
                      >
                        <Check className="w-3 h-3" />
                        <span>Save</span>
                      </button>
                    </div>
                  </form>
                ) : (
                  item.note_text && (
                    <div className="mt-2 p-2 rounded-lg bg-slate-950/80 border border-slate-800 flex items-start gap-2">
                      <FileText className="w-3.5 h-3.5 text-indigo-400 shrink-0 mt-0.5" />
                      <p className="text-xs text-slate-200 whitespace-pre-wrap leading-relaxed">
                        {item.note_text}
                      </p>
                    </div>
                  )
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
