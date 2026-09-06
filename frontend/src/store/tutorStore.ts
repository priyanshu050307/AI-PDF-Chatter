import { create } from 'zustand';
import { tutorApi } from '@/services/tutorApi';
import {
  StudySession,
  Flashcard,
  Quiz,
  StudySummary,
  TutorDifficulty,
  TopicScope,
  FlashcardRating,
} from '@/types';

type TutorTab = 'tutor' | 'flashcards' | 'quiz' | 'history';

interface TutorState {
  activeTab: TutorTab;
  activeSession: StudySession | null;
  sessions: StudySession[];
  flashcards: Flashcard[];
  activeQuiz: Quiz | null;
  summary: StudySummary | null;
  currentHint: string | null;
  isLoading: boolean;
  isGeneratingDeck: boolean;
  isGeneratingQuiz: boolean;
  error: string | null;

  setActiveTab: (tab: TutorTab) => void;
  setActiveSession: (session: StudySession | null) => void;
  setError: (error: string | null) => void;

  fetchSessions: (documentId: string) => Promise<void>;
  createSession: (
    documentId: string,
    difficulty?: TutorDifficulty,
    topicScope?: TopicScope,
    title?: string
  ) => Promise<StudySession | null>;
  startSession: (sessionId: string) => Promise<void>;
  submitAnswer: (sessionId: string, answer: string) => Promise<void>;
  nextConcept: (sessionId: string) => Promise<void>;
  requestHint: (sessionId: string) => Promise<void>;
  fetchSummary: (sessionId: string) => Promise<void>;
  deleteSession: (sessionId: string, documentId: string) => Promise<void>;

  generateFlashcards: (documentId: string, count?: number, sessionId?: string) => Promise<void>;
  fetchFlashcards: (documentId: string, sessionId?: string) => Promise<void>;
  rateFlashcard: (cardId: string, rating: FlashcardRating) => Promise<void>;

  generateQuiz: (documentId: string, questionCount?: number, sessionId?: string) => Promise<void>;
  fetchQuiz: (quizId: string) => Promise<void>;
  submitQuiz: (quizId: string, answers: Record<string, string>) => Promise<void>;

  resetStore: () => void;
}

