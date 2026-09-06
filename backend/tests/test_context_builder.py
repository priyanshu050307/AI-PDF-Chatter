import pytest
from app.services.context_builder import ContextBuilder, StructuredContext, estimate_tokens
from app.schemas.chat import ChatIntent


def test_estimate_tokens():
    text = "Hello world! This is a simple test text."
    assert estimate_tokens(text) > 0
    assert estimate_tokens("") == 0


def test_context_builder_basic():
    builder = ContextBuilder()
    ctx = StructuredContext(
        selection_text="Defense in depth uses multiple security controls.",
        page_number=87,
        page_content="Page 87 content detailing security architectures.",
        chapter_title="Network Security",
        section_title="Defense in Depth",
        intent=ChatIntent.EXPLAIN
    )

    prompt, snapshot, citations = builder.build_system_prompt_and_snapshot("Explain this", ctx)

    assert "ACTIVE SELECTION" in prompt
    assert "Defense in depth uses multiple security controls." in prompt
    assert "Page: 87" in prompt
    assert "PRIMARY ACTION INSTRUCTION" in prompt
    assert snapshot["intent"] == "EXPLAIN"
    assert snapshot["page_number"] == 87
    assert snapshot["has_selection"] is True


def test_context_builder_token_budget_pruning():
    # Set low retrieval budget
    builder = ContextBuilder(max_retrieval_tokens=20)

    chunks = [
        {"chunk_id": "c1", "content": "Short chunk 1", "page_start": 1, "page_end": 1},
        {"chunk_id": "c2", "content": "This is a very long chunk 2 that will exceed the max retrieval token budget of 20 tokens easily.", "page_start": 2, "page_end": 2}
    ]

    ctx = StructuredContext(retrieved_chunks=chunks)
    prompt, snapshot, citations = builder.build_system_prompt_and_snapshot("Question", ctx)

    assert snapshot["retrieved_chunks_count"] <= 2
    assert len(citations) <= 2


def test_context_builder_missing_metadata_fallback():
    builder = ContextBuilder()
    ctx = StructuredContext(
        selection_text=None,
        page_number=5,
        page_content="Only page content available",
        chapter_title=None,
        section_title=None,
        intent=ChatIntent.QUESTION
    )

    prompt, snapshot, citations = builder.build_system_prompt_and_snapshot("What is this page about?", ctx)

    assert "CURRENT PAGE CONTEXT" in prompt
    assert "Page: 5" in prompt
    assert snapshot["chapter_title"] is None
    assert snapshot["has_selection"] is False


def test_context_builder_intents():
    builder = ContextBuilder()
    selection = "Cryptographic hashing algorithms transform input data into fixed-size digests."

    # EXPLAIN
    ctx_explain = StructuredContext(selection_text=selection, intent=ChatIntent.EXPLAIN)
    prompt_e, _, _ = builder.build_system_prompt_and_snapshot("Explain this", ctx_explain)
    assert "Explain the active selection" in prompt_e

    # SIMPLIFY
    ctx_simplify = StructuredContext(selection_text=selection, intent=ChatIntent.SIMPLIFY)
    prompt_s, _, _ = builder.build_system_prompt_and_snapshot("Simplify this", ctx_simplify)
    assert "beginner-friendly" in prompt_s

    # EXAMPLE
    ctx_example = StructuredContext(selection_text=selection, intent=ChatIntent.EXAMPLE)
    prompt_ex, _, _ = builder.build_system_prompt_and_snapshot("Give example", ctx_example)
    assert "real-world example" in prompt_ex
