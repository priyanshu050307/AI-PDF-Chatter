'use client';

import React, { useState } from 'react';
import { HelpCircle, Sparkles, Lightbulb, MessageSquare, Highlighter, FileText, Check, X } from 'lucide-react';
import { useReaderStore } from '@/store/readerStore';
import { ChatIntent, HighlightColor } from '@/types';
import { apiService } from '@/services/api';

interface SelectionToolbarProps {
  position: { x: number; y: number } | null;
  onActionTriggered?: () => void;
}

const PALETTE: { color: HighlightColor; label: string; bg: string; dot: string }[] = [
  { color: 'yellow', label: 'Yellow', bg: 'hover:bg-yellow-500/20', dot: 'bg-yellow-400' },
  { color: 'green', label: 'Green', bg: 'hover:bg-emerald-500/20', dot: 'bg-emerald-400' },
  { color: 'blue', label: 'Blue', bg: 'hover:bg-sky-500/20', dot: 'bg-sky-400' },
  { color: 'pink', label: 'Pink', bg: 'hover:bg-pink-500/20', dot: 'bg-pink-400' },
  { color: 'purple', label: 'Purple', bg: 'hover:bg-purple-500/20', dot: 'bg-purple-400' },
];

export const SelectionToolbar: React.FC<SelectionToolbarProps> = ({
  position,
  onActionTriggered
}) => {
  const {
    documentId,
    activeSelection,
    currentPage,
    chapterTitle,
    sectionTitle,
    setActiveIntent,
    setPendingPrompt,
    addHighlight,
    clearSelection
  } = useReaderStore();

  const [showColorPicker, setShowColorPicker] = useState(false);
  const [showNoteEditor, setShowNoteEditor] = useState(false);
  const [noteText, setNoteText] = useState('');
  const [selectedColor, setSelectedColor] = useState<HighlightColor>('yellow');
  const [isSaving, setIsSaving] = useState(false);

  if (!activeSelection || !position || !documentId) return null;

  const handleAiAction = (intent: ChatIntent, defaultPrompt: string) => {
    setActiveIntent(intent);
    setPendingPrompt(defaultPrompt);
    if (onActionTriggered) {
      onActionTriggered();
    }
  };

  const handleCreateHighlight = async (color: HighlightColor, note?: string) => {
    setIsSaving(true);
    try {
      const payload = {
        page_number: activeSelection.page_number || currentPage,
        selected_text: activeSelection.selected_text,
        start_offset: activeSelection.selection_start || 0,
        end_offset: activeSelection.selection_end || 0,
        color: color,
        note_text: note && note.trim().length > 0 ? note.trim() : undefined,
        bounding_box: activeSelection.bounding_box,
        chapter_title: chapterTitle || undefined,
        section_title: sectionTitle || undefined,
      };

      const saved = await apiService.createHighlight(documentId, payload);
      addHighlight(saved);
      clearSelection();
      setShowColorPicker(false);
      setShowNoteEditor(false);
      setNoteText('');
    } catch (err) {
      console.error('Failed to create highlight annotation:', err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveNoteSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleCreateHighlight(selectedColor, noteText);
  };

  return (
    <div
      style={{
        position: 'absolute',
        left: `${position.x}px`,
        top: `${Math.max(10, position.y - 52)}px`,
        transform: 'translateX(-50%)',
        zIndex: 50
      }}
      className="flex flex-col items-center animate-in fade-in zoom-in-95 duration-150 select-none"
    >
      {/* Primary Floating Bar */}
      <div className="flex items-center gap-1 p-1.5 bg-slate-900/95 border border-slate-700/80 backdrop-blur-md rounded-xl shadow-2xl">
        <button
          onClick={() => handleAiAction('EXPLAIN', 'Explain this selected passage in detail.')}
          className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-slate-200 hover:text-white bg-slate-800 hover:bg-indigo-600/80 rounded-lg transition-colors"
          title="Explain selected text"
        >
          <HelpCircle className="w-3.5 h-3.5 text-indigo-400" />
          <span>Explain</span>
        </button>

        <button
          onClick={() => handleAiAction('SIMPLIFY', 'Simplify this selected passage into beginner-friendly terms.')}
          className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-slate-200 hover:text-white bg-slate-800 hover:bg-emerald-600/80 rounded-lg transition-colors"
          title="Simplify in easy terms"
        >
          <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
          <span>Simplify</span>
        </button>

        <button
          onClick={() => handleAiAction('EXAMPLE', 'Give me a real-world example illustrating this selected text.')}
          className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-slate-200 hover:text-white bg-slate-800 hover:bg-amber-600/80 rounded-lg transition-colors"
          title="Provide practical example"
        >
          <Lightbulb className="w-3.5 h-3.5 text-amber-400" />
          <span>Example</span>
        </button>

        <div className="w-[1px] h-4 bg-slate-700 mx-0.5" />

        {/* Phase 6 Highlight Button */}
        <button
          onClick={() => {
            setShowColorPicker(!showColorPicker);
            setShowNoteEditor(false);
          }}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-amber-300 hover:text-white rounded-lg transition-colors ${
            showColorPicker ? 'bg-amber-600/80' : 'bg-slate-800 hover:bg-amber-600/60'
          }`}
          title="Highlight text"
        >
          <Highlighter className="w-3.5 h-3.5 text-amber-400" />
          <span>Highlight</span>
        </button>

        {/* Phase 6 Add Note Button */}
        <button
          onClick={() => {
            setShowNoteEditor(!showNoteEditor);
            setShowColorPicker(false);
          }}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-sky-300 hover:text-white rounded-lg transition-colors ${
            showNoteEditor ? 'bg-sky-600/80' : 'bg-slate-800 hover:bg-sky-600/60'
          }`}
          title="Add personal note"
        >
          <FileText className="w-3.5 h-3.5 text-sky-400" />
          <span>Add Note</span>
        </button>

        <div className="w-[1px] h-4 bg-slate-700 mx-0.5" />

        <button
          onClick={() => handleAiAction('QUESTION', '')}
          className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-indigo-300 hover:text-white bg-indigo-950/60 hover:bg-indigo-600 rounded-lg transition-colors"
          title="Ask question about selection"
        >
          <MessageSquare className="w-3.5 h-3.5 text-indigo-400" />
          <span>Ask AI</span>
        </button>
      </div>

      {/* Color Picker Palette Popover */}
      {showColorPicker && (
        <div className="mt-1.5 flex items-center gap-1 p-1 bg-slate-900/95 border border-slate-700 rounded-xl shadow-xl animate-in fade-in slide-in-from-top-1 duration-150">
          {PALETTE.map((p) => (
            <button
              key={p.color}
              disabled={isSaving}
              onClick={() => handleCreateHighlight(p.color)}
              className={`flex items-center gap-1 px-2 py-1 rounded-lg text-xs text-slate-200 transition-colors ${p.bg}`}
              title={`Highlight in ${p.label}`}
            >
              <span className={`w-3 h-3 rounded-full ${p.dot}`} />
              <span className="capitalize">{p.color}</span>
            </button>
          ))}
        </div>
      )}

      {/* Inline Note Editor Popover */}
      {showNoteEditor && (
        <form
          onSubmit={handleSaveNoteSubmit}
          className="mt-1.5 w-72 p-2.5 bg-slate-900/95 border border-slate-700 rounded-xl shadow-2xl space-y-2 animate-in fade-in slide-in-from-top-1 duration-150"
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider">Highlight & Add Note</span>
            <div className="flex items-center gap-1">
              {PALETTE.map((p) => (
                <button
                  key={p.color}
                  type="button"
                  onClick={() => setSelectedColor(p.color)}
                  className={`w-3.5 h-3.5 rounded-full ${p.dot} transition-transform ${
                    selectedColor === p.color ? 'ring-2 ring-white ring-offset-1 ring-offset-slate-900 scale-110' : 'opacity-60'
                  }`}
                />
              ))}
            </div>
          </div>
          <textarea
            value={noteText}
            onChange={(e) => setNoteText(e.target.value)}
            placeholder="Type your note or key takeaways..."
            rows={2}
            className="w-full p-2 text-xs bg-slate-950 border border-slate-800 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            autoFocus
          />
          <div className="flex items-center justify-end gap-1.5">
            <button
              type="button"
              onClick={() => setShowNoteEditor(false)}
              className="px-2 py-1 text-xs text-slate-400 hover:text-white"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSaving}
              className="flex items-center gap-1 px-3 py-1 text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors"
            >
              <Check className="w-3.5 h-3.5" />
              <span>Save Note</span>
            </button>
          </div>
        </form>
      )}
    </div>
  );
};
