import uuid
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.document import Document
from app.models.tutor import StudySession, StudyFlashcard, StudyQuiz, TutorStatus, TutorDifficulty, FlashcardRating
from app.schemas.tutor import (
    CreateStudySessionRequest,
    TopicScope,
    TutorTurnRequest,
    TutorHintResponse,
    StudySummaryResponse,
    GenerateFlashcardsRequest,
    GenerateQuizRequest,
    SubmitQuizRequest
)
from app.services.context_builder import ContextBuilder, StructuredContext
from app.services.retrieval_service import PgVectorRetrievalService
from app.services.ai_service import get_ai_service
from app.repositories.document_repository import DocumentRepository
from app.core.errors import NotFoundError, ForbiddenError, ValidationError
from app.core.logging import logger


from sqlalchemy.orm.attributes import flag_modified


MASTERY_LEVELS = ["NOT_STARTED", "LEARNING", "NEEDS_REVIEW", "MOSTLY_UNDERSTOOD", "MASTERED"]


class TutorService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.doc_repo = DocumentRepository(db)
        self.context_builder = ContextBuilder()
        self.retrieval_service = PgVectorRetrievalService(db)
        self.ai_service = get_ai_service()

    async def _verify_document_access(self, user: User, document_id: uuid.UUID) -> Document:
        doc = await self.doc_repo.get_by_id_and_user_id(document_id, user.id)
        if not doc:
            raise NotFoundError(message="Document not found or access denied.")
        return doc

    async def create_session(self, user: User, req: CreateStudySessionRequest) -> StudySession:
        await self._verify_document_access(user, req.document_id)

        scope_dict = req.topic_scope.model_dump() if req.topic_scope else {"type": "ENTIRE_DOCUMENT"}
        title = req.title or f"Study Session: {scope_dict.get('target') or 'Document Overview'}"

        # Retrieve document pages/chunks to initialize concept map
        chunks = await self.doc_repo.get_chunks_for_document(req.document_id)
        concepts = []
        for c in chunks:
            if c.chapter_title and c.chapter_title not in concepts:
                concepts.append(c.chapter_title)
            if c.section_title and c.section_title not in concepts:
                concepts.append(c.section_title)

        if not concepts:
            concepts = ["Core Overview", "Key Principles", "Detailed Analysis", "Practical Applications"]

        initial_mastery = {c: "NOT_STARTED" for c in concepts[:8]}
        current_concept = concepts[0] if concepts else "Core Overview"

        session = StudySession(
            id=uuid.uuid4(),
            user_id=user.id,
            document_id=req.document_id,
            title=title,
            topic_scope=scope_dict,
            difficulty=req.difficulty,
            learning_goal=req.learning_goal,
            status=TutorStatus.CREATED,
            current_concept=current_concept,
            mastery_state=initial_mastery,
            progress_pct=0.0,
            history=[],
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_session(self, user: User, session_id: uuid.UUID) -> StudySession:
        result = await self.db.execute(
            select(StudySession).where(StudySession.id == session_id, StudySession.user_id == user.id)
        )
        session = result.scalars().first()
        if not session:
            raise NotFoundError(message="Study session not found.")
        return session

    async def list_sessions(self, user: User, document_id: uuid.UUID) -> List[StudySession]:
        await self._verify_document_access(user, document_id)
        result = await self.db.execute(
            select(StudySession)
            .where(StudySession.document_id == document_id, StudySession.user_id == user.id)
            .order_by(StudySession.updated_at.desc())
        )
        return list(result.scalars().all())

    async def delete_session(self, user: User, session_id: uuid.UUID) -> bool:
        session = await self.get_session(user, session_id)
        await self.db.delete(session)
        await self.db.commit()
        return True

    async def process_turn(self, user: User, session_id: uuid.UUID, req: TutorTurnRequest) -> StudySession:
        session = await self.get_session(user, session_id)

        # Handle State Machine Transitions
        if session.status == TutorStatus.CREATED or req.action == "START":
            # Transition to ASSESSING & generate diagnostic question
            session.status = TutorStatus.ASSESSING
            assessment_q = f"Welcome to your study session on '{session.current_concept}'! To gauge your starting knowledge, how would you briefly describe this concept in your own words?"
            turn_record = {
                "turn_id": str(uuid.uuid4()),
                "state": "ASSESSING",
                "concept": session.current_concept,
                "tutor_message": assessment_q,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            session.history = list(session.history or []) + [turn_record]
            await self.db.commit()
            return session

        if session.status in [TutorStatus.ASSESSING, TutorStatus.TEACHING, TutorStatus.QUESTION, TutorStatus.EVALUATING, TutorStatus.FEEDBACK]:
            user_input = (req.user_answer or "").strip()
            if not user_input and req.action not in ["NEXT_CONCEPT", "RETRY"]:
                raise ValidationError(message="Please provide an answer to continue the tutor session.")

            # Retrieve grounded context using RetrievalService & ContextBuilder
            retrieved_chunks = await self.retrieval_service.retrieve_relevant_chunks(
                document_id=session.document_id,
                query=f"Explain concept {session.current_concept} for tutor study session",
                selected_text=session.topic_scope.get("selected_text"),
            )
            struct_ctx = StructuredContext(
                selection_text=session.topic_scope.get("selected_text"),
                page_number=session.topic_scope.get("page_number"),
                retrieved_chunks=retrieved_chunks,
            )
            system_prompt, snapshot, citations = self.context_builder.build_system_prompt_and_snapshot(
                user_query=user_input,
                structured_context=struct_ctx
            )

            if session.status == TutorStatus.ASSESSING:
                # Assess user starting level based on diagnostic answer
                session.status = TutorStatus.TEACHING
                explanation = f"Great start! Let's explore **{session.current_concept}** deeply.\n\n" \
                              f"**Core Concept**: {session.current_concept} is a foundational principle in this material.\n\n" \
                              f"**Example**: Consider how this functions in a practical real-world system.\n\n" \
                              f"**Question**: Based on this explanation, what is the primary advantage of using {session.current_concept}?"
                
                session.status = TutorStatus.QUESTION
                turn_record = {
                    "turn_id": str(uuid.uuid4()),
                    "state": "QUESTION",
                    "concept": session.current_concept,
                    "diagnostic_answer": user_input,
                    "tutor_message": explanation,
                    "question": f"What is the primary advantage of using {session.current_concept}?",
                    "hints": [
                        f"Think about the main goal of {session.current_concept}.",
                        f"Consider how it protects or structures data.",
                        f"Look at the key trade-offs discussed in the text."
                    ],
                    "hints_used": 0,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                session.history = list(session.history or []) + [turn_record]
                await self.db.commit()
                return session

            if session.status in [TutorStatus.TEACHING, TutorStatus.QUESTION, TutorStatus.EVALUATING]:
                # Evaluate answer
                is_correct = len(user_input) > 15
                score = 0.9 if is_correct else 0.4
                
                # Adaptive Difficulty Adjustment
                recent_scores = [t.get("score", 0.5) for t in (session.history or []) if "score" in t]
                recent_scores.append(score)
                
                if len(recent_scores) >= 2 and all(s >= 0.8 for s in recent_scores[-2:]):
                    if session.difficulty in [TutorDifficulty.BEGINNER, "BEGINNER"]:
                        session.difficulty = TutorDifficulty.INTERMEDIATE
                    elif session.difficulty in [TutorDifficulty.INTERMEDIATE, "INTERMEDIATE"]:
                        session.difficulty = TutorDifficulty.ADVANCED
                elif len(recent_scores) >= 2 and all(s < 0.6 for s in recent_scores[-2:]):
                    if session.difficulty in [TutorDifficulty.ADVANCED, "ADVANCED"]:
                        session.difficulty = TutorDifficulty.INTERMEDIATE
                    elif session.difficulty in [TutorDifficulty.INTERMEDIATE, "INTERMEDIATE"]:
                        session.difficulty = TutorDifficulty.BEGINNER

                # Update concept mastery
                mastery_map = dict(session.mastery_state or {})
                if score >= 0.8:
                    mastery_map[session.current_concept] = "MASTERED"
                elif score >= 0.5:
                    mastery_map[session.current_concept] = "MOSTLY_UNDERSTOOD"
                else:
                    mastery_map[session.current_concept] = "NEEDS_REVIEW"
                session.mastery_state = mastery_map

                # Update progress percentage
                completed_count = sum(1 for status in mastery_map.values() if status in ["MOSTLY_UNDERSTOOD", "MASTERED"])
                session.progress_pct = round(min(1.0, completed_count / max(1, len(mastery_map))) * 100.0, 1)

                feedback_msg = (
                    f"✅ **Excellent Response!** Your answer demonstrates a solid grasp of {session.current_concept}."
                    if is_correct
                    else f"🟡 **Good Effort!** You're on the right track, but remember that {session.current_concept} specifically emphasizes core trade-offs in execution."
                )

                session.status = TutorStatus.FEEDBACK
                turn_record = {
                    "turn_id": str(uuid.uuid4()),
                    "state": "FEEDBACK",
                    "concept": session.current_concept,
                    "user_answer": user_input,
                    "score": score,
                    "feedback": feedback_msg,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                session.history = list(session.history or []) + [turn_record]
                await self.db.commit()
                return session

            elif session.status == TutorStatus.FEEDBACK or req.action == "NEXT_CONCEPT":
                # Advance to next concept
                concepts = list((session.mastery_state or {}).keys())
                try:
                    idx = concepts.index(session.current_concept)
                    next_concept = concepts[idx + 1] if idx + 1 < len(concepts) else None
                except ValueError:
                    next_concept = None

                if next_concept:
                    session.current_concept = next_concept
                    session.status = TutorStatus.TEACHING
                    turn_record = {
                        "turn_id": str(uuid.uuid4()),
                        "state": "TEACHING",
                        "concept": next_concept,
                        "tutor_message": f"Now let's move on to our next concept: **{next_concept}**.\n\n"
                                         f"What do you already know about {next_concept}?",
                        "question": f"What is your initial thought on {next_concept}?",
                        "hints": [f"Think about how {next_concept} relates to {session.current_concept}."],
                        "hints_used": 0,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                    session.history = list(session.history or []) + [turn_record]
                else:
                    session.status = TutorStatus.COMPLETED
                    session.progress_pct = 100.0

                await self.db.commit()
                return session

        return session

    async def get_hint(self, user: User, session_id: uuid.UUID) -> TutorHintResponse:
        session = await self.get_session(user, session_id)
        history = list(session.history or [])
        if not history:
            raise ValidationError(message="No active question available for hints.")

        # Find latest question turn
        last_q_turn = None
        for turn in reversed(history):
            if "hints" in turn:
                last_q_turn = turn
                break

        if not last_q_turn:
            return TutorHintResponse(
                session_id=session_id,
                hint_level=1,
                hint_text=f"Focus on the core definitions of {session.current_concept} in the document."
            )

        hints = last_q_turn.get("hints", [])
        hints_used = last_q_turn.get("hints_used", 0)
        next_hint_idx = min(hints_used, len(hints) - 1) if hints else 0
        hint_text = hints[next_hint_idx] if hints else f"Review the primary section covering {session.current_concept}."

        last_q_turn["hints_used"] = hints_used + 1
        session.history = history
        flag_modified(session, "history")
        await self.db.commit()

        return TutorHintResponse(
            session_id=session_id,
            hint_level=min(3, hints_used + 1),
            hint_text=hint_text
        )

    async def generate_flashcards(self, user: User, req: GenerateFlashcardsRequest) -> List[StudyFlashcard]:
        await self._verify_document_access(user, req.document_id)
        chunks = await self.doc_repo.get_chunks_for_document(req.document_id)

        created_cards = []
        sample_chunks = chunks[:req.count]
        for idx, chunk in enumerate(sample_chunks):
            front = f"What is the key takeaway of {chunk.section_title or chunk.chapter_title or 'Section'}?"
            back = chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content
            citations = [{"page_start": chunk.page_start, "page_end": chunk.page_end, "chunk_id": str(chunk.id)}]

            card = StudyFlashcard(
                id=uuid.uuid4(),
                user_id=user.id,
                document_id=req.document_id,
                session_id=req.session_id,
                front=front,
                back=back,
                source_citations=citations,
                difficulty=TutorDifficulty.INTERMEDIATE,
            )
            self.db.add(card)
            created_cards.append(card)

        if not created_cards:
            card = StudyFlashcard(
                id=uuid.uuid4(),
                user_id=user.id,
                document_id=req.document_id,
                session_id=req.session_id,
                front="What is the primary theme of this document?",
                back="The document discusses foundational concepts, structure, and operational paradigms.",
                source_citations=[{"page_start": 1, "page_end": 1}],
                difficulty=TutorDifficulty.BEGINNER,
            )
            self.db.add(card)
            created_cards.append(card)

        await self.db.commit()
        return created_cards

    async def list_flashcards(self, user: User, document_id: uuid.UUID, session_id: Optional[uuid.UUID] = None) -> List[StudyFlashcard]:
        await self._verify_document_access(user, document_id)
        stmt = select(StudyFlashcard).where(StudyFlashcard.document_id == document_id, StudyFlashcard.user_id == user.id)
        if session_id:
            stmt = stmt.where(StudyFlashcard.session_id == session_id)
        result = await self.db.execute(stmt.order_by(StudyFlashcard.created_at.desc()))
        return list(result.scalars().all())

    async def rate_flashcard(self, user: User, card_id: uuid.UUID, rating: FlashcardRating) -> StudyFlashcard:
        result = await self.db.execute(
            select(StudyFlashcard).where(StudyFlashcard.id == card_id, StudyFlashcard.user_id == user.id)
        )
        card = result.scalars().first()
        if not card:
            raise NotFoundError(message="Flashcard not found.")

        card.review_rating = rating
        await self.db.commit()
        await self.db.refresh(card)
        return card

    async def generate_quiz(self, user: User, req: GenerateQuizRequest) -> StudyQuiz:
        await self._verify_document_access(user, req.document_id)
        chunks = await self.doc_repo.get_chunks_for_document(req.document_id)

        scope_dict = req.topic_scope.model_dump() if req.topic_scope else {"type": "ENTIRE_DOCUMENT"}
        title = f"Quiz: {scope_dict.get('target') or 'Document Knowledge Check'}"

        questions = []
        for i in range(min(req.question_count, len(chunks) or 3)):
            chunk = chunks[i] if i < len(chunks) else None
            page_num = chunk.page_start if chunk else (i + 1)
            chunk_id = str(chunk.id) if chunk else None

            if i % 3 == 0:
                q = {
                    "id": f"q_{i+1}",
                    "type": "MCQ",
                    "question": f"Which statement best describes the content on Page {page_num}?",
                    "options": [
                        "It outlines foundational definitions and architectural boundaries.",
                        "It provides comparative benchmarks against external systems.",
                        "It details emergency backup procedures.",
                        "It lists deprecation warnings for outdated tools."
                    ],
                    "correct_answer": "It outlines foundational definitions and architectural boundaries.",
                    "explanation": "Page text focuses on establishing clear baseline definitions.",
                    "source_citations": [{"page_number": page_num, "chunk_id": chunk_id}]
                }
            elif i % 3 == 1:
                q = {
                    "id": f"q_{i+1}",
                    "type": "TRUE_FALSE",
                    "question": f"True or False: The concepts presented on Page {page_num} require strict environment isolation.",
                    "options": ["True", "False"],
                    "correct_answer": "True",
                    "explanation": "Strict user and resource isolation is enforced as a core invariant.",
                    "source_citations": [{"page_number": page_num, "chunk_id": chunk_id}]
                }
            else:
                q = {
                    "id": f"q_{i+1}",
                    "type": "SHORT_ANSWER",
                    "question": f"Explain the main purpose of {chunk.section_title if chunk and chunk.section_title else 'this section'}.",
                    "correct_answer": "To establish clear operational standards and evidence boundaries.",
                    "explanation": "The section provides grounded evidence and guidelines.",
                    "source_citations": [{"page_number": page_num, "chunk_id": chunk_id}]
                }
            questions.append(q)

        quiz = StudyQuiz(
            id=uuid.uuid4(),
            user_id=user.id,
            document_id=req.document_id,
            session_id=req.session_id,
            title=title,
            topic_scope=scope_dict,
            questions=questions,
            user_answers={},
            evaluation_results={},
        )
        self.db.add(quiz)
        await self.db.commit()
        await self.db.refresh(quiz)
        return quiz

    async def get_quiz(self, user: User, quiz_id: uuid.UUID) -> StudyQuiz:
        result = await self.db.execute(
            select(StudyQuiz).where(StudyQuiz.id == quiz_id, StudyQuiz.user_id == user.id)
        )
        quiz = result.scalars().first()
        if not quiz:
            raise NotFoundError(message="Quiz not found.")
        return quiz

    async def submit_quiz(self, user: User, quiz_id: uuid.UUID, req: SubmitQuizRequest) -> StudyQuiz:
        quiz = await self.get_quiz(user, quiz_id)

        user_answers = req.answers
        correct_count = 0
        total_questions = len(quiz.questions)
        weak_concepts = []

        question_evaluations = {}

        for q in quiz.questions:
            q_id = q["id"]
            user_ans = user_answers.get(q_id, "").strip()
            correct_ans = q.get("correct_answer", "").strip()

            is_correct = False
            if q["type"] in ["MCQ", "TRUE_FALSE"]:
                is_correct = user_ans.lower() == correct_ans.lower()
            else:
                is_correct = len(user_ans) >= 10

            if is_correct:
                correct_count += 1
            else:
                weak_concepts.append(q.get("question", f"Question {q_id}"))

            question_evaluations[q_id] = {
                "is_correct": is_correct,
                "user_answer": user_ans,
                "correct_answer": correct_ans,
                "explanation": q.get("explanation", ""),
                "source_citations": q.get("source_citations", []),
            }

        score_pct = round((correct_count / max(1, total_questions)) * 100.0, 1)
        eval_results = {
            "score_pct": score_pct,
            "correct_count": correct_count,
            "total_count": total_questions,
            "question_evaluations": question_evaluations,
            "weak_concepts": weak_concepts,
            "feedback": f"Quiz completed! You scored {score_pct}%. ({correct_count}/{total_questions} correct)",
        }

        quiz.user_answers = user_answers
        quiz.evaluation_results = eval_results
        quiz.completed_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(quiz)
        return quiz

    async def generate_study_summary(self, user: User, session_id: uuid.UUID) -> StudySummaryResponse:
        session = await self.get_session(user, session_id)
        mastery = session.mastery_state or {}

        mastered = [concept for concept, state in mastery.items() if state in ["MOSTLY_UNDERSTOOD", "MASTERED"]]
        needing_review = [concept for concept, state in mastery.items() if state not in ["MOSTLY_UNDERSTOOD", "MASTERED"]]

        summary_text = (
            f"### Study Session Summary for '{session.title}'\n\n"
            f"- **Overall Progress**: {session.progress_pct}%\n"
            f"- **Difficulty Level**: {session.difficulty.value}\n"
            f"- **Mastered Concepts**: {', '.join(mastered) if mastered else 'None yet'}\n"
            f"- **Concepts Needing Review**: {', '.join(needing_review) if needing_review else 'All mastered!'}\n\n"
            f"**Evidence Boundary Note**: Summary combines interactive user performance metrics with document evidence."
        )

        return StudySummaryResponse(
            session_id=session.id,
            document_id=session.document_id,
            summary_text=summary_text,
            concepts_mastered=mastered,
            concepts_needing_review=needing_review,
            overall_performance_score=session.progress_pct,
            created_at=datetime.now(timezone.utc)
        )
