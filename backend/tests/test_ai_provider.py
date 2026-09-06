import pytest
from httpx import AsyncClient
from app.core.config import settings
from app.core.errors import AIProviderUnavailableError
from app.services.ai_service import (
    get_ai_service,
    MockAIService,
    OllamaAIService,
    OpenAIAIService,
)
from app.services.embedding_service import (
    get_embedding_service,
    MockEmbeddingService,
    OllamaEmbeddingService,
    OpenAIEmbeddingService,
)


@pytest.mark.asyncio
async def test_mock_provider_factory(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "mock")
    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "mock")

    ai_svc = get_ai_service()
    emb_svc = get_embedding_service()

    assert isinstance(ai_svc, MockAIService)
    assert isinstance(emb_svc, MockEmbeddingService)

    ai_health = await ai_svc.health_check()
    emb_health = await emb_svc.health_check()

    assert ai_health["available"] is True
    assert ai_health["provider"] == "mock"
    assert emb_health["available"] is True
    assert emb_health["provider"] == "mock"
    assert emb_health["dimension"] == settings.EMBEDDING_DIMENSION


@pytest.mark.asyncio
async def test_ollama_provider_factory_and_unreachable_handling(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "ollama")
    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "ollama")
    # Use invalid port to guarantee unreachability
    monkeypatch.setattr(settings, "OLLAMA_BASE_URL", "http://localhost:59999")

    ai_svc = get_ai_service()
    emb_svc = get_embedding_service()

    assert isinstance(ai_svc, OllamaAIService)
    assert isinstance(emb_svc, OllamaEmbeddingService)

    # Verify no silent fallback to Mock: raises AIProviderUnavailableError
    with pytest.raises(AIProviderUnavailableError) as exc_info:
        await ai_svc.generate_answer(
            system_prompt="Test prompt",
            messages=[{"role": "user", "content": "Hello"}]
        )
    assert "unavailable" in str(exc_info.value.message).lower()
    assert exc_info.value.status_code == 503

    with pytest.raises(AIProviderUnavailableError) as exc_info_emb:
        await emb_svc.generate_embeddings(["Sample text chunk"])
    assert "unavailable" in str(exc_info_emb.value.message).lower()
    assert exc_info_emb.value.status_code == 503

    # Verify health check reports unavailable safely without crashing
    ai_health = await ai_svc.health_check()
    emb_health = await emb_svc.health_check()

    assert ai_health["available"] is False
    assert ai_health["provider"] == "ollama"
    assert emb_health["available"] is False
    assert emb_health["provider"] == "ollama"


@pytest.mark.asyncio
async def test_ai_health_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/ai/health")
    assert response.status_code == 200
    data = response.json()

    assert "status" in data
    assert "llm_provider" in data
    assert "embedding_provider" in data
    assert "embedding_dimension" in data
    assert data["embedding_dimension"] == settings.EMBEDDING_DIMENSION
