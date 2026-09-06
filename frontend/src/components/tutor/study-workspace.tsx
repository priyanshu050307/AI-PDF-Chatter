'use client';

import React, { useEffect } from 'react';
import { useTutorStore } from '@/store/tutorStore';
import { TutorCard } from './tutor-card';
import { FlashcardDeck } from './flashcard-deck';
import { QuizRunner } from './quiz-runner';
import { StudyHistoryList } from './study-history-list';
import {
  GraduationCap,
  Layers,
  HelpCircle,
  History,
  AlertCircle,
  Sparkles,
} from 'lucide-react';

interface StudyWorkspaceProps {
  documentId: string;
}

export const StudyWorkspace: React.FC<StudyWorkspaceProps> = ({ documentId }) => {
  const { activeTab, setActiveTab, fetchSessions, fetchFlashcards, error, setError } = useTutorStore();

  useEffect(() => {
    if (documentId) {
      fetchSessions(documentId);
      fetchFlashcards(documentId);
    }
  }, [documentId, fetchSessions, fetchFlashcards]);

  return (
    <div className="flex flex-col h-full bg-slate-950 text-slate-100 p-4 space-y-4">
      {/* Top Header Tabs */}
      <div className="flex items-center justify-between bg-slate-900/80 p-1.5 rounded-xl border border-slate-800 backdrop-blur-md">
        <div className="flex items-center gap-1">
          <button
            onClick={() => setActiveTab('tutor')}
            className={`px-3.5 py-2 rounded-lg text-xs font-medium flex items-center gap-2 transition-all ${
              activeTab === 'tutor'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/20'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <GraduationCap className="w-4 h-4" />
            <span>AI Tutor</span>
          </button>

          <button
            onClick={() => setActiveTab('flashcards')}
            className={`px-3.5 py-2 rounded-lg text-xs font-medium flex items-center gap-2 transition-all ${
              activeTab === 'flashcards'
                ? 'bg-cyan-600 text-white shadow-md shadow-cyan-500/20'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <Layers className="w-4 h-4" />
            <span>Flashcards</span>
          </button>

          <button
            onClick={() => setActiveTab('quiz')}
            className={`px-3.5 py-2 rounded-lg text-xs font-medium flex items-center gap-2 transition-all ${
              activeTab === 'quiz'
                ? 'bg-emerald-600 text-white shadow-md shadow-emerald-500/20'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <HelpCircle className="w-4 h-4" />
            <span>Quizzes</span>
          </button>

          <button
            onClick={() => setActiveTab('history')}
            className={`px-3.5 py-2 rounded-lg text-xs font-medium flex items-center gap-2 transition-all ${
              activeTab === 'history'
                ? 'bg-purple-600 text-white shadow-md shadow-purple-500/20'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <History className="w-4 h-4" />
            <span>History</span>
          </button>
        </div>

        <div className="hidden sm:flex items-center gap-1.5 px-3 py-1 bg-slate-950/60 border border-slate-800 rounded-lg text-[11px] text-slate-400">
          <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
          <span>Phase 7 • Study & Tutor Mode</span>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/30 text-rose-300 rounded-lg text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={() => setError(null)}
            className="text-xs text-rose-400 hover:underline font-mono"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Main Tab Active Body */}
      <div className="flex-1 min-h-0">
        {activeTab === 'tutor' && <TutorCard documentId={documentId} />}
        {activeTab === 'flashcards' && <FlashcardDeck documentId={documentId} />}
        {activeTab === 'quiz' && <QuizRunner documentId={documentId} />}
        {activeTab === 'history' && <StudyHistoryList documentId={documentId} />}
      </div>
    </div>
  );
};
