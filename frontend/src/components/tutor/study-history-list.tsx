'use client';

import React, { useEffect } from 'react';
import { useTutorStore } from '@/store/tutorStore';
import { StudySession } from '@/types';
import {
  History,
  BookOpen,
  GraduationCap,
  Play,
  Trash2,
  Plus,
  Clock,
  Sparkles,
} from 'lucide-react';

interface StudyHistoryListProps {
  documentId: string;
}

export const StudyHistoryList: React.FC<StudyHistoryListProps> = ({ documentId }) => {
  const { sessions, fetchSessions, setActiveSession, deleteSession, createSession, isLoading } =
    useTutorStore();

  useEffect(() => {
    fetchSessions(documentId);
  }, [documentId, fetchSessions]);

  const handleResume = (session: StudySession) => {
    setActiveSession(session);
  };

  const handleDelete = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    await deleteSession(sessionId, documentId);
  };

  const handleCreateNew = async () => {
    await createSession(documentId);
  };

  return (
    <div className="flex flex-col h-full bg-slate-950 text-slate-100 rounded-xl border border-slate-800 shadow-xl overflow-hidden p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-purple-500/10 border border-purple-500/30 rounded-lg flex items-center justify-center text-purple-400">
            <History className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-slate-100">Study Sessions History</h4>
            <p className="text-xs text-slate-400">{sessions.length} Saved Tutor Sessions</p>
          </div>
        </div>

        <button
          onClick={handleCreateNew}
          disabled={isLoading}
          className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg flex items-center gap-1.5 transition-all shadow-md"
        >
          <Plus className="w-4 h-4" />
          <span>New Session</span>
        </button>
      </div>

      {/* List Area */}
      <div className="flex-1 overflow-y-auto space-y-3">
        {sessions.length === 0 ? (
          <div className="text-center py-12 text-slate-500 text-xs">
            No study sessions found for this document. Click "New Session" to start.
          </div>
        ) : (
          sessions.map((session) => (
            <div
              key={session.id}
              onClick={() => handleResume(session)}
              className="p-4 bg-slate-900/80 hover:bg-slate-900 border border-slate-800 hover:border-indigo-500/40 rounded-xl transition-all cursor-pointer flex items-center justify-between gap-4 group"
            >
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 bg-slate-800 border border-slate-700 rounded-lg flex items-center justify-center text-indigo-400 group-hover:bg-indigo-600 group-hover:text-white transition-colors">
                  <GraduationCap className="w-4 h-4" />
                </div>
                <div>
                  <h5 className="text-sm font-semibold text-slate-200 group-hover:text-white transition-colors">
                    {session.title}
                  </h5>
                  <div className="flex items-center gap-2 text-xs text-slate-400 mt-0.5">
                    <span className="font-mono text-indigo-300">{session.difficulty}</span>
                    <span>•</span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {new Date(session.updated_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-3">
                {/* Progress pill */}
                <div className="text-right">
                  <span className="text-xs font-mono font-semibold text-slate-300">
                    {session.progress_pct}%
                  </span>
                  <div className="w-16 bg-slate-800 h-1 rounded-full overflow-hidden mt-1">
                    <div
                      className="bg-indigo-500 h-full"
                      style={{ width: `${session.progress_pct}%` }}
                    />
                  </div>
                </div>

                <button
                  onClick={(e) => handleDelete(session.id, e)}
                  className="p-2 text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors"
                  title="Delete Session"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
