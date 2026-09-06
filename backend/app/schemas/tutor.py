import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from app.models.tutor import TutorStatus, TutorDifficulty, FlashcardRating


class TopicScope(BaseModel):
    type: Literal["ENTIRE_DOCUMENT", "CHAPTER", "SECTION", "SELECTION", "HIGHLIGHTS"] = "ENTIRE_DOCUMENT"
    target: Optional[str] = None
    page_number: Optional[int] = None
    selected_text: Optional[str] = None


class CreateStudySessionRequest(BaseModel):
    document_id: uuid.UUID
    title: Optional[str] = None
    topic_scope: Optional[TopicScope] = None
    difficulty: TutorDifficulty = TutorDifficulty.INTERMEDIATE
    learning_goal: str = "UNDERSTAND"


class StudySessionResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    document_id: uuid.UUID
    title: str
    topic_scope: Dict[str, Any]
    difficulty: TutorDifficulty
    learning_goal: str
    status: TutorStatus
    current_concept: Optional[str] = None
    mastery_state: Dict[str, Any] = Field(default_factory=dict)
    progress_pct: float = 0.0
    history: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TutorTurnRequest(BaseModel):
    action: Optional[Literal["START", "ANSWER", "NEXT_CONCEPT", "RETRY"]] = "ANSWER"
    user_answer: Optional[str] = None


class TutorHintResponse(BaseModel):
    session_id: uuid.UUID
    hint_level: int  # 1, 2, 3
    hint_text: str


class StudySummaryResponse(BaseModel):
    session_id: uuid.UUID
    document_id: uuid.UUID
    summary_text: str
    concepts_mastered: List[str]
    concepts_needing_review: List[str]
    overall_performance_score: float
    created_at: datetime


class GenerateFlashcardsRequest(BaseModel):
    document_id: uuid.UUID
    session_id: Optional[uuid.UUID] = None
    topic_scope: Optional[TopicScope] = None
    count: int = Field(default=5, ge=1, le=20)


class FlashcardResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    document_id: uuid.UUID
    session_id: Optional[uuid.UUID] = None
    front: str
    back: str
    source_citations: List[Dict[str, Any]] = Field(default_factory=list)
    difficulty: TutorDifficulty
    review_rating: Optional[FlashcardRating] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class RateFlashcardRequest(BaseModel):
    rating: FlashcardRating


class GenerateQuizRequest(BaseModel):
    document_id: uuid.UUID
    session_id: Optional[uuid.UUID] = None
    topic_scope: Optional[TopicScope] = None
    question_count: int = Field(default=5, ge=1, le=10)


class SubmitQuizRequest(BaseModel):
    answers: Dict[str, str]  # question_id -> user choice or text answer


class QuizResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    document_id: uuid.UUID
    session_id: Optional[uuid.UUID] = None
    title: str
    topic_scope: Dict[str, Any]
    questions: List[Dict[str, Any]] = Field(default_factory=list)
    user_answers: Dict[str, Any] = Field(default_factory=dict)
    evaluation_results: Dict[str, Any] = Field(default_factory=dict)
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}
