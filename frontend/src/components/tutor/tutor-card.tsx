'use client';

import React, { useState } from 'react';
import { useTutorStore } from '@/store/tutorStore';
import { useReaderStore } from '@/store/readerStore';
import {
  GraduationCap,
  Sparkles,
  Lightbulb,
  CheckCircle2,
  ChevronRight,
  HelpCircle,
  BarChart3,
  Award,
  BookOpen,
  Send,
  RotateCcw,
} from 'lucide-react';

interface TutorCardProps {
  documentId: string;
}

export const TutorCard: React.FC<TutorCardProps> = ({ documentId }) => {
  const {
    activeSession,
    startSession,
    submitAnswer,
    nextConcept,
    requestHint,
    currentHint,
    fetchSummary,
    summary,
    isLoading,
    createSession,
  } = useTutorStore();

  const { setCurrentPage } = useReaderStore();
  const [answerInput, setAnswerInput] = useState('');
  const [difficultySelect, setDifficultySelect] = useState<'BEGINNER' | 'INTERMEDIATE' | 'ADVANCED'>('INTERMEDIATE');

  if (!activeSession) {
    return (
      <div className="flex flex-col items-center justify-center p-8 bg-slate-900/60 rounded-xl border border-slate-800 backdrop-blur-md text-center max-w-lg mx-auto my-6 shadow-2xl">
        <div className="w-16 h-16 bg-gradient-to-tr from-indigo-500 to-purple-500 rounded-2xl flex items-center justify-center mb-4 shadow-lg shadow-indigo-500/20">
          <GraduationCap className="w-8 h-8 text-white" />
        </div>
        <h3 className="text-xl font-bold text-slate-100 mb-2">AI Tutor & Guided Study</h3>
        <p className="text-slate-400 text-sm mb-6 leading-relaxed">
          Start an interactive, grounded AI study session. The AI tutor evaluates your knowledge, breaks down concepts step-by-step, provides hints, and adapts difficulty based on your comprehension.
        </p>

        <div className="w-full bg-slate-800/80 p-4 rounded-lg border border-slate-700/60 mb-6 text-left">
          <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
            Target Starting Difficulty
          </label>
          <div className="grid grid-cols-3 gap-2">
            {(['BEGINNER', 'INTERMEDIATE', 'ADVANCED'] as const).map((diff) => (
              <button
                key={diff}
                onClick={() => setDifficultySelect(diff)}
                className={`py-2 px-3 text-xs font-medium rounded-md transition-all ${
                  difficultySelect === diff
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/30'
                    : 'bg-slate-700/50 text-slate-300 hover:bg-slate-700'
                }`}
              >
                {diff}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={() => createSession(documentId, difficultySelect)}
          disabled={isLoading}
          className="w-full py-3 px-6 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 text-white font-medium text-sm rounded-lg shadow-lg hover:brightness-110 active:scale-[0.99] transition-all flex items-center justify-center gap-2"
        >
          <Sparkles className="w-4 h-4" />
          {isLoading ? 'Initializing Session...' : 'Start Guided Study Session'}
        </button>
      </div>
    );
  }

  const history = activeSession.history || [];
  const latestTurn = history.length > 0 ? history[history.length - 1] : null;

  const handleStart = async () => {
    await startSession(activeSession.id);
  };

  const handleSubmitAnswer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!answerInput.trim() || isLoading) return;
    const text = answerInput;
    setAnswerInput('');
    await submitAnswer(activeSession.id, text);
  };

  const getDifficultyBadge = (diff: string) => {
    switch (diff) {
      case 'BEGINNER':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
      case 'ADVANCED':
        return 'bg-purple-500/10 text-purple-400 border-purple-500/30';
      default:
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-950 text-slate-100 rounded-xl border border-slate-800 shadow-xl overflow-hidden">
      {/* Session Top Bar */}
      <div className="px-5 py-4 bg-slate-900/90 border-b border-slate-800 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-indigo-500/10 border border-indigo-500/30 rounded-lg flex items-center justify-center text-indigo-400">
            <GraduationCap className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
              {activeSession.title}
              <span
                className={`text-[10px] px-2 py-0.5 rounded-full border font-mono uppercase tracking-wider ${getDifficultyBadge(
                  activeSession.difficulty
                )}`}
              >
                {activeSession.difficulty}
              </span>
            </h4>
            <div className="flex items-center gap-2 text-xs text-slate-400 mt-0.5">
              <span>Concept: <strong className="text-indigo-300">{activeSession.current_concept}</strong></span>
              <span>•</span>
              <span>Status: <span className="font-mono text-xs text-slate-300">{activeSession.status}</span></span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => fetchSummary(activeSession.id)}
            className="p-2 text-xs text-slate-300 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg flex items-center gap-1.5 transition-colors"
            title="Generate Study Summary"
          >
            <BarChart3 className="w-3.5 h-3.5 text-indigo-400" />
            <span>Summary</span>
          </button>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-slate-900 h-1.5 overflow-hidden">
        <div
          className="bg-gradient-to-r from-indigo-500 to-emerald-400 h-full transition-all duration-500"
          style={{ width: `${activeSession.progress_pct}%` }}
        />
      </div>

      {/* Main Conversation / Turn Area */}
      <div className="flex-1 overflow-y-auto p-5 space-y-4">
        {/* Render Conversation Turn History */}
        {history.map((turn: any, idx: number) => (
          <div key={turn.turn_id || idx} className="space-y-3">
            {turn.tutor_message && (
              <div className="flex items-start gap-3 bg-slate-900/70 p-4 rounded-xl border border-slate-800">
                <div className="w-7 h-7 bg-indigo-600/20 text-indigo-400 rounded-lg flex items-center justify-center shrink-0 mt-0.5">
                  <Sparkles className="w-4 h-4" />
                </div>
                <div className="text-sm text-slate-200 leading-relaxed whitespace-pre-line flex-1">
                  {turn.tutor_message}
                </div>
              </div>
            )}

            {turn.user_answer && (
              <div className="flex justify-end">
                <div className="max-w-[85%] bg-indigo-600/20 border border-indigo-500/30 text-indigo-100 p-3 px-4 rounded-xl text-sm leading-relaxed">
                  {turn.user_answer}
                </div>
              </div>
            )}

            {turn.feedback && (
              <div className="p-4 bg-slate-900/90 border border-slate-800 rounded-xl space-y-2">
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span className="flex items-center gap-1.5 font-medium text-emerald-400">
                    <CheckCircle2 className="w-4 h-4" /> Tutor Assessment
                  </span>
                  {turn.score !== undefined && (
                    <span className="font-mono text-slate-300">Score: {(turn.score * 100).toFixed(0)}%</span>
                  )}
                </div>
                <div className="text-sm text-slate-200 leading-relaxed whitespace-pre-line">
                  {turn.feedback}
                </div>
              </div>
            )}
          </div>
        ))}

        {/* Status: CREATED -> Offer START Button */}
        {activeSession.status === 'CREATED' && (
          <div className="text-center py-6">
            <button
              onClick={handleStart}
              disabled={isLoading}
              className="py-2.5 px-5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium shadow-md transition-all flex items-center justify-center gap-2 mx-auto"
            >
              <Sparkles className="w-4 h-4" />
              Begin Diagnostic Check
            </button>
          </div>
        )}

        {/* Current Hint Display */}
        {currentHint && (
          <div className="p-3 bg-amber-500/10 border border-amber-500/30 text-amber-200 rounded-lg text-xs leading-relaxed flex items-start gap-2">
            <Lightbulb className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <strong className="block text-amber-300 font-semibold mb-0.5">Progressive Hint:</strong>
              {currentHint}
            </div>
          </div>
        )}

        {/* Study Summary Card (Modal View) */}
        {summary && (
          <div className="p-5 bg-slate-900 border border-indigo-500/40 rounded-xl space-y-3 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h4 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <Award className="w-5 h-5 text-indigo-400" />
                Session Mastery Summary
              </h4>
              <span className="text-xs font-mono bg-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded border border-indigo-500/30">
                Score: {(summary.overall_performance_score * 100).toFixed(0)}%
              </span>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed whitespace-pre-line">
              {summary.summary_text}
            </p>

            <div className="grid grid-cols-2 gap-3 text-xs pt-2">
              <div className="bg-emerald-950/40 border border-emerald-800/40 p-3 rounded-lg">
                <span className="font-semibold text-emerald-400 block mb-1">Concepts Mastered:</span>
                <ul className="list-disc list-inside text-slate-300 space-y-0.5">
                  {summary.concepts_mastered.map((c, i) => (
                    <li key={i}>{c}</li>
                  ))}
                  {summary.concepts_mastered.length === 0 && <li className="text-slate-500 italic">None yet</li>}
                </ul>
              </div>

              <div className="bg-amber-950/40 border border-amber-800/40 p-3 rounded-lg">
                <span className="font-semibold text-amber-400 block mb-1">Needs Review:</span>
                <ul className="list-disc list-inside text-slate-300 space-y-0.5">
                  {summary.concepts_needing_review.map((c, i) => (
                    <li key={i}>{c}</li>
                  ))}
                  {summary.concepts_needing_review.length === 0 && <li className="text-slate-500 italic">All concepts clear!</li>}
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Control Actions & Input Footer */}
      <div className="p-4 bg-slate-900 border-t border-slate-800 space-y-3">
        {/* Action bar for Hints & Next Concept */}
        <div className="flex items-center justify-between gap-2">
          {activeSession.status !== 'COMPLETED' && (
            <button
              onClick={() => requestHint(activeSession.id)}
              disabled={isLoading}
              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-amber-400 border border-slate-700 text-xs rounded-lg flex items-center gap-1.5 transition-colors"
            >
              <Lightbulb className="w-3.5 h-3.5" />
              Request Hint
            </button>
          )}

          {activeSession.status === 'FEEDBACK' && (
            <button
              onClick={() => nextConcept(activeSession.id)}
              disabled={isLoading}
              className="ml-auto px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg flex items-center gap-1.5 transition-all shadow-md"
            >
              <span>Next Concept</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Answer Text Form */}
        {activeSession.status !== 'COMPLETED' && activeSession.status !== 'CREATED' && (
          <form onSubmit={handleSubmitAnswer} className="flex gap-2">
            <input
              type="text"
              value={answerInput}
              onChange={(e) => setAnswerInput(e.target.value)}
              placeholder="Type your answer or explanation here..."
              disabled={isLoading}
              className="flex-1 px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
            />
            <button
              type="submit"
              disabled={isLoading || !answerInput.trim()}
              className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors flex items-center justify-center shrink-0"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        )}
      </div>
    </div>
  );
};
