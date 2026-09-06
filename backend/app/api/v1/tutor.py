import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.tutor import (
    CreateStudySessionRequest,
    StudySessionResponse,
    TutorTurnRequest,
    TutorHintResponse,
    StudySummaryResponse,
    GenerateFlashcardsRequest,
    FlashcardResponse,
    RateFlashcardRequest,
    GenerateQuizRequest,
    SubmitQuizRequest,
    QuizResponse
)
from app.schemas.common import StatusResponse
from app.services.tutor_service import TutorService

router = APIRouter()


@router.post("/sessions", response_model=StudySessionResponse, status_code=status.HTTP_201_CREATED)
async def create_study_session(
    req: CreateStudySessionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Create a new guided AI study/tutor session."""
    service = TutorService(db)
    return await service.create_session(current_user, req)


@router.get("/sessions", response_model=List[StudySessionResponse])
async def list_study_sessions(
    document_id: uuid.UUID = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """List study sessions belonging to authenticated user for a specific document."""
    service = TutorService(db)
    return await service.list_sessions(current_user, document_id)


@router.get("/sessions/{session_id}", response_model=StudySessionResponse)
async def get_study_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get metadata, state, and interaction history for a study session."""
    service = TutorService(db)
    return await service.get_session(current_user, session_id)


@router.post("/sessions/{session_id}/turn", response_model=StudySessionResponse)
async def process_tutor_turn(
    session_id: uuid.UUID,
    req: TutorTurnRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Submit user response or advance state machine turn in tutor session."""
    service = TutorService(db)
    return await service.process_turn(current_user, session_id, req)


@router.post("/sessions/{session_id}/hint", response_model=TutorHintResponse)
async def get_tutor_hint(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Request a progressive hint (Hint 1, 2, 3) for the current active question."""
    service = TutorService(db)
    return await service.get_hint(current_user, session_id)


@router.get("/sessions/{session_id}/summary", response_model=StudySummaryResponse)
async def get_study_session_summary(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Generate comprehensive study summary of user performance vs document evidence."""
    service = TutorService(db)
    return await service.generate_study_summary(current_user, session_id)


@router.delete("/sessions/{session_id}", response_model=StatusResponse)
async def delete_study_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Delete a study session."""
    service = TutorService(db)
    await service.delete_session(current_user, session_id)
    return StatusResponse(success=True, message="Study session deleted successfully.")


@router.post("/flashcards/generate", response_model=List[FlashcardResponse], status_code=status.HTTP_201_CREATED)
async def generate_flashcards(
    req: GenerateFlashcardsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Generate grounded AI study flashcards for document or topic scope."""
    service = TutorService(db)
    return await service.generate_flashcards(current_user, req)


@router.get("/flashcards", response_model=List[FlashcardResponse])
async def list_flashcards(
    document_id: uuid.UUID = Query(...),
    session_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """List flashcards for a document or specific session."""
    service = TutorService(db)
    return await service.list_flashcards(current_user, document_id, session_id)


@router.post("/flashcards/{card_id}/rate", response_model=FlashcardResponse)
async def rate_flashcard(
    card_id: uuid.UUID,
    req: RateFlashcardRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Rate flashcard review (AGAIN, HARD, GOOD, EASY)."""
    service = TutorService(db)
    return await service.rate_flashcard(current_user, card_id, req.rating)


@router.post("/quizzes/generate", response_model=QuizResponse, status_code=status.HTTP_201_CREATED)
async def generate_quiz(
    req: GenerateQuizRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Generate a grounded quiz (MCQ, True/False, Short Answer) with citations."""
    service = TutorService(db)
    return await service.generate_quiz(current_user, req)


@router.get("/quizzes/{quiz_id}", response_model=QuizResponse)
async def get_quiz(
    quiz_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get quiz detail and questions."""
    service = TutorService(db)
    return await service.get_quiz(current_user, quiz_id)


@router.post("/quizzes/{quiz_id}/submit", response_model=QuizResponse)
async def submit_quiz(
    quiz_id: uuid.UUID,
    req: SubmitQuizRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Submit quiz answers for evaluation and score calculation."""
    service = TutorService(db)
    return await service.submit_quiz(current_user, quiz_id, req)
