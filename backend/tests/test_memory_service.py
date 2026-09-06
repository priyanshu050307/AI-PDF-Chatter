import uuid
import pytest
from app.services.memory_service import ConversationMemoryService
from app.models.conversation import Conversation, ChatMessage
from app.schemas.chat import ChatIntent


def test_select_recent_history_bounded():
    memory_svc = ConversationMemoryService(max_history_messages=4, max_history_tokens=100)

    messages = [
        ChatMessage(sender="user", content="Question 1"),
        ChatMessage(sender="assistant", content="Answer 1"),
        ChatMessage(sender="user", content="Question 2"),
        ChatMessage(sender="assistant", content="Answer 2"),
        ChatMessage(sender="user", content="Question 3"),
        ChatMessage(sender="assistant", content="Answer 3"),
    ]

    selected = memory_svc.select_recent_history(messages)

    assert len(selected) == 4
    assert selected[0]["content"] == "Question 2"
    assert selected[3]["content"] == "Answer 3"


def test_select_recent_history_token_budget_cap():
    memory_svc = ConversationMemoryService(max_history_messages=10, max_history_tokens=30)

    messages = [
        ChatMessage(sender="user", content="First question"),
        ChatMessage(sender="assistant", content="This is a very long detailed answer that will take up many tokens and exceed budget. " * 5),
        ChatMessage(sender="user", content="Short Q"),
        ChatMessage(sender="assistant", content="Short A"),
    ]

    selected = memory_svc.select_recent_history(messages)

    # Should only take Short Q and Short A because adding long detailed answer exceeds token budget of 30
    assert len(selected) <= 3
    assert selected[-1]["content"] == "Short A"


def test_resolve_followup_reference():
    memory_svc = ConversationMemoryService()

    recent = [
        {"role": "user", "content": "Explain asymmetric encryption."},
        {"role": "assistant", "content": "Asymmetric encryption uses public and private key pairs for secure data transfer."}
    ]

    # Non-ambiguous query
    q1 = memory_svc.resolve_followup_reference("What is symmetric encryption?", recent)
    assert "reference" not in q1

    # Ambiguous query with "it"
    q2 = memory_svc.resolve_followup_reference("Why is it slower than symmetric encryption?", recent)
    assert "[Conversation context reference:" in q2
    assert "Asymmetric encryption" in q2


@pytest.mark.asyncio
async def test_generate_summary_mock():
    memory_svc = ConversationMemoryService()

    messages = [
        ChatMessage(sender="user", content="What is defense in depth?"),
        ChatMessage(sender="assistant", content="Defense in depth is a layered security approach."),
        ChatMessage(sender="user", content="Give an example."),
        ChatMessage(sender="assistant", content="An example is using firewalls, multi-factor authentication, and endpoint encryption.")
    ]

    summary = await memory_svc.generate_summary("Cybersecurity", messages)
    assert len(summary) > 0