export const useTutorStore = create<TutorState>((set, get) => ({
  activeTab: 'tutor',
  activeSession: null,
  sessions: [],
  flashcards: [],
  activeQuiz: null,
  summary: null,
  currentHint: null,
  isLoading: false,
  isGeneratingDeck: false,
  isGeneratingQuiz: false,
  error: null,

  setActiveTab: (tab) => set({ activeTab: tab }),
  setActiveSession: (session) => set({ activeSession: session }),
  setError: (error) => set({ error }),

  fetchSessions: async (documentId) => {
    try {
      set({ isLoading: true, error: null });
      const sessions = await tutorApi.listSessions(documentId);
      set({ sessions, isLoading: false });
    } catch (err: any) {
      set({ error: err?.error?.message || 'Failed to fetch study sessions', isLoading: false });
    }
  },

  createSession: async (documentId, difficulty = 'INTERMEDIATE', topicScope, title) => {
    try {
      set({ isLoading: true, error: null });
      const session = await tutorApi.createSession({
        document_id: documentId,
        difficulty,
        topic_scope: topicScope,
        title,
      });
      set((state) => ({
        sessions: [session, ...state.sessions],
        activeSession: session,
        activeTab: 'tutor',
        isLoading: false,
      }));
      return session;
    } catch (err: any) {
      set({ error: err?.error?.message || 'Failed to create study session', isLoading: false });
      return null;
    }
  },

  startSession: async (sessionId) => {
    try {
      set({ isLoading: true, error: null });
      const updated = await tutorApi.processTurn(sessionId, { action: 'START' });
      set({ activeSession: updated, isLoading: false });
    } catch (err: any) {
      set({ error: err?.error?.message || 'Failed to start session turn', isLoading: false });
    }
  },

  submitAnswer: async (sessionId, answer) => {
    try {
      set({ isLoading: true, error: null, currentHint: null });
      const updated = await tutorApi.processTurn(sessionId, { action: 'ANSWER', user_answer: answer });
      set({ activeSession: updated, isLoading: false });
    } catch (err: any) {
      set({ error: err?.error?.message || 'Failed to submit answer', isLoading: false });
    }
  },

  nextConcept: async (sessionId) => {
    try {
      set({ isLoading: true, error: null, currentHint: null });
      const updated = await tutorApi.processTurn(sessionId, { action: 'NEXT_CONCEPT' });
      set({ activeSession: updated, isLoading: false });
    } catch (err: any) {
      set({ error: err?.error?.message || 'Failed to advance to next concept', isLoading: false });
    }
  },

  requestHint: async (sessionId) => {
    try {
      set({ isLoading: true, error: null });
      const res = await tutorApi.getHint(sessionId);
      set({ currentHint: res.hint_text, isLoading: false });
    } catch (err: any) {
      set({ error: err?.error?.message || 'Failed to fetch hint', isLoading: false });
    }
  },

  fetchSummary: async (sessionId) => {
    try {
      set({ isLoading: true, error: null });
      const summary = await tutorApi.getSummary(sessionId);
      set({ summary, isLoading: false });
    } catch (err: any) {
      set({ error: err?.error?.message || 'Failed to generate study summary', isLoading: false });
    }
  },

  deleteSession: async (sessionId, documentId) => {
    try {
      set({ isLoading: true, error: null });
      await tutorApi.deleteSession(sessionId);
      set((state) => ({
        sessions: state.sessions.filter((s) => s.id !== sessionId),
        activeSession: state.activeSession?.id === sessionId ? null : state.activeSession,
        isLoading: false,
      }));
    } catch (err: any) {
      set({ error: err?.error?.message || 'Failed to delete session', isLoading: false });
    }
  },

  generateFlashcards: async (documentId, count = 5, sessionId) => {
    try {
      set({ isGeneratingDeck: true, error: null });
      const cards = await tutorApi.generateFlashcards({ document_id: documentId, count, session_id: sessionId });
      set({ flashcards: cards, activeTab: 'flashcards', isGeneratingDeck: false });
    } catch (err: any) {
      set({ error: err?.error?.message || 'Failed to generate flashcards', isGeneratingDeck: false });
    }
  },

  fetchFlashcards: async (documentId, sessionId) => {
    try {
      set({ isLoading: true, error: null });
      const cards = await tutorApi.listFlashcards(documentId, sessionId);
      set({ flashcards: cards, isLoading: false });
    } catch (err: any) {
      set({ error: err?.error?.message || 'Failed to fetch flashcards', isLoading: false });
    }
  },

  rateFlashcard: async (cardId, rating) => {
    try {
      const updated = await tutorApi.rateFlashcard(cardId, rating);
      set((state) => ({
        flashcards: state.flashcards.map((c) => (c.id === cardId ? updated : c)),
      }));
    } catch (err: any) {
      set({ error: err?.error?.message || 'Failed to rate flashcard' });
    }
  },

  generateQuiz: async (documentId, questionCount = 5, sessionId) => {
    try {
      set({ isGeneratingQuiz: true, error: null });
      const quiz = await tutorApi.generateQuiz({ document_id: documentId, question_count: questionCount, session_id: sessionId });
      set({ activeQuiz: quiz, activeTab: 'quiz', isGeneratingQuiz: false });
    } catch (err: any) {
      set({ error: err?.error?.message || 'Failed to generate quiz', isGeneratingQuiz: false });
    }
  },

  fetchQuiz: async (quizId) => {
    try {
      set({ isLoading: true, error: null });
      const quiz = await tutorApi.getQuiz(quizId);
      set({ activeQuiz: quiz, isLoading: false });
    } catch (err: any) {
      set({ error: err?.error?.message || 'Failed to fetch quiz', isLoading: false });
    }
  },

  submitQuiz: async (quizId, answers) => {
    try {
      set({ isLoading: true, error: null });
      const evaluated = await tutorApi.submitQuiz(quizId, { answers });
      set({ activeQuiz: evaluated, isLoading: false });
    } catch (err: any) {
      set({ error: err?.error?.message || 'Failed to submit quiz', isLoading: false });
    }
  },

  resetStore: () =>
    set({
      activeTab: 'tutor',
      activeSession: null,
      sessions: [],
      flashcards: [],
      activeQuiz: null,
      summary: null,
      currentHint: null,
      isLoading: false,
      isGeneratingDeck: false,
      isGeneratingQuiz: false,
      error: null,
    }),
}));
