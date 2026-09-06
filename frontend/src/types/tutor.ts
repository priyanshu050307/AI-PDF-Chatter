export type TutorDifficulty = 'BEGINNER' | 'INTERMEDIATE' | 'ADVANCED';

export type TutorStatus =
  | 'CREATED'
  | 'ASSESSING'
  | 'TEACHING'
  | 'QUESTION'
  | 'EVALUATING'
  | 'FEEDBACK'
  | 'NEXT_CONCEPT'
  | 'COMPLETED';

export type FlashcardRating = 'AGAIN' | 'HARD' | 'GOOD' | 'EASY';

export interface TopicScope {
  type: 'ENTIRE_DOCUMENT' | 'CHAPTER' | 'SECTION' | 'SELECTION' | 'HIGHLIGHTS';
  target?: string;
  page_number?: number;
  selected_text?: string;
}

export interface CreateStudySessionRequest {
  document_id: string;
  title?: string;
  topic_scope?: TopicScope;
  difficulty?: TutorDifficulty;
  learning_goal?: string;
}

export interface StudySession {
  id: string;
  user_id: string;
  document_id: string;
  title: string;
  topic_scope: TopicScope;
  difficulty: TutorDifficulty;
  learning_goal: string;
  status: TutorStatus;
  current_concept?: string;
  mastery_state: Record<string, 'NOT_STARTED' | 'NEEDS_REVIEW' | 'MOSTLY_UNDERSTOOD' | 'MASTERED'>;
  progress_pct: number;
  history: Array<{
    turn_id: string;
    state: TutorStatus;
    concept?: string;
    user_answer?: string;
    diagnostic_answer?: string;
    tutor_message?: string;
    question?: string;
    score?: number;
    feedback?: string;
    hints?: string[];
    hints_used?: number;
    created_at: string;
  }>;
  created_at: string;
  updated_at: string;
}

export interface TutorTurnRequest {
  action?: 'START' | 'ANSWER' | 'NEXT_CONCEPT' | 'RETRY';
  user_answer?: string;
}

export interface TutorHintResponse {
  session_id: string;
  hint_level: number;
  hint_text: string;
}

export interface StudySummary {
  session_id: string;
  document_id: string;
  summary_text: string;
  concepts_mastered: string[];
  concepts_needing_review: string[];
  overall_performance_score: number;
  created_at: string;
}

export interface GenerateFlashcardsRequest {
  document_id: string;
  session_id?: string;
  topic_scope?: TopicScope;
  count?: number;
}

export interface Flashcard {
  id: string;
  user_id: string;
  document_id: string;
  session_id?: string;
  front: string;
  back: string;
  source_citations: Array<{
    chunk_id?: string;
    page_number?: number;
    snippet?: string;
  }>;
  difficulty: TutorDifficulty;
  review_rating?: FlashcardRating;
  created_at: string;
}

export interface RateFlashcardRequest {
  rating: FlashcardRating;
}

export interface GenerateQuizRequest {
  document_id: string;
  session_id?: string;
  topic_scope?: TopicScope;
  question_count?: number;
}

export interface QuizQuestion {
  id: string;
  type: 'MCQ' | 'TRUE_FALSE' | 'SHORT_ANSWER';
  question: string;
  options?: string[];
  correct_answer: string;
  explanation: string;
  citation_page?: number;
}

export interface Quiz {
  id: string;
  user_id: string;
  document_id: string;
  session_id?: string;
  title: string;
  topic_scope: TopicScope;
  questions: QuizQuestion[];
  user_answers: Record<string, string>;
  evaluation_results: Record<
    string,
    {
      user_answer: string;
      correct_answer: string;
      is_correct: boolean;
      score: number;
      explanation: string;
    }
  >;
  completed_at?: string;
  created_at: string;
}

export interface SubmitQuizRequest {
  answers: Record<string, string>;
}
