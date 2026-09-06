import { apiClient } from '@/lib/api-client';
import {
  CreateStudySessionRequest,
  StudySession,
  TutorTurnRequest,
  TutorHintResponse,
  StudySummary,
  GenerateFlashcardsRequest,
  Flashcard,
  RateFlashcardRequest,
  GenerateQuizRequest,
  Quiz,
  SubmitQuizRequest,
} from '@/types';

export const tutorApi = {
  createSession: async (payload: CreateStudySessionRequest): Promise<StudySession> => {
    return apiClient.post<StudySession>('/tutor/sessions', payload);
  },

  listSessions: async (documentId: string): Promise<StudySession[]> => {
    return apiClient.get<StudySession[]>(`/tutor/sessions?document_id=${documentId}`);
  },

  getSession: async (sessionId: string): Promise<StudySession> => {
    return apiClient.get<StudySession>(`/tutor/sessions/${sessionId}`);
  },

  deleteSession: async (sessionId: string): Promise<void> => {
    return apiClient.delete<void>(`/tutor/sessions/${sessionId}`);
  },

  processTurn: async (sessionId: string, payload: TutorTurnRequest): Promise<StudySession> => {
    return apiClient.post<StudySession>(`/tutor/sessions/${sessionId}/turn`, payload);
  },

  getHint: async (sessionId: string): Promise<TutorHintResponse> => {
    return apiClient.get<TutorHintResponse>(`/tutor/sessions/${sessionId}/hint`);
  },

  getSummary: async (sessionId: string): Promise<StudySummary> => {
    return apiClient.get<StudySummary>(`/tutor/sessions/${sessionId}/summary`);
  },

  generateFlashcards: async (payload: GenerateFlashcardsRequest): Promise<Flashcard[]> => {
    return apiClient.post<Flashcard[]>('/tutor/flashcards/generate', payload);
  },

  listFlashcards: async (documentId: string, sessionId?: string): Promise<Flashcard[]> => {
    const query = new URLSearchParams({ document_id: documentId });
    if (sessionId) query.append('session_id', sessionId);
    return apiClient.get<Flashcard[]>(`/tutor/flashcards?${query.toString()}`);
  },

  rateFlashcard: async (cardId: string, rating: RateFlashcardRequest['rating']): Promise<Flashcard> => {
    return apiClient.post<Flashcard>(`/tutor/flashcards/${cardId}/rate`, { rating });
  },

  generateQuiz: async (payload: GenerateQuizRequest): Promise<Quiz> => {
    return apiClient.post<Quiz>('/tutor/quizzes/generate', payload);
  },

  getQuiz: async (quizId: string): Promise<Quiz> => {
    return apiClient.get<Quiz>(`/tutor/quizzes/${quizId}`);
  },

  submitQuiz: async (quizId: string, payload: SubmitQuizRequest): Promise<Quiz> => {
    return apiClient.post<Quiz>(`/tutor/quizzes/${quizId}/submit`, payload);
  },
};
