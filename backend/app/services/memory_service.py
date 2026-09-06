import re
import uuid
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from app.core.config import settings
from app.core.logging import logger
from app.models.conversation import Conversation, ChatMessage
from app.services.context_builder import estimate_tokens
from app.services.ai_service import get_ai_service


@dataclass
class ConversationMemory:
    summary: Optional[str] = None
    recent_messages: List[Dict[str, str]] = field(default_factory=list)
    summary_tokens: int = 0
    history_tokens: int = 0
    total_tokens: int = 0


class ConversationMemoryService:
    """
    Dedicated Memory Service to manage conversation persistence, bounded history selection,
    rolling summaries, token budgets, and follow-up reference resolution.
    """

    def __init__(
        self,
        max_history_messages: int = settings.CONVERSATION_MAX_HISTORY_MESSAGES,
        max_history_tokens: int = settings.CONVERSATION_MAX_HISTORY_TOKENS,
        summary_trigger_messages: int = settings.CONVERSATION_SUMMARY_TRIGGER_MESSAGES,
        summary_max_tokens: int = settings.CONVERSATION_SUMMARY_MAX_TOKENS
    ):
        self.max_history_messages = max_history_messages
        self.max_history_tokens = max_history_tokens
        self.summary_trigger_messages = summary_trigger_messages
        self.summary_max_tokens = summary_max_tokens

    def select_recent_history(
        self,
        messages: List[ChatMessage],
        max_messages: Optional[int] = None,
        max_tokens: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        Selects recent conversation messages while strictly respecting
        message count and token budget limits.
        """
        limit_count = max_messages or self.max_history_messages
        limit_tokens = max_tokens or self.max_history_tokens

        # Reverse iterate from most recent
        selected: List[Dict[str, str]] = []
        current_tokens = 0

        for msg in reversed(messages):
            if len(selected) >= limit_count:
                break

            role = "user" if msg.sender.lower() == "user" else "assistant"
            content = msg.content
            msg_tokens = estimate_tokens(content)

            if current_tokens + msg_tokens > limit_tokens:
                # If adding this message exceeds token budget, stop adding older messages
                break

            selected.append({"role": role, "content": content})
            current_tokens += msg_tokens

        # Reverse back to chronological order
        selected.reverse()
        return selected

    def build_memory(
        self,
        conversation: Conversation,
        messages: List[ChatMessage]
    ) -> ConversationMemory:
        """
        Builds structured conversation memory combining rolling summary and bounded recent history.
        """
        summary = conversation.summary
        summary_tokens = estimate_tokens(summary) if summary else 0

        recent_msgs = self.select_recent_history(messages)
        history_tokens = sum(estimate_tokens(m["content"]) for m in recent_msgs)

        return ConversationMemory(
            summary=summary,
            recent_messages=recent_msgs,
            summary_tokens=summary_tokens,
            history_tokens=history_tokens,
            total_tokens=summary_tokens + history_tokens
        )

    def resolve_followup_reference(
        self,
        query: str,
        recent_messages: List[Dict[str, str]],
        active_selection: Optional[str] = None
    ) -> str:
        """
        Resolves ambiguous pronouns/references ("it", "this", "that", "the previous example")
        using recent turns or active selection context.
        """
        if not recent_messages:
            return query

        query_lower = query.lower()
        ambiguous_patterns = [
            r"\bit\b", r"\bthis\b", r"\bthat\b", r"\bthey\b", r"\bthese\b",
            r"previous example", r"above passage", r"last point", r"why is it", r"how does that"
        ]

        is_ambiguous = any(re.search(pat, query_lower) for pat in ambiguous_patterns)
        if not is_ambiguous:
            return query

        # Find last non-trivial message content
        last_turn = recent_messages[-1]["content"] if recent_messages else ""
        if len(last_turn) > 200:
            last_turn = last_turn[:200] + "..."

        resolution_hint = f"[Conversation context reference: Question '{query}' refers to topic discussed in prior turn: '{last_turn}']"
        return f"{query}\n\n{resolution_hint}"

    async def generate_summary(
        self,
        conversation_title: str,
        messages: List[ChatMessage]
    ) -> str:
        """Generates a concise, rolling summary of conversation history using AI Service."""
        ai_service = get_ai_service()
        system_prompt = (
            "You are a conversation summarizer. Create a concise, factual summary of the discussion. "
            "Focus on key topics discussed, main questions asked, and conclusions. Do NOT invent facts. "
            "Keep the summary under 200 words."
        )

        formatted_messages = []
        for m in messages:
            role = "User" if m.sender.lower() == "user" else "Assistant"
            formatted_messages.append(f"{role}: {m.content}")

        dialogue_text = "\n".join(formatted_messages)

        prompt_input = [
            {"role": "user", "content": f"Summarize the following conversation about '{conversation_title}':\n\n{dialogue_text}"}
        ]

        try:
            res = await ai_service.generate_answer(system_prompt, prompt_input)
            return res.get("content", "").strip()
        except Exception as e:
            logger.error(f"Error generating conversation summary: {e}")
            raise e
